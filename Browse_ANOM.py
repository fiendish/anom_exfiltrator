#!/usr/bin/env python3  
#
# Copyright 2016 (c) Avital Kelman
#
# Exfiltrate documents from http://anom.archivesnationales.culture.gouv.fr
# without their filthy Java applet.
# This is the app UI component for launching a temporary local webserver.
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

import threading
import web_interface
import tkinter as tk
from tkinter import messagebox
import webbrowser

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
        sys.stdout = TextRedirector(text) # direct stdout to the text box

if __name__ == '__main__':
    app = ServerConsole()
    t = threading.Thread(target=web_interface.runServer)
    t.daemon = True
    t.start()
    webbrowser.open("http://localhost:8000")
    app.mainloop()

