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

# This is the module that executes scanning and measurement in the near field scanner
# It should be possible to run this module stand alone, but it is ment to be a module in the
# complete near field scanner application

import tkinter as tk
from tkinter import ttk
import matplotlib.image as img
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import math
import numpy as np
import random
import time
import importlib
from datetime import datetime
import pyvisa
import json
import os
import scan_config as cfg # To hold global variables
from scan_calibrate import save_calibration
if not(cfg.sa_model == ""):
    sa = importlib.import_module(cfg.sa_model, package=None) # "HP_8591"
import xy_scanner as scan

# Global variables
stop, done_points, start_time = 0, 0, 0
fig, canvas = None, None
image_frame, root_frame, main_window = None, None, None
last_width, last_height = 0, 0
peak_detector = 0
x_start_dv, y_start_dv, x_stop_dv, y_stop_dv, x_step_dv, y_step_dv = 0, 0, 0, 0, 0, 0
start_freq_dv, stop_freq_dv, points_iv, rbw_iv, rbw_auto_iv, average_iv, sweep_time_iv = 0, 0, 0, 0, 0, 0, 0
showpath_iv, new_name_sv = 0, 0
pred_speed_dv, predeta_sv = 0, 0
disable_updates_from_entries = 0
scan_limit_change = 0
bg_cache, grid_data, im_overlay = None, None, None
mouse_motion_cid, mouse_click_cid = None, None

def open_imagefile():
    global img_xmin, img_ymin, img_xmax, img_ymax
    if cfg.image_path and os.path.exists(cfg.image_path):
        try:
            cfg.image = img.imread(cfg.image_path)
            img_xmin, img_ymin = 0, 0 
            img_xmax = cfg.image.shape[1] # image.shape[1} is x-size shape of image (width)
            img_ymax = cfg.image.shape[0] # image.shape[0] is y-size shape of image (height)
            refresh_window(root_frame)
            return True
        except Exception as e:
            print(f"Error loading image {cfg.image_path}: {e}")
            cfg.image = []
            img_xmin, img_ymin, img_xmax, img_ymax = 0, 0, 0, 0
            refresh_window(root_frame)
            return False
    else:
        cfg.image = []
        img_xmin, img_ymin, img_xmax, img_ymax = 0, 0, 0, 0
        refresh_window(root_frame)
        return False

def resize(event):
    global last_width, last_height
    # Only process configure events originating directly from the main root window
    if event.widget == main_window:
        # Trigger window resize only if width or height actually changed (ignores window moves)
        if event.width != last_width or event.height != last_height:
            last_width = event.width
            last_height = event.height
            refresh_window(root_frame)

def update_eta_widget():
    start_ts = datetime.timestamp(datetime.now())
    no_of_x_step = math.floor((cfg.x_stop-cfg.x_start) / cfg.x_step) + 1     # number of x steps
    no_of_y_step = math.floor((cfg.y_stop-cfg.y_start) / cfg.y_step) + 1 
    cfg.total_points = no_of_x_step * no_of_y_step # Needed by eta()
    total_time = cfg.total_points * pred_speed_dv.get() # (end_ts - start_ts)
    eta_time = datetime.fromtimestamp(start_ts + total_time)
    if pred_speed_dv.get() > 0: # Dont update the prediction if speed is zero
        predeta_sv.set(eta_time.strftime("%Y-%m-%d %H:%M:%S"))
    else:
        predeta_sv.set("")

def mouse_motion_event(event):
    global fig, canvas, scan_limit_change, disable_updates_from_entries
    if type(event.xdata) == np.float64 and type(event.ydata) == np.float64:
        disable_updates_from_entries = 1

        if (scan_limit_change & 1) == 1: # Moving x_start line
            cfg.x_start = round(event.xdata, 1)
            x_start_dv.set(cfg.x_start)

        if (scan_limit_change & 2) == 2: # Moving x_stop line
            cfg.x_stop = round(event.xdata, 1)
            x_stop_dv.set(cfg.x_stop)

        if (scan_limit_change & 4) == 4: # Moving y_start line
            cfg.y_start = round(event.ydata, 1)
            y_start_dv.set(cfg.y_start)

        if (scan_limit_change & 8) == 8: # Moving y_stop line
            cfg.y_stop = round(event.ydata, 1)
            y_stop_dv.set(cfg.y_stop)

        disable_updates_from_entries = 0
        refresh_window(root_frame) # Redraw scan box line while dragging

def button_release(event):
    global fig, canvas, mouse_motion_cid, scan_limit_change
    scan_limit_change = 0
    if mouse_motion_cid != None:
        fig.canvas.mpl_disconnect(mouse_motion_cid)
        mouse_motion_cid = None
    if cfg.x_start > cfg.x_stop: # Start and stop is in the wrong order
        x_temp = cfg.x_start
        cfg.x_start = cfg.x_stop
        cfg.x_stop = x_temp
        x_stop_dv.set(cfg.x_stop) # update the GUI
        x_start_dv.set(cfg.x_start)
    if cfg.y_start > cfg.y_stop: # Start and stop is in the wrong order
        y_temp = cfg.y_start
        cfg.y_start = cfg.y_stop
        cfg.y_stop = y_temp
        y_stop_dv.set(cfg.y_stop) # update the GUI
        y_start_dv.set(cfg.y_start)
    update_eta_widget()
    refresh_window(root_frame)

def mouse_event(event):
    global fig, canvas, mouse_motion_cid, scan_limit_change, disable_updates_from_entries
    if type(event.xdata) == np.float64 and type(event.ydata) == np.float64 and event.button == 1: # left click
        scan_limit_change = 0

        # Check proximity to existing edges (tolerance = 1.5 mm)
        tolerance = 1.5
        if abs(event.xdata - cfg.x_start) < tolerance:
            scan_limit_change |= 1 # Grab x_start
        if abs(event.xdata - cfg.x_stop) < tolerance:
            scan_limit_change |= 2 # Grab x_stop
        if abs(event.ydata - cfg.y_start) < tolerance:
            scan_limit_change |= 4 # Grab y_start
        if abs(event.ydata - cfg.y_stop) < tolerance:
            scan_limit_change |= 8 # Grab y_stop

        # Check that not both start and stop was grabbed simultaneously
        if scan_limit_change & 1 and scan_limit_change & 2: # Both x_start and x_stop is grabbed
            scan_limit_change &= 0b1110 # Un-grab x_start
        if scan_limit_change & 4 and scan_limit_change & 8: # Both y_start and y_stop is grabbed
            scan_limit_change &= 0b1011 # Un-grab y_start

        if scan_limit_change == 0: # No edges or corners was clicked, set start (or stop) and then drag the other
            if event.xdata < (cfg.x_stop + cfg.x_start)/2: # click was to the left of center of scan area
                cfg.x_start = round(event.xdata, 1)
                scan_limit_change |= 2 # Grab x_stop
            else: # Click was to the right of the center of scan area
                cfg.x_stop = round(event.xdata, 1)
                scan_limit_change |= 1 # Grab x_start
            if event.ydata < (cfg.y_stop + cfg.y_start)/2: # click was to the below of center of scan area
                cfg.y_start = round(event.ydata, 1)
                scan_limit_change |= 8 # Grab y_stop
            else: # Click was above the center of scan area
                cfg.y_stop = round(event.ydata, 1)
                scan_limit_change |= 4 # Grab y_start
                
        disable_updates_from_entries = 1
        x_start_dv.set(cfg.x_start)
        y_start_dv.set(cfg.y_start)
        x_stop_dv.set(cfg.x_stop)
        y_stop_dv.set(cfg.y_stop)
        disable_updates_from_entries = 0

        # Connect drag motion and button release listeners
        fig.canvas.mpl_connect('button_release_event', button_release)
        mouse_motion_cid = fig.canvas.mpl_connect('motion_notify_event', mouse_motion_event)
        refresh_window(root_frame)

def refresh_window(root_frame):
    global fig, canvas, im_overlay, bg_cache, grid_data
    if fig is None or canvas is None:
        return
    fig.clear() # Always clear previous plot state first
    im_overlay = None
    bg_cache = None
    # Only render background drawing and scan bounding box if an image exists and is calibrated
    if (len(cfg.image) != 0) and (cfg.x_img[0] != cfg.x_img[1]) and (cfg.y_img[0] != cfg.y_img[1]) and \
        (cfg.x_scan[0] != cfg.x_scan[1]) and (cfg.y_scan[0] != cfg.y_scan[1]):
        subplot1 = fig.add_subplot()
        subplot1.grid(color = 'lightgray')

        # Image to scanner coordinate relations
        img_xscale = (cfg.x_img[0] - cfg.x_img[1]) / (cfg.x_scan[0] - cfg.x_scan[1]) # x-pixels / scanner increment
        img_yscale = (cfg.y_img[0] - cfg.y_img[1]) / (cfg.y_scan[0] - cfg.y_scan[1]) # y-pixels / scanner increment
        img_xmin = cfg.x_scan[0] - cfg.x_img[0] / img_xscale # x offset of image origo
        img_ymin = cfg.y_scan[0] - cfg.y_img[0] / img_yscale # y offset of image origo
        img_xmax = cfg.image.shape[1] / img_xscale + img_xmin # image.shape[1} # x-size shape of image (height)
        img_ymax = cfg.image.shape[0] / img_yscale + img_ymin # image.shape[0] # y-size shape of image (width)

        # displaying the layout image in scanner coordinates
        subplot1.imshow(cfg.image, cmap="gray", alpha=1.0, extent=[img_xmin, img_xmax, img_ymax, img_ymin], origin="upper")
        square_x = [cfg.x_start, cfg.x_start, cfg.x_stop, cfg.x_stop, cfg.x_start, ] # Make coordinates for a square around the scan area
        square_y = [cfg.y_start, cfg.y_stop, cfg.y_stop, cfg.y_start, cfg.y_start, ] # Make coordinates for a square around the scan area
        subplot1.plot(square_x, square_y, linewidth='3', alpha=0.5, )

        # make a 2D heatmap matrix filled with NaNs for the dynamic preview function
        x_dist = abs(cfg.x_stop - cfg.x_start)
        y_dist = abs(cfg.y_stop - cfg.y_start)
        x_step_val = cfg.x_step if cfg.x_step > 0 else 1.0
        y_step_val = cfg.y_step if cfg.y_step > 0 else 1.0
        no_of_x_step = max(1, math.floor(x_dist / x_step_val) + 1)
        no_of_y_step = max(1, math.floor(y_dist / y_step_val) + 1)        
        if grid_data is None or grid_data.shape != (no_of_y_step, no_of_x_step):
            grid_data = np.full((no_of_y_step, no_of_x_step), np.nan)

        # Extent bounds shifted by half-step so pixel centers align with coordinates
        x_min_bound = min(cfg.x_start, cfg.x_stop)
        x_max_bound = max(cfg.x_start, cfg.x_stop)
        y_min_bound = min(cfg.y_start, cfg.y_stop)
        y_max_bound = max(cfg.y_start, cfg.y_stop)

        half_x = (cfg.x_step if cfg.x_step > 0 else 1.0) / 2.0
        half_y = (cfg.y_step if cfg.y_step > 0 else 1.0) / 2.0

        grid_extent = [
            x_min_bound - half_x, x_max_bound + half_x, 
            y_max_bound + half_y, y_min_bound - half_y
        ]
        # Min/max bounds calculation
        valid_vals = grid_data[~np.isnan(grid_data)]
        if len(valid_vals) > 0:
            v_min, v_max = np.min(valid_vals), np.max(valid_vals)
            if v_min == v_max:
                v_min -= 1
                v_max += 1
        else:
            v_min, v_max = -100, 0  # Default fallback dBm limits
        # Create 2D Overlay
        im_overlay = subplot1.imshow(
            grid_data, cmap='rainbow', alpha=0.8, 
            extent=grid_extent, origin='upper', 
            vmin=v_min, vmax=v_max )
        subplot1.set_xlim(img_xmin, img_xmax)
        subplot1.set_ylim(img_ymax, img_ymin) # Preserve PCB image extents
        fig.tight_layout()
    # Always redraw canvas to ensure an empty plot is displayed when cfg.image is cleared
    canvas.draw()
    if len(cfg.image) != 0:
        bg_cache = canvas.copy_from_bbox(fig.bbox) # Store the clean figure background
    root_frame.update()

def update_fields_from_globals(): # Update all the widget fields (Entry's) from global varaibles
    global disable_updates_from_entries
    disable_updates_from_entries = 1
    new_name_sv.set(cfg.proj_name_path)
    x_start_dv.set(cfg.x_start)
    y_start_dv.set(cfg.y_start)
    x_stop_dv.set(cfg.x_stop)
    y_stop_dv.set(cfg.y_stop)
    x_step_dv.set(cfg.x_step)
    y_step_dv.set(cfg.y_step)
    start_freq_dv.set(cfg.start_freq/1E6) # in MHz in GUI and in Hz in variable
    stop_freq_dv.set(cfg.stop_freq/1E6) # in MHz in GUI and in Hz in variable
    points_iv.set(cfg.points)
    average_iv.set(cfg.average)
    sweep_time_iv.set(cfg.sweep_time)
    rbw_iv.set(cfg.rbw)
    rbw_auto_iv.set(cfg.rbw_auto)
    open_imagefile()
    disable_updates_from_entries = 0
    root_frame.update()

# ****************************************************************************************************
#  # This is the main routine in the scan_execute module that executes the scanning
# ****************************************************************************************************
def execute_scan(frame): # This is the main routine in the execute_scan module that scans the near field radiation
    global fig, canvas, image_frame, root_frame, showpath_iv, disable_updates_from_entries, new_name_sv
    global x_start_dv, y_start_dv, x_stop_dv, y_stop_dv, x_step_dv, y_step_dv, start_freq_dv, stop_freq_dv
    global points_iv, rbw_iv, rbw_auto_iv, sweep_time_iv, average_iv, mouse_click_cid, pred_speed_dv, predeta_sv
    root_frame = frame
    root_frame.columnconfigure(1, weight=1)
    root_frame.rowconfigure(0, weight=1)
    
    # Create left and right frames
    left_frame = tk.Frame(root_frame, width=200, height=500)
    left_frame.grid(row=0, column=0, padx=2, pady=2, sticky='n')

    # Create image frame
    image_frame = tk.Frame(root_frame) #, width=600, height=600)
    image_frame.grid(row=0, column=1, padx=5, pady=2, sticky='nsew')
    image_frame.columnconfigure(0, weight=1)
    image_frame.rowconfigure(0, weight=1)

    def on_x_step_changed(event=None):
        """Automatically mirror x_step changes onto y_step when modified."""
        if disable_updates_from_entries == 0:
            try:
                val = float(x_step_dv.get())
                if val > 0:
                    y_step_dv.set(val)  # Copy x_step value to y_step widget
            except (ValueError, tk.TclError):
                pass
        update_coordinates_from_entries(event)

    def update_coordinates_from_entries(event=None):
        if disable_updates_from_entries == 0:
            try:
                new_x_start = float(x_start_dv.get())
                new_y_start = float(y_start_dv.get())
                new_x_stop  = float(x_stop_dv.get())
                new_y_stop  = float(y_stop_dv.get())
                new_x_step  = float(x_step_dv.get())
                new_y_step  = float(y_step_dv.get())
                new_start_freq = float(start_freq_dv.get()*1E6) # in MHz in GUI and in Hz in variable
                new_stop_freq  = float(stop_freq_dv.get()*1E6) # in MHz in GUI and in Hz in variable
                new_points     = int(points_iv.get())
                new_average    = int(average_iv.get())
                new_sweep_time         = int(sweep_time_iv.get())
                new_rbw        = int(rbw_iv.get())
                new_rbw_auto   = int(rbw_auto_iv.get())
                
                # Guard against invalid steps (zero or negative)
                if new_x_step <= 0 or new_y_step <= 0:
                    print("Step size must be greater than zero.")
                    update_fields_from_globals() # Revert GUI fields back to valid globals
                    return

                if new_average < 0:
                    print("Number of Average must be greater than zero.")
                    update_fields_from_globals() # Revert GUI fields back to valid globals
                    return

                # If all values are valid, commit to global config
                cfg.x_start    = new_x_start
                cfg.y_start    = new_y_start
                cfg.x_stop     = new_x_stop
                cfg.y_stop     = new_y_stop
                cfg.x_step     = new_x_step
                cfg.y_step     = new_y_step
                cfg.start_freq = new_start_freq
                cfg.points     = new_points
                cfg.average    = new_average
                cfg.sweep_time = new_sweep_time
                cfg.rbw        = new_rbw
                cfg.rbw_auto   = new_rbw_auto

                update_eta_widget()
                refresh_window(root_frame)

            except (ValueError, TclError):
                # Happens if an entry box is left blank or contains non-numeric text
                update_fields_from_globals() # Silently restore last known good values

    fig = Figure(figsize = (6, 6), dpi = 100) # 6*100 = 600 means fig will become 600x600 pixels
    canvas = FigureCanvasTkAgg(fig, master = image_frame)   
    canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')
    mouse_click_cid = fig.canvas.mpl_connect('button_press_event', mouse_event)
    open_imagefile() # Will allways open cfg.image_path

    # Create file selection frame
    file_frame = tk.Frame(left_frame, width=200, height=40)
    file_frame.grid(row=0, column=0, padx=2, pady=2, sticky='nw')
    new_name_sv = tk.StringVar(root_frame)
    new_name_sv.set(cfg.proj_name_path) # "Measurement data")
    name_widget = tk.Entry(file_frame, width=22, font=("Calibri",12), textvariable=new_name_sv,)
    name_widget.grid(row=0, column=0, padx=5, pady=0, sticky='nw')

    # Create settings frame
    settings_frame = tk.Frame(left_frame, width=200, height=400)
    settings_frame.grid(row=1, column=0, padx=2, pady=2, sticky='nw')

    coord_widget_lst = []
    ##### Start point
    coord_widget_lst.append(tk.Label(settings_frame, text="Start x:", width=7, anchor="w"))
    coord_widget_lst[-1].grid(row=0, column=0, padx=5, pady=2, sticky='nw')
    x_start_dv = tk.DoubleVar(root_frame)
    x_start_dv.set(cfg.x_start)
    coord_widget_lst.append(tk.Entry(settings_frame, width=8, font=("Calibri",12), textvariable=x_start_dv,))
    coord_widget_lst[-1].bind('<FocusOut>', update_coordinates_from_entries)
    coord_widget_lst[-1].bind('<Return>', update_coordinates_from_entries)
    coord_widget_lst[-1].grid(row=0, column=1, padx=5, pady=0, sticky='nw')
    coord_widget_lst.append(tk.Label(settings_frame, text="mm", width=4, anchor="w"))
    coord_widget_lst[-1].grid(row=0, column=2, padx=5, pady=2, sticky='nw')
    coord_widget_lst.append(tk.Label(settings_frame, text="Start y:", width=7, anchor="w"))
    coord_widget_lst[-1].grid(row=1, column=0, padx=5, pady=2, sticky='nw')
    y_start_dv = tk.DoubleVar(root_frame)
    y_start_dv.set(cfg.y_start)
    coord_widget_lst.append(tk.Entry(settings_frame, width=8, font=("Calibri",12), textvariable=y_start_dv,))
    coord_widget_lst[-1].bind('<FocusOut>', update_coordinates_from_entries)
    coord_widget_lst[-1].bind('<Return>', update_coordinates_from_entries)
    coord_widget_lst[-1].grid(row=1, column=1, padx=5, pady=0, sticky='nw')
    coord_widget_lst.append(tk.Label(settings_frame, text="mm", width=4, anchor="w"))
    coord_widget_lst[-1].grid(row=1, column=2, padx=5, pady=2, sticky='nw')
 
    ##### Stop point
    coord_widget_lst.append(tk.Label(settings_frame, text="Stop x:", width=7, anchor="w"))
    coord_widget_lst[-1].grid(row=2, column=0, padx=5, pady=2, sticky='nw')
    x_stop_dv = tk.DoubleVar(root_frame)
    x_stop_dv.set(cfg.x_stop)
    coord_widget_lst.append(tk.Entry(settings_frame, width=8, font=("Calibri",12), textvariable=x_stop_dv,))
    coord_widget_lst[-1].bind('<FocusOut>', update_coordinates_from_entries)
    coord_widget_lst[-1].bind('<Return>', update_coordinates_from_entries)
    coord_widget_lst[-1].grid(row=2, column=1, padx=5, pady=0, sticky='nw')
    coord_widget_lst.append(tk.Label(settings_frame, text="mm", width=4, anchor="w"))
    coord_widget_lst[-1].grid(row=2, column=2, padx=5, pady=2, sticky='nw')
    coord_widget_lst.append(tk.Label(settings_frame, text="Stop y:", width=7, anchor="w"))
    coord_widget_lst[-1].grid(row=3, column=0, padx=5, pady=2, sticky='nw')
    y_stop_dv = tk.DoubleVar(root_frame)
    y_stop_dv.set(cfg.y_stop)
    coord_widget_lst.append(tk.Entry(settings_frame, width=8, font=("Calibri",12), textvariable=y_stop_dv,))
    coord_widget_lst[-1].bind('<FocusOut>', update_coordinates_from_entries)
    coord_widget_lst[-1].bind('<Return>', update_coordinates_from_entries)
    coord_widget_lst[-1].grid(row=3, column=1, padx=5, pady=0, sticky='nw')
    coord_widget_lst.append(tk.Label(settings_frame, text="mm", width=4, anchor="w"))
    coord_widget_lst[-1].grid(row=3, column=2, padx=5, pady=2, sticky='nw')

    ##### x_step
    coord_widget_lst.append(tk.Label(settings_frame, text="x Step:", width=7, anchor="w"))
    coord_widget_lst[-1].grid(row=4, column=0, padx=5, pady=2, sticky='nw')
    x_step_dv = tk.DoubleVar(root_frame)
    x_step_dv.set(cfg.x_step)
    coord_widget_lst.append(tk.Entry(settings_frame, width=8, font=("Calibri",12), textvariable=x_step_dv,))  
    coord_widget_lst[-1].bind('<FocusOut>', on_x_step_changed)
    coord_widget_lst[-1].bind('<Return>', on_x_step_changed)
    coord_widget_lst[-1].grid(row=4, column=1, padx=5, pady=0, sticky='nw')
    coord_widget_lst.append(tk.Label(settings_frame, text="mm", width=4, anchor="w"))
    coord_widget_lst[-1].grid(row=4, column=2, padx=5, pady=2, sticky='nw')

    ##### y_step
    coord_widget_lst.append(tk.Label(settings_frame, text="y Step:", width=7, anchor="w"))
    coord_widget_lst[-1].grid(row=5, column=0, padx=5, pady=2, sticky='nw')
    y_step_dv = tk.DoubleVar(root_frame)
    y_step_dv.set(cfg.y_step)
    coord_widget_lst.append(tk.Entry(settings_frame, width=8, font=("Calibri",12), textvariable=y_step_dv,))  
    coord_widget_lst[-1].bind('<FocusOut>', update_coordinates_from_entries)
    coord_widget_lst[-1].bind('<Return>', update_coordinates_from_entries)
    coord_widget_lst[-1].grid(row=5, column=1, padx=5, pady=0, sticky='nw')
    coord_widget_lst.append(tk.Label(settings_frame, text="mm", width=4, anchor="w"))
    coord_widget_lst[-1].grid(row=5, column=2, padx=5, pady=2, sticky='nw')

    def update_span(*args):
        """Update global frequency span parameters from GUI inputs."""
        if disable_updates_from_entries == 0:
            try:
                cfg.start_freq = float(start_freq_dv.get()) * 1E6
                cfg.stop_freq = float(stop_freq_dv.get()) * 1E6
                cfg.points = int(points_iv.get())
                update_eta_widget()
            except (ValueError, tk.TclError):
                pass

    ##### start_freq
    coord_widget_lst.append(tk.Label(settings_frame, text="Start freq:", width=7, anchor="w"))
    coord_widget_lst[-1].grid(row=6, column=0, padx=5, pady=2, sticky='nw')
    start_freq_dv = tk.DoubleVar(root_frame)
    start_freq_dv.set(cfg.start_freq/1E6)
    coord_widget_lst.append(tk.Entry(settings_frame, width=8, font=("Calibri",12), textvariable=start_freq_dv,))  
    coord_widget_lst[-1].bind('<FocusOut>', update_span)
    coord_widget_lst[-1].bind('<Return>', update_span)
    coord_widget_lst[-1].grid(row=6, column=1, padx=5, pady=0, sticky='nw')
    coord_widget_lst.append(tk.Label(settings_frame, text="MHz", width=4, anchor="w"))
    coord_widget_lst[-1].grid(row=6, column=2, padx=5, pady=2, sticky='nw')

    ##### stop_freq
    coord_widget_lst.append(tk.Label(settings_frame, text="Stop freq:", width=7, anchor="w"))
    coord_widget_lst[-1].grid(row=7, column=0, padx=5, pady=2, sticky='nw')
    stop_freq_dv = tk.DoubleVar(root_frame)
    stop_freq_dv.set(cfg.stop_freq/1E6)
    coord_widget_lst.append(tk.Entry(settings_frame, width=8, font=("Calibri",12), textvariable=stop_freq_dv,))  
    coord_widget_lst[-1].bind('<FocusOut>', update_span)
    coord_widget_lst[-1].bind('<Return>', update_span)
    coord_widget_lst[-1].grid(row=7, column=1, padx=5, pady=0, sticky='nw')
    coord_widget_lst.append(tk.Label(settings_frame, text="MHz", width=4, anchor="w"))
    coord_widget_lst[-1].grid(row=7, column=2, padx=5, pady=2, sticky='nw')

    ##### points TODO not working right now
    coord_widget_lst.append(tk.Label(settings_frame, text="Points:", width=7, anchor="w"))
    coord_widget_lst[-1].grid(row=8, column=0, padx=5, pady=2, sticky='nw')
    points_iv = tk.IntVar(root_frame)
    points_iv.set(cfg.points)
    coord_widget_lst.append(tk.Entry(settings_frame, width=8, font=("Calibri",12), textvariable=points_iv,))  
    points_iv.trace_add('write', update_span)
    coord_widget_lst[-1].grid(row=8, column=1, padx=5, pady=0, sticky='nw')

    def set_average(*args):
        if disable_updates_from_entries == 0:
            try:
                cfg.average = average_iv.get()
                update_eta_widget()
            except (ValueError, tk.TclError):
                pass

    ##### average
    avg_lbl_sv = tk.StringVar(root_frame, value="Average:") # Tracks label text dynamically
    coord_widget_lst.append(tk.Label(settings_frame, textvariable=avg_lbl_sv, width=7, anchor="w"))
    coord_widget_lst[-1].grid(row=9, column=0, padx=5, pady=2, sticky='nw')
    average_iv = tk.IntVar(root_frame)
    average_iv.set(cfg.average)
    coord_widget_lst.append(tk.Entry(settings_frame, width=8, font=("Calibri",12), textvariable=average_iv))  
    average_iv.trace_add('write', set_average)
    coord_widget_lst[-1].grid(row=9, column=1, padx=5, pady=0, sticky='nw')

    ##### sweep time
    def set_sweep_time(*args):
        if disable_updates_from_entries == 0:
            try:
                cfg.sweep_time = sweep_time_iv.get()
                update_eta_widget()
            except (ValueError, tk.TclError):
                pass
    
    coord_widget_lst.append(tk.Label(settings_frame, text="Sweep time:", width=9, anchor="w"))
    coord_widget_lst[-1].grid(row=10, column=0, padx=5, pady=2, sticky='nw')
    sweep_time_iv = tk.IntVar(root_frame)
    sweep_time_iv.set(cfg.sweep_time)
    coord_widget_lst.append(tk.Entry(settings_frame, width=8, font=("Calibri",12), textvariable=sweep_time_iv))  
    sweep_time_iv.trace_add('write', set_sweep_time)
    coord_widget_lst[-1].grid(row=10, column=1, padx=5, pady=0, sticky='nw')

    ##### RBW - Resolution bandwidth TODO This is not ready
    def set_rbw(*args):
        if disable_updates_from_entries == 0:
            try:
                cfg.rbw = rbw_iv.get()
                cfg.rbw_auto = rbw_auto_iv.get()
            except (ValueError, tk.TclError):
                pass

    coord_widget_lst.append(tk.Label(settings_frame, text="Res BW:", width=7, anchor="w"))
    coord_widget_lst[-1].grid(row=11, column=0, padx=5, pady=2, sticky='nw')
    rbw_iv = tk.IntVar(root_frame)
    rbw_iv.set(cfg.rbw)
    coord_widget_lst.append(tk.Entry(settings_frame, width=8, font=("Calibri",12), textvariable=rbw_iv))  
    rbw_iv.trace_add('write', set_rbw)
    coord_widget_lst[-1].grid(row=11, column=1, padx=5, pady=0, sticky='nw')
    coord_widget_lst.append(tk.Label(settings_frame, text="kHz", width=4, anchor="w"))
    coord_widget_lst[-1].grid(row=11, column=2, padx=5, pady=2, sticky='nw')
    ##### RBW - Auto on/off
    rbw_auto_iv = tk.IntVar(root_frame)
    rbw_auto_iv.set(cfg.rbw_auto)
    rbw_auto_check = tk.Checkbutton(settings_frame, width=20, text="Enable RBW auto", variable=rbw_auto_iv, onvalue=1, offvalue=0)
    rbw_auto_iv.trace_add('write', set_rbw)
    rbw_auto_check.grid(row=12, column=0, columnspan=3, sticky='nw')

    ##### Peak detector
    def detector_select(*args):
        global peak_detector
        try:
            peak_detector = peak_detector_iv.get()
        except (ValueError, tk.TclError):
            pass

    peak_detector_iv = tk.IntVar(root_frame)
    peak_detector_iv.trace_add('write', detector_select)
    detector_check = tk.Checkbutton(settings_frame, width=20, text="Enable peak detector", variable=peak_detector_iv, onvalue=1, offvalue=0)
    detector_check.grid(row=13, column=0, columnspan=3, sticky='nw')

    ##### Max hold checkbox
    def toggle_max_hold(*args):
        global max_hold_detector
        try:
            if max_hold_iv.get() == 1:
                avg_lbl_sv.set("Sweeps:")
            else:
                avg_lbl_sv.set("Average:")
            max_hold_detector = max_hold_iv.get()
        except (ValueError, tk.TclError):
            pass

    max_hold_iv = tk.IntVar(root_frame)
    max_hold_iv.trace_add('write', toggle_max_hold)
    maxhold_check = tk.Checkbutton(settings_frame, width=20, text="Enable max hold", variable=max_hold_iv, onvalue=1, offvalue=0)
    maxhold_check.grid(row=14, column=0, columnspan=3, sticky='nw')

    ##### Checkbox for show path
    showpath_iv = tk.IntVar(root_frame)
    showpath_iv.set(1)
    showpath_check = tk.Checkbutton(settings_frame, width=20, text="Show path when scanning", variable=showpath_iv, onvalue=1, offvalue=0)
    showpath_check.grid(row=15, column=0, columnspan=3, sticky='nw')

    def test_scan_speed():
        scan.write("G0 X"+str(cfg.x_start)+" Y"+str(cfg.y_start)+"\n") # Move to start
        cfg.freq_lst = sa.set_span(cfg.start_freq, cfg.stop_freq)
        sa.set_points(cfg.points)
        sweeps_to_take = average_iv.get() if max_hold_iv.get() == 1 else 1
        cfg.average = average_iv.get() if max_hold_iv.get() == 0 else 0
        sa.set_average(cfg.average)
        sa.set_sweep_time(cfg.sweep_time)
        sa.set_rbw(cfg.rbw, cfg.rbw_auto)
        if peak_detector == 1:
            sa.set_peak_detector()
        else:
            sa.set_sample_detector()
        sa.measure_spectrum(sweeps = sweeps_to_take)
        start_ts = datetime.timestamp(datetime.now())
        sa.measure_spectrum(sweeps = sweeps_to_take)
        scan.write("G0 X"+str(cfg.x_start+cfg.x_step)+"\n") # Move one step
        end_ts = datetime.timestamp(datetime.now())
        scan.write("G0 X"+str(cfg.x_start)+" Y"+str(cfg.y_start)+"\n") # Move back to start
        pred_speed_dv.set(round((end_ts - start_ts), 2)) # time to measure one point and move one step (in seconds)
        update_eta_widget()
        sa.local()

    # Create speed prediction frame
    prediction_frame = tk.Frame(left_frame, width=200, height=50)
    prediction_frame.grid(row=6, column=0, padx=5, pady=2)
    pred_button = tk.Button(prediction_frame, text="Test speed", command=test_scan_speed, bg='lightgrey')
    pred_button.grid(row=0, column=0, padx=5, pady=2)
    pred_speed_dv = tk.DoubleVar(root_frame)
    pred_label = tk.Label(prediction_frame, textvariable=pred_speed_dv, width=8, bg='white')
    pred_label.grid(row=0, column=1, padx=5, pady=2)

    predtxt_label = tk.Label(prediction_frame, text="Predicted scan ETA:", )
    predtxt_label.grid(row=1, column=0, columnspan=2, padx=5, pady=2)
    predeta_sv = tk.StringVar(root_frame)
    predeta_label = tk.Label(prediction_frame, textvariable=predeta_sv, width= 17, bg='white')
    predeta_label.grid(row=2, column=0, columnspan=2, padx=5, pady=2)
    progressbar = ttk.Progressbar(prediction_frame, length=150, maximum=100)
    progressbar.grid(row=3, column=0, columnspan=2)

    def eta(): # Calculate and printout of Estimated Time of Arrival
        now_ts = datetime.timestamp(datetime.now())
        start_ts = datetime.timestamp(start_time)
        total_time = (cfg.total_points / done_points) * (now_ts - start_ts)
        eta_time = datetime.fromtimestamp(start_ts + total_time)
        return eta_time.strftime("%Y-%m-%d %H:%M:%S")

    def fake_spectrum(x, y): # Create a fake spectrum in the x, y-coordinate based on a set of input data
        # Faked spectrum consists of a number of Gauss functions
        # Each function is amp(x,y) = a * e^( -1 * ((x-xoffset)^2 + (y-yoffset)^2) / (2 * c^2)) where
        # a = height of peak
        # xoffset, yoffset = position of center of peak in frequency
        # c = standard deviation
        # x, y = spatial coordinates

        # Inner function to calculate spectral contribution from a single aggressor source
        def aggressor_signal(f, x, y, xoffset, yoffset, spatial_width=3.5, 
                             fs_peak=1.5E9, fs_bw=250E6, f_start=40E6, 
                             f_spacing=80E6, peak_bw=5.0E6, amp_fake=30):
            # Spatial amplitude (x & y dependant):
            amp_xy = math.exp(-1 * (((x - xoffset)**2 + (y - yoffset)**2)) / (spatial_width**2))
            # Wide frequency space amplitude like structure resonance (f dependant)
            # will be modulated as one wide gaussian filter applied on a comb of many narrow peaks
            amp_struct = math.exp(-1 * (((f - fs_peak)**2) / (fs_bw**2)))
            # Narrow frequency space amplitude like a comb generator (f dependant)
            amp_comb = math.exp(-1 * (((int(f) % int(f_spacing)) - f_start)**2) / (peak_bw**2))
            # Return calculated signal level above noise floor for this single source
            return amp_fake * amp_xy * amp_struct * amp_comb
        # Basic noise floor of measurements
        noise_floor = -80 # dBm noise floor value
        noise_ampl = 1 # dBm added noise amplitude
        spectrum_lst = []
        for i in range(cfg.points): # for all frequencies in the current span
            f = cfg.freq_lst[i] # current frequency to calculate
            # --- Aggressor Source 1: Primary MCU Clock / Resonance ---
            src1 = aggressor_signal(
                f, x, y,
                xoffset=10.1, yoffset=9.6, spatial_width=3.5,    # Spatial location (mm)
                fs_peak=1.3E9, fs_bw=250E6,                      # Structure resonance (Hz)
                f_start=40E6, f_spacing=80E6, peak_bw=5.0E6,     # Comb harmonics (Hz)
                amp_fake=30                                      # Peak amplitude (dB above noise)
            )
            # --- Aggressor Source 2: Secondary Switching Regulator / High-Freq Source ---
            src2 = aggressor_signal(
                f, x, y,
                xoffset=24.0, yoffset=15.0, spatial_width=5.0,   # Spatial location (mm)
                fs_peak=1.8E9, fs_bw=400E6,                      # Structure resonance (Hz)
                f_start=33E6, f_spacing=33E6, peak_bw=4.0E6,     # Comb harmonics (Hz)
                amp_fake=25                                      # Peak amplitude (dB above noise)
            )
            # Total spectrum value = noise floor + random noise + sum of aggressor sources
            amp_tot = round(noise_floor + noise_ampl * random.random() + src1 + src2, 2)
            spectrum_lst.append(amp_tot)
        return spectrum_lst

    def save_scan_data():
        """Save scan metadata and measurement matrix to a structured JSON/NFS file."""
        timestr = time.strftime("%Y%m%d_%H%M%S")
        filename = new_name_sv.get() + timestr + ".nfs"
        cfg.scanfile1_path = filename # Save filename in globals so "scan_result" can show it.
        # Convert numpy arrays to lists if necessary
        r_matrix = cfg.R.tolist() if isinstance(cfg.R, np.ndarray) else cfg.R
        freq_list = cfg.freq_lst.tolist() if isinstance(cfg.freq_lst, np.ndarray) else list(cfg.freq_lst)

        scan_data = {
            "x_start":         cfg.x_start,         # Start of scan in scanner coordinates
            "y_start":         cfg.y_start,
            "x_stop":          cfg.x_stop,          # Stop of scan (upper boundary) in scanner coordinates
            "y_stop":          cfg.y_stop,
            "x_step":          cfg.x_step,          # mm/step in x-direction
            "y_step":          cfg.y_step,          # mm/step in y-direction
            "image_path":      cfg.image_path,      # Background image filename
            "no_of_calpoints": cfg.no_of_calpoints, # Number of cal points saved 
            "x_img":           list(cfg.x_img),     # image cal coordinates x-axis 
            "y_img":           list(cfg.y_img),     # image cal coordinates y-axis
            "x_scan":          list(cfg.x_scan),    # scanner cal coordinates x-axis
            "y_scan":          list(cfg.y_scan),    # scanner cal coordinates y-axis
            "start_freq":      cfg.start_freq,      # start frequency in Hz
            "stop_freq":       cfg.stop_freq,       # stop frequency in Hz
            "points":          cfg.points,          # number of points in spectrum to measure
            "average":         cfg.average,         # number of SA sweeps to average
            "sweep_time":      cfg.sweep_time,      # sweep time
            "rbw":             cfg.rbw,             # Resolution bandwidth
            "rbw_auto":        cfg.rbw_auto,        # Auto RBW enabled
            "peak_detector":   cfg.peak_detector,   # Peak detector enabled
            "max_hold":        cfg.max_hold,        # max hold detector enabled
            "freq_lst":        cfg.freq_lst,        # list containing frequencies for measured scan points
            "R":               cfg.R                # Measurement matrix with all spatial and frequency points
        }
        with open(filename, 'w') as f:
            json.dump(scan_data, f, indent=2)

    def start_scanning():
        global stop, start_time, done_points, im_overlay, bg_cache, grid_data, mouse_click_cid
        if (len(cfg.image) == 0) or (cfg.x_img[0] == cfg.x_img[1]) or (cfg.y_img[0] == cfg.y_img[1]) or \
            (cfg.x_scan[0] == cfg.x_scan[1]) or (cfg.y_scan[0] == cfg.y_scan[1]):
            print("There is no properly calibrated background image!")
            errorwindow = Toplevel(root_frame)
            errorwindow.title("Error")
            tk.Label(errorwindow, text="There is no properly calibrated background image!").pack()
            if (len(cfg.image) == 0):
                tk.Label(errorwindow, text="There is no image loaded").pack()
            if (cfg.x_img[0] == cfg.x_img[1]):
                tk.Label(errorwindow, text="Image x-calibration coordinates [0] & [1] are the same"+str(cfg.x_img[0])).pack()
            if (cfg.y_img[0] == cfg.y_img[1]):
                tk.Label(errorwindow, text="Image y-calibration coordinates [0] & [1] are the same"+str(cfg.y_img[0])).pack()
            if (cfg.x_scan[0] == cfg.x_scan[1]):
                tk.Label(errorwindow, text="Scanner x-calibration coordinates [0] & [1] are the same"+str(cfg.x_scan[0])).pack()
            if (cfg.y_scan[0] == cfg.y_scan[1]):
                tk.Label(errorwindow, text="Scanner y-calibration coordinates [0] & [1] are the same"+str(cfg.y_scan[0])).pack()
            tk.Button(errorwindow, text="  OK  ", command=errorwindow.destroy).pack()
            return False # There is no point in starting a scan if there is not a properly calibrated image
        if mouse_click_cid is not None:
            fig.canvas.mpl_disconnect(mouse_click_cid) # Disconnect mouse input when scanning
            mouse_click_cid = None
        stop = 0
        stop_button.configure(bg='tomato') 
        start_button.configure(bg='white')
        done_points = 0
        grid_data = None
        refresh_window(root_frame)  # Ensure window is freshly drawn
        cfg.freq_lst = sa.set_span(cfg.start_freq, cfg.stop_freq)
        print(cfg.start_freq, cfg.stop_freq)
        sa.set_points(cfg.points)
        sa.set_rbw(cfg.rbw, cfg.rbw_auto)
        sweeps_to_take = average_iv.get() if max_hold_iv.get() == 1 else 1
        cfg.average = average_iv.get() if max_hold_iv.get() == 0 else 0
        sa.set_average(cfg.average)
        if peak_detector == 1:
            sa.set_peak_detector()
        else:
            sa.set_sample_detector()
        no_of_x_step = math.floor((cfg.x_stop-cfg.x_start) / cfg.x_step) + 1     # number of x steps
        no_of_y_step = math.floor((cfg.y_stop-cfg.y_start) / cfg.y_step) + 1 
        cfg.total_points = no_of_x_step * no_of_y_step # Needed by eta()
        scan.write("G0 X" + str(cfg.x_start) + " Y" + str(cfg.y_start) + "\n") # Go to start position before registring the start_time
        start_time = datetime.now() # Needed by eta()
        R = [[0]*no_of_x_step for _ in range(no_of_y_step)] # Creating an (empty) result 2D-vector

        def measure_one_point(curr_x, curr_y):
            global done_points, im_overlay, bg_cache, grid_data
            xcoord = round(cfg.x_start + curr_x * cfg.x_step, 2)
            scan.write("G0 X" + str(xcoord) + "\n") # A positioning move at the "Rapid Feed Rate".
            
            if (scan.scanner_handle == 0) or (sa.specanalyzer == 0):
                R[curr_y][curr_x] = fake_spectrum(cfg.x_start + curr_x * cfg.x_step, cfg.y_start + curr_y * cfg.y_step)
            else:
                R[curr_y][curr_x] = sa.measure_spectrum(sweeps = sweeps_to_take)
                
            peak_val = max(R[curr_y][curr_x]) # Store peak value of recently measured spectrum

            if showpath_iv.get() == 1:
                if im_overlay is None or bg_cache is None:
                    refresh_window(root_frame) # Fallback if overlay or background doesn't exist yet

                grid_data[curr_y, curr_x] = peak_val
                im_overlay.set_data(grid_data)

                # Dynamically update color bounds based on measured values so far
                valid_vals = grid_data[~np.isnan(grid_data)]
                v_min, v_max = np.min(valid_vals), np.max(valid_vals)
                if v_min == v_max:
                    v_min -= 1
                    v_max += 1
                im_overlay.set_clim(v_min, v_max)

                canvas.restore_region(bg_cache) # Blit background image data
                im_overlay.axes.draw_artist(im_overlay)
                canvas.blit(fig.bbox)
                root_frame.update_idletasks()

            done_points += 1  # Needed by eta()
            predeta_sv.set(eta()) # Printout the ETA for current scan
            progressbar['value'] = 100 * (done_points / cfg.total_points)
            prediction_frame.update()

        for y in range(0, no_of_y_step, 2):
            # Forward pass (even row y)
            ycoord = round(cfg.y_start + y * cfg.y_step, 2)
            scan.write("G0 Y" + str(ycoord) + "\n")
            for x in range(no_of_x_step):
                if stop == 1:
                    break
                measure_one_point(x, y)

            # Backward pass (odd row y + 1)
            if y + 1 < no_of_y_step:
                ycoord = round(cfg.y_start + (y + 1) * cfg.y_step, 2)
                if(ycoord > cfg.y_stop):
                    break
                scan.write("G0 Y" + str(ycoord) + "\n")
                for x in range(no_of_x_step-1, -1, -1): # from no_of_x_step down to zero
                    if stop == 1:
                        break
                    measure_one_point(x, y+1)
            if stop == 1:
                break

        # scan.write("G0 X0. Y0.\n") # Go back to origin when scan is done
        cfg.R = R.copy() # copy result to global variables
        save_scan_data()
        save_calibration() # save the scan_config.py file with calibration data including the filename of the scan data
        # refresh_window(root_frame) # And refresh to remove the graphics
        sa.local()
        start_button.configure(bg='lightgreen')
        stop_button.configure(bg='white')
        if mouse_click_cid is None and fig is not None:
            mouse_click_cid = fig.canvas.mpl_connect('button_press_event', mouse_event) # Reconnect mouse events

    def stop_scanning():
        global stop, mouse_click_cid
        stop_button.configure(bg='white') 
        start_button.configure(bg='lightgreen')
        stop = 1
        if mouse_click_cid is None and fig is not None:
            mouse_click_cid = fig.canvas.mpl_connect('button_press_event', mouse_event) # Reconnect mouse events

   # Create start/stop buttons frame
    start_frame = tk.Frame(left_frame, width=200, height=50)
    start_frame.grid(row=7, column=0, padx=5, pady=2)
    start_button = tk.Button(start_frame, text='Start', command=start_scanning, bg='lightgreen')
    start_button.grid(row=0, column=0, padx=5, pady=2)
    stop_button = tk.Button(start_frame, text="Stop", command=stop_scanning, bg='white') # Button will change to 'tomato' when scanning
    stop_button.grid(row=0, column=1, padx=5, pady=2)

##    # Debuging buttons
##    debug_frame = tk.Frame(left_frame, width=200, height=100)
##    debug_frame.grid(row=20, column=0, padx=2, pady=5, sticky='nw')
##    debug5_widget = tk.Button(debug_frame, text="Print scan_config", command=print_scan_config)
##    debug5_widget.grid(row=2, column=0, padx=5, pady=0)

def on_image_frame_resize(event):
    global fig, canvas, last_width, last_height
    # Only handle configure events coming directly from image_frame
    if event.widget == image_frame:
        new_w = event.width
        new_h = event.height
        if new_w < 50 or new_h < 50: # Ignore invalid or tiny initial render sizes
            return
        # Only update if dimensions actually changed (stops loops!)
        if new_w != last_width or new_h != last_height:
            last_width = new_w
            last_height = new_h
            fig_dpi = 100
            # Convert exact available pixels into inches for Matplotlib
            fig.set_size_inches(new_w / fig_dpi, new_h / fig_dpi)
            refresh_window(root_frame)

def enable_dynamic_resize(window):
    global main_window
    main_window = window
    # Bind directly to image_frame rather than top-level window
    image_frame.bind("<Configure>", on_image_frame_resize)

if __name__ == '__main__': # Standalone init and enable for manual control
    root = tk.Tk()  # create root window
    root.title("Execute Scan stand alone test module")
    if(cfg.scanner_comport != ""):
        scan.init(cfg.scanner_comport) # Init xy_scanner
    if(cfg.sa_address != ""):
        rm = pyvisa.ResourceManager()
        sa.init(rm, cfg.sa_address) # Init spectrum analyzer
    execute_scan(root)
    enable_dynamic_resize(root)
    root.mainloop()
