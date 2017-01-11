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
#
#
import sys
sys.dont_write_bytecode = True

from urllib.parse import urlparse, parse_qs
import urllib.request
import os
import subprocess
import shutil
import signal
from socket import timeout
import concurrent.futures

def clearline():
    sys.stdout.write("\033[K")  # clear line

class Templates(object):
    @property
    def thumbnail(self):
        return "<div style='padding-right: 0.5em; padding-left: 0.5em;'>\
                <a href='%%URL%%' onclick=\"\
                document.getElementById('bg').style.display='inline';\
                document.getElementById('image').style.display='none';\
                document.getElementById('image').src='%%URL%%'; return false;\
                \">%%REF%%<br><img src='%%THUMB%%' width='100%'></a>\
                </div><hr>"
    @property
    def html(self):
        return "<!doctype html><html lang='en'><head><meta charset='utf-8'>\
                <title>ANOM Exfiltrator</title></head><body>%%BODY%%</body>\
                </html>"
    @property
    def frames_body(self):
        return "<div id='content'><div id='left'>%%THUMBNAILS%%</div>\
                <div id='right'>%%TITLE%%<br>\
                <img id='bg' style='display:none' src='loading.gif'>\
                <img id='image' src=''\
                onload=\"document.getElementById('bg').style.display='none';\
                this.style.display='inline';\">\
                </div></div>"
    @property
    def frames_style(self):
        return "<style>html,body {font-size:14pt; height: 100%; overflow: hidden; margin: 0;}\
            #content {height: 100%;}"\
            "#left {float: left; min-width: 120px; width:8%; height: 100%; overflow: auto; "\
            "box-sizing: border-box;}"\
            "#right {height: 100%; overflow: auto;"\
            "box-sizing: border-box; padding-left: 0.5em;}"\
            "img {background: url('loading.gif') no-repeat;}"\
            "</style>"

Templates = Templates() # properties only work on instances

class Exfiltrator(object):
    def __init__(self, url, storage_prefix=None):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        self._storage_prefix = storage_prefix
        self._quit = False
        self.setUrl(url)

    def die(self):
        self._quit = True
        self._executor.shutdown(False)

    def setUrl(self, url):
        # the url encodes basic document information
        self._url = url
        o = urlparse(self._url)
        qs = parse_qs(o.query)
        self._title = qs['title'][0]
        self._first_page = int(qs['first'][0].rsplit("_", 1)[1])
        self._last_page = qs['last'][0].rsplit("_", 1)[1]
        self._pad = len(self._last_page)
        self._last_page = int(self._last_page)
        try:
            self._document = qs['first'][0].split('/')[1].rsplit("_", 1)[0]
            self._box = qs['first'][0].split('/')[0]
        except:
            self._document = qs['first'][0].rsplit("_", 1)[0]
            self._box = ""
        self._firstpart = o.scheme + "://" + o.netloc + qs['dossier'][0] + self._box
        self._storagedir = self.boxstr + self._document
        if self._storage_prefix:
            self._storagedir = os.path.join(self._storage_prefix, self._storagedir)
        self._cur_page = ""

    @property
    def boxstr(self):
        if self._box != "":
            return self._box+"_"
        else:
            return ""

    def exitIfQuit(self):
        if self._quit:
            sys.exit()

    def cleanup(self, path):
        try:
            shutil.rmtree(path, ignore_errors=True)
        finally:
            return

    def generateViewer(self):
        thumbnails = ""            
        for page in range(self._first_page, self._last_page+1):
            p = self._storagedir + "_" + (('%0'+str(self._pad)+"d") % page)
            thumb = Templates.thumbnail.replace("%%URL%%", p + ".jpg")
            thumb = thumb.replace("%%THUMB%%", "thumbs/"+p+"_tnl.jpg")
            thumb = thumb.replace("%%REF%%", "Page "+str(page))
            thumbnails += thumb           
        html = Templates.html
        html = html.replace("<head>", "<head>" + Templates.frames_style)
        html = html.replace("%%BODY%%", Templates.frames_body)
        html = html.replace("%%TITLE%%", self._title)
        html = html.replace("%%THUMBNAILS%%", thumbnails)
        return html

    def fetch_thumbnail(self, page, no_save=False):
        # These run inside concurrent futures, so check for a terminated main.
        self.exitIfQuit()
        storage = os.path.join(self._storagedir, "thumbs")
        curPage = self._document + "_" + (('%0'+str(self._pad)+"d") % page)
        fileName = self.boxstr + curPage
        pageDir = curPage + "_img"

        url = (self._firstpart + "/" + pageDir + "/" + pageDir 
            + "_TILE_016_0000_0000.JP2")
        fallback = (self._firstpart + "/" + curPage + "_tnl.jpg")
        jp2 = os.path.join(storage, fileName+"_tnl.JP2")

        print("Fetching thumbnail for page "+str(page), end="\r")
        # skip completed thumbnails, but try the actual thumbnail as fallback
        # in case zoom 16 doesn't exist for this page
        thumbpath = os.path.join(storage, fileName+"_tnl.jpg")
        while not os.path.exists(thumbpath):
            try:
                if no_save and url.endswith(".jpg"):
                    return self.fetch_url(url)
                else:
                    self.fetch_to_file(url, jp2)
                    subprocess.run(["gm", "mogrify", "-format", "jpg", jp2])
                    os.remove(jp2)
                    if no_save:
                        f = open(thumbpath, "rb").read()
                        os.remove(thumbpath)
                        return f
            except urllib.error.HTTPError as e:
                if e.code == 404 and url != fallback:
                    url = fallback
                else:
                    raise

    def fetch_all_thumbnails(self):
        if not os.path.exists(os.path.join(self._storagedir, "thumbs")):
            os.makedirs(os.path.join(self._storagedir, "thumbs"))
        pool = [self._executor.submit(self.fetch_thumbnail, page) for page in range(self._first_page, self._last_page+1)]
        concurrent.futures.wait(pool, None, concurrent.futures.FIRST_EXCEPTION)
        clearline()

    def fetch_url(self, url):
        while True:
            try:
                with urllib.request.urlopen(url, None, 10) as r:
                    return r.read()
            except timeout:
                continue

    def fetch_to_file(self, url, to_file):
        file_dir = os.path.dirname(to_file)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        # don't download twice, but retry on timeouts
        while not os.path.exists(to_file):
            try:
                with urllib.request.urlopen(url, None, 10) as r, open(to_file, 'wb') as of:
                    of.write(r.read())
            except timeout:
                continue

    def fetch_page(self, page, no_save=False):
        curPage = self._document + "_" + (('%0'+str(self._pad)+"d") % page)
        storage = self._storagedir
        fileName = self.boxstr + curPage
        pageDir = curPage + "_img"
        pageFile = os.path.join(storage, fileName+".jpg")

        # don't download and assemble completed pages
        if not os.path.exists(pageFile):
            # Pages are composed of sub-image tiles, like a slippy map.
            # Make a temporary dir for all of the pieces.
            if not os.path.exists(os.path.join(storage, fileName)):
                os.makedirs(os.path.join(storage, fileName))

            # Pages don't have uniform tile counts, so we detect
            # them for each page starting from something arbitrarily high.
            # Unfortunately this means not threading all the tile requests.
            max_y = 50
            max_x = 50
            y = 0
            while y < max_y:
                x = 0
                while x < max_x:
                    tileFile = (pageDir + "_TILE_001_" + ('%04d' % y) + "_" 
                         + ('%04d' % x) + ".JP2")
                    tileURL = self._firstpart + "/" + pageDir + "/" + tileFile

                    try:
                        tileDest = os.path.join(storage, fileName, tileFile)
                        self.fetch_to_file(tileURL, tileDest)
                        x += 1
                    except urllib.error.HTTPError as e:
                        if e.code == 404:
                            if y == 0:
                                max_x = x
                            else:
                                max_y = y
                                break
                        else:
                            print(str(e))
                            raise
                y += 1

            clearline()
            print("Assembling page "+str(page)+".", end="\r")

            try:
                # GraphicsMagick Montage is perfect for reassembling the tiles
                subprocess.run(["gm", "montage", "-mode", "concatenate", "-quality", "80", "-tile",
                                "%dx%d" % (max_x, max_y),
                                os.path.join(storage, fileName, "*.JP2"),
                                pageFile])
            finally:        
                # Clean up. Erase downloaded tile images for the assembled page.
                self.cleanup(os.path.join(storage, fileName))
                if not os.listdir(storage):
                    os.rmdir(storage)

        clearline()
        print("Finished page "+str(page)+".")
        if no_save:
            f = open(pageFile, "rb").read()
            os.remove(pageFile)
            return f
        return

    def fetch_desired_pages(self, start=None, end=None):
        if not start:
            start = self._first_page
        if not end:
            end = self._last_page
        for page in range(start, end+1):
            self.exitIfQuit()
            self.fetch_page(page)

    def exfiltrate(self, start=None, end=None):
        print("")
        print("Processing request.")
        print("Press Ctrl+C to abort.")
        print("Completed files will be put in the "+self._storagedir+" folder.")
        print("Run again with the same parameters to resume exfiltration.")
        # Throw in a HTML viewer
        with open(os.path.join(self._storagedir, "index.html"), "w") as tf:
            tf.write(self.generateViewer())
        self.exitIfQuit()
        print("Fetching thumbnails")
        self.fetch_all_thumbnails()
        self.exitIfQuit()
        print("Done fetching thumbnails")
        print("Fetching pages")
        self.fetch_desired_pages(start, end)

        clearline()
        print("")
        print("Done!")
        print("Look in the "+self._storagedir+" folder.")


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

