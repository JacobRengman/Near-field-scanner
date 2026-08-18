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
# This is the scan_setup module that set up all the connection to hardware
# for the near field scanner to work properly.
# It can also be used to set up a new project name and or copy the setup
# from an old near field scanning.

from tkinter import *
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import os
import sys
import glob
try:
    import serial
    import serial.tools.list_ports
except:
    print("Please install pyserial with the command \'pip install pyserial\'")
    exit(0)
import xy_scanner as scan
try:
    import pyvisa
except:
    print("Please install pyvisa via the \'pip install pyvisa\' command.")
    exit(0)
import importlib
import sys
import platform
import scan_config as cfg
from scan_result import open_datafile1 as open_datafile1
from scan_calibrate import save_calibration as save_calibration
proj_name = "testet"

def update_fields_from_globals(): # Update all the widget fields (Entry's) from global varaibles
    global x_img_iv, y_img_iv, x_scan_dv, y_scan_dv
    print("calibrate.update_fields_from_globals")
    for i in range(4):
        x_img_iv[i].set(cfg.x_img[i])
        y_img_iv[i].set(cfg.y_img[i])
        x_scan_dv[i].set(cfg.x_scan[i])
        y_scan_dv[i].set(cfg.y_scan[i])

# Seting up spectrum analyzer, GPIB-address (VISA-address), COM-port to xy-table, perhaps a splash image, licens button, credit button
def scan_setup(root_frame):
    global proj_name
    root_frame.columnconfigure(0, weight=0)  # left_frame takes exact content width
    root_frame.columnconfigure(1, weight=1)  # image_frame takes remaining space
    root_frame.rowconfigure(0, weight=1)
    
    # Create left and right frames
    left_frame = tk.Frame(root_frame) # , width=200, height=500)
    left_frame.grid(row=0, column=0, padx=2, pady=2, sticky='nw')

    # Create image frame
    image_frame = tk.Frame(root_frame)
    image_frame.grid(row=0, column=1, padx=5, pady=2, sticky='nsew')

    def update_sa_address(*args):
        cfg.sa_address = visaaddr_sv.get()
        if(cfg.sa_address != ""):
            try:
                rm = pyvisa.ResourceManager()
            except:
                print("Pyvisa failed. Most likely due to some error in USB-driver.")
                print("Please install Keysight IO onnection Expert or equivalent.")
                sa_test_button.configure(bg='orange')
                errorwindow = Toplevel(root_frame)
                errorwindow.title("Error")
                Label(errorwindow, text="Pyvisa failed. Most likely due to some error in USB-driver.").pack()
                Label(errorwindow, text="Please install Keysight IO onnection Expert or equivalent.").pack()
                Label(errorwindow, text="Application will continue without Pyvisa / spectrum analyzer.").pack()
                Button(errorwindow, text="  OK  ", command=errorwindow.destroy).pack()
                return False # Pyvisa is not working properly
            if not(cfg.sa_model == ""):
                sa = importlib.import_module(cfg.sa_model, package=None) # "HP_8591"
            cfg.specanalyzer = sa.init(rm, cfg.sa_address) # Spectrum Analyzer connection
        if cfg.specanalyzer != 0:
            print("Spectrum analyzer connected")
            sa_test_button.configure(bg='lightgreen')
        else:
            print("Spectrum analyzer NOT connected!")
            sa_test_button.configure(bg='tomato')
        sa.local()

    py = 2
    # Spectrum analyzer model
    samodel_label = tk.Label(left_frame, text="Spectrum analyzer model:", width=20, anchor="w")
    samodel_label.grid(row=0, column=0, padx=5, pady=py, sticky='w')
    samodel_sv = StringVar(root_frame)
    samodel_entry = tk.Entry(left_frame, textvariable=samodel_sv, width=46, font=("Calibri",12), state='disabled') # only for display
    samodel_entry.grid(row=0, column=1, padx=5, pady=py, sticky='w')
    samodel_sv.set(cfg.sa_model)
    # samodel_sv.trace('w', update_sa_model)
    sa_load_button = tk.Button(left_frame, text="Open", width=5) # , command=select_sa_model) # TODO add command backend to load spectrum analyzer model selection list
    sa_load_button.grid(row=0, column=2, padx=5, pady=py, sticky='w')

    # Spectrum analyzer VISA address
    visaaddr_label = tk.Label(left_frame, text="Spectrum analyzer address:", width=20, anchor="w")
    visaaddr_label.grid(row=1, column=0, padx=5, pady=py, sticky='w')
    visaaddr_sv = StringVar(root_frame)

    visaaddr_combo = ttk.Combobox(left_frame, textvariable=visaaddr_sv, width=44, font=("Calibri",12), values=[])
    visaaddr_combo.grid(row=1, column=1, padx=5, pady=py, sticky='w')
    visaaddr_sv.set(cfg.sa_address)
    visaaddr_sv.trace('w', update_sa_address)
    sa_test_button = tk.Button(left_frame, text="Test", width=5, command=update_sa_address) # grey before tested
    sa_test_button.grid(row=1, column=2, padx=5, pady=py, sticky='w')

    def serial_ports(): # Returns a list of available serial ports
        """Return available serial ports instantly using OS driver query."""
        return [port.device for port in serial.tools.list_ports.comports()]
##        if sys.platform.startswith('win'):
##            ports = ['COM%s' % (i + 1) for i in range(256)]
##        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
##            # this excludes your current terminal "/dev/tty"
##            ports = glob.glob('/dev/tty[A-Za-z]*')
##        elif sys.platform.startswith('darwin'):
##            ports = glob.glob('/dev/tty.*')
##        else:
##            raise EnvironmentError('Unsupported platform')
##        result = []
##        for port in ports:
##            try:
##                s = serial.Serial(port)
##                s.close()
##                result.append(port)
##            except (OSError, serial.SerialException):
##                pass
##        return result

    def update_scan_port(*args):
        cfg.scanner_comport = scanport_sv.get()
        if(cfg.scanner_comport != ""):
            cfg.scan = scan.init(cfg.scanner_comport) # Init xy_scanner
        if cfg.scan == 1:
            print("Scanner connected", cfg.scan)
            scan_test_button.configure(bg='lightgreen')
        else:
            print("Scanner NOT connected!", cfg.scan)
            scan_test_button.configure(bg='tomato')

    # Com port address to scanner table
    scanaddr_label = tk.Label(left_frame, text="Scanner COM port:", width=20, anchor="w")
    scanaddr_label.grid(row=2, column=0, padx=5, pady=py, sticky='w')
    scanport_sv = StringVar(root_frame)
    scanaddr_combo = ttk.Combobox(left_frame, textvariable=scanport_sv, width=44, font=("Calibri",12), values=[])
    scanaddr_combo.grid(row=2, column=1, padx=5, pady=py, sticky='w')
    scanport_sv.set(cfg.scanner_comport)
    scanport_sv.trace('w', update_scan_port)
    scan_test_button = tk.Button(left_frame, text="Test", width=5, command=update_scan_port) # grey before tested
    scan_test_button.grid(row=2, column=2, padx=5, pady=py, sticky='w')

    def populate_and_test_hardware():
        """Runs AFTER the GUI is drawn on screen."""
        # 1. Populate COM ports
        scanaddr_combo['values'] = serial_ports()
        
        # 2. Populate VISA resources
        try:
            rm = pyvisa.ResourceManager()
            visaaddr_combo['values'] = list(rm.list_resources())
        except Exception as e:
            print(f"VISA list error: {e}")

        # 3. Attach traces AFTER populating so they don't fire during startup
        visaaddr_sv.trace_add('write', update_sa_address)
        scanport_sv.trace_add('write', update_scan_port)

        # 4. Perform connection tests
        update_sa_address()
        update_scan_port()

    # Schedule hardware discovery 1200ms AFTER main loop starts
    root_frame.after(1200, populate_and_test_hardware)
    
    # Open old Project file name / selector
    def open_project_dialog():
        cfg.scanfile1_path = os.path.basename(filedialog.askopenfilename(title="Select a File", filetypes=[("Near Field Scan files", "*.nfs")]))
        cfg.proj_name_path = cfg.scanfile1_path[9:15]
        if cfg.scanfile1_path:
            # selected_file1_label.config(text=cfg.scanfile1_path)
            pass
        if cfg.scanfile1_path == "":
            return # There is no purpose in loading an empty file
        else:
            scanfile1_name = os.path.basename(cfg.scanfile1_path)
            proj_name_sv.set(scanfile1_name)
            cfg.scanfile1_path = scanfile1_name
            proj_name_sv.set(scanfile1_name)
            if open_datafile1(scanfile1_name):
                base_name = scanfile1_name.split('_')[0] if '_' in scanfile1_name else os.path.splitext(scanfile1_name)[0]
                cfg.proj_name_path = base_name
                newproj_sv.set(base_name)
                save_calibration()

    select_proj_label = tk.Label(left_frame, text="Copy setup from project file:", width=20, anchor="w")
    select_proj_label.grid(row=3, column=0, padx=5, pady=py, sticky='w')
    proj_name_sv = StringVar(root_frame)
    selected_proj_label = Label(left_frame, textvariable=proj_name_sv, width=46, font=("Calibri",12), bg='white', anchor="w")
    selected_proj_label.grid(row=3, column=1, padx=2, sticky='w')
    scanfile1_name = os.path.basename(cfg.scanfile1_path)
    proj_name_sv.set(scanfile1_name)
    open_proj_button = Button(left_frame, text="Open", width=5, command=open_project_dialog)
    open_proj_button.grid(row=3, column=2, padx=0, pady=0)

    # Create a new project
    def new_project_setup():
        print("new_project_setup all global variables set back to default")
        if newproj_sv.get() == "":
            print("The newproj_sv project name isnt valid!")
            errorwindow = Toplevel(root_frame)
            errorwindow.title("Error")
            Label(errorwindow, text="The newproj_sv project name isnt valid!").pack()
            Label(errorwindow, text="newproj_sv = " + newproj_sv.get()).pack()
            Button(errorwindow, text="  OK  ", command=errorwindow.destroy).pack()
            return False # Non valid project name
        # Return all global variables to their default values and then save them
        cfg.proj_name_path = newproj_sv.get()
        cfg.image_path = ""
        cfg.image = []
        cfg.no_of_calpoints =  0
        cfg.x_img, cfg.y_img = [0, 0, 0, 0], [0, 0, 0, 0]
        cfg.x_scan, cfg.y_scan = [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]
        cfg.scanfile1_path, cfg.scanfile2_path = "", ""
        cfg.total_points = 0
        cfg.x_start, cfg.y_start, cfg.x_stop, cfg.y_stop = 0.0, 0.0, 0.0, 0.0
        cfg.x_step, cfg.y_step = 5.0, 5.0
        cfg.freq_lst, cfg.R, cfg.S = [], [], []
        proj_name_sv.set("")
        save_calibration() # Save all the global variables to a new scan_config.py -file
        return True

    # New Project name
    newproj_label = tk.Label(left_frame, text="New project name:", width=20, anchor="w")
    newproj_label.grid(row=4, column=0, padx=5, pady=py, sticky='w')
    newproj_sv = StringVar(root_frame)
    scanaddr_entry = tk.Entry(left_frame, textvariable=newproj_sv, width=46, font=("Calibri",12))
    scanaddr_entry.grid(row=4, column=1, padx=5, pady=py, sticky='w')
    newproj_sv.set(proj_name)
    new_button = tk.Button(left_frame, text="New", width=5, command=new_project_setup)
    new_button.grid(row=4, column=2, padx=5, pady=py, sticky='w')

    def test_module_pressence():
        try: # Add all the module dependencies here so import can be tested
            import pyvisa
            import serial
            import time
            import math
            import matplotlib
            import datetime
            moduletst_button.configure(bg='lightgreen')
        except:
            print("At least one module didn't get imported!")
            moduletst_button.configure(bg='tomato')

    # Check that all needed modules are installed
    moduletst_label = tk.Label(left_frame, text="Test if all modules are installed", width=25, anchor="w")
    moduletst_label.grid(row=5, column=0, columnspan=2, padx=5, pady=py, sticky='w')
    moduletst_button = tk.Button(left_frame, text="Test", width=5, command=test_module_pressence)
    moduletst_button.grid(row=5, column=2, padx=5, pady=py, sticky='w')
    test_module_pressence()

    def test_python_version():
        if sys.version_info[0] == 3 and sys.version_info[1] == 7:
            pversiontst_button.configure(bg='lightgreen')
        elif sys.version_info[0] == 3 and sys.version_info[1] > 7:
            if platform.system() == "Windows":
                pversiontst_button.configure(bg='tomato') # PyVisa is known to have issues with Python > 3.7 on Windows
            else:
                pversiontst_button.configure(bg='lightgreen')
        elif sys.version_info[0] == 3 and sys.version_info[1] < 7:
            pversiontst_button.configure(bg='yellow')

    # Test version of Python (Python 3.7 is known working under Windows, higher than 3.7 might give issues with PyVisa)
    pversiontst_label = tk.Label(left_frame, text="Installed version of Python", width=25, anchor="w")
    pversiontst_label.grid(row=6, column=0, columnspan=2, padx=5, pady=py, sticky='w')
    pversion_sv = StringVar(root_frame)
    pversion_entry = tk.Entry(left_frame, textvariable=pversion_sv, width=46, font=("Calibri",12), state='disabled') # only for display
    pversion_entry.grid(row=6, column=1, padx=5, pady=py, sticky='w')
    pversion_sv.set("Python "+str(sys.version_info[0])+"."+str(sys.version_info[1])+"."+str(sys.version_info[2]))
    pversiontst_button = tk.Button(left_frame, text="Test", width=5, command=test_python_version)
    pversiontst_button.grid(row=6, column=2, padx=5, pady=py, sticky='w')
    test_python_version()

    def show_credits_window():
        creditswindow = Toplevel(root_frame)
        creditswindow.title("Credits")
        credits0_label = Label(creditswindow, text="The following persons and organisations have contributed")
        credits0_label.grid(row=0, column=0, padx=5, pady=5, sticky='n')
        credits1_label = Label(creditswindow, text="to the development of this software.")
        credits1_label.grid(row=1, column=0, padx=5, pady=5, sticky='n')
        credits_text = Text(creditswindow, height = 20, width = 80)
        contributors_str="""
Jacob Rengman, <https://www.irr.se>, Initial author and EMC expert
Göran Nordahl, <https://www.lohmega.com>, Background reserch and inspiration
Stefan Petersen, <https://www.spe.ciellt.se>, Embedded software expert
Trimble Sweden AB, <https://www.trimble.com>"""
# Add your own information here if you whish to be credited before making a pull request
        credits_text.grid(row=2, column=0, padx=5, pady=5, sticky='n')
        credits_text.insert(END, contributors_str)
        exit_button = tk.Button(creditswindow, text=" EXIT ", command=creditswindow.destroy)
        exit_button.grid(row=10, column=0, padx=5, pady=5, sticky='n')

    def show_license_window():
        licensewindow = Toplevel(root_frame)
        licensewindow.title("License")
        license_text = Text(licensewindow, height = 18, width = 70)
        license_str="""
Near field scanner:
Copyright (C) 2024-2026 Jacob Rengman

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>."""
        license_text.grid(row=0, column=0, padx=5, pady=5, sticky='n')
        license_text.insert(END, license_str)
        exit_button = Button(licensewindow, text=" EXIT ", command=licensewindow.destroy)
        exit_button.grid(row=10, column=0, padx=5, pady=5, sticky='n')

    def show_about_window():
        aboutwindow = Toplevel(root_frame, height=100, width=100)
        aboutwindow.title("About")
        about_label = tk.Label(aboutwindow, text="Near field scanner "+cfg.app_version, font=("Helvetica", 25))
        about_label.grid(row=0, column=0, padx=5, pady=5, sticky='n')
        about_text = Text(aboutwindow, height = 18, width = 70)
        about_str="""
Near field scanner is a software to measure
and visualize the electromagnetic near field radiation.
The software require a spectrum analyzer and
a xyz-positioning table like CNC 3018 or similar
to be connected to work properly.

Copyright (C) 2024-2026 Jacob Rengman

Please consider to contribute to the continued development
of this software: https://paypal.me/JacobRengman or contact
me directly with error reports or feature requests: jre@irr.se"""
        about_text.grid(row=1, column=0, padx=5, pady=5, sticky='n')
        about_text.insert(END, about_str)
        button_frame = tk.Frame(aboutwindow, width=200, height=500)
        button_frame.grid(row=10, column=0, padx=2, pady=2, sticky='n')
        credits_button = tk.Button(button_frame, text=" CREDITS ", command=show_credits_window)
        credits_button.grid(row=0, column=0, padx=5, pady=5, sticky='n')
        license_button = tk.Button(button_frame, text=" LICENSE ", command=show_license_window)
        license_button.grid(row=0, column=1, padx=5, pady=5, sticky='n')
        exit_button = tk.Button(button_frame, text=" EXIT ", command=aboutwindow.destroy)
        exit_button.grid(row=0, column=2, padx=5, pady=5, sticky='n')

    pversiontst_label.grid(row=6, column=0, columnspan=2, padx=5, pady=py, sticky='w')
    pversion_sv = StringVar(root_frame)
    pversion_entry = tk.Entry(left_frame, textvariable=pversion_sv, width=46, font=("Calibri",12), state='disabled') # only for display
    pversion_entry.grid(row=6, column=1, padx=5, pady=py, sticky='w')
    pversion_sv.set("Python "+str(sys.version_info[0])+"."+str(sys.version_info[1])+"."+str(sys.version_info[2]))
    pversiontst_button = tk.Button(left_frame, text="Test", width=5, command=test_python_version)
    pversiontst_button.grid(row=6, column=2, padx=5, pady=py, sticky='w')
    test_python_version()

    # About button
    about_button = Button(left_frame, text="About Near field scanner", command=show_about_window)
    about_button.grid(row=7, column=0, padx=5, pady=py, sticky='w')
    
if __name__ == '__main__':
    # Standalone init and enable for manual control
    root = tk.Tk()  # create root window
    root.title("Scanner setup stand alone test module")  # title of the GUI window
    scan_setup(root)
    root.mainloop()
