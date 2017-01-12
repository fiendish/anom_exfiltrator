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
from socketserver import ThreadingMixIn
import tkinter as tk
from tkinter import messagebox
import webbrowser
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
    def log_request(self, *args, **kwargs):
        pass
    def log_error(self, *args, **kwargs):
        pass

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
        self.send_header('Content-length', len(image))
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
                # Replace the global exfiltrator with a new one so we can
                # keep working while the old one cleans up.
                exfilt = exfiltrate.Exfiltrator(url, tempdir.name)
                self.html_response(exfilt.generateViewer())
                return
            elif path.split("/")[0] == 'thumbs' and path.endswith("_tnl.jpg"):
                page = int(path.split("_")[-2])
                self.image_response( exfilt.fetch_thumbnail(page, True) )
                return
            elif path.endswith(".jpg"):
                page = int(path.split("_")[-1].split(".")[0])
                self.image_response(exfilt.fetch_page(page, True))
                return
            else:
                SimpleHTTPRequestHandler.do_GET(self)
                return
        except (ConnectionError, BrokenPipeError):
            return
        except SystemExit:
            return
        except Exception as e:
            self.text_response("Internal Server Error: " + type(e).__name__ + " " + str(e))
            raise

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass

def runServer(address='localhost', port=8000):
    httpd = ThreadedHTTPServer((address, port), ExfiltrateWebRequestHandler)
    serve = threading.Thread(target=httpd.serve_forever)
    serve.daemon = True
    serve.start()
    webbrowser.open("http://"+address+":"+str(port))
    return serve

if __name__ == '__main__':
    class ServerConsole(tk.Tk):
        def hyperlink(self, event):
            widget = self.winfo_containing(event.x_root, event.y_root)
            if widget == event.widget:
                webbrowser.open(event.widget.cget("text"))
            self.unhighlight(event)
        def highlight(self, event):
            event.widget.config(fg="red")
        def unhighlight(self, event):
            event.widget.config(fg="blue")

        def __init__(self):
            self.server = None
            tk.Tk.__init__(self)
            self.title("ANOM Exfiltrator Web Interface Console")
            
            info = tk.Frame(self)
            info.pack(side="top", fill="x", pady=10, padx=10)
            t0 = tk.Label(info, text="The ANOM Exfiltrator is running.", font=('',11))
            t0.pack(side="top")
            t1 = tk.Label(info, text="To interact with it, point your web browser to ", font=('',11))
            t1.pack(side="left")

            t2 = tk.Label(info, fg="blue", cursor="hand2", text=r"http://localhost:8000", font=('',12,'underline'))
            t2.bind("<Button-1>", self.highlight)
            t2.bind("<ButtonRelease-1>", self.hyperlink)
            t2.pack(side="left")
            
            t3 = tk.Label(info, text=" <-- or click", font=('',11))
            t3.pack(side="left")
            
            toolbar = tk.Frame(self, padx=5, pady=5)
            toolbar.pack(side="bottom", fill="x")
            qb = tk.Button(toolbar, text="Quit ANOM Exfiltrator", command=self.quit, padx=10, pady=10)
            qb.pack(side="right")
            
            txtfrm = tk.Frame(self)
            scrollbar = tk.Scrollbar(txtfrm)
            scrollbar['width'] = max(18, int(scrollbar['width']))
            text = tk.Text(txtfrm, wrap="word", yscrollcommand=scrollbar.set)
            scrollbar['command'] = text.yview
            scrollbar.pack(side="right", fill="y")
            text.pack(side="left", fill="both", expand=True)
            txtfrm.pack(fill="both", expand=True)
                        
            # Send prints to the GUI.
            # But don't send stderr unless you want to see all the server
            # request messages.
            sys.stdout = TextRedirector(text)
            self.server = runServer()

    class TextRedirector(object):
        def __init__(self, widget):
            self.widget = widget
            self.write("Informational messages will appear here.\n")
            self.write("----------------------------------------\n")
        def flush(self):
            pass
        def write(self, txt):
            self.widget.see("end")
            self.widget.configure(state="normal")
            self.widget.insert("end", txt, None)
            self.widget.configure(state="disabled")

    app = ServerConsole()
    app.mainloop()
