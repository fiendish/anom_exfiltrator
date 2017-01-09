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

class ExfiltrateThread(threading.Thread):
    def __init__(self, url, start=None, end=None):
        threading.Thread.__init__(self)
        self._stopper = threading.Event()
        self._url = url
        self._start = start
        self._end = end
        self._which_page = ""
        
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

    def run(self):
        o = urlparse(self._url)
        qs = parse_qs(o.query)

        firstpart = o.scheme + "://" + o.netloc + qs['dossier'][0]

        # the url encodes basic document information
        document_title = qs['title'][0]

        document_first_page = int(qs['first'][0].rsplit("_", 1)[1])
        document_last_page = qs['last'][0].rsplit("_", 1)[1]
        pad_zeroes = len(document_last_page)
        document_last_page = int(document_last_page)

        try:
            document_name = qs['first'][0].split('/')[1].rsplit("_", 1)[0]
            box_id = qs['first'][0].split('/')[0]
        except:
            document_name = qs['first'][0].rsplit("_", 1)[0]
            box_id = ""

        if self._start is None:
            self._start = document_first_page
        if self._end is None:
            self._end = document_last_page

        if self.stopped():
            self.cleanup()
            return

        print("")
        print("Press Ctrl+C to abort.")
        print("Run again with the same parameters to resume exfiltration.")

        if not os.path.exists(document_name):
            os.makedirs(document_name)

        # Throw in a title document.
        with open(os.path.join(document_name, document_name+".txt"), "w") as tf:
            tf.write("Title: " + document_title + "\n\n")
            tf.write("Pages: " + str(document_first_page) + "-"
                     + str(document_last_page) + "\n")

        # fetch next page
        for page in range(self._start, self._end+1):
            self._which_page = document_name + "_" + (('%0'+str(pad_zeroes)+"d") % page)
            page_dir = self._which_page + "_img"

            # skip completed pages
            if os.path.exists(os.path.join(document_name, self._which_page+".jpg")):
                continue

            # Pages are composed of sub-image tiles, like a slippy map.
            # Make a temporary dir for all of the pieces.
            if not os.path.exists(self._which_page):
                os.makedirs(self._which_page)

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
                    tile_url = firstpart + box_id + "/" + page_dir + "/" + tile

                    try:
                        print("Fetching p" + str(page) + ",y" + str(cur_y) + ",x"
                              + str(cur_x) + ".", end="\r")
                        f = os.path.join(self._which_page, tile)
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
                if not os.path.exists(document_name):
                    os.makedirs(document_name)

                # GraphicsMagick Montage is perfect for reassembling the tiles
                subprocess.run(["gm", "montage", "-mode", "concatenate", "-quality",
                               "80", "-tile", "%dx%d" % (max_x, max_y),
                               os.path.join(self._which_page, "*.JP2"),
                               os.path.join(document_name, self._which_page+".jpg")])
            except:
                if not os.listdir(document_name):
                    os.rmdir(document_name)
                raise

            clearline()
            print("Finished page "+str(page)+".")

            # Clean up. Erase downloaded tile images for the assembled page.
            shutil.rmtree(self._which_page, ignore_errors=True)

        clearline()
        print("")
        print("Done! Look in the "+document_name+" folder.")
        
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

