#!/usr/bin/python3
#
# Copyright 2016 (c) Avital Kelman
#
# Exfiltrate documents from http://anom.archivesnationales.culture.gouv.fr
# without their filthy Java browser applet
#
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
#
# Usage:
# python3 exfiltrate.py <document_url> [first_page] [last_page]
#
#

from urllib.parse import urlparse, parse_qs
import urllib.request
import os
import subprocess
import shutil
import signal
import sys
from socket import timeout
import threading
import time

def clearline():
    sys.stdout.write("\033[K")  # clear line

class Templates(object):
    @property
    def thumbnail(self):
        return "<a href='#' onclick=\"\
                document.getElementById('image').src='%%URL%%';\">%%REF%%\
                <img src='%%URL%%' style='vertical-align:middle' width='60%'>\
                </a><br>"
    @property
    def html(self):
        return "<!doctype html><html lang='en'><head><meta charset='utf-8'>\
                <title>ANOM Exfiltrator</title></head><body>%%BODY%%</body>\
                </html>"
    @property
    def frames_body(self):
        return "<div id='title' style='text-align:center'>%%TITLE%%</div><br>\
                <div id='content'><div id='left'>%%THUMBNAILS%%</div>\
                <div id='right'><img id='image' src=''></div></div>"
    @property
    def frames_style(self):
        return "<style>html,body {font-size:14pt; height: 100%; overflow: hidden; margin: 0;}\
            #content {height: 100%;}"\
            "#left {float: left; width: 20%; height: 100%; overflow: auto; "\
            "box-sizing: border-box; padding: 0.4em;}"\
            "#right {float: left; width: 80%; height: 100%; overflow: auto;"\
            "box-sizing: border-box; padding: 0.4em;}</style>"

Templates = Templates() # properties only work on instances

class ExfiltrateThread(threading.Thread):
    def __init__(self, url, start=None, end=None):
        threading.Thread.__init__(self)
        self._stopper = threading.Event()
        self._url = url
        self._start = start
        self._first_page = start
        self._last_page = end
        self._end = end
        self._which_page = ""
        self._pad = 0
        self._document = ""
        self._box = ""
        self._title = ""
        
    def boxstr(self):
        if self._box != "":
            return self._box+"_"
        else:
            return ""
            
    def cleanup(self):
        try:
            shutil.rmtree(self._which_page, ignore_errors=True)
        finally:
            return

    def stop(self):
        print("Stopping")
        self._stopper.set()

    def stopped(self):
        return self._stopper.isSet()
    
    def join(self, timeout=None):
        self.stop()
        threading.Thread.join(self, timeout)

    def generateViewer(self):
        # Throw in a HTML viewer
        thumbnails = ""            
        for page in range(self._start, self._end+1):
            p = self._storagedir + "_" + (('%0'+str(self._pad)+"d") % page)
            thumb = Templates.thumbnail.replace("%%URL%%", p + ".jpg")
            thumb = thumb.replace("%%REF%%", "Page "+str(page))
            thumbnails += thumb           
        with open(os.path.join(self._storagedir, "index.html"), "w") as tf:
            html = Templates.html
            html = html.replace("<head>", "<head>" + Templates.frames_style)
            html = html.replace("%%BODY%%", Templates.frames_body)
            html = html.replace("%%TITLE%%", self._title)
            html = html.replace("%%THUMBNAILS%%", thumbnails)
            tf.write(html)

    def run(self):
        o = urlparse(self._url)
        qs = parse_qs(o.query)

        firstpart = o.scheme + "://" + o.netloc + qs['dossier'][0]

        # the url encodes basic document information
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

        if self._start is None:
            self._start = self._first_page
        if self._end is None:
            self._end = self._last_page

        if self.stopped():
            self.cleanup()
            return

        self._storagedir = self.boxstr() + self._document
        
        print("")
        print("Processing request.")
        print("Press Ctrl+C to abort.")
        print("Completed files will be put in the "+self._storagedir+" folder.")
        print("Run again with the same parameters to resume exfiltration.")

        if not os.path.exists(self._storagedir):
            os.makedirs(self._storagedir)

        # Throw in a title document.
        with open(os.path.join(self._storagedir, self._storagedir+".txt"), "w") as tf:
            tf.write("Title: " + self._title + "\n\n")
            tf.write("Pages: " + str(self._first_page) + "-"
                     + str(self._last_page) + "\n")

        # Throw in a HTML viewer
        self.generateViewer()

        # fetch next page
        for page in range(self._start, self._end+1):
            self._which_page = self._document + "_" + (('%0'+str(self._pad)+"d") % page)
            page_dir = self._which_page + "_img"

            # skip completed pages
            if os.path.exists(os.path.join(self._storagedir, self.boxstr()+self._which_page+".jpg")):
                continue

            # Pages are composed of sub-image tiles, like a slippy map.
            # Make a temporary dir for all of the pieces.
            if not os.path.exists(self.boxstr()+self._which_page):
                os.makedirs(self.boxstr()+self._which_page)

            # Pages don't have uniform tile bounds, so we have to detect
            # them for each page starting from something arbitrarily high.
            max_y = 50
            max_x = 50

            cur_z = 1  # Zoom level. 16 is tiny, 4 is medium, 1 is large
            cur_y = 0
            while cur_y < max_y:
                cur_x = 0
                while cur_x < max_x:
                    if self.stopped():
                        self.cleanup()
                        return
                    tile = (page_dir + "_TILE_" + ('%03d' % cur_z) + "_"
                            + ('%04d' % cur_y) + "_" + ('%04d' % cur_x) + ".JP2")
                    tile_url = firstpart + self._box + "/" + page_dir + "/" + tile

                    try:
                        print("Fetching p" + str(page) + ",y" + str(cur_y) + ",x"
                              + str(cur_x) + ".", end="\r")
                        f = os.path.join(self.boxstr()+self._which_page, tile)
                        with urllib.request.urlopen(tile_url, None, 10) as r, open(f, 'wb') as of:
                            of.write(r.read())
                        cur_x += 1
                    except timeout:
                        print("Download timed out. Trying again.")
                        continue  # try again
                    except urllib.error.HTTPError as e:
                        if e.code == 404:
                            if cur_y == 0:
                                max_x = cur_x
                            else:
                                max_y = cur_y
                                break
                        else:
                            print(str(e))
                            raise
                    except urllib.error.URLError as e:
                        print(str(e))
                cur_y += 1

            clearline()
            print("Assembling page "+str(page)+".", end="\r")

            try:
                if not os.path.exists(self._storagedir):
                    os.makedirs(self._storagedir)

                # GraphicsMagick Montage is perfect for reassembling the tiles
                subprocess.run(["gm", "montage", "-mode", "concatenate", "-quality",
                               "80", "-tile", "%dx%d" % (max_x, max_y),
                               os.path.join(self.boxstr()+self._which_page, "*.JP2"),
                               os.path.join(self._storagedir, self.boxstr()+self._which_page+".jpg")])
            except:
                if not os.listdir(self._storagedir):
                    os.rmdir(self._storagedir)
                raise

            clearline()
            print("Finished page "+str(page)+".")

            # Clean up. Erase downloaded tile images for the assembled page.
            shutil.rmtree(self.boxstr()+self._which_page, ignore_errors=True)

        clearline()
        print("")
        print("Done! Look in the "+self._storagedir+" folder.")
        
if __name__ == '__main__':
    start = None
    end = None
    if len(sys.argv) > 2:
        start = int(sys.argv[2])
        end = int(start)
    if len(sys.argv) > 3:
        end = int(sys.argv[3])

    exfilt = ExfiltrateThread(sys.argv[1], start, end)
    exfilt.daemon = True
    exfilt.start()
    
    def die(a=None, b=None):
        clearline()
        print("")
        print("Exit!")
        exfilt.cleanup()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, die)

    import atexit
    atexit.register(exfilt.cleanup)
    while True:
        time.sleep(0.1)

