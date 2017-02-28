#!/usr/bin/env python3
#
# Copyright 2016 (c) Avital Kelman
#
# Exfiltrate documents from http://anom.archivesnationales.culture.gouv.fr
# without their filthy Java applet.
# This is the app UI base component. It is meant to be subclassed.
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

import sys
sys.dont_write_bytecode = True

import threading
import tkinter as tk
import webbrowser


class TextRedirector(object):
    def __init__(self, widget, err=False):
        self.widget = widget
        self.err = err
        self.widget.tag_config('err', foreground='red')
        self.lock = threading.Lock()

    def flush(self):
        pass

    def write(self, txt):
        with self.lock:
            self.widget.see("end")
            if self.err:
                self.widget.insert("end", txt, 'err')
            else:
                self.widget.insert("end", txt)


class App(tk.Tk):
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
        tk.Tk.__init__(self)
        self.title("ANOM Exfiltrator")
        self.bottombar = tk.Frame(self, padx=5, pady=5)
        self.bottombar.pack(side="bottom", fill="x")
        self.quitbutton = tk.Button(self.bottombar,
                                    text="Quit ANOM Exfiltrator",
                                    command=self.quit, padx=10, pady=10)
        self.quitbutton.pack(side="right")
        self.statusbox = tk.Frame(self)
        scrollbar = tk.Scrollbar(self.statusbox)
        scrollbar['width'] = max(18, int(scrollbar['width']))
        self.statustext = tk.Text(self.statusbox, wrap="word",
                                  yscrollcommand=scrollbar.set)
        scrollbar['command'] = self.statustext.yview
        scrollbar.pack(side="right", fill="y")
        self.statustext.pack(side="left", fill="both", expand=True)
        self.statusbox.pack(side="bottom", fill="both", expand=True)
        sys.stdout = TextRedirector(self.statustext)  # stdout to the text box
        print("Informational messages will appear here.")
        print("----------------------------------------")
