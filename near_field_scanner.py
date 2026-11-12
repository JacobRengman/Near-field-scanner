# Copyright (C) 2024-2026 Jacob Rengman
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# This is the near field scanner application main module. This module only set up the
# notebook that holds the other modules of the near field scanner.

print("Starting Near Field Scanner Application...") # Early printout

import os
import tkinter as tk
from tkinter import ttk
import scan_config as cfg
from modules import scan_setup as setup
from modules import scan_calibrate as calibrate
from modules import scan_execute as execute
from modules import scan_result as result
from modules import scan_help as help_manager
from PIL import Image, ImageTk

# Work-around for a harmless but ugly message when the program exits:
#   "Exception ignored in: <function Image.__del__ ...> TypeError: catching classes that do
#    not inherit from BaseException is not allowed"
# The Tk interpreter is already gone when Python cleans up the PhotoImage objects, and by then
# tkinter.TclError (which the standard Image.__del__ tries to catch) has been cleared.
def _safe_image_del(self):
    if self.name:
        try:
            self.tk.call('image', 'delete', self.name)
        except Exception:
            pass # The interpreter is already destroyed, nothing left to delete
tk.Image.__del__ = _safe_image_del

cfg.app_version = "v1.2.0" # Please increment version before a pull request

win = tk.Tk()
win.geometry("840x780")
try:
    win.iconbitmap(os.path.join('assets', 'scan_icon.ico')) # TODO Make a better scanner logotype
except tk.TclError:
    pass # .ico window icons are only supported on Windows
win.title("Near field scanner application " + cfg.app_version)
win.rowconfigure(0, weight=1)
win.columnconfigure(0, weight=1)
style = ttk.Style()
style.configure('.', font=('Helvetica', 12))
notebook = ttk.Notebook(win)
tab_name_lst = ["  Scan setup  ", "  Background calibration  ", "  Execute scan  ", "  Show result  "]
tab_lst = []
[tab_lst.append(ttk.Frame(notebook)) for _ in tab_name_lst]

# Tab 0 = Setup of software parameters
# Seting up spectrum analyzer, GPIB-address (VISA -address), COM-port to XY-table, perhaps a splash image, licens button, credit button
setup.scan_setup(tab_lst[0])

# tab 1 = Background calibration
# Choosing (layout) background image and calibrate the image coordinates to the scanner coordinates
calibrate.calibrate(tab_lst[1])
calibrate.enable_dynamic_resize(win)

# tab 2 = Execute scan
# including setup of project name / scan name, scanning coordinates, X/Y-step size, Z-clearance, frequency start/stop, averaging, 
execute.execute_scan(tab_lst[2])
execute.enable_dynamic_resize(win)

# tab 3 = Show result
# Including frequency "zoom" slider, spatial markers, frequency markers, calculation of delta frequencis
result.scan_result(tab_lst[3])

def refresh_tabs(event):
    index = notebook.index(notebook.select())
    if index == 1: # scan_calibrate
        calibrate.update_fields_from_globals()
    if index == 2: # execute_scan
        execute.update_fields_from_globals()
        execute.refresh_window(tab_lst[2])
    if index == 3: # scan_result
        win.update_idletasks()
        result.update_fields_from_globals()
        result.adjust_aspect()

def handle_f1(event):
    """Trigger context help based on currently selected notebook tab."""
    current_tab = notebook.index(notebook.select())
    help_manager.open_help_window(win, current_tab)

notebook.bind("<<NotebookTabChanged>>", refresh_tabs)
win.bind_all("<F1>", handle_f1)

ph = []
ph.append(tk.PhotoImage(file=os.path.join('assets', 'setup_38x37.png')))
ph.append(tk.PhotoImage(file=os.path.join('assets', 'calibrate_38x38.png')))
ph.append(tk.PhotoImage(file=os.path.join('assets', 'Execute_38x38.png')))
ph.append(tk.PhotoImage(file=os.path.join('assets', 'Result_38x38.png')))
for a in range(len(tab_name_lst)):
    notebook.add(tab_lst[a], text=tab_name_lst[a], image=ph[a], compound=tk.LEFT)
notebook.grid(row=0, column=0, sticky='nsew')
win.mainloop()
