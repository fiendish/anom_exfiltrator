#!/usr/bin/env python3  
#
# Copyright 2016 (c) Avital Kelman
#
# Exfiltrate documents from http://anom.archivesnationales.culture.gouv.fr
# without their filthy Java applet.
# This is the app UI component for exfiltrating documents.
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
# python3 Exfiltrate_ANOM.py
#
#

import sys
sys.dont_write_bytecode = True

import threading
import web_interface
import app_base
import tkinter as tk
from tkinter import messagebox
import webbrowser
import exfiltrate

class AppConsole(app_base.App):
    def __init__(self):
        app_base.App.__init__(self)
        self.title("ANOM Document Exfiltrator")
        info = tk.Frame(self)
        info.pack(side="top", fill="x", pady=10, padx=10)
        t0 = tk.Label(info, text="Copy/Paste your ANOM URL into this box:", font=('',11))
        t0.pack(side="top")
        self.urlentry = tk.Entry(info)
        self.urlentry.pack(side="top", fill="x")
        help = tk.Frame(info)
        help.pack(side="top")
        t1 = tk.Label(help, text="For instructions on how to get the URL, see: ", font=('',11))
        t11 = tk.Label(help, fg="blue", cursor="hand2", text="https://github.com/fiendish/anom_exfiltrator#walkthrough", font=('',12,'underline'))
        t11.bind("<Button-1>", self.highlight)
        t11.bind("<ButtonRelease-1>", self.hyperlink)
        t1.pack(side="left")
        t11.pack(side="left")

        exfiltrate_button = tk.Button(info, text="Exfiltrate ANOM Document", command=self.exfiltrate, padx=10, pady=10)
        exfiltrate_button.pack(side="top")
        t2 = tk.Label(info, text="Note: Very large documents could use hundreds of megabytes of disk space and take a long time to exfiltrate.", fg='red', font=('',11))
        t2.pack(side="top")
        self.exfilt = None
        # direct stderr to the text box too
        sys.stderr = app_base.TextRedirector(self.statustext, True)
         
    def exfiltrate(self):
        if self.exfilt:
            self.exfilt.die()
        try:
           self.exfilt = exfiltrate.Exfiltrator(self.urlentry.get().strip())
           t = threading.Thread(target=self.exfilt.exfiltrate)
           t.start()
        except KeyError as e:
           sys.stderr.write("Your document URL is missing its "+str(e)+" field.")

if __name__ == '__main__':
    app = AppConsole()
    app.mainloop()

