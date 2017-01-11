#!/usr/bin/env python3  
#
# Copyright 2016 (c) Avital Kelman
#
# Exfiltrate documents from http://anom.archivesnationales.culture.gouv.fr
# without their filthy Java applet.
# This is the web UI component.
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
# python3 web_interface.py
#
#
import sys
sys.dont_write_bytecode = True

from http.server import SimpleHTTPRequestHandler, HTTPServer
import exfiltrate
import urllib
import threading
import signal
import os
import tempfile

tempdir = tempfile.TemporaryDirectory()
exfilt = None

def exit_handler(signal=None, b=None):
    print("Shutting down web interface")
    if exfilt:
        exfilt.die()
    sys.exit(0)

signal.signal(signal.SIGINT, exit_handler)

class ExfiltrateWebRequestHandler(SimpleHTTPRequestHandler):        
    def text_response(self, text):
        self.send_response(200)
        self.send_header('Content-type','text/plain')
        self.end_headers()
        self.wfile.write(bytes(text, "utf8"))

    def html_response(self, html):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        self.wfile.write(bytes(html, "utf8"))

    def image_response(self, image):
        self.send_response(200)
        self.send_header('Content-type', 'image/jpeg')
        self.send_header('Content-length', sys.getsizeof(image))
        self.end_headers()
        self.wfile.write(image)

    def do_GET(self):
        try:
            path = self.path.lstrip("/")
            basepath = urllib.parse.urlparse(path).path
            if path == "":
                self.html_response(open("index.html", "r").read())
            elif basepath == "exfiltrate_query":
                qs = urllib.parse.urlparse(path).query
                url = urllib.parse.parse_qs(qs).get('url')
                if url is not None:
                    url = url[0].strip()
                global exfilt
                if exfilt:
                    exfilt.die()
                    exfilt.cleanup(exfilt._storagedir)
                # Replace the global exfiltrator with a new one so we can
                # keep working while the old one cleans up.
                exfilt = exfiltrate.Exfiltrator(url, tempdir.name)
                self.html_response(exfilt.generateViewer())
                return
            elif path.split("/")[0] == 'thumbs' and path.endswith("_tnl.jpg"):
                page = int(path.split("_")[-2])
                self.image_response( exfilt.fetch_thumbnail(page, True) )
                exfilt.cleanup(exfilt._storagedir)
                return
            elif path.endswith(".jpg"):
                page = int(path.split("_")[-1].split(".")[0])
                self.image_response(exfilt.fetch_page(page, True))
                exfilt.cleanup(exfilt._storagedir)
                return
            else:
                SimpleHTTPRequestHandler.do_GET(self)
                return
        except ConnectionError:
            return
        except SystemExit:
            return
        except Exception as e:
            self.text_response("Internal Server Error: " + type(e).__name__ + " " + str(e))
            raise

def run():
    # Server settings
    # Choose port 8080 or 8000, for port 80, which is normally used for a http server, you need root access
    server_address = ('127.0.0.1', 8000)
    httpd = HTTPServer(server_address, ExfiltrateWebRequestHandler)
    print('Visit http://localhost:8000 in your web browser')
    serve = threading.Thread(target=httpd.serve_forever)
    try:
        serve.daemon = True
        serve.start()
        serve.join()
    finally:
        print("Good bye")

if __name__ == '__main__':
    run()
