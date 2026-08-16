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
# This is "show result" module of the near filed scaner application.
# This module shows the result from a scanning. The result can be zoomed
# in frequency and spatially.

import tkinter as tk
from tkinter import filedialog
import os
try:
    import matplotlib.image as img
except:
    print("Please install matplotlib via the \'pip install matplotlib\' command.")
    exit(0)
from matplotlib.figure import Figure 
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.axes_grid1 import make_axes_locatable
import importlib
import math
import numpy as np
import json
from PIL import ImageGrab
import json
import scan_config as cfg # To hold application global variables
import xy_scanner as scan
if not(cfg.sa_model == ""):
    sa = importlib.import_module(cfg.sa_model, package=None) # "HP_8591"

# Global variables for this module
x_mkr = [0.0]*4               # Spatial markers
y_mkr = [0.0]*4               # Spatial markers
no_of_mkr = 0                 # Start with no markers active
x_mkr_dv, y_mkr_dv = [], []   # List of DoubleVar for x & y marker coordinates
frmkr_dv, frdelta_dv = [], [] # List of frequency marker frequencies
freq_mkr = [0.0]*8            # Frequency marker lists
ampl_mkr = [0.0]*8            # Amplitude of each frequency marker
no_of_frmkr = 0               # Start with no markers active
spectrum, spectrum_min, spectrum_max = 0, 0, 0
x_steps, y_steps, no_of_x_step, no_of_y_step = 0, 0, 0, 0
selected_file1_label, selected_file2_label = 0, 0
img_xmin, img_ymin, img_xmax, img_ymax = 0, 0, 0, 0
zoom_xmin, zoom_ymin, zoom_xmax, zoom_ymax = 0, 0, 0, 0
target_xmin, target_ymin, target_xmax, target_ymax = 0, 0, 0, 0
fig, fig2, canvas, canvas2 = 0, 0, 0, 0
image_frame, spectrum_frame, left_frame, main_window = 0, 0, 0, 0
plot_cb = 0
mouse_move_cid, freq_slider_active, move_limit = 0, 0, 0
from_freq, to_freq = 0, -1
last_img_w, last_img_h = 0, 0
last_spec_w, last_spec_h = 0, 0
panstart_x, panstart_y = 0, 0
pan_active = False
pan_target_xmin, pan_target_xmax, pan_target_ymin, pan_target_ymax = 0, 0, 0, 0

color8  = ['#FF0000', '#FFC100', '#C1FF00', '#00FF00', '#00FFC1', '#00C1FF', '#0000FF', '#C100FF']
color8l = ['#FF8080', '#FFE080', '#E0FF80', '#80FF80', '#80FFE0', '#80E0FF', '#8080E0', '#E080FF']
color4  = ['#FF0000', '#C1FF00', '#00FFC1', '#0000FF', '#E0E0E0']
#color4l = ['#FF8000', '#E0FF80', '#80FFE0', '#8080E0']
color4l = ['#FF9080', '#FFE280', '#80FF90', '#A080FF', '#E0E0E0']

def mag(H_field, V_field):
    magnitude = 10 * math.log(math.sqrt((10 ** (H_field/10)) ** 2 + (10 ** (V_field/10)) ** 2), 10)
    return magnitude

def open_datafile1(filename):
    global no_of_x_step, no_of_y_step, x_steps, y_steps, spectrum, spectrum_min, spectrum_max
    global zoom_xmin, zoom_ymin, zoom_xmax, zoom_ymax, img_xmin, img_ymin, img_xmax, img_ymax
    global target_xmin, target_ymin, target_xmax, target_ymax, from_freq, to_freq, pan_active

    if not filename or not os.path.exists(filename):
        return False

    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading file {filename}: {e}")
        errorwin = tk.Toplevel(root_frame)
        errorwin.title("Error")
        tk.Label(errorwin, text="Selected file is not a valid scan dataset.").pack(padx=10, pady=10)
        tk.Button(errorwin, text="  OK  ", command=errorwin.destroy).pack(pady=5)
        return False

    # Generate coordinate vectors safely
    y_steps = tuple(np.arange(data['y_start'], data['y_stop'] + 0.001, data['y_step']))
    x_steps = tuple(np.arange(data['x_start'], data['x_stop'] + 0.001, data['x_step']))
    no_of_x_step = len(x_steps)
    no_of_y_step = len(y_steps)

    # Populate global config values
    cfg.x_start         = data['x_start']
    cfg.y_start         = data['y_start']
    cfg.x_stop          = data['x_stop']
    cfg.y_stop          = data['y_stop']
    cfg.x_step          = data['x_step']
    cfg.y_step          = data['y_step']
    cfg.image_path      = data['image_path']
    cfg.no_of_calpoints = data['no_of_calpoints']
    cfg.x_img           = data['x_img']
    cfg.y_img           = data['y_img']
    cfg.x_scan          = data['x_scan']
    cfg.y_scan          = data['y_scan']
    cfg.start_freq      = data['start_freq']
    cfg.stop_freq       = data['stop_freq']
    cfg.points          = data['points']
    cfg.average         = data['average']
    cfg.sweep_time      = data["sweep_time"]
    cfg.rbw             = data['rbw']
    cfg.rbw_auto        = data['rbw_auto']
    cfg.peak_detector   = data["peak_detector"]
    cfg.max_hold        = data["max_hold"]
    cfg.freq_lst        = data['freq_lst']
    cfg.R               = data['R']
    cfg.S               = []
    spectrum = tot_spectrum()
    spectrum_max = np.ceil(max(spectrum))
    spectrum_min = np.floor(min(spectrum))
    from_freq, to_freq = 0, len(cfg.freq_lst) - 1

    if not os.path.exists(cfg.image_path):
        print(f"Background image not found: {cfg.image_path}")
        return False
    cfg.image = img.imread(cfg.image_path)
    # Calculate image boundaries
    img_xscale = (cfg.x_img[0] - cfg.x_img[1]) / (cfg.x_scan[0] - cfg.x_scan[1])
    img_yscale = (cfg.y_img[0] - cfg.y_img[1]) / (cfg.y_scan[0] - cfg.y_scan[1])
    img_xmin = cfg.x_scan[0] - cfg.x_img[0] / img_xscale
    img_ymin = cfg.y_scan[0] - cfg.y_img[0] / img_yscale
    img_xmax = cfg.image.shape[1] / img_xscale + img_xmin
    img_ymax = cfg.image.shape[0] / img_yscale + img_ymin
    target_xmin = min(img_xmin, cfg.x_start - cfg.x_step / 2)
    target_ymin = min(img_ymin, cfg.y_start - cfg.y_step / 2)
    target_xmax = max(img_xmax, cfg.x_stop + cfg.x_step / 2)
    target_ymax = max(img_ymax, cfg.y_stop + cfg.y_step / 2)
    adjust_aspect()
    return True

def open_datafile2(filename): 
    """Open second dataset (perpendicular field scan) and verify consistency with dataset 1."""
    global spectrum, spectrum_min, spectrum_max
    if not filename or not os.path.exists(filename):
        cfg.S = []
        return False
    if filename == cfg.scanfile1_path:
        print("Same file chosen for file1 and file2:", filename)
        cfg.scanfile2_path = ""
        cfg.S = []
        return False
    try:
        with open(filename, 'r') as f:
            data2 = json.load(f)
    except Exception as e:
        print(f"Error reading file2 {filename}: {e}")
        cfg.S = []
        return False
    # Collect any consistency mismatches between file 2 and dataset 1 (cfg globals)
    mismatches = []
    # Scalar field checks
    scalar_checks = [
        ('x_start', cfg.x_start),
        ('y_start', cfg.y_start),
        ('x_stop', cfg.x_stop),
        ('y_stop', cfg.y_stop),
        ('x_step', cfg.x_step),
        ('y_step', cfg.y_step),
        ('image_path', cfg.image_path),
        ('no_of_calpoints', cfg.no_of_calpoints),
        ('start_freq', cfg.start_freq),
        ('stop_freq', cfg.stop_freq),
        ('points', cfg.points),
        ('average', cfg.average),
    ]
    for key, expected_val in scalar_checks:
        if data2.get(key) != expected_val:
            mismatches.append(f"{key}: {data2.get(key)} (file 2) != {expected_val} (file 1)")
    # Vector/List checks (ensuring tuple-to-list equivalence)
    list_checks = [
        ('x_img', list(cfg.x_img)),
        ('y_img', list(cfg.y_img)),
        ('x_scan', list(cfg.x_scan)),
        ('y_scan', list(cfg.y_scan)),
        ('freq_lst', list(cfg.freq_lst)),
    ]
    for key, expected_val in list_checks:
        if data2.get(key) != expected_val:
            mismatches.append(f"{key} array mismatch")
    # Handle dataset mismatches
    if mismatches:
        print("The two datasets are not consistent! Loading aborted.")
        errorwindow3 = tk.Toplevel(root_frame)
        errorwindow3.title("Inconsistent Datasets")
        tk.Label(errorwindow3, text="The two datasets are not consistent! File loading aborted.", font=("Arial", 9, "bold")).pack(padx=10, pady=5)
        # Display first few specific mismatches in the dialog
        for mismatch in mismatches[:5]:
            tk.Label(errorwindow3, text=mismatch, font=("Consolas", 8)).pack(anchor='w', padx=15)
        tk.Button(errorwindow3, text="  OK  ", command=errorwindow3.destroy).pack(pady=8)
        cfg.S = []
        return False

    # Copy perpendicular scan matrix to cfg.S
    cfg.S = data2['R']
    spectrum = tot_spectrum()
    spectrum_max = np.ceil(max(spectrum))
    spectrum_min = np.floor(min(spectrum))
    adjust_aspect()  # Scale & center view to image_frame
    return True

def tot_spectrum():
    freq_spectrum = []
    for i in range(len(cfg.freq_lst)):
        F = [] # list of amplitudes for one frequency in each point
        for x in range(no_of_x_step):
            for y in range(no_of_y_step):
                if len(cfg.S) == 0: # S == 0 when there is only one set of scan data (two sets is when two perpendicular megnetic fields are recorded)
                    try:
                        F.append(cfg.R[y][x][i])
                    except:
                        print("len(F)", len(F))
                        print("len(cfg.R)", len(cfg.R))
                        print("y", y)
                        print("x", x)
                        print("i", i)
                        print("len(R[y])", len(cfg.R[y]))
                        print("len(R[y][x])", len(cfg.R[y][x]))
                        print("len(R[y][x][i])", len(cfg.R[y][x][i]))
                else:
                    # F.append(round(mag(cfg.R[y][x][i], cfg.S[y][x][i]), 2)) # Calculate magnitude from XY-field probes TODO This is the correct calculation of magnitude
                    F.append(round(max(cfg.R[y][x][i], cfg.S[y][x][i]), 2)) # Take maximum value of the two fields
        freq_spectrum.append(max(F)) # Max ampliture for each frequency
    return freq_spectrum

def find_nearest(array, value): # Find the nearest value in an array and return its index
    array = np.asarray(array)
    index = (np.abs(array - value)).argmin()
    return index

def update_fields_from_globals(): # Update all the widget fields (Entry's) from global varaibles
    """Re-sync scan_result UI components with global cfg state."""
    scanfile1_name = os.path.basename(cfg.scanfile1_path)
    selected_file1_label.config(text=scanfile1_name)
    if scanfile1_name: # if the scanfile1_name exists
        open_datafile1(scanfile1_name)
        scanfile2_name = os.path.basename(cfg.scanfile2_path)
        selected_file2_label.config(text=scanfile2_name)
        open_datafile2(scanfile2_name)
    else:
        # Reset data arrays and purge canvas view when no project file is loaded
        cfg.R = []
        cfg.S = []
        cfg.image = []
        selected_file2_label.config(text="")
        refresh_window(root_frame)

def update_frequency_deltas():
    """Recalculate frequency delta readout fields."""
    for i in range(1, 8):
        f_curr = frmkr_dv[i].get()
        f_prev = frmkr_dv[i - 1].get()
        if f_curr != 0.0 and f_prev != 0.0:
            frdelta_dv[i].set(round(f_curr - f_prev, 2))
        else:
            frdelta_dv[i].set(0.0)

def enable_dynamic_resize(window):
    """Enable dynamic window resize listeners for scan_result."""
    global main_window
    main_window = window
    if image_frame and spectrum_frame:
        image_frame.bind("<Configure>", on_image_frame_resize)
        spectrum_frame.bind("<Configure>", on_spectrum_frame_resize)

def on_image_frame_resize(event):
    """Fired automatically when image_frame changes size."""
    global fig, canvas, last_img_w, last_img_h
    if event.widget == image_frame:
        new_w, new_h = event.width, event.height
        if new_w < 50 or new_h < 50: # Window is too small
            return

        if new_w != last_img_w or new_h != last_img_h:
            last_img_w, last_img_h = new_w, new_h
            fig_dpi = 100
            fig.set_size_inches(new_w / fig_dpi, new_h / fig_dpi)
            adjust_aspect()

def on_spectrum_frame_resize(event):
    """Fired automatically when spectrum_frame changes size."""
    global fig2, canvas2, last_spec_w, last_spec_h
    if event.widget == spectrum_frame:
        new_w, new_h = event.width, event.height
        if new_w < 50 or new_h < 20:
            return

        if new_w != last_spec_w or new_h != last_spec_h:
            last_spec_w, last_spec_h = new_w, new_h
            fig_dpi = 100
            fig2.set_size_inches(new_w / fig_dpi, new_h / fig_dpi)
            if root_frame and len(cfg.R) != 0:
                refresh_window(root_frame)

def image_scroll(event): # This event occur when scrollwheel is rotated or when a two finger up/down
    """Zoom spatial plot in/out centered on mouse position."""
    global target_xmin, target_ymin, target_xmax, target_ymax
    if event.xdata is None or event.ydata is None:
        return
    is_zoom_in = (event.button == 'up') or (hasattr(event, 'step') and event.step > 0)
    is_zoom_out = (event.button == 'down') or (hasattr(event, 'step') and event.step < 0)
    if is_zoom_in:
        target_xmin += (event.xdata - target_xmin) * 0.1
        target_xmax -= (target_xmax - event.xdata) * 0.1
        target_ymin += (event.ydata - target_ymin) * 0.1
        target_ymax -= (target_ymax - event.ydata) * 0.1
    elif is_zoom_out:
        target_xmin -= (event.xdata - target_xmin) * 0.1
        target_xmax += (target_xmax - event.xdata) * 0.1
        target_ymin -= (event.ydata - target_ymin) * 0.1
        target_ymax += (target_ymax - event.ydata) * 0.1
    adjust_aspect()

def adjust_aspect(): # Aspect correction (filing the frame)
    """Calculate zoom_ bounds deterministically from target_ bounds to match image_frame aspect ratio."""
    global zoom_xmax, zoom_xmin, zoom_ymax, zoom_ymin
    if image_frame is None or target_ymax == target_ymin:
        return
    fw = image_frame.winfo_width()
    fh = image_frame.winfo_height()
    target_w = abs(target_xmax - target_xmin)
    target_h = abs(target_ymax - target_ymin)
    # Fallback for startup before image_frame is rendered on screen
    if fw < 20 or fh < 20 or target_h == 0 or target_w == 0:
        zoom_xmin, zoom_xmax = target_xmin, target_xmax
        zoom_ymin, zoom_ymax = target_ymin, target_ymax
        refresh_window(root_frame)
        return
    frame_aspect = fw / fh
    target_aspect = target_w / target_h
    x_center = (target_xmin + target_xmax) / 2.0
    y_center = (target_ymin + target_ymax) / 2.0
    if target_aspect < frame_aspect:
        view_h = target_h
        view_w = target_h * frame_aspect
    else:
        view_w = target_w
        view_h = target_w / frame_aspect
    zoom_xmin = x_center - view_w / 2.0
    zoom_xmax = x_center + view_w / 2.0
    zoom_ymin = y_center - view_h / 2.0
    zoom_ymax = y_center + view_h / 2.0
    refresh_window(root_frame)
    
def mouse_motion_event(event):
    """Mouse motion handler for spectrum preview hover and middle-click panning."""
    global pan_active, panstart_x, panstart_y, target_xmin, target_xmax, target_ymin, target_ymax
    # Handle Active Panning
    if pan_active and event.xdata is not None and event.ydata is not None:
        dx = event.xdata - panstart_x
        dy = event.ydata - panstart_y
        target_xmin -= dx
        target_xmax -= dx
        target_ymin -= dy
        target_ymax -= dy
        adjust_aspect()
        return
    # Handle Spectrum Preview Hover
    if type(event.xdata) == np.float64 and len(cfg.R) != 0:
        index_x = find_nearest(x_steps, event.xdata)
        index_y = find_nearest(y_steps, event.ydata)
        freq_spectrum = cfg.R[index_y][index_x]
        if cfg.x_start < event.xdata < cfg.x_stop and cfg.y_start < event.ydata < cfg.y_stop:
            fig2.clear()
            subplot2 = fig2.add_subplot()
            subplot2.plot(cfg.freq_lst, spectrum, color='#E0E0E0', alpha=0.5)
            subplot2.plot(cfg.freq_lst, freq_spectrum, color=color4[no_of_mkr])
            subplot2.grid(color='lightgrey', linestyle=":", linewidth=1)
            ax = fig2.gca()
            ax.set_ylim([spectrum_min, spectrum_max])
            canvas2.draw()
            spectrum_frame.update()

def figure_leave_event(event): # Mounse pointer leave the spatial radiation plot (stop the hovering spectral plot)
    refresh_window(root_frame)

def spatial_mouse_button(event):
    """Mouse button click handler for spatial markers (Left/Right) and Pan (Middle)."""
    global no_of_mkr, panstart_x, panstart_y, pan_active
    # print("spatial_mouse_button: ", event.xdata, event.ydata)
    if event.xdata is None or event.ydata is None:
        return
    # MIDDLE CLICK -> Start Panning
    if event.button == 2:
        panstart_x = event.xdata
        panstart_y = event.ydata
        pan_active = True
        return
    # LEFT / RIGHT CLICK -> Spatial Markers
    closest = 10000
    point = 10
    for i in range(no_of_mkr):
        distance = math.hypot(x_mkr[i] - event.xdata, y_mkr[i] - event.ydata)
        if distance < 10 and distance < closest:
            closest = distance
            point = i
    if point < 5: # at least one close point is found and the closest is "i"
        if event.button == 1: # left click, check if close to point -> move that point
            x_mkr_dv[point].set(round(event.xdata, 1))
            y_mkr_dv[point].set(round(event.ydata, 1))
            x_mkr[point] = round(event.xdata, 1)
            y_mkr[point] = round(event.ydata, 1)
        elif event.button == 3: # right click -> remove point
            no_of_mkr -= 1
            x_mkr.append(0.0)
            y_mkr.append(0.0)
            del x_mkr[point], y_mkr[point]
            for k in range(point, 3):
                x_mkr_dv[k].set(x_mkr_dv[k+1].get())
                y_mkr_dv[k].set(y_mkr_dv[k+1].get())
            x_mkr_dv[3].set(0.0)
            y_mkr_dv[3].set(0.0)
    elif event.button == 1 and no_of_mkr < 4: # add point if points are fewer than 4
        x_mkr[no_of_mkr] = round(event.xdata, 1)
        y_mkr[no_of_mkr] = round(event.ydata, 1)
        x_mkr_dv[no_of_mkr].set(round(event.xdata, 1))
        y_mkr_dv[no_of_mkr].set(round(event.ydata, 1))
        no_of_mkr += 1
    refresh_window(root_frame)

def refresh_window(root_frame):
    global fig, fig2, canvas, canvas2, zoom_xmax, zoom_xmin, zoom_ymax, zoom_ymin
    fig.clear()
    fig2.clear()
    if len(cfg.R) == 0: # If no scan data exists, render empty canvases and exit
        canvas.draw()
        canvas2.draw()
        root_frame.update()
        return
    Rz = []
    for y in range(no_of_y_step):
        z = []
        for x in range(no_of_x_step):
            if len(cfg.S) == 0: # Data exists only in R
                z.append(round(max(cfg.R[y][x][from_freq:to_freq]), 1)) # Ampliture in each point is just max ampliture for every frequency
            else:
                z.append(round(mag(max(cfg.R[y][x][from_freq:to_freq]), max(cfg.S[y][x][from_freq:to_freq])), 1)) # Amplitude magitude from two fields x- and Y-probes
        Rz.append(z)

    # Set up matplotlib plot
    subplot1 = fig.add_subplot()
    subplot2 = fig2.add_subplot()
    subplot1.grid(color = 'lightgray')

    # displaying the layout image in scanner coordinates
    if len(cfg.image) != 0: # Don't display an empty image
        subplot1.imshow(cfg.image, cmap="gray", alpha=1.0, extent=[img_xmin, img_xmax, img_ymax, img_ymin], origin="upper")
    # display the measured amplitude overlayed on the layout (in scanner coordinates)
    x_stop_adj = cfg.x_stop-(cfg.x_stop-cfg.x_start)%cfg.x_step+cfg.x_step/2
    y_stop_adj = cfg.y_stop-(cfg.y_stop-cfg.y_start)%cfg.y_step+cfg.y_step/2
    mesh = subplot1.imshow(Rz, cmap="rainbow", alpha=0.5,
                    extent=[cfg.x_start-cfg.x_step/2, x_stop_adj, y_stop_adj, cfg.y_start-cfg.y_step/2],
                    interpolation="none", origin="upper")
    if plot_cb == 1: # To plot or not to plot a colorbar
        divider = make_axes_locatable(subplot1)
        cax = divider.append_axes("right", size="5%", pad=0.5)
        cb = fig.colorbar(mesh, shrink=0.7, cax=cax)
        cb.ax.set_title("dBm")
    
    # Plot markers if they exists
    subplot1.scatter(x_mkr[0:no_of_mkr], y_mkr[0:no_of_mkr], c=color4[0:no_of_mkr], alpha=0.8, edgecolor='black', s=70)
    subplot1.imshow([[0,0],[0,0]], alpha=0.0, origin='upper', extent=[zoom_xmin, zoom_xmax, zoom_ymax, zoom_ymin]) # zoom image [from-x, to-x, to-y, from-y]
    if no_of_mkr == 0:
        subplot2.plot(cfg.freq_lst[:from_freq], spectrum[:from_freq], color='#F0F0F0')
        subplot2.plot(cfg.freq_lst[from_freq:to_freq], spectrum[from_freq:to_freq], color='black')
        subplot2.plot(cfg.freq_lst[to_freq:], spectrum[to_freq:], color='#F0F0F0')
    else:
        subplot2.plot(cfg.freq_lst, spectrum, color='#F0F0F0')
        for i in range(no_of_mkr): # Plot spectrum for each spatial markers
            freq_spectrum = cfg.R[find_nearest(y_steps, y_mkr[i])][find_nearest(x_steps, x_mkr[i])] 
            subplot2.plot(cfg.freq_lst, freq_spectrum, color=color4[i], alpha=0.8)
    subplot2.plot([cfg.freq_lst[from_freq], cfg.freq_lst[from_freq]], [spectrum_min, spectrum_max], color='grey', alpha=0.5, linewidth=8) # Low freq range limit
    subplot2.plot([cfg.freq_lst[to_freq], cfg.freq_lst[to_freq]],     [spectrum_min, spectrum_max], color='grey', alpha=0.5, linewidth=8) # High freq range limit
    subplot2.grid(color = 'lightgrey', linestyle=":", linewidth = 1)
    subplot2.scatter(freq_mkr[0:no_of_frmkr], ampl_mkr[0:no_of_frmkr], c=color8[0:no_of_frmkr], alpha=0.5)
    ax2 = fig2.gca()
    ax2.set_ylim([spectrum_min, spectrum_max])
    subplot2.set_xlabel("Frequency [Hz]")
    subplot2.set_ylabel("Amplitude [dBm]")
    fig.tight_layout()
    fig2.tight_layout()
    canvas.draw()
    canvas2.draw()
    root_frame.update()

def spectrum_mouse_button(event): # Mouse button is pressed inside spectrum_frame
    global no_of_frmkr, mouse_move_cid, freq_slider_active, move_limit, frmkr_dv
    freq_index = find_nearest(cfg.freq_lst, event.xdata)
    if event.button == 1: # left click, check if close to from_freq or to_freq
        from_distance = abs(freq_index - from_freq)
        to_distance = abs(freq_index - to_freq)
        if from_distance < 5 or to_distance < 5:
            freq_slider_active = 1
            if from_distance < to_distance: # Move the from_freq
                move_limit = 0
            else: # to_distance < from_distance: # Move the to_freq
                move_limit = 1
            mouse_move_cid = fig2.canvas.mpl_connect('motion_notify_event', freq_slide)
            return # jump out of the mouse button event
    closest = 10000
    point = 10
    for i in range(no_of_frmkr): # look at all frequency markers
        distance = abs(find_nearest(cfg.freq_lst, freq_mkr[i]) - freq_index)
        if (distance < 5) and (distance < closest):
            closest = distance
            point = i
    low_idx = max(0, freq_index - 5)
    high_idx = min(len(spectrum), freq_index + 5)
    peak_index = low_idx + np.argmax(spectrum[low_idx:high_idx])
    if point < 8: # at least one close point is found and the closest is "i"
        if event.button == 1: # left click, check if close to point -> move that point
            frmkr_dv[point].set(cfg.freq_lst[peak_index]/1E6)
            freq_mkr[point] = cfg.freq_lst[peak_index]
            ampl_mkr[point] = spectrum[peak_index]
        elif event.button == 3: # right click -> remove point
            no_of_frmkr -= 1
            freq_mkr.append(0.0)
            ampl_mkr.append(0.0)
            freq_mkr.pop(point)
            ampl_mkr.pop(point)
            for k in range(point, 7):
                frmkr_dv[k].set(frmkr_dv[k+1].get())
            frmkr_dv[7].set(0.0)
    elif (event.button == 1) and (no_of_frmkr < 8): # add marker if markers are fewer than 8
        index = freq_mkr.index(next((x for x in freq_mkr if x > cfg.freq_lst[peak_index]), 0)) # Finding the index to insert new marker (in order)
        freq_mkr.insert(index, cfg.freq_lst[peak_index])
        ampl_mkr.insert(index, spectrum[peak_index])
        freq_mkr.pop(8)
        ampl_mkr.pop(8)
        no_of_frmkr += 1
        for i in range(min(no_of_frmkr, 7), index, -1):
            frmkr_dv[i].set(frmkr_dv[i-1].get())
        frmkr_dv[index].set(cfg.freq_lst[peak_index]/1E6)
    update_frequency_deltas()
    refresh_window(root_frame)

def freq_slide(event): # This is the motion_notify_event, but not all motions are supposed to pan the image
    """Motion handler for sliding the frequency range bounds with safety guards."""
    global from_freq, to_freq
    # Guard: Do nothing if slider inactive, event outside plot, or no frequency data
    if not freq_slider_active or event.xdata is None or len(cfg.freq_lst) == 0:
        return
    min_dist = 8  # Minimum index gap between from_freq and to_freq
    max_idx = len(cfg.freq_lst) - 1
    # Calculate index nearest to mouse position
    idx = find_nearest(cfg.freq_lst, event.xdata)
    if move_limit == 0:  # Moving low frequency limit (from_freq)
        # Keep from_freq between index 0 and (to_freq - min_dist)
        from_freq = max(0, min(idx, to_freq - min_dist))
    else:  # Moving high frequency limit (to_freq)
        # Keep to_freq between (from_freq + min_dist) and max_idx
        to_freq = max(from_freq + min_dist, min(idx, max_idx))
    refresh_window(root_frame)

def button_release(event): # Button is released = frequency slider should stop
    """Release handler for frequency slider and middle-click panning."""
    global freq_slider_active, pan_active
    #print("button_release: ", event.button)
    if event.button == 1:
        freq_slider_active = 0
        fig2.canvas.mpl_disconnect(mouse_move_cid)
    elif event.button == 2:
        pan_active = False

# ****************************************************************************************************
#  # This is the main routine in the scan_result module that shows the near filed radiation
# ****************************************************************************************************
def scan_result(frame):
    global fig, fig2, canvas, canvas2, image_frame, root_frame, left_frame, spectrum_frame
    global x_mkr_dv, y_mkr_dv, zoom_xmin, zoom_ymin, zoom_xmax, zoom_ymax
    global img_xmin, img_ymin, img_xmax, img_ymax, no_of_mkr, no_of_frmkr, plot_cb
    global frmkr_dv, frdelta_dv, selected_file1_label, selected_file2_label
    root_frame = frame
    root_frame.rowconfigure(0, weight=1, minsize=560)  # upper_frame (image + markers) gets natural height
    root_frame.rowconfigure(1, weight=0)  # spectrum_frame stays at a fixed height
    root_frame.columnconfigure(0, weight=1)

    # Create upper frame that holds left and image frames
    upper_frame = tk.Frame(root_frame)
    upper_frame.grid(row=0, column=0, padx=2, pady=2, sticky='nsew')
    upper_frame.columnconfigure(0, weight=0)  # left_frame stays FIXED width
    upper_frame.columnconfigure(1, weight=1)  # image_frame expands horizontally
    upper_frame.rowconfigure(0, weight=1)

    # Create left tk.Frame that holds coordinates for markers
    left_frame = tk.Frame(upper_frame)
    left_frame.grid(row=0, column=0, padx=2, pady=2, sticky='nw')

    # Create frame for scanning result image
    image_frame = tk.Frame(upper_frame)
    image_frame.grid(row=0, column=1, padx=5, pady=2, sticky='nsew')
    image_frame.columnconfigure(0, weight=1)
    image_frame.rowconfigure(0, weight=1)
 
    # Create spectrum & slider frame
    spectrum_frame = tk.Frame(root_frame)
    spectrum_frame.grid(row=1, column=0, padx=5, pady=0, sticky='nsew')
    spectrum_frame.columnconfigure(0, weight=1)
    spectrum_frame.rowconfigure(0, weight=1)

    # Spatial Image Canvas
    fig = Figure(dpi=100)
    canvas = FigureCanvasTkAgg(fig, master=image_frame)
    canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')
    canvas.get_tk_widget().bind('<Enter>', lambda e: canvas.get_tk_widget().focus_set())

    # Connect spatial plot Matplotlib events
    canvas.mpl_connect('motion_notify_event', mouse_motion_event)
    canvas.mpl_connect('figure_leave_event', figure_leave_event)
    canvas.mpl_connect('button_press_event', spatial_mouse_button)
    canvas.mpl_connect('button_release_event', button_release)
    canvas.mpl_connect('scroll_event', image_scroll)
    # Focus canvas on hover for scroll wheel responsiveness
    canvas.get_tk_widget().bind('<Enter>', lambda e: canvas.get_tk_widget().focus_set())

    # Spectrum Canvas
    fig2 = Figure(figsize=(8, 1.8), dpi=100)
    canvas2 = FigureCanvasTkAgg(fig2, master=spectrum_frame)
    canvas2.get_tk_widget().grid(row=0, column=0, sticky='nsew')

    # Connect spectrum plot Matplotlib events
    canvas2.mpl_connect('button_press_event', spectrum_mouse_button)
    canvas2.mpl_connect('button_release_event', button_release)

    # Create file selection frame
    file_frame = tk.Frame(left_frame, width=200, height=40)
    file_frame.grid(row=0, column=0, padx=2, pady=2, sticky='nw')
    scanfile1_name = os.path.basename(cfg.scanfile1_path)
    scanfile2_name = os.path.basename(cfg.scanfile2_path)

    def open_datafile1_dialog():
        cfg.scanfile1_path = filedialog.askopenfilename(title="Select a File", filetypes=[("Near Field Scan files", "*.nfs")])
        scanfile1_name = os.path.basename(cfg.scanfile1_path)
        if cfg.scanfile1_path:
            selected_file1_label.config(text=scanfile1_name)
        if scanfile1_name == "":
            selected_file1_label.config(text="")
            return # There is no purpose in loading an empty file
        else:
            if not open_datafile1(scanfile1_name): # Check if file can be opened
                cfg.scanfile1_path = ""
                cfg.image_path = ""
                cfg.image = []
                selected_file1_label.config(text="")
            else: # scanfile2 should be removed when scanfile1 is loaded
                cfg.scanfile2_path = ""
                selected_file2_label.config(text="")

    selected_file1_label = tk.Label(file_frame, text=scanfile1_name, width=26, font=("Arial", 8), bg='white', anchor="w")
    selected_file1_label.grid(row=0, column=0, padx=2)
    open_button1 = tk.Button(file_frame, text="Open", command=open_datafile1_dialog)
    open_button1.grid(row=0, column=1, padx=0, pady=0)

    def open_datafile2_dialog():
        cfg.scanfile2_path = filedialog.askopenfilename(title="Select a File", filetypes=[("Near Field Scan files", "*.nfs")])
        scanfile2_name = os.path.basename(cfg.scanfile2_path)
        if cfg.scanfile2_path:
            selected_file2_label.config(text=scanfile2_name)
        if scanfile2_name == "":
            return # There is no purpose in loading an empty file, TODO: Unload the S[] matrix
        else:
            if not open_datafile2(scanfile2_name): # Check if file can be opened
                cfg.scanfile2_path = ""
                selected_file2_label.config(text="")

    selected_file2_label = tk.Label(file_frame, text=scanfile2_name, width=26, font=("Arial", 8), bg='white', anchor="w")
    selected_file2_label.grid(row=1, column=0, padx=2)
    open_button2 = tk.Button(file_frame, text="Open", command=open_datafile2_dialog)
    open_button2.grid(row=1, column=1, padx=0, pady=0)

   # Create coordinate list frame
    marker_frame = tk.Frame(left_frame, width=200, height=400)
    marker_frame.grid(row=1, column=0, padx=2, pady=5, sticky='nw')

    mkr_widget_lst = [] # List of all type of tkinter widgets in the marker_frame
    # Create labels and entrys in marker_frame
    mkr_widget = tk.Label(marker_frame, text="XY-markers", anchor="w")
    mkr_widget.grid(row=0, column=0, columnspan=3, padx=5, pady=2, sticky='nw')

    def goto_mkr(idx):
        """Send scanner to selected spatial marker position."""
        if idx < no_of_mkr:
            scan.write(f"G0 X{x_mkr_dv[idx].get()} Y{y_mkr_dv[idx].get()}\n")
            if cfg.sa_model != "":
                sa.local()

    for i in range(4): # For all four sets of coordinate pairs
        # Marker Label
        mkr_widget_lst.append(tk.Label(marker_frame, bg=color4l[i], text=f"Marker {i+1}", width=7, anchor="w"))
        mkr_widget_lst[-1].grid(row=i+1, column=0, padx=5, pady=2, sticky='nw')
        # Read-only X coordinate display
        x_mkr_dv.append(tk.DoubleVar(root_frame, value=x_mkr[i]))
        coord_x_lbl = tk.Label(marker_frame, textvariable=x_mkr_dv[i], width=5, font=("Calibri", 12), bg='white', relief='sunken')
        coord_x_lbl.grid(row=i+1, column=1, padx=5, pady=0)
        # Read-only Y coordinate display
        y_mkr_dv.append(tk.DoubleVar(root_frame, value=y_mkr[i]))
        coord_y_lbl = tk.Label(marker_frame, textvariable=y_mkr_dv[i], width=5, font=("Calibri", 12), bg='white', relief='sunken')
        coord_y_lbl.grid(row=i+1, column=2, padx=5, pady=0)
        # Go To Button
        btn = tk.Button(marker_frame, text="Go", command=lambda idx=i: goto_mkr(idx))
        btn.grid(row=i+1, column=3, padx=5, pady=0)

    def clear_all_mkr():
        global no_of_mkr
        no_of_mkr = 0
        for i in range (4):
            x_mkr[i] = 0.0
            y_mkr[i] = 0.0
            x_mkr_dv[i].set(0.0)
            y_mkr_dv[i].set(0.0)
        refresh_window(root_frame)

    clear_mkr_button = tk.Button(marker_frame, text="Clear all spatial markers", command=clear_all_mkr)
    clear_mkr_button.grid(row=5, column=0, columnspan=3)

    # Create frequency marker frame
    frmkr_frame = tk.Frame(left_frame, width=200, height=400)
    frmkr_frame.grid(row=2, column=0, padx=2, pady=5, sticky='nw')

    frmkr_widget_lst = [] # List of all type of tkinter widgets in the frmkr_frame
    frmkr_dv.clear()
    frdelta_dv.clear()
    # Create labels and entrys in frmkr_frame
    frmkr_widget = tk.Label(frmkr_frame, text="Frequency markers", anchor="w")
    frmkr_widget.grid(row=0, column=0, columnspan=3, padx=5, pady=2, sticky='nw')
    for i in range(8): # For all eight frequency markers
        # Frequency Label
        frmkr_widget_lst.append(tk.Label(frmkr_frame, bg=color8l[i], text=f"Freq {i+1}", width=5, anchor="w"))
        frmkr_widget_lst[-1].grid(row=i+1, column=0, padx=5, pady=2, sticky='nw')
        # Read-only Frequency Display
        frmkr_dv.append(tk.DoubleVar(root_frame, value=freq_mkr[i]))
        freq_lbl = tk.Label(frmkr_frame, textvariable=frmkr_dv[i], width=8, font=("Calibri", 12), bg='white', relief='sunken')
        freq_lbl.grid(row=i+1, column=1, padx=5, pady=0)
        # Read-only Delta Display
        frdelta_dv.append(tk.DoubleVar(root_frame, value=0.0))
        if i == 0:
            frmkr_widget_lst.append(tk.Label(frmkr_frame, text="Delta f", width=8, anchor="w"))
        else:
            frmkr_widget_lst.append(tk.Label(frmkr_frame, textvariable=frdelta_dv[i], width=6, font=("Calibri", 12), bg='#f0f0f0', relief='sunken'))
        frmkr_widget_lst[-1].grid(row=i+1, column=2, padx=5, pady=0)

    def clear_all_frmkr():
        global no_of_frmkr
        no_of_frmkr = 0
        for i in range (8):
            freq_mkr[i] = 0.0
            ampl_mkr[i] = 0.0
            frmkr_dv[i].set(0.0)
            frdelta_dv[i].set(0.0)
        refresh_window(root_frame)

    clear_frmkr_button = tk.Button(frmkr_frame, text="Clear all frequency markers", command=clear_all_frmkr)
    clear_frmkr_button.grid(row=9, column=0, columnspan=3)

    def update_plot_cb(self, *args): # Checkbox to show colorbar
        global plot_cb
        plot_cb = showcb_iv.get()
        refresh_window(root_frame)

    showcb_iv = tk.IntVar(root_frame)
    showcb_check = tk.Checkbutton(frmkr_frame, width=20, text="Show colorbar", variable=showcb_iv, onvalue = 1, offvalue=0)
    showcb_check.grid(row=10, column=0, columnspan=3)
    showcb_iv.trace('w', update_plot_cb)

    def save_spectrum_data():
        """Export spectrum plot data to CSV and display confirmation dialog."""
        if not cfg.scanfile1_path or len(cfg.freq_lst) == 0:
            return
        csv_filename = cfg.scanfile1_path[:-4] + "_spectrum.csv"
        with open(csv_filename, "w") as f:
            f.write("Frequency;Amplitude\n")
            for i in range(len(cfg.freq_lst)):
                f.write(f"{cfg.freq_lst[i]};{spectrum[i]}\n")
        save_csv_window = tk.Toplevel(root_frame, height=100, width=150)
        save_csv_window.title("Spectrum Data")
        tk.Label(save_csv_window, text="Spectrum data has been saved as: "+csv_filename).pack(padx=10, pady=10)
        tk.Button(save_csv_window, text=" EXIT ", command=save_csv_window.destroy).pack(pady=5)

    def save_window_screenshot():
        """Capture a screenshot of the entire application window."""
        if not cfg.scanfile1_path:
            return
        png_filename = cfg.scanfile1_path[:-4] + ".png"
        # Get screen coordinates of root window
        x = root_frame.winfo_rootx()
        y = root_frame.winfo_rooty()
        w = root_frame.winfo_width()
        h = root_frame.winfo_height()
        # Grab pixel region and save
        img_crop = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        img_crop.save(png_filename)
        save_img_window = tk.Toplevel(root_frame, height=100, width=150)
        save_img_window.title("Screenshoot saved")
        tk.Label(save_img_window, text=f"Full window image saved as:\n{os.path.basename(png_filename)}").pack(padx=10, pady=10)
        tk.Button(save_img_window, text=" EXIT ", command=save_img_window.destroy).pack(pady=5)

    # Debuging buttons
    # debug_frame = tk.Frame(left_frame, width=200, height=100)
    # debug_frame.grid(row=20, column=0, padx=2, pady=5, sticky='nw')
    # debug1_widget = tk.Button(debug_frame, text="Adjust aspect", command=adjust_aspect)
    # debug1_widget.grid(row=0, column=0, padx=5, pady=0)
    # debug2_widget = tk.Button(debug_frame, text="Print framesize", command=print_framesize)
    # debug2_widget.grid(row=0, column=1, padx=5, pady=0)

    # Save buttons
    save_frame = tk.Frame(left_frame, width=200, height=100)
    save_frame.grid(row=21, column=0, padx=2, pady=5, sticky='nw')
    save6_widget = tk.Button(save_frame, text="Save CSV", command=save_spectrum_data)
    save6_widget.grid(row=2, column=0, padx=5, pady=0)
    save7_widget = tk.Button(save_frame, text="Save image", command=save_window_screenshot)
    save7_widget.grid(row=2, column=1, padx=5, pady=0)

    if scanfile1_name != "":
        if not open_datafile1(scanfile1_name): # And finally load the scan data and refresh_window
            cfg.scanfile1_path = ""
            selected_file1_label.config(text="")
    if scanfile2_name != "":
        if not open_datafile2(scanfile2_name): # And finally load the scan data and refresh_window
            cfg.scanfile2_path = ""
            selected_file2_label.config(text="")

if __name__ == "__main__": # Standalone init and enable for manual control
    root = tk.Tk()  # create root window
    root.title("Show result stand alone test module") # title of the GUI window
    root.resizable(True, True) # Make the window resizeable
    scan_result(root)
    enable_dynamic_resize(root)
    root.mainloop()
