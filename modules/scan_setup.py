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
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from hardware.scanners import xy_scanner as scan
try:
    import pyvisa
except:
    print("Please install pyvisa via the \'pip install pyvisa\' command.")
    exit(0)
import importlib
import platform
import time
import scan_config as cfg
from modules.scan_result import open_datafile1 as open_datafile1
from modules.scan_calibrate import save_calibration as save_calibration
proj_name = "testet"

def discover_sa_models():
    """Dynamically find all spectrum analyzer driver modules."""
    # Find path relative to this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sa_dir = os.path.join(base_dir, '..', 'hardware', 'spectrum_analyzers')
    
    if not os.path.exists(sa_dir):
        return []

    models = []
    for file in os.listdir(sa_dir):
        if file.endswith('.py') and not file.startswith('__') and _is_sa_driver(os.path.join(sa_dir, file)):
            model_name = os.path.splitext(file)[0]
            models.append(model_name)
    return sorted(models)

def _is_sa_driver(path):
    """True if the file looks like a spectrum analyzer driver. The file is only read as text,
    never imported, since importing a test script could run code that talks to hardware."""
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    except OSError:
        return False
    return "def measure_spectrum" in text and "def init" in text

def serial_ports():
    """Return a list of available COM/serial port device names."""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

_visa_resources = []     # Result of the latest VISA search (searching can take several seconds)
_visa_searched = False   # True when the VISA search has been done at least once

def get_all_sa_resources(refresh_visa=False):
    """Combine PyVISA resources with system COM ports for the SA dropdown.
    COM ports are always read fresh (fast). The VISA/GPIB search is slow, so its result is
    kept and only searched again at the first call or when refresh_visa is True."""
    global _visa_resources, _visa_searched
    resources = []

    # 1. Query PyVISA resources (GPIB, USB-TMC, TCPIP, ASRL)
    if refresh_visa or not _visa_searched:
        start = time.time()
        try:
            rm = pyvisa.ResourceManager()
            _visa_resources = list(rm.list_resources())
        except Exception as e:
            print(f"VISA resource list error: {e}")
            _visa_resources = []
        _visa_searched = True
    resources.extend(_visa_resources)

    # 2. Append standard COM ports (avoiding duplicates)
    #try:
    com_ports = serial_ports()
    for port in com_ports:
        if port not in resources:
            resources.append(port)
    #except Exception as e:
    #    print(f"Serial port list error: {e}")

    return sorted(resources)

def update_fields_from_globals(): # Update all the widget fields (Entry's) from global variables
    global x_img_iv, y_img_iv, x_scan_dv, y_scan_dv
    for i in range(4):
        x_img_iv[i].set(cfg.x_img[i])
        y_img_iv[i].set(cfg.y_img[i])
        x_scan_dv[i].set(cfg.x_scan[i])
        y_scan_dv[i].set(cfg.y_scan[i])

# Setting up spectrum analyzer, GPIB-address (VISA-address), COM-port to XY-table, perhaps a splash image, license button, credit button
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
        sa = None # The driver module, only set if it could be imported
        cfg.sa_address = visaaddr_sv.get()
        if cfg.sa_address != "" and cfg.sa_model != "":
            try:
                importlib.invalidate_caches() # Find driver files that were added after the program started
                # Dynamic import from hardware.spectrum_analyzers package
                sa = importlib.import_module(f"hardware.spectrum_analyzers.{cfg.sa_model}")
                rm = pyvisa.ResourceManager()
                cfg.specanalyzer = sa.init(rm, cfg.sa_address)
            except Exception as e:
                print(f"Error loading SA driver {cfg.sa_model}: {e}")
                print("Pyvisa failed. Most likely due to some error in USB-driver.")
                print("Please install Keysight IO Connection Expert or equivalent.")
                sa_test_button.configure(bg='orange')
                cfg.specanalyzer = 0

        if getattr(cfg, "specanalyzer", 0) != 0: # cfg.specanalyzer doesn't exist until the first connection attempt
            sa_test_button.configure(bg='lightgreen')
        else:
            print("Spectrum analyzer NOT connected!")
            sa_test_button.configure(bg='tomato')
        if sa is not None:
            sa.local()

    py = 2
    # Spectrum analyzer model dropdown
    samodel_label = tk.Label(left_frame, text="Spectrum analyzer model:", width=20, anchor="w")
    samodel_label.grid(row=0, column=0, padx=5, pady=py, sticky='w')
    samodel_sv = tk.StringVar(root_frame)
    samodel_sv.set(cfg.sa_model)
    sa_models_list = discover_sa_models()
    def refresh_model_list():
        """Called just before the model list opens, so drivers added while the program runs show up."""
        samodel_combo['values'] = discover_sa_models()
    samodel_combo = ttk.Combobox(left_frame, textvariable=samodel_sv, width=44, font=("Calibri",12), values=sa_models_list, state="readonly", postcommand=refresh_model_list) # User can only pick from discovered drivers
    samodel_combo.grid(row=0, column=1, padx=5, pady=py, sticky='w')

    def busy_cursor(on):
        """Show a wait cursor while a slow search is running."""
        root_frame.winfo_toplevel().configure(cursor="watch" if on else "")
        root_frame.update_idletasks()

    def refresh_sa_addresses(rescan_visa=False):
        """Update the spectrum analyzer address list. COM ports are always read fresh (fast).
        The VISA/GPIB search can take seconds, so it is only repeated when rescan_visa is True."""
        if rescan_visa:
            busy_cursor(True)
        try:
            visaaddr_combo['values'] = get_all_sa_resources(refresh_visa=rescan_visa)
        finally:
            if rescan_visa:
                busy_cursor(False)

    def on_sa_model_changed(*args):
        cfg.sa_model = samodel_sv.get()
        importlib.invalidate_caches() # Find driver files that were added after the program started
        refresh_sa_addresses(rescan_visa=True) # The new model may be connected over GPIB/VISA
        save_calibration()  # Persist selection to scan_config.py

    samodel_sv.trace_add('write', on_sa_model_changed)

    # Spectrum analyzer VISA address or COM port if support for TinySA is added for instance
    visaaddr_label = tk.Label(left_frame, text="Spectrum analyzer address:", width=20, anchor="w")
    visaaddr_label.grid(row=1, column=0, padx=5, pady=py, sticky='w')
    visaaddr_sv = tk.StringVar(root_frame)

    # postcommand: the COM ports are read again each time the list is opened (VISA result is cached)
    visaaddr_combo = ttk.Combobox(left_frame, textvariable=visaaddr_sv, width=44, font=("Calibri",12), values=[], postcommand=refresh_sa_addresses)
    visaaddr_combo.grid(row=1, column=1, padx=5, pady=py, sticky='w')
    visaaddr_sv.set(cfg.sa_address)
    # NOTE: trace is attached once in populate_and_test_hardware() (attaching it here too
    # made every address change connect twice).
    sa_test_button = tk.Button(left_frame, text="Test", width=5, command=update_sa_address) # grey before tested
    sa_test_button.grid(row=1, column=2, padx=5, pady=py, sticky='w')
    # Search for new GPIB/VISA instruments again (can take a few seconds)
    sa_refresh_button = tk.Button(left_frame, text="Refresh", width=5, command=lambda: refresh_sa_addresses(rescan_visa=True))
    sa_refresh_button.grid(row=0, column=2, padx=5, pady=py, sticky='w') # Third column, same row as the model dropdown

    def serial_ports(): # Returns a list of available serial ports
        """Return available serial ports instantly using OS driver query."""
        return [port.device for port in serial.tools.list_ports.comports()]

    def update_scan_port(*args):
        cfg.scanner_comport = scanport_sv.get()
        if(cfg.scanner_comport != ""):
            cfg.scan = scan.init(cfg.scanner_comport) # Init xy_scanner
        if cfg.scan == 1:
            scan_test_button.configure(bg='lightgreen')
        else:
            print("Scanner NOT connected!")
            scan_test_button.configure(bg='tomato')

    # Com port address to scanner table
    scanaddr_label = tk.Label(left_frame, text="Scanner COM port:", width=20, anchor="w")
    scanaddr_label.grid(row=2, column=0, padx=5, pady=py, sticky='w')
    scanport_sv = tk.StringVar(root_frame)
    # postcommand: the COM ports are read again each time the list is opened (fast)
    scanaddr_combo = ttk.Combobox(left_frame, textvariable=scanport_sv, width=44, font=("Calibri",12), values=[], postcommand=lambda: scanaddr_combo.configure(values=serial_ports()))
    scanaddr_combo.grid(row=2, column=1, padx=5, pady=py, sticky='w')
    scanport_sv.set(cfg.scanner_comport)
    # NOTE: trace is attached once in populate_and_test_hardware(); attaching it here too
    # made every port change run update_scan_port twice (second call failed: port already open).
    scan_test_button = tk.Button(left_frame, text="Test", width=5, command=update_scan_port) # grey before tested
    scan_test_button.grid(row=2, column=2, padx=5, pady=py, sticky='w')

    def populate_and_test_hardware():
        """Populate comboboxes and run connection tests after GUI renders."""
        # Populate Scanner COM ports
        scan_ports = serial_ports()
        scanaddr_combo['values'] = scan_ports

        # Populate Spectrum Analyzer resources (VISA + COM ports)
        sa_resources = get_all_sa_resources()
        visaaddr_combo['values'] = sa_resources

        # Attach traces after populating fields
        visaaddr_sv.trace_add('write', update_sa_address)
        scanport_sv.trace_add('write', update_scan_port)

        # Execute connection tests
        update_sa_address()
        update_scan_port()

    # Schedule hardware discovery 1200ms after window render
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
    proj_name_sv = tk.StringVar(root_frame)
    selected_proj_label = tk.Label(left_frame, textvariable=proj_name_sv, width=46, font=("Calibri",12), bg='white', anchor="w")
    selected_proj_label.grid(row=3, column=1, padx=2, sticky='w')
    scanfile1_name = os.path.basename(cfg.scanfile1_path)
    proj_name_sv.set(scanfile1_name)
    open_proj_button = tk.Button(left_frame, text="Open", width=5, command=open_project_dialog)
    open_proj_button.grid(row=3, column=2, padx=5, pady=py, sticky='w')

    # Create a new project
    def new_project_setup():
        if newproj_sv.get() == "":
            print("The newproj_sv project name isn't valid!")
            errorwindow = tk.Toplevel(root_frame)
            errorwindow.title("Error")
            tk.Label(errorwindow, text="The newproj_sv project name isn't valid!").pack()
            tk.Label(errorwindow, text="newproj_sv = " + newproj_sv.get()).pack()
            tk.Button(errorwindow, text="  OK  ", command=errorwindow.destroy).pack()
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
    newproj_sv = tk.StringVar(root_frame)
    scanaddr_entry = tk.Entry(left_frame, textvariable=newproj_sv, width=46, font=("Calibri",12))
    scanaddr_entry.grid(row=4, column=1, padx=5, pady=py, sticky='w')
    newproj_sv.set(proj_name)
    new_button = tk.Button(left_frame, text="New", width=5, command=new_project_setup)
    new_button.grid(row=4, column=2, padx=5, pady=py, sticky='w')

    # Test version of Python (Python 3.7 is known working under Windows, higher than 3.7 might give issues with PyVisa, Python 3.14.7 seems to work also)
    pversiontst_label = tk.Label(left_frame, text="Installed version of Python", width=25, anchor="w")
    pversiontst_label.grid(row=6, column=0, columnspan=2, padx=5, pady=py, sticky='w')
    pversion_sv = tk.StringVar(root_frame)
    pversion_entry = tk.Entry(left_frame, textvariable=pversion_sv, width=46, font=("Calibri",12), state='disabled') # only for display
    pversion_entry.grid(row=6, column=1, padx=5, pady=py, sticky='w')
    pversion_sv.set("Python "+str(sys.version_info[0])+"."+str(sys.version_info[1])+"."+str(sys.version_info[2]))

    def show_credits_window():
        creditswindow = tk.Toplevel(root_frame)
        creditswindow.title("Credits")
        credits0_label = tk.Label(creditswindow, text="The following persons and organisations have contributed")
        credits0_label.grid(row=0, column=0, padx=5, pady=5, sticky='n')
        credits1_label = tk.Label(creditswindow, text="to the development of this software.")
        credits1_label.grid(row=1, column=0, padx=5, pady=5, sticky='n')
        credits_text = tk.Text(creditswindow, height = 20, width = 80)
        contributors_str="""
Jacob Rengman, <https://www.irr.se>, Initial author and EMC expert
Göran Nordahl, <https://www.lohmega.com>, Background research and inspiration
Stefan Petersen, <https://www.spe.ciellt.se>, Embedded software expert
Trimble Sweden AB, <https://www.trimble.com>"""
# Add your own information here (at the end) if you wish to be credited before making a pull request
        credits_text.grid(row=2, column=0, padx=5, pady=5, sticky='n')
        credits_text.insert(tk.END, contributors_str)
        exit_button = tk.Button(creditswindow, text=" EXIT ", command=creditswindow.destroy)
        exit_button.grid(row=10, column=0, padx=5, pady=5, sticky='n')

    def show_license_window():
        licensewindow = tk.Toplevel(root_frame)
        licensewindow.title("License")
        license_text = tk.Text(licensewindow, height = 18, width = 70)
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
        license_text.insert(tk.END, license_str)
        exit_button = tk.Button(licensewindow, text=" EXIT ", command=licensewindow.destroy)
        exit_button.grid(row=10, column=0, padx=5, pady=5, sticky='n')

    def show_about_window():
        aboutwindow = tk.Toplevel(root_frame, height=100, width=100)
        aboutwindow.title("About")
        about_label = tk.Label(aboutwindow, text="Near field scanner "+cfg.app_version, font=("Helvetica", 25))
        about_label.grid(row=0, column=0, padx=5, pady=5, sticky='n')
        about_text = tk.Text(aboutwindow, height = 18, width = 70)
        about_str="""
Near field scanner is a software to measure
and visualize the electromagnetic near field radiation.
The software require a spectrum analyzer and
an XYZ-positioning table like CNC 3018 or similar
to be connected to work properly.

Copyright (C) 2024-2026 Jacob Rengman

Please consider to contribute to the continued development
of this software: https://paypal.me/JacobRengman or contact
me directly with error reports or feature requests: jre@irr.se"""
        about_text.grid(row=1, column=0, padx=5, pady=5, sticky='n')
        about_text.insert(tk.END, about_str)
        button_frame = tk.Frame(aboutwindow, width=200, height=500)
        button_frame.grid(row=10, column=0, padx=2, pady=2, sticky='n')
        credits_button = tk.Button(button_frame, text=" CREDITS ", command=show_credits_window)
        credits_button.grid(row=0, column=0, padx=5, pady=5, sticky='n')
        license_button = tk.Button(button_frame, text=" LICENSE ", command=show_license_window)
        license_button.grid(row=0, column=1, padx=5, pady=5, sticky='n')
        exit_button = tk.Button(button_frame, text=" EXIT ", command=aboutwindow.destroy)
        exit_button.grid(row=0, column=2, padx=5, pady=5, sticky='n')

    # About button
    about_button = tk.Button(left_frame, text="About Near field scanner", command=show_about_window)
    about_button.grid(row=7, column=0, padx=5, columnspan=3, pady=10, sticky='we')
    
if __name__ == '__main__': # Standalone init and enable for manual control
    os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Back up CWD one level in standalone mode
    root = tk.Tk()  # create root window
    root.title("Scanner setup stand alone test module")  # title of the GUI window
    scan_setup(root)
    root.mainloop()
