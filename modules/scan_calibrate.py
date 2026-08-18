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
# This is the calibration module of the near filed scaner application.
# This is where a background image is loaded (preferably the component
# placement drawing in black on white background. Two points are selected
# in the image and scanner coordainates are assigned to thouse points.

import tkinter as tk
from tkinter import filedialog, ttk
import os
import sys
import matplotlib.image as img
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg 
import math
import numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import scan_config as cfg # To hold global variables
from hardware import xy_scanner as scan

# Global variables
jog_step = 0
x_pos, y_pos, z_pos = 0.0, 0.0, 0.0
img_xmin, img_ymin, img_xmax, img_ymax = 0, 0, 0, 0
pan_xmin, pan_ymin, pan_xmax, pan_ymax = 0, 0, 0, 0
panstart_x, panstart_y, pan_active = 0.0, 0.0, 0
fig, canvas, mouse_motion_cid = 0, 0, 0
main_window, root_frame, left_frame, image_frame = 0, 0, 0, 0
x_img_iv, y_img_iv = [], [] # List of IntVar for x_img, y_img coordinates
x_scan_dv, y_scan_dv = [], [] # List of DoubleVar for x_scan, y_scan coordinates
selected_file_label = None # cfg.image_path
disable_updates_from_entries = 0
last_width, last_height = 0, 0
image_rotation = 0
open_button = None
jog_step = 0.0
jog_step_buttons = []  # Stores references to jog_step selector buttons
rotate_icon = None

# Global constants
color_2 = ['#FF9080', '#FFE280', '#80FF90', '#A080FF']
color_1 = ['#FF1000', '#FFA810', '#00FF10', '#2000FF']

def open_imagefile():
    global img_xmin, img_ymin, img_xmax, img_ymax
    if cfg.image_path and cfg.image_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
        try:
            cfg.image = img.imread(os.path.join('background_images', cfg.image_path))
            img_xmin, img_ymin = 0, 0 
            img_xmax = cfg.image.shape[1] # image.shape[1} is x-size shape of image (width)
            img_ymax = cfg.image.shape[0] # image.shape[0] is y-size shape of image (height)
            refresh_window(root_frame)
            return True
        except Exception as e:
            print(f"Error loading image {os.path.join('background_images', cfg.image_path)}: {e}")
            cfg.image = []
            img_xmin, img_ymin, img_xmax, img_ymax = 0, 0, 0, 0
            refresh_window(root_frame)
            return False
    else:
        print(f"open_imagefile: Failed {cfg.image_path}")
        cfg.image = []
        img_xmin, img_ymin, img_xmax, img_ymax = 0, 0, 0, 0
        refresh_window(root_frame)
        return False

def is_calibration_valid():
    """Checks if P0 and P1 form a valid, non-zero calibration bounding box."""
    if cfg.no_of_calpoints < 2:
        return False
    dx_img = cfg.x_img[1] - cfg.x_img[0]
    dy_img = cfg.y_img[1] - cfg.y_img[0]
    dx_scan = cfg.x_scan[1] - cfg.x_scan[0]
    dy_scan = cfg.y_scan[1] - cfg.y_scan[0]
    # Guard against division by zero (points on the same horizontal or vertical line)
    if dx_img == 0 or dy_img == 0 or dx_scan == 0 or dy_scan == 0:
        return False
    return True

def img_to_scan(x_pixel, y_pixel):
    """Forward Transform: Image Pixels -> Scanner mm"""
    scale_x = (cfg.x_scan[1] - cfg.x_scan[0]) / (cfg.x_img[1] - cfg.x_img[0])
    scale_y = (cfg.y_scan[1] - cfg.y_scan[0]) / (cfg.y_img[1] - cfg.y_img[0])
    x_mm = cfg.x_scan[0] + (x_pixel - cfg.x_img[0]) * scale_x
    y_mm = cfg.y_scan[0] + (y_pixel - cfg.y_img[0]) * scale_y
    return round(x_mm, 1), round(y_mm, 1)

def scan_to_img(x_mm, y_mm):
    """Inverse Transform: Scanner mm -> Image Pixels"""
    scale_x = (cfg.x_img[1] - cfg.x_img[0]) / (cfg.x_scan[1] - cfg.x_scan[0])
    scale_y = (cfg.y_img[1] - cfg.y_img[0]) / (cfg.y_scan[1] - cfg.y_scan[0])
    x_pixel = cfg.x_img[0] + (x_mm - cfg.x_scan[0]) * scale_x
    y_pixel = cfg.y_img[0] + (y_mm - cfg.y_scan[0]) * scale_y
    return int(round(x_pixel, 0)), int(round(y_pixel, 0))

def enable_dynamic_resize(window): # Enable dynamic window resize_window for scan_calibrate
    """Enable dynamic window resize for scan_calibrate."""
    global main_window
    main_window = window
    main_window.bind("<Configure>", on_image_frame_resize)

def rotate_image_ccw():
    """Rotate image matrix 90 degrees CCW and update calibration coordinates."""
    global img_xmin, img_ymin, img_xmax, img_ymax, image_rotation
    if len(cfg.image) == 0:
        return
    orig_width = cfg.image.shape[1]
    # Rotate image array 90 degrees CCW
    cfg.image = np.ascontiguousarray(np.rot90(cfg.image, k=1))
    # Transform existing calibration markers to match the new image orientation
    for i in range(cfg.no_of_calpoints):
        old_x = cfg.x_img[i]
        old_y = cfg.y_img[i]
        cfg.x_img[i] = old_y
        cfg.y_img[i] = orig_width - old_x
        x_img_iv[i].set(cfg.x_img[i])
        y_img_iv[i].set(cfg.y_img[i])
    # Update cumulative rotation angle
    image_rotation = (image_rotation + 90) % 360
    # Reset image extent bounds to new orientation dimensions
    img_xmin, img_ymin = 0, 0
    img_xmax = cfg.image.shape[1]
    img_ymax = cfg.image.shape[0]
    adjust_aspect()

def on_image_frame_resize(event):
    """Fired automatically when image_frame changes size."""
    global fig, canvas, last_width, last_height
    if event.widget == image_frame:
        new_w, new_h = event.width, event.height

        # Ignore tiny/invalid initial frame renders
        if new_w < 50 or new_h < 50:
            return

        # Only resize Matplotlib figure if dimensions actually changed
        if new_w != last_width or new_h != last_height:
            last_width = new_w
            last_height = new_h

            fig_dpi = 100
            fig.set_size_inches(new_w / fig_dpi, new_h / fig_dpi)
            adjust_aspect()

def get_btn_label():
    """Format the button text based on current cfg.image_path."""
    return f"{cfg.image_path}" if cfg.image_path else "Open background file..."

def reset_jog_step():
    """Reset jog step size to 0.0 and clear button highlights."""
    global jog_step
    jog_step = 0.0
    for btn in jog_step_buttons:
        if btn:
            btn.config(bg='lightgrey')

def update_fields_from_globals(): # Update all the widget fields (Entry's) from global varaibles
    global x_img_iv, y_img_iv, x_scan_dv, y_scan_dv, selected_file_label
    global disable_updates_from_entries, open_button
    reset_jog_step()  # Reset jog step size on tab focus/refresh
    disable_updates_from_entries = 1
    for i in range(4):
        x_img_iv[i].set(cfg.x_img[i])
        y_img_iv[i].set(cfg.y_img[i])
        x_scan_dv[i].set(cfg.x_scan[i])
        y_scan_dv[i].set(cfg.y_scan[i])
    open_imagefile() # Reload/clear image state first
    if open_button:
        open_button.config(text=get_btn_label())
    open_imagefile()
    disable_updates_from_entries = 0
    root_frame.update()

def image_scroll(event): # This event occur when scrollwheel is rotated or when a two finger up/down motion on the mousepad is performed
    global img_xmin, img_ymin, img_xmax, img_ymax
    if event.button == 'up': # Zoom in
        img_xmin += int(round((event.xdata - img_xmin) * 0.1, 0))
        img_xmax -= int(round((img_xmax - event.xdata) * 0.1, 0))
        img_ymin += int(round((event.ydata - img_ymin) * 0.1, 0))
        img_ymax -= int(round((img_ymax - event.ydata) * 0.1, 0))
    if event.button == 'down': # Zoom out
        img_xmin -= int(round((event.xdata - img_xmin) * 0.1, 0))
        img_xmax += int(round((img_xmax - event.xdata) * 0.1, 0))
        img_ymin -= int(round((event.ydata - img_ymin) * 0.1, 0))
        img_ymax += int(round((img_ymax - event.ydata) * 0.1, 0))
    adjust_aspect()

def adjust_aspect(): # Aspect correction (filing the frame)
    global img_xmin, img_xmax, img_ymin, img_ymax
    if len(cfg.image) == 0:
        return # No purpose in adjusting if there is no image
    if (img_xmax == 0) and (img_ymax == 0): # Something went wrong during previous open_imagefile. cfg_image_path was still = "" TODO fix this issue
        open_imagefile()
    zoom_img_aspect = (img_xmax - img_xmin) / (img_ymax - img_ymin)
    frame_aspect =  (root_frame.winfo_width() - left_frame.winfo_width()) / (root_frame.winfo_height())
    if zoom_img_aspect < frame_aspect: # image should get wider
        delta_x = int(round((frame_aspect * (img_ymax - img_ymin) - img_xmax + img_xmin) / 2, 0))
        img_xmax += delta_x
        img_xmin -= delta_x
    if zoom_img_aspect > frame_aspect: # image should get higher
        delta_y = int(round(((img_xmax - img_xmin) / frame_aspect - img_ymax + img_ymin) / 2, 0))
        img_ymax += delta_y
        img_ymin -= delta_y

    # Limit the amount of zoom out
    if img_xmin < 0:
        img_xmin = 0
    if img_xmax > cfg.image.shape[1]: 
        img_xmax = cfg.image.shape[1]
    if img_ymin < 0: 
        img_ymin = 0
    if img_ymax > cfg.image.shape[0]: 
        img_ymax = cfg.image.shape[0]
    refresh_window(root_frame) # redraw image with new zoom scale

def refresh_window(root_frame):
    fig.clear()
    if len(cfg.image) != 0:
        fig.clear()
        subplot1 = fig.add_subplot()
        subplot1.scatter(cfg.x_img[0:cfg.no_of_calpoints], cfg.y_img[0:cfg.no_of_calpoints],
                            c=color_1[0:cfg.no_of_calpoints], alpha=0.5, s=50) # Draw spatial markers with image coordinates
        subplot1.imshow(cfg.image, cmap="gray", alpha=1.0, origin="upper") # Draw image
        subplot1.imshow([[0,0],[0,0]], alpha=0.0, origin='upper', extent=[img_xmin, img_xmax, img_ymax, img_ymin]) # zoom image [from-x, to-x, to-y, from-y]
        fig.tight_layout()
    canvas.draw()
    root_frame.update()

def on_img_entry_changed(point_idx):
    """Triggered when an Image coordinate Entry loses focus or receives Return."""
    if disable_updates_from_entries:
        return
    try:
        cfg.x_img[point_idx] = int(x_img_iv[point_idx].get())
        cfg.y_img[point_idx] = int(y_img_iv[point_idx].get())

        # If P0 or P1 changed, re-sync P2 and P3 scanner positions
        if point_idx < 2 and is_calibration_valid():
            for p in range(2, cfg.no_of_calpoints):
                x_mm, y_mm = img_to_scan(cfg.x_img[p], cfg.y_img[p])
                cfg.x_scan[p] = x_mm
                cfg.y_scan[p] = y_mm
                x_scan_dv[p].set(x_mm)
                y_scan_dv[p].set(y_mm)
        # If P2 or P3 changed, update its Scanner field
        elif point_idx >= 2 and is_calibration_valid():
            x_mm, y_mm = img_to_scan(cfg.x_img[point_idx], cfg.y_img[point_idx])
            cfg.x_scan[point_idx] = x_mm
            cfg.y_scan[point_idx] = y_mm
            x_scan_dv[point_idx].set(x_mm)
            y_scan_dv[point_idx].set(y_mm)
        refresh_window(root_frame)
    except (ValueError, tk.TclError):
        update_fields_from_globals()

def on_scan_entry_changed(point_idx):
    """Triggered when a Scanner coordinate Entry loses focus or receives Return."""
    if disable_updates_from_entries:
        return
    try:
        cfg.x_scan[point_idx] = round(float(x_scan_dv[point_idx].get()), 1)
        cfg.y_scan[point_idx] = round(float(y_scan_dv[point_idx].get()), 1)

        # If P0 or P1 changed, re-sync P2 and P3
        if point_idx < 2 and is_calibration_valid():
            for p in range(2, cfg.no_of_calpoints):
                x_mm, y_mm = img_to_scan(cfg.x_img[p], cfg.y_img[p])
                cfg.x_scan[p] = x_mm
                cfg.y_scan[p] = y_mm
                x_scan_dv[p].set(x_mm)
                y_scan_dv[p].set(y_mm)
        # Reverse Transform: If P2 or P3 scanner field was manually typed, update Image field
        elif point_idx >= 2 and is_calibration_valid():
            x_px, y_px = scan_to_img(cfg.x_scan[point_idx], cfg.y_scan[point_idx])
            cfg.x_img[point_idx] = x_px
            cfg.y_img[point_idx] = y_px
            x_img_iv[point_idx].set(x_px)
            y_img_iv[point_idx].set(y_px)
        refresh_window(root_frame)
    except (ValueError, tk.TclError):
        update_fields_from_globals()

def mouse_event(event): # Mouse button event
    global panstart_x, panstart_y, pan_active, pan_xmin, pan_ymin, pan_xmax, pan_ymax, mouse_motion_cid
    if (event.button == 2): # Center button is pressed -> start panning
        panstart_x = event.x # data
        panstart_y = event.y # data
        pan_active = 1
        pan_xmin, pan_ymin, pan_xmax, pan_ymax = img_xmin, img_ymin, img_xmax, img_ymax # Save image extent when pan is started
        mouse_motion_cid = fig.canvas.mpl_connect('motion_notify_event', pan_image)
        return # Exit this event handler ASAP if panning is activated
    if event.xdata is None or event.ydata is None:
        return
    closest = 10000
    point = 10
    for i in range(cfg.no_of_calpoints): # look at all calibration points
        distance = math.hypot(cfg.x_img[i]-event.xdata, cfg.y_img[i]-event.ydata) # check distanse from points
        if (distance < 100) and (distance < closest):
            closest = distance
            point = i
    if point < 5: # at least one close point is found and the closest is "i"
        if event.button == 1: # left click, check if close to point -> move that point
            x_px = int(round(event.xdata, 0))
            y_px = int(round(event.ydata, 0))
            cfg.x_img[point] = x_px
            cfg.y_img[point] = y_px
            x_img_iv[point].set(x_px)
            y_img_iv[point].set(y_px)
            if point >= 2 and is_calibration_valid(): # Auto calculate coordinates for P2 / P3
                x_mm, y_mm = img_to_scan(x_px, y_px)
                cfg.x_scan[point] = x_mm
                cfg.y_scan[point] = y_mm
                x_scan_dv[point].set(x_mm)
                y_scan_dv[point].set(y_mm)
            refresh_window(root_frame)

        elif (event.button == 3) and (cfg.no_of_calpoints > 0): # right click -> remove point
            cfg.no_of_calpoints -= 1
            cfg.x_img.append(0)
            cfg.y_img.append(0)
            del cfg.x_img[point], cfg.y_img[point] # Remove point from image lists
            cfg.x_scan.append(0.0)
            cfg.y_scan.append(0.0)
            del cfg.x_scan[point], cfg.y_scan[point] # Remove point from scanner lists
            update_fields_from_globals() # Update Entry widgets and redraw canvas
            refresh_window(root_frame)
    elif event.button == 1 and cfg.no_of_calpoints < 4: # left click -> add point if points are fewer than 4
        idx = cfg.no_of_calpoints
        x_px = int(round(event.xdata, 0))
        y_px = int(round(event.ydata, 0))
        cfg.x_img[idx] = x_px
        cfg.y_img[idx] = y_px
        x_img_iv[idx].set(x_px)
        y_img_iv[idx].set(y_px)
        if idx >= 2 and is_calibration_valid(): # Auto-fill coordinates if calibration is active
            x_mm, y_mm = img_to_scan(x_px, y_px)
            cfg.x_scan[idx] = x_mm
            cfg.y_scan[idx] = y_mm
            x_scan_dv[idx].set(x_mm)
            y_scan_dv[idx].set(y_mm)
        cfg.no_of_calpoints += 1
        refresh_window(root_frame)

def button_release(event): # Mouse button released
    global pan_active
    if (event.button == 2): # Center button is released (stop panning)
        pan_active = 0
        fig.canvas.mpl_disconnect(mouse_motion_cid) # Disconnect motion_notify_event

def pan_image(event): # This is the motion_notify_event. Event is connected only when middle button is pressed and still hold.
    global panstart_x, panstart_y, img_xmin, img_xmax, img_ymin, img_ymax
    if pan_active == 1:
        delta_x = int(round(panstart_x - event.x, 0))
        delta_y = -1 * int(round(panstart_y - event.y, 0))
        # Limit the amount of panning
        if (pan_xmin + delta_x) < 0: # Not OK to pan the entire delta_x
            delta_x = -pan_xmin
        if (pan_xmax + delta_x) > cfg.image.shape[1]: # Not OK to pan the entire delta_x
            delta_x = cfg.image.shape[1] - pan_xmax
        if (pan_ymin + delta_y) < 0: # Not OK to pan the entire delta_y
            delta_y = -pan_ymin
        if (pan_ymax + delta_y) > cfg.image.shape[0]: # Not OK to pan the entire delta_x
            delta_y = cfg.image.shape[0] - pan_ymax
        img_xmin = pan_xmin + delta_x
        img_xmax = pan_xmax + delta_x
        img_ymin = pan_ymin + delta_y
        img_ymax = pan_ymax + delta_y
        refresh_window(root_frame) # redraw image panorated to the new coordiantes

def save_calibration():
    global image_rotation
    # Save rotated image file if rotated by 90, 180, or 270 degrees
    if image_rotation in (90, 180, 270) and len(cfg.image) > 0:
        base_name, _ = os.path.splitext(cfg.image_path)
        new_image_path = f"{base_name}_{image_rotation}.png"
        img.imsave(os.path.join('background_images', new_image_path), cfg.image) # Save rotated array as PNG file
        cfg.image_path = new_image_path # Update global path
        image_rotation = 0 # reset rotation tracker
        if open_button:
            open_button.config(text=get_btn_label())
            
    # Aspect Ratio Sanity Check
    if is_calibration_valid():
        scale_x = abs((cfg.x_scan[1] - cfg.x_scan[0]) / (cfg.x_img[1] - cfg.x_img[0]))
        scale_y = abs((cfg.y_scan[1] - cfg.y_scan[0]) / (cfg.y_img[1] - cfg.y_img[0]))
        aspect_ratio = scale_x / scale_y
        if aspect_ratio < 0.5 or aspect_ratio > 2.0:
            warn_win = tk.Toplevel(root_frame)
            warn_win.title("Calibration Warning")
            tk.Label(warn_win, text="WARNING: Unreasonable Aspect Ratio!", font=("Calibri", 12, "bold"), fg="red").pack(padx=10, pady=5)
            tk.Label(warn_win, text=f"Pixel scale ratio (X/Y) is {aspect_ratio:.2f}.").pack(padx=10, pady=2)
            tk.Label(warn_win, text="Please double-check P0 and P1 calibration coordinates.").pack(padx=10, pady=5)
            tk.Button(warn_win, text=" OK ", command=warn_win.destroy).pack(pady=5)
            # We still allow saving, but the user is explicitly warned!

    print("save_calibration")
    with open("scan_config.py", "w") as f:
        f.write("app_version =      \"" + cfg.app_version + "\"\n") # Application version string
        f.write("scanner_comport =  \"" + str(cfg.scanner_comport)+"\"\n")
        f.write("sa_model =         \"" + str(cfg.sa_model)+"\"\n")
        f.write("sa_address =       \"" + str(cfg.sa_address)+"\"\n") # 320 is maximum
        f.write("proj_name_path =   \"" + str(cfg.proj_name_path)+"\"\n") # 150 is maximum
        f.write("image_path =       \"" + cfg.image_path+"\"\n")
        f.write("image =            []\n")
        f.write("no_of_calpoints =  " + str(cfg.no_of_calpoints)+"\n") # mm/step in x-direction
        f.write("x_img =            " + str(cfg.x_img)+"\n") # image cal coordinates x-axis 
        f.write("y_img =            " + str(cfg.y_img)+"\n") # image cal coordinates y-axis
        f.write("x_scan =           " + str(cfg.x_scan)+"\n") # scanner cal coordinates x-axis
        f.write("y_scan =           " + str(cfg.y_scan)+"\n") # scanner cal coordinates y-axis
        f.write("scanfile1_path =   \"" + str(cfg.scanfile1_path)+"\"\n") # scanner cal coordinates x-axis
        f.write("scanfile2_path =   \"" + str(cfg.scanfile2_path)+"\"\n") # scanner cal coordinates y-axis
        f.write("total_points =     " + str(cfg.total_points)+"\n") # scanner cal coordinates y-axis
        f.write("x_start =          " + str(cfg.x_start)+"\n") # scanner cal coordinates y-axis
        f.write("y_start =          " + str(cfg.y_start)+"\n") # scanner cal coordinates y-axis
        f.write("x_stop =           " + str(cfg.x_stop)+"\n") # scanner cal coordinates y-axis
        f.write("y_stop =           " + str(cfg.y_stop)+"\n") # scanner cal coordinates y-axis
        f.write("x_step =           " + str(cfg.x_step)+"\n") # scanner cal coordinates y-axis
        f.write("y_step =           " + str(cfg.y_step)+"\n") # scanner cal coordinates y-axis
        f.write("start_freq =       " + str(cfg.start_freq)+"\n") # start frequency 
        f.write("stop_freq =        " + str(cfg.stop_freq)+"\n") # stop frequency
        f.write("points =           " + str(cfg.points)+"\n") # number of points in spectrum to measure 
        f.write("average =          " + str(cfg.average)+"\n") # number of measurements to average
        f.write("rbw =              " + str(cfg.rbw)+"\n") # resolution bandwidth
        f.write("rbw_auto =         " + str(cfg.rbw_auto)+"\n") # resolution bandwidth auto (0 or 1)
        f.write("sweep_time =       " + str(cfg.sweep_time)+"\n") # Sweep time
        f.write("peak_detector =    " + str(cfg.peak_detector)+"\n") # Peak detector receiver
        f.write("max_hold =         " + str(cfg.max_hold)+"\n") # Max hold receiver for time intermittent agressors
        f.write("freq_lst =         []\n") # list containing frequencies for measured scan points
        f.write("R =                []\n") # Measured data for all spatial and frequency points
        f.write("S =                []\n") # Measured data for all spatial and frequency points

# ****************************************************************************************************
#  # This is the main routine in the scan_calibrate module that calibrates the layout image
# ****************************************************************************************************
def calibrate(frame): # This is the main routine of the scan_calibrate module that can calibrate a background image
    global jog_step, x_pos, y_pos, z_pos, img_xmin, img_ymin, img_xmax, img_ymax, selected_file_label
    global fig, canvas, root_frame, left_frame, image_frame, x_img_iv, y_img_iv, x_scan_dv, y_scan_dv
    global jog_step_buttons, open_button, rotate_icon
    root_frame = frame
    root_frame.columnconfigure(0, weight=0)  # left_frame takes content width
    root_frame.columnconfigure(1, weight=1)  # image_frame expands to fill tab space
    root_frame.rowconfigure(0, weight=1)

    # Create left frame
    left_frame = tk.Frame(root_frame)
    left_frame.grid(row=0, column=0, padx=2, pady=2, sticky='nw')

    # Create file selection frame
    file_frame = tk.Frame(left_frame)
    file_frame.grid(row=0, column=0, padx=2, pady=2, sticky='nw')

    # Create image frame
    image_frame = tk.Frame(root_frame)
    image_frame.grid(row=0, column=1, padx=5, pady=2, sticky='nsew')
    image_frame.columnconfigure(0, weight=1)
    image_frame.rowconfigure(0, weight=1)    

    fig = Figure(dpi=100) # Size is dynamic
    canvas = FigureCanvasTkAgg(fig, master = image_frame)
    canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')

    fig.canvas.mpl_connect('button_press_event', mouse_event) # Adding and removing calibration points, start panning with mid button
    fig.canvas.mpl_connect('scroll_event', image_scroll) # Zooming of the image
    fig.canvas.mpl_connect('button_release_event', button_release) # Stop the panning when mid mouse button is released
    refresh_window(root_frame)

    # Create file selection frame
    file_frame = tk.Frame(left_frame, width=180, height=40)
    file_frame.grid(row=0, column=0, padx=2, pady=2)
    open_imagefile()

    def open_imagefile_dialog():
        selected = filedialog.askopenfilename(title="Select Background Image", filetypes=[("PNG files", "*.png")])
        if selected:
            cfg.image_path = os.path.basename(selected)
            open_button.config(text=get_btn_label())
            open_imagefile()

    # Combined Filename & Open Button
    open_button = tk.Button(
        file_frame, 
        text=get_btn_label(), 
        width=22, 
        anchor="w", 
        relief="raised", 
        bg="#ffffff",
        activebackground="#e1e1e1",
        command=open_imagefile_dialog
    )
    open_button.grid(row=0, column=0, padx=2, pady=0)

    # Lazy-load rotate_icon bound to main root window
    if rotate_icon is None:
        rotate_icon = tk.PhotoImage(file=os.path.join('assets', 'rotate_image_20x20.png'))

    # Create rotation button
    rotate_button = tk.Button(file_frame, image=rotate_icon, command=rotate_image_ccw)
    rotate_button.image = rotate_icon
    rotate_button.grid(row=0, column=2, padx=2, pady=0)
    
    # Create coordinate list frame
    coord_frame = tk.Frame(left_frame, width=200, height=400)
    coord_frame.grid(row=1, column=0, padx=2, pady=2)

    coord_widget_lst = [] # List of all type of tkinter widgets in the coord_frame
    py = 2
    x_img_iv.clear()
    y_img_iv.clear()
    x_scan_dv.clear()
    y_scan_dv.clear()
    
    while len(cfg.x_img) < 4:
        cfg.x_img.append(0)
        cfg.y_img.append(0)
        cfg.x_scan.append(0)
        cfg.y_scan.append(0)
    # Create labels and entrys in coord_frame
    for i in range(4): # For all four sets of coordinate pairs
        coord_widget_lst.append(tk.Label(coord_frame, bg=color_2[i], text="Image xy:", width=8, anchor="w"))
        coord_widget_lst[-1].grid(row=4*i, column=0, padx=5, pady=py, sticky='nw')
        x_img_iv.append(tk.IntVar(root_frame))
        coord_widget_lst.append(tk.Entry(coord_frame, textvariable=x_img_iv[i], width=6, font=("Calibri",12)))
        x_img_iv[-1].set(cfg.x_img[i]) # Default value of scanner coordinate
        coord_widget_lst[-1].bind('<FocusOut>', lambda e, idx=i: on_img_entry_changed(idx))
        coord_widget_lst[-1].bind('<Return>', lambda e, idx=i: on_img_entry_changed(idx))
        coord_widget_lst[-1].grid(row=4*i, column=1, padx=5, pady=0)
        y_img_iv.append(tk.IntVar(root_frame))
        coord_widget_lst.append(tk.Entry(coord_frame, textvariable=y_img_iv[i], width=6, font=("Calibri",12)))
        y_img_iv[-1].set(cfg.y_img[i])  # Default value of scanner coordinate
        coord_widget_lst[-1].bind('<FocusOut>', lambda e, idx=i: on_img_entry_changed(idx))
        coord_widget_lst[-1].bind('<Return>', lambda e, idx=i: on_img_entry_changed(idx))
        coord_widget_lst[-1].grid(row=4*i, column=2, padx=5, pady=0)

        coord_widget_lst.append(tk.Label(coord_frame, bg=color_2[i], text="Scanner xy:", width=8, anchor="w"))
        coord_widget_lst[-1].grid(row=4*i+1, column=0, padx=5, pady=py)
        x_scan_dv.append(tk.DoubleVar(root_frame))
        coord_widget_lst.append(tk.Entry(coord_frame, textvariable=x_scan_dv[i], width=6, font=("Calibri",12)))
        x_scan_dv[-1].set(cfg.x_scan[i]) # Default value of scanner coordinate
        coord_widget_lst[-1].bind('<FocusOut>', lambda e, idx=i: on_scan_entry_changed(idx))
        coord_widget_lst[-1].bind('<Return>', lambda e, idx=i: on_scan_entry_changed(idx))
        coord_widget_lst[-1].grid(row=4*i+1, column=1, padx=5, pady=0)
        y_scan_dv.append(tk.DoubleVar(root_frame))
        coord_widget_lst.append(tk.Entry(coord_frame, textvariable=y_scan_dv[i], width=6, font=("Calibri",12)))
        y_scan_dv[-1].set(cfg.y_scan[i]) # Default value of scanner coordinate
        coord_widget_lst[-1].bind('<FocusOut>', lambda e, idx=i: on_scan_entry_changed(idx))
        coord_widget_lst[-1].bind('<Return>', lambda e, idx=i: on_scan_entry_changed(idx))
        coord_widget_lst[-1].grid(row=4*i+1, column=2, padx=5, pady=0)

        coord_widget_lst.append(tk.Button(coord_frame, text="Get xy", width=5))
        coord_widget_lst[-1].grid(row=4*i+2, column=1, padx=5, pady=0)
        coord_widget_lst.append(tk.Button(coord_frame, text="Go to", width=5))
        coord_widget_lst[-1].grid(row=4*i+2, column=2, padx=5, pady=0)

    getxy_Callback_lst = []
    for i in range(4): # For all four sets of coordinate pairs
        def getxy_Callback(i=i): # Store pressent scanner coordinates in the correct calibration point
            cfg.x_scan[i] = round(x_pos, 2)
            cfg.y_scan[i] = round(y_pos, 2)
            x_scan_dv[i].set(str(round(x_pos, 2)))
            y_scan_dv[i].set(str(round(y_pos, 2)))
            if i >= 2 and is_calibration_valid(): # Auto-update image coordinates if modifying P2/P3
                x_px, y_px = scan_to_img(cfg.x_scan[i], cfg.y_scan[i])
                cfg.x_img[i] = x_px
                cfg.y_img[i] = y_px
                x_img_iv[i].set(x_px)
                y_img_iv[i].set(y_px)
                refresh_window(root_frame)
        getxy_Callback_lst.append(getxy_Callback)
        coord_widget_lst[i*8+6].config(command=getxy_Callback_lst[i]) # widget #6 of 8 is the get_xy button

    goto_Callback_lst = []
    for i in range(4): # For all four sets of coordinate pairs
        def goto_Callback(i=i): # Send coordinate from one calibration point to scanner as gcode
            global x_pos, y_pos
            x_pos, y_pos = cfg.x_scan[i], cfg.y_scan[i]
            sc_label_x.config(text="X:{0:7.2f}".format(x_pos))
            sc_label_y.config(text="Y:{0:7.2f}".format(y_pos))
            scan.write("G0 X" + str(cfg.x_scan[i]) + " Y" + str(cfg.y_scan[i]) + "\n")
        goto_Callback_lst.append(goto_Callback)
        coord_widget_lst[i*8+7].config(command=goto_Callback_lst[i]) # 7th widget #7 of 8 is the goto button

    def check_step_size():
        if jog_step == 0.0:
            print("You have to select step size before moving.")
            errorwindow = tk.Toplevel(root_frame)
            errorwindow.title("Error")
            tk.Label(errorwindow, text="Please select step size before moving.").pack()
            tk.Label(errorwindow, text="Current jog step size is = " + str(jog_step)).pack()
            tk.Button(errorwindow, text="  OK  ", command=errorwindow.destroy).pack()

    def x_plus_Callback():
        global x_pos
        check_step_size()
        x_pos = x_pos + jog_step
        sc_label_x.config(text="X:{0:7.2f}".format(x_pos))
        scan.write("G0 X" + str(x_pos) + "\n")
    def x_minus_Callback():
        global x_pos
        check_step_size()
        x_pos = x_pos - jog_step
        sc_label_x.config(text="X:{0:7.2f}".format(x_pos))
        scan.write("G0 X" + str(x_pos) + "\n")
    def y_plus_Callback():
        global y_pos
        check_step_size()
        y_pos = y_pos + jog_step
        sc_label_y.config(text="Y:{0:7.2f}".format(y_pos))
        scan.write("G0 Y" + str(y_pos) + "\n")
    def y_minus_Callback():
        global y_pos
        check_step_size()
        y_pos = y_pos - jog_step
        sc_label_y.config(text="Y:{0:7.2f}".format(y_pos))
        scan.write("G0 Y" + str(y_pos) + "\n")
    def z_plus_Callback():
        global z_pos
        check_step_size()
        z_pos = z_pos + jog_step
        sc_label_z.config(text="Z:{0:7.2f}".format(z_pos))
        scan.write("G0 Z" + str(z_pos) + "\n")
    def z_minus_Callback():
        global z_pos
        check_step_size()
        if jog_step < 10: # prevent long moves in negative z direction
            z_pos = z_pos - jog_step
        sc_label_z.config(text="Z:{0:7.2f}".format(z_pos))
        scan.write("G0 Z" + str(z_pos) + "\n")
    def go_origo_Callback():
        global x_pos, y_pos, z_pos
        x_pos = 0
        y_pos = 0
        # z_pos = 0
        sc_label_x.config(text="X:{0:7.2f}".format(x_pos))
        sc_label_y.config(text="Y:{0:7.2f}".format(y_pos))
        # sc_label_z.config(text="Z:{0:7.2f}".format(z_pos))
        scan.write("G0 X" + str(x_pos) + " Y" + str(y_pos) + "\n")

    def handle_key_jog(event):
        """Handle keyboard arrow and PageUp/PageDown keys for hardware jogging."""
        # Guard 1: Ignore keypresses if typing inside an Entry widget
        if isinstance(event.widget, (tk.Entry, ttk.Entry)):
            return
        # Guard 2: Ensure Calibration tab is active when embedded in Notebook
        if root_frame and hasattr(root_frame, 'master') and isinstance(root_frame.master, ttk.Notebook):
            try:
                selected_tab = root_frame.master.select()
                if selected_tab and root_frame.master.nametowidget(selected_tab) != root_frame:
                    return  # Another tab is active; ignore keypress
            except Exception:
                pass
        # Process key mappings
        key = event.keysym
        if key == 'Left':
            x_minus_Callback()
        elif key == 'Right':
            x_plus_Callback()
        elif key == 'Up':
            y_minus_Callback()
        elif key == 'Down':
            y_plus_Callback()
        elif key == 'Prior':  # Page Up
            z_plus_Callback()
        elif key == 'Next':   # Page Down
            z_minus_Callback()

    # Create scanner move frame
    move_frame = tk.Frame(left_frame, width=200, height=40)
    move_frame.grid(row=3, column=0, padx=4, pady=2)
    move_button01 = tk.Button(move_frame, text="Y-", width=7, command=y_minus_Callback, # TODO Use lambda with a delta coordinate instead 
                            repeatdelay=600, repeatinterval=200)
    move_button01.grid(row=0, column=1, padx=4, pady=2)
    move_button02 = tk.Button(move_frame, text="Up", width=7, command=z_plus_Callback,
                            repeatdelay=600, repeatinterval=200)
    move_button02.grid(row=0, column=2, padx=4, pady=2)
    move_button10 = tk.Button(move_frame, text="X-", width=7, command=x_minus_Callback,
                            repeatdelay=600, repeatinterval=200)
    move_button10.grid(row=1, column=0, padx=4, pady=2)
    move_button11 = tk.Button(move_frame, text=" Go Origo", command=go_origo_Callback, width=7)
    move_button11.grid(row=1, column=1, padx=4, pady=2)
    move_button12 = tk.Button(move_frame, text="X+", width=7, command=x_plus_Callback,
                            repeatdelay=600, repeatinterval=200)
    move_button12.grid(row=1, column=2, padx=4, pady=2)
    move_button21 = tk.Button(move_frame, text="Y+", width=7, command=y_plus_Callback,
                            repeatdelay=600, repeatinterval=200)
    move_button21.grid(row=2, column=1, padx=4, pady=2)
    move_button22 = tk.Button(move_frame, text="Dn", width=7, command=z_minus_Callback,
                            repeatdelay=600, repeatinterval=200)
    move_button22.grid(row=2, column=2, padx=4, pady=2)

    # Create jog_step selector frame
    step_frame = tk.Frame(left_frame, width=200, height=40)
    step_frame.grid(row=4, column=0, padx=5, pady=2)
    
    def set_step(val, active_btn):
        global jog_step
        jog_step = val
        for btn in jog_step_buttons:
            btn.config(bg='grey' if btn == active_btn else 'lightgrey')

    step_button001 = tk.Button(step_frame, text="0.01", width=4, activebackground="grey",
                             command=lambda: set_step(0.01, step_button001), bg='lightgrey')
    step_button001.grid(row=0, column=0, padx=5, pady=2)
    step_button01 = tk.Button(step_frame, text="0.1", width=4, activebackground="grey",
                            command=lambda: set_step(0.1, step_button01), bg='lightgrey')
    step_button01.grid(row=0, column=1, padx=5, pady=2)
    step_button1 = tk.Button(step_frame, text="1.0", width=4, activebackground="grey",
                           command=lambda: set_step(1.0, step_button1), bg='lightgrey')
    step_button1.grid(row=0, column=2, padx=5, pady=2)
    step_button10 = tk.Button(step_frame, text="10", width=4, activebackground="grey",
                            command=lambda: set_step(10.0, step_button10), bg='lightgrey')
    step_button10.grid(row=0, column=3, padx=5, pady=2)

    jog_step_buttons = [step_button001, step_button01, step_button1, step_button10]
    # Automatically reset jog_step size when leaving/unmapping this tab frame
    root_frame.bind("<Unmap>", lambda event: reset_jog_step())

    # Create scanner coordinates frame
    sc_frame = tk.Frame(left_frame, width=200, height=50)
    sc_frame.grid(row=5, column=0, padx=5, pady=2)
    sc_label_x = tk.Label(sc_frame, text="X:{0:7.2f}".format(x_pos), width=7, anchor="w")
    sc_label_x.grid(row=0, column=0, padx=5, pady=2)
    sc_label_y = tk.Label(sc_frame, text="Y:{0:7.2f}".format(y_pos), width=7, anchor="w")
    sc_label_y.grid(row=0, column=1, padx=5, pady=2)
    sc_label_z = tk.Label(sc_frame, text="Z:{0:7.2f}".format(z_pos), width=7, anchor="w")
    sc_label_z.grid(row=0, column=2, padx=5, pady=2)

    def store_new_origo():
        global x_pos, y_pos
        # This will reset the xy-scanner origo to the current position
        # It is achieved by disconnecting and then reconnecting scanner com port
        scan.close() # Close connection to xy_scanner
        x_pos, y_pos, z_pos = 0.0, 0.0, 0.0
        sc_label_x.config(text="X:{0:7.2f}".format(x_pos))
        sc_label_y.config(text="Y:{0:7.2f}".format(y_pos))
        sc_label_z.config(text="Z:{0:7.2f}".format(z_pos))
        cfg.scan = scan.init(cfg.scanner_comport) # Init xy_scanner

    # Create ready buttons frame
    ready_frame = tk.Frame(left_frame, width=200, height=50)
    ready_frame.grid(row=6, column=0, padx=5, pady=2)
    ready_button0 = tk.Button(ready_frame, text="Store new origo", command=store_new_origo)
    ready_button0.grid(row=0, column=0, padx=5, pady=2)
    ready_button1 = tk.Button(ready_frame, text="Save calibration", command=save_calibration)
    ready_button1.grid(row=0, column=1, padx=5, pady=2)

    # Bind keyboard jogging (Arrow keys & PageUp/PageDown)
    top_window = root_frame.winfo_toplevel()
    for key_spec in ('<Left>', '<Right>', '<Up>', '<Down>', '<Prior>', '<Next>'):
        top_window.bind(key_spec, handle_key_jog)

if __name__ == '__main__':
    # Standalone init and enable for manual control
    root = tk.Tk()  # create root window
    root.title("Scanner calibration stand alone test module")  # title of the GUI window
    if(cfg.scanner_comport != ""):
        # Init xy_scanner
        cfg.scan = scan.init(cfg.scanner_comport)
    calibrate(root)
    enable_dynamic_resize(root)
    root.mainloop()
