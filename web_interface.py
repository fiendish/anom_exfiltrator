#!/usr/bin/env python3
 
from http.server import SimpleHTTPRequestHandler, HTTPServer
import exfiltrate
import urllib
import threading
import signal
import sys

def exit_handler(signal=None, b=None):
   print("Shutting down web interface")
   sys.exit(0)

signal.signal(signal.SIGINT, exit_handler)

# HTTPRequestHandler class
class testHTTPServer_RequestHandler(SimpleHTTPRequestHandler):
   # GET
   def do_GET(self):
      try:   
         if self.path == "/":
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            msg = open("index.html", "r").read()
         else:
            basepath = urllib.parse.urlparse(self.path).path
            if basepath == "/exfiltrate_query":
                qs = urllib.parse.urlparse(self.path).query
                url = urllib.parse.parse_qs(qs).get('url')
                if url is not None:
                   url = url[0]
                exfilt = threading.Thread(target=exfiltrate.main, args=(url,))
                exfilt.daemon = True
                exfilt.start()
                self.send_response(200)
                self.send_header('Content-type','text/html')
                self.end_headers()
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                msg = "<!doctype html><html lang=\"en\"><head>  <meta charset=\"utf-8\"><title>ANOM Exfiltrator</title></head><body>"
                msg = "title: " + qs['title'][0] + "<br>"
                msg += "dossier: " + qs['dossier'][0] + "<br>"
                first = int(qs['first'][0].rsplit("_",1)[1])
                last = int(qs['last'][0].rsplit("_",1)[1])
                msg += "pages: " + str(first) + "-" + str(last) + "<br>"
                msg += "<br>"
                try:
                    folder = qs['first'][0].split('/')[1].rsplit("_", 1)[0]
                except:
                    folder = qs['first'][0].rsplit("_", 1)[0]
                msg += "Your files are being downloaded to: "
                msg += "<a href=\"/" + folder + "\">" + folder + "</a>\n"
                msg += "</body></html>"
            else:
                SimpleHTTPRequestHandler.do_GET(self)
                return
      except:
         self.send_response(404)
         self.send_header('Content-type','text/html')
         self.end_headers()
         msg = "Error 404, "+self.path+" not found."
         
      self.wfile.write(bytes(msg, "utf8"))
      return

def run():
  # Server settings
  # Choose port 8080 or 8000, for port 80, which is normally used for a http server, you need root access
  server_address = ('127.0.0.1', 8000)
  httpd = HTTPServer(server_address, testHTTPServer_RequestHandler)
  print('Visit http://localhost:8000 in your web browser')
  try:
     httpd.serve_forever()
  finally:
     print("Good bye")

run()
