#!/usr/bin/env python3
#
# Copyright 2016 (c) Avital Kelman
#
# Exfiltrate documents from http://anom.archivesnationales.culture.gouv.fr
# without their filthy Java applet.
# This is the exfiltrator component.
#
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
# Usage:
# python3 exfiltrate.py <document_url> [first_page] [last_page]
# or
# import exfiltrate
# e = exfiltrate.Exfiltrator(<document_url>, [local_storage_prefix])
# e.fetch_thumbnail(page, [no_save=BOOL])
# e.fetch_page(page, [no_save=BOOL])
# e.exfiltrate(start_page, end_page)
#
#

import concurrent.futures
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback
import urllib.request
import xml.etree.ElementTree as ET
from collections import OrderedDict
from html.parser import HTMLParser
from socket import timeout
from urllib.parse import quote, unquote

sys.dont_write_bytecode = True


class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.params = {}
        self.has_applet = False
        self.record = False

    def handle_starttag(self, tag, attrs):
        if tag == 'param':
            par = dict(attrs)
            self.params[par['name']] = par['value']
        elif tag == 'applet':
            self.has_applet = True
        elif tag == 'strong':
            self.record = True
        else:
            return

    def handle_data(self, data):
        if self.record:
            self.params['title'] = data
            self.record = False


def subproc_noconsole(cmd):
    startupinfo = None
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    subprocess.check_call(cmd,
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL,
                          stdin=subprocess.DEVNULL,
                          startupinfo=startupinfo)


def human_readable_file_size(size, precision=2):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
    suffix_index = 0
    while size >= 1024 and suffix_index < 4:
        suffix_index += 1  # increment the index of the suffix
        size = size/1024.0  # apply the division
    f = "%.*f" % (precision, size)
    return "%s %s" % (f.rstrip('0').rstrip('.'), suffixes[suffix_index])


class Templates(object):
    @property
    def thumbnail(self):
        return ("<div style='padding-right: 0.5em; padding-left: 0.5em;'>"
                "<a href='%%URL%%' onclick=\""
                "document.getElementById('bg').style.display='inline';"
                "document.getElementById('image').style.display='none';"
                "document.getElementById('image').src='%%URL%%';"
                "document.getElementById('pagenum').innerHTML='%%REF%%<br>';"
                "return false;"
                "\">%%REF%%<br><img src='%%THUMB%%' width='100%'></a>"
                "</div><hr>")

    @property
    def html(self):
        return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
                "<title>ANOM Exfiltrator</title></head><body>%%BODY%%</body>"
                "</html>")

    @property
    def frames_body(self):
        return ("<div id='content'><div id='left'>%%THUMBNAILS%%</div>"
                "<div id='right'><span id='pagenum'></span>Title: %%TITLE%%"
                "<br>"
                "<img id='bg' style='display:none' src='loading.gif'>"
                "<img id='image' src=''"
                "onload=\"document.getElementById('bg').style.display='none';"
                "this.style.display='inline';\">"
                "</div></div>")

    @property
    def frames_style(self):
        return ("<style>html,body"
                "{font-size:14pt; height: 100%; overflow: hidden; margin: 0;}"
                "#content {height: 100%;}"
                "#left {float: left; min-width: 120px; width:8%; height: 100%;"
                "overflow: auto; box-sizing: border-box;}"
                "#right {height: 100%; overflow: auto;"
                "box-sizing: border-box; padding-left: 0.5em;}"
                "img {background: url('loading.gif') no-repeat;}"
                "</style>")


Templates = Templates()  # properties only work on instances


class Exfiltrator(object):
    ANOM = "http://anom.archivesnationales.culture.gouv.fr"

    def __init__(self, url, storage_prefix="exfiltrated_documents"):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self._storage_prefix = storage_prefix
        self._quit = False
        self._url = url.replace(" ", "%20")
        self.pages_to_fetch = OrderedDict()
        self.xml_docs = OrderedDict()

    def die(self):
        self._quit = True
        self._executor.shutdown(False)

    def safe_filename(self, filename):
        return re.sub(r'[^\w\-_\.\(\)]', '_', unquote(filename))

    def fetch_applet_page(self):
        applet_page = self.fetch_url(self._url)
        parser = MyHTMLParser()
        parser.feed(applet_page.decode('utf-8'))

        if not parser.has_applet:
            raise Exception("No Applet Found Here")

        self.doc_url = parser.params['docUrl']
        self._document = parser.params.get('metadata')
        if not self._document:
            self._document = parser.params.get('title')
        self._storagesubdir = self.safe_filename(self._document)
        if parser.params.get('from'):
            if len(self._storagesubdir) > 80:
                f = parser.params['from'].rsplit('/', 1)[-1][:-1]
                self._storagesubdir = self.safe_filename(f)
            digits = int(parser.params['nbnum'])
            page_pat = "%" + ("0%dd_img.xml" % digits)
            for i in range(int(parser.params['min']),
                           int(parser.params['max']) + 1):
                self.xml_docs[i] = {
                        'pagenum': i,
                        'url': quote(self.doc_url + parser.params['from']
                                     + (page_pat % i))
                    }
        else:
            for i in range(1, 1 + int(parser.params['nbpage'])):
                self.xml_docs[i] = {
                        'pagenum': i,
                        'url': quote(self.doc_url + parser.params["page%d" % i]
                                     + "_img.xml")
                    }

    def fetch_xml_doc(self, doc):
        if doc['pagenum'] in self.pages_to_fetch:
            return self.pages_to_fetch[doc['pagenum']]
        res = self.fetch_url(self.ANOM + doc['url'])
        path = doc['url']
        doc_xml = ET.fromstring(res)
        layers = list(doc_xml.find('layers'))

        def layer_sorted(l):
            s = l.find('image').find('ATiledImage').find('size')
            return int(s.get('width')) * int(s.get('height'))

        layers.sort(key=layer_sorted, reverse=True)
        big = layers[0].find('image').find('ATiledImage')
        small = layers[-1].find('image').find('ATiledImage')

        big_path = big.get('tileStreamSpecTemplate')[1:]
        small_path = small.get('tileStreamSpecTemplate')[1:] % (0, 0)
        thumb_path = path.replace('img.xml', 'tnl.jpg')

        big_x = math.ceil(int(big.find('size').get('width'))
                          / int(big.find('tileSize').get('width')))
        big_y = math.ceil(int(big.find('size').get('height'))
                          / int(big.find('tileSize').get('height')))

        self.pages_to_fetch[doc['pagenum']] = {
                'basedir': path.rsplit('/', 1)[0],
                'big_pattern': big_path, 'small': small_path,
                'x': big_x, 'y': big_y, 'thumb': thumb_path,
                'pagenum': doc['pagenum'],
                'out': self.safe_filename(path).replace('_img.xml', ''),
                'sanithumb': self.safe_filename(thumb_path)[1:]
            }
        return self.pages_to_fetch[doc['pagenum']]

    def prefetch_xml_docs(self):
        self.pages_to_fetch = OrderedDict()

        pool = [
            self._executor.submit(self.fetch_xml_doc, d)
            for d in self.xml_docs.values()
        ]
        for f in concurrent.futures.as_completed(pool):
            print(".", end="")
            sys.stdout.flush()
        print("")
        self.pages_to_fetch = OrderedDict(sorted(self.pages_to_fetch.items(),
                                          key=lambda x: x[1]['pagenum']))

    @property
    def _storagedir(self):
        return os.path.join(self._storage_prefix, self._storagesubdir)

    def exit_if_quit(self):
        if self._quit:
            sys.exit()

    def cleanup(self, path):
        try:
            shutil.rmtree(path, ignore_errors=True)
        finally:
            return

    def generate_viewer(self, url_postfix=""):
        thumbnails = ""
        for page in self.xml_docs.values():
            p = self.safe_filename(page['url'].replace('_img.xml', ''))[1:]
            thumb = Templates.thumbnail.replace("%%URL%%", p + ".jpg"
                                                + url_postfix)
            thumb = thumb.replace("%%THUMB%%", "thumbs/"+p+"_tnl.jpg"
                                  + url_postfix)
            thumb = thumb.replace("%%REF%%", "Page "+str(page['pagenum']))
            thumbnails += thumb
        html = Templates.html
        html = html.replace("<head>", "<head>" + Templates.frames_style)
        html = html.replace("%%BODY%%", Templates.frames_body)
        html = html.replace("%%TITLE%%", self._document)
        html = html.replace("%%THUMBNAILS%%", thumbnails)
        return html

    def fetch_thumbnail(self, page, no_save=False):
        # These run inside concurrent futures, so check for a terminated main.
        self.exit_if_quit()
        storage = os.path.join(self._storagedir, "thumbs")

        url = self.ANOM + page['basedir'] + page['small']
        fallback = self.ANOM + page['thumb']
        thumbpath = os.path.join(storage, page['sanithumb'])
        tofile = os.path.join(storage,
                              page['sanithumb'].replace('.jpg', '.JP2'))

        # skip completed thumbnails, but try the actual thumbnail as fallback
        # in case zoom 16 doesn't exist for this page
        while not os.path.exists(thumbpath):
            try:
                if no_save and url.endswith(".jpg"):
                    return self.fetch_url(url)
                else:
                    self.fetch_to_file(url, tofile)
                    if tofile.endswith(".JP2"):
                        subproc_noconsole(
                            ["gm", "mogrify", "-format", "jpg", tofile]
                        )
                        os.remove(tofile)
                    f = open(thumbpath, "rb").read()
                    if no_save:
                        os.remove(thumbpath)
                    return f
            except urllib.error.HTTPError as e:
                if e.code == 404 and url != fallback:
                    url = fallback
                    tofile = thumbpath
                else:
                    raise
            except Exception as e:
                print(str(e))
                traceback.print_exc()
                os._exit(1)

    def fetch_all_thumbnails(self):
        os.makedirs(os.path.join(self._storagedir, "thumbs"), exist_ok=True)
        pool = [
            self._executor.submit(self.fetch_thumbnail, page)
            for page in self.pages_to_fetch.values()
        ]
        for f in concurrent.futures.as_completed(pool):
            print(".", end="")
            sys.stdout.flush()
        print("")

    def fetch_url(self, url):
        retries = 0
        while True:
            self.exit_if_quit()
            try:
                with urllib.request.urlopen(url, None, 20) as r:
                    return r.read()
            except Exception as e:
                print(url, e)
                if retries < 10:
                    retries += 1
                    print("Network error. Retrying [%d of 10]." % retries)
                    time.sleep(5)
                    continue
                else:
                    break

    def fetch_to_file(self, url, to_file):
        file_dir = os.path.dirname(to_file)
        os.makedirs(file_dir, exist_ok=True)
        # don't download twice, but retry on timeouts
        while not os.path.exists(to_file):
            try:
                with open(to_file, 'wb') as of:
                    of.write(self.fetch_url(url))
            except timeout:
                continue

    def fetch_tile(self, url, destdir):
        dest = os.path.join(destdir, self.safe_filename(url))
        try:
            self.fetch_to_file(self.ANOM + url, dest)
        except urllib.error.HTTPError as e:
            print(str(e))
            raise
        return dest

    def fetch_page(self, page, no_save=False):
        storage = self._storagedir

        page_file = os.path.join(storage, page['out'][1:] + ".jpg")

        print(
            "Looking for " + self._document + " page " + str(page['pagenum'])
            + "."
        )

        # don't download and assemble completed pages
        if not os.path.exists(page_file):
            # Pages are composed of sub-image tiles, like a slippy map.
            # Make a temporary dir for all of the pieces.
            tmpdir = os.path.join(storage, page['out'])
            os.makedirs(tmpdir, exist_ok=True)

            numpieces = page['x'] * page['y']
            print("Fetching " + str(numpieces) + " pieces of page "
                  + str(page['pagenum']) + ".")

            tiles_to_fetch = []
            for y in range(0, page['y']):
                for x in range(0, page['x']):
                    tiles_to_fetch.append(page['basedir']
                                          + (page['big_pattern'] % (y, x)))

            successful_downloads = []

            pool = [
                self._executor.submit(self.fetch_tile, tile, tmpdir)
                for tile in tiles_to_fetch
            ]
            for f in concurrent.futures.as_completed(pool):
                successful_downloads.append(f.result())
                print(".", end="")
                sys.stdout.flush()

            print("")
            print("Assembling page %d." % page['pagenum'])
            successful_downloads.sort()
            try:
                # GraphicsMagick Montage is perfect for reassembling the tiles
                subproc_noconsole(
                    [
                        "gm", "montage", "-mode", "concatenate", "-quality",
                        "85", "-tile", "%dx%d" % (page['x'], page['y'])
                    ]
                    + successful_downloads + [page_file]
                )
            except:
                try:
                    os.remove(page_file)
                except:
                    pass
                raise
            finally:
                # Clean up downloaded tile images for the assembled page.
                self.cleanup(tmpdir)

        f = open(page_file, "rb").read()
        print("Finished page " + str(page['pagenum'])
              + ". [Size: " + human_readable_file_size(len(f)) + "]")
        if no_save:
            os.remove(page_file)
        return f

    def fetch_desired_pages(self, start=None, end=None):
        if not start:
            start = list(self.pages_to_fetch.values())[0]['pagenum']
        if not end:
            end = list(self.pages_to_fetch.values())[-1]['pagenum']
        total = 0
        for page in self.pages_to_fetch.values():
            if page['pagenum'] >= start and page['pagenum'] <= end:
                self.exit_if_quit()
                print("")
                total += len(self.fetch_page(page))
                n = page['pagenum'] - start + 1
                print("Estimated total size of all images: "
                      + human_readable_file_size((total/n) * (end-start)))

    def exfiltrate(self, start=None, end=None):
        print("")
        print("Processing request.")
        print("Run again with the same parameters to resume exfiltration.")

        print("Searching For Document")
        self.fetch_applet_page()
        print("Found.")

        os.makedirs(self._storagedir, exist_ok=True)
        print("Completed files will be put in the " + self._storagedir
              + " folder.")

        # Throw in a HTML viewer
        with open(os.path.join(self._storagedir, "index.html"), "w") as tf:
            tf.write(self.generate_viewer())
        self.exit_if_quit()

        print("Searching For Page Specification Files")
        self.prefetch_xml_docs()
        print("Found.")

        print("Fetching Thumbnails")
        self.fetch_all_thumbnails()
        self.exit_if_quit()
        print("Thumbnails Finished.")

        print("Fetching Pages")
        self.fetch_desired_pages(start, end)

        print("")
        print("Done!")
        print("Look in the " + self._storagedir + " folder.")


if __name__ == '__main__':
    start = None
    end = None
    if len(sys.argv) > 2:
        start = int(sys.argv[2])
        end = int(start)
    if len(sys.argv) > 3:
        end = int(sys.argv[3])

    e = Exfiltrator(sys.argv[1])

    def quit(a=None, b=None):
        print("")
        print("Exit!")
        sys.exit(0)
    signal.signal(signal.SIGINT, quit)
    import atexit
    atexit.register(e.die)

    e.exfiltrate(start, end)
