#!/usr/bin/env python3
#
# Copyright 2016 (c) Avital Kelman
#
# Exfiltrate documents from http://anom.archivesnationales.culture.gouv.fr
# without their filthy Java applet.
# This is the app UI component for launching a temporary local webserver
# for browsing ANOM documents.
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
# python3 Browse_ANOM.py
#
#

import sys
sys.dont_write_bytecode = True

import encodings.idna  # NOQA # work around bug in PyInstaller https://github.com/pyinstaller/pyinstaller/issues/1113
import threading
import tkinter as tk

import app_base
import web_interface



class ServerConsole(app_base.App):
    def __init__(self):
        app_base.App.__init__(self)
        self.title("ANOM Document Browser Web Console")
        self.quitbutton.config(text="Quit ANOM Console")
        info = tk.Frame(self)
        info.pack(side="top", fill="x", pady=10, padx=10)
        t0 = tk.Label(info, text="The ANOM Document Browser is running.",
                      font=('', 11))
        t0.pack(side="top")
        t1 = tk.Label(info,
                      text="To interact with it, point your web browser to ",
                      font=('', 11))
        t1.pack(side="left")
        t2 = tk.Label(info, fg="blue", cursor="hand2",
                      text="http://localhost:8000", font=('', 12, 'underline'))
        t2.bind("<Button-1>", self.highlight)
        t2.bind("<ButtonRelease-1>", self.hyperlink)
        t2.pack(side="left")
        t3 = tk.Label(info, text=" <-- or click", font=('', 11))
        t3.pack(side="left")


if __name__ == '__main__':
    app = ServerConsole()
    t = threading.Thread(target=web_interface.run_server)
    t.daemon = True
    t.start()
    app.mainloop()
