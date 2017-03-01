#!/usr/bin/env python3
#
# Copyright 2016 (c) Avital Kelman
#
# Exfiltrate documents from http://anom.archivesnationales.culture.gouv.fr
# without their filthy Java applet.
# This is the web server component.
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

import os
import signal
import tempfile
import traceback
import urllib
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

import exfiltrate


cache = {}
tempdir = tempfile.TemporaryDirectory()


def new_exfilt(url):
    if url not in cache:
        cache[url] = exfiltrate.Exfiltrator(url, tempdir.name)
        cache[url].fetch_applet_page()
    return cache[url]


def exit_handler(signal=None, b=None):
    print("Shutting down web interface")
    sys.exit(0)


signal.signal(signal.SIGINT, exit_handler)


class ExfiltrateWebRequestHandler(SimpleHTTPRequestHandler):
    def log_request(self, *args, **kwargs):
        pass

    def log_error(self, *args, **kwargs):
        pass

    def text_response(self, text):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(bytes(text, "utf8"))

    def html_response(self, html):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(bytes(html, "utf8"))

    def image_response(self, image):
        self.send_response(200)
        self.send_header('Content-type', 'image/jpeg')
        self.send_header('Content-length', len(image))
        self.end_headers()
        self.wfile.write(image)

    def do_GET(self):  # noqa
        try:
            path = self.path.lstrip("/")
            basepath = urllib.parse.urlparse(path).path
            qs = urllib.parse.urlparse(path).query
            url = urllib.parse.parse_qs(qs).get('url', [""])[0].strip()
            if path == "":
                html = ('<form action="ANOM?">Copy/Paste the ANOM link URL'
                        ' into this box <br>It should look a bit like:  <span '
                        'style="font-size:85%;color:green;">http://anom.archiv'
                        'esnationales.culture.gouv.fr/p2w/?dossier=/collection'
                        '/INVENTAIRES/DPPC/NMD/&first=ETAT_CIVIL_MER_018&last='
                        'ETAT_CIVIL_MER_022&title=Delsol,+Auguste+12+d%C3%A9ce'
                        'mbre+1828</span><br><br><textarea rows="10" cols="50"'
                        ' name="url" value=""></textarea><br><input type="subm'
                        'it" value="Browse Document" /></form><br><br><hr>For '
                        'instructions on how to get the link, see: <a target="'
                        '_blank" href="https://github.com/fiendish/anom_exfilt'
                        'rator#getting-urls">https://github.com/fiendish/anom_'
                        'exfiltrator#getting-urls</a>')
                self.html_response(html)
            elif path == "loading.gif":
                # Concession to get one-file apps with PyInstaller
                if hasattr(sys, '_MEIPASS'):
                    gif_path = os.path.join(sys._MEIPASS, "loading.gif")
                else:
                    gif_path = "loading.gif"
                with open(gif_path, "rb") as loading_gif:
                    self.image_response(loading_gif.read())
            elif basepath == "ANOM":
                if url is not "":
                    exfilt = new_exfilt(url)
                    self.html_response(
                        exfilt.generate_viewer(
                            '?'+qs, 'Getting very large images can take some'
                            ' time.<br>Watch the ANOM Document Browser Web'
                            ' Console to monitor progress.'
                        )
                    )
                else:
                    self.text_response("Your request is missing an ANOM URL."
                                       " Go back and try again.")
            elif (basepath.split("/", 1)[0] == 'thumbs'
                    and basepath.endswith("_tnl.jpg")):
                if url is not "":
                    exfilt = new_exfilt(url)
                    for doc in exfilt.xml_docs.values():
                        p = str(doc['pagenum']) + "_tnl.jpg"
                        if p == basepath.split("/", 1)[1]:
                            p = exfilt.fetch_xml_doc(doc)
                            self.image_response(exfilt.fetch_thumbnail(p,
                                                                       True))
                else:
                    self.text_response("Your request is missing an ANOM URL."
                                       " Go back and try again.")
            elif basepath.endswith(".jpg"):
                if url is not "":
                    exfilt = new_exfilt(url)
                    for doc in exfilt.xml_docs.values():
                        p = str(doc['pagenum']) + ".jpg"
                        if p == basepath:
                            p = exfilt.fetch_xml_doc(doc)
                            self.image_response(exfilt.fetch_page(p, True))
                else:
                    self.text_response("Your request is missing an ANOM URL."
                                       " Go back and try again.")
            else:
                SimpleHTTPRequestHandler.do_GET(self)
        except (ConnectionError, BrokenPipeError):
            return
        except SystemExit:
            return
        except Exception as e:
            self.text_response(traceback.format_exc())


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass


def run_server(address='', port=8000):
    httpd = ThreadedHTTPServer((address, port), ExfiltrateWebRequestHandler)
    httpd.serve_forever()


if __name__ == '__main__':
    run_server()
