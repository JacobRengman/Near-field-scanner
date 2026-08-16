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
# This is the near field scanner application interactive help module.
# Help can be involed at anytime by pressing F1. The help shown will
# depend on which Notebook tab that is active. Help is not available
# when modules are executed in stand alone mode.

import os
import tkinter as tk
from tkinter import ttk

# Global reference to prevent duplicate windows and image garbage collection
help_win = None
image_refs = []


def open_help_window(parent, tab_index):
    """Open or focus the context-sensitive help window."""
    global help_win, image_refs

    if help_win is not None and tk.Toplevel.winfo_exists(help_win):
        help_win.lift()
        help_win.focus_force()
    else:
        help_win = tk.Toplevel(parent)
        help_win.title("Near Field Scanner - User Manual & Help")
        help_win.geometry("680x600")
        help_win.minsize(500, 400)

    # Clear old widgets inside help_win when re-populating
    for widget in help_win.winfo_children():
        widget.destroy()

    image_refs.clear()

    # Layout: Text widget + vertical scrollbar
    frame = ttk.Frame(help_win)
    frame.pack(fill="both", expand=True, padx=5, pady=5)

    scrollbar = ttk.Scrollbar(frame, orient="vertical")
    text_area = tk.Text(
        frame,
        wrap="word",
        yscrollcommand=scrollbar.set,
        padx=12,
        pady=12,
        font=("Helvetica", 10),
    )
    scrollbar.config(command=text_area.yview)

    scrollbar.pack(side="right", fill="y")
    text_area.pack(side="left", fill="both", expand=True)

    # Configure styling tags
    text_area.tag_configure("title", font=("Helvetica", 15, "bold"), spacing3=10)
    text_area.tag_configure(
        "section", font=("Helvetica", 11, "bold"), spacing1=12, spacing3=4
    )
    text_area.tag_configure(
        "subsection", font=("Helvetica", 10, "bold"), spacing1=8, spacing3=2
    )
    text_area.tag_configure("body", font=("Helvetica", 10), spacing2=3)
    text_area.tag_configure("action", font=("Consolas", 9, "bold"), foreground="#0055AA")

    # Load context-specific documentation
    populate_help_content(text_area, tab_index)

    # Set text widget to read-only mode
    text_area.config(state="disabled")


def insert_image(text_widget, image_path, caption=""):
    """Safely embed an image with an optional caption inside the Text widget."""
    if os.path.exists(image_path):
        try:
            img = tk.PhotoImage(file=image_path)
            image_refs.append(img)  # Retain reference against garbage collection
            text_widget.image_create(tk.END, image=img)
            text_widget.insert(tk.END, "\n")
            if caption:
                text_widget.insert(tk.END, f"Figure: {caption}\n\n", "action")
            else:
                text_widget.insert(tk.END, "\n")
        except Exception as e:
            print(f"Help image load error ({image_path}): {e}")


def populate_help_content(text, tab_index):
    """Insert context help organized top-to-bottom following GUI layout."""

    if tab_index == 0:  # -------------------- TAB 1: SCAN SETUP --------------------
        text.insert(tk.END, "Tab 1: Scan Setup & Configuration\n", "title")
        text.insert(
            tk.END,
            "Establish hardware communication parameters between the host PC, "
            "the spectrum analyzer receiver, and the 3-axis CNC scanner.\n\n",
            "body",
        )

        # IMAGE PLACEHOLDER: Full Setup Tab Overview TODO add image
        # insert_image(text, "images/help_setup_overview.png", "Scan Setup Interface")

        text.insert(tk.END, "1. Spectrum Analyzer Settings\n", "section")
        text.insert(
            tk.END,
            "* SA Model: Select driver module matching your spectrum analyzer. This function is not yet\n"
            "  implemented.\n"
            "* VISA / GPIB Address: Enter communication string (e.g., GPIB0::18::INSTR or TCPIP::192.168.1.100).\n"
            "* Test Connection: Verifies instrument communication and queries identification string (*IDN?).\n\n",
            "body",
        )

        text.insert(tk.END, "2. XY-Scanner Table Settings\n", "section")
        text.insert(
            tk.END,
            "* Serial COM Port: Select COM port assigned to motion controller.\n"
            "  Find your COM Port by looking in the Device Manager (Windows Control Panel) by"
            "  obseving the ports section while inserting the USB cable to the scanner.\n\n",
            "body",
        )
        text.insert(tk.END, "3. Project setup\n", "section")
        text.insert(
            tk.END,
            "* A new project can be setup by either copying the settings including background"
            "  calibration (optional) by\n"
            "* Open an old .nfs-file. If you want to start from scratch you can enter a new project\n"
            "  name and press the \n"
            "* New button.\n\n",
            "body",
        )

    elif tab_index == 1:  # ---------------- TAB 2: BACKGROUND CALIBRATION ----------------
        text.insert(tk.END, "Tab 2: Background Image Calibration\n", "title")
        text.insert(
            tk.END,
            "Align pixel space from a PCB component drawing with physical scanner coordinates (in millimeter).\n\n",
            "body",
        )

        text.insert(tk.END, "Left Panel: Image and coordinate view\n", "section")
        text.insert(
            tk.END,
            "",
            "body",
        )

        # IMAGE PLACEHOLDER: Calibration Tab Layout TODO add image
        # insert_image(text, "images/help_calibrate_overview.png", "Calibration Control Panel")

        text.insert(tk.END, "A. File & Orientation Frame\n", "subsection")
        text.insert(
            tk.END,
            "* File Button: Click to load layout drawing. It will work best with a component placement\n"
            "  drawing with components + RefDes in black on white background. The board outline needs\n"
            "  to be visible.\n"
            "* Rotate Button: Rotates image 90° CCW per click and remaps active marker coordinates.\n"
            "  Use this button to rotate the image in the same way that your board is rotated on the\n"
            "  scanner table\n\n",
            "body",
        )

        text.insert(tk.END, "B. Calibration Coordinate Points\n", "subsection")
        text.insert(
            tk.END,
            "* The fist two points are required to align the background image pixels with the circuit\n"
            "  board coordinates. Place the first two points preferably in opposite corners.\n"
            "* The secondary two points are optional and can be used to determine the exact position of\n"
            "  an edge or other feature on the board.\n"
            "* Placement of points can be done by clicking left mouse button. Points can be moved by\n"
            "  left clicking close to an already placed point. Points can be removed by right clicking\n"
            "  close to any point.\n"
            "* Image xy: Pixel coordinates inside drawing.\n"
            "* Scanner xy: Physical coordinates in mm.\n"
            "* [Get xy]: Copies current live scanner position into selected row.\n"
            "* [Go to]: Moves physical scanner head directly to specified mm position.\n\n"
            "  Determining the scanner head position is eased if the field probe is replaced with a\n"
            "  stylus. 3D/Step file for stylus holder is provided in the file package.\n\n",

            "body",
        )

        text.insert(tk.END, "C. Manual Motion Controls (Jogging)\n", "subsection")
        text.insert(
            tk.END,
            "* Directional Buttons (X-, X+, Y-, Y+, Up, Dn): Step head along axes.\n"
            "* Go Origo: Returns scanner head to physical (0, 0) origin.\n"
            "* Step Selector (0.01, 0.1, 1.0, 10 mm): Sets movement distance per click.\n\n"
            "  The step selector is automatically returned to zero when changing tab for security reasons.\n\n",
            "body",
        )

        text.insert(tk.END, "D. Storage Actions\n", "subsection")
        text.insert(
            tk.END,
            "* Store New Origo: Resets current position in the scanner as new physical (0,0) reference.\n"
            "* Save Calibration: Writes parameters to config file and exports image if rotated.\n\n",
            "body",
        )

        # IMAGE PLACEHOLDER: Interactive Canvas Controls TODO add image
        # insert_image(text, "images/help_calibrate_canvas.png", "Canvas Marker Placement")

        text.insert(tk.END, "Right Panel: Interactive Plot Controls\n", "section")
        text.insert(
            tk.END,
            "* Left-Click: Add new calibration point or drag existing marker.\n"
            "* Right-Click: Delete marker nearest to cursor.\n"
            "* Middle-Click + Drag: Pan viewport across PCB image.\n"
            "* Mouse Wheel: Dynamically zoom in/out centered on cursor position.\n\n",
            "body",
        )

    elif tab_index == 2:  # ------------------- TAB 3: EXECUTE SCAN -------------------
        text.insert(tk.END, "Tab 3: Execute Scan Parameters\n", "title")
        text.insert(
            tk.END,
            "Define spatial area, resolution grid, and spectrum analyzer sweep parameters.\n\n",
            "body",
        )

        # IMAGE PLACEHOLDER: Execute Tab TODO add image
        # insert_image(text, "images/help_execute_overview.png", "Scan Execution Setup")

        text.insert(tk.END, "1. File & Area Setup\n", "section")
        text.insert(
            tk.END,
            "* Project / Dataset Name: Sets target .nfs output file path. It is recommended to\n"
            "  add a description here regarding what probe and polarisation was used.\n" 
            "* X/Y Start & Stop: Define rectangular scanning boundaries (mm). These can be easily\n"
            "  adjusted with the mouse left button. Either as single clik, Klick and drag edges / corners.\n"
            "  Or by clicking a start point and drag to a stop point.\n"
            "* X/Y Step Size: Spatial resolution between measurement points (mm). Remember that the total\n"
            "  scan time grows with the square of the inversed step size.\n\n",
            "body",
        )

        text.insert(tk.END, "2. Frequency Sweep Parameters\n", "section")
        text.insert(
            tk.END,
            "* Start / Stop Frequency: Measurement band in MHz.\n"
            "* Sweep Points: Number of bins per trace in one spectrum measurement.\n"
            "* RBW / Auto RBW: Resolution Bandwidth setting.\n"
            "* Averages: Trace sweeps per grid point for noise reduction.\n"
            "* Peak / Max-Hold Detector: Receiver trace acquisition mode. Use Max-Hold only\n"
            "  when dealing with a slowly changing intermitent signal generator. This is seldomly needed.\n\n",
            "body",
        )

        text.insert(tk.END, "3. Scan time prediction\n", "section")
        text.insert(
            tk.END,
            "* The scan time prediction can estimate at which time the scanning will be ready when\n"
            "  using the pressent parameters. The prediction is achieved by measuring the time it takes\n"
            "  to move one step and measure one point. The test needs to be invoked by the\n"
            "* Test speed button when ever spectrum analyzer parameters or step size is changed.\n\n",
            "body",
        )

        text.insert(tk.END, "4. Progress bar\n", "section")
        text.insert(
            tk.END,
            "* The progress bar will show the progress of a started scanning.\n\n",
            "body",
        )

        text.insert(tk.END, "5. Execution Control\n", "section")
        text.insert(
            tk.END,
            "* START SCAN: Initiates automated movement and data acquisition sequence.\n"
            "* STOP SCAN: Emergency pause/stop sequence, saving partial data gathered.\n\n",
            "body",
        )

    elif tab_index == 3:  # -------------------- TAB 4: SHOW RESULT --------------------
        text.insert(tk.END, "Tab 4: Results & Spectrum Analysis\n", "title")
        text.insert(
            tk.END,
            "Visualize spatial near-field energy distributions overlaid onto PCB drawings and inspect localized spectra.\n\n",
            "body",
        )

        # IMAGE PLACEHOLDER: Result Tab Overview TODO add image
        # insert_image(text, "images/help_result_overview.png", "Result Visualization Window")

        text.insert(tk.END, "1. Dataset Loading\n", "section")
        text.insert(
            tk.END,
            "* Dataset 1 (Primary): Opens main scan file (.nfs).\n"
            "* Dataset 2 (Secondary): Opens secondary scan file with orthogonal field (.nfs)\n"
            "  to calculate combined total field magnitude:\n\n"
            "  Scanning with a near filed probe in both polarisations is often needed since\n"
            "  a high filed amplitude can be hidden if the field vector is perpendicular to\n"
            "  the probe in any given measurement point\n\n",
            "body",
        )

        text.insert(tk.END, "2. Spatial Heatmap Controls\n", "section")
        text.insert(
            tk.END,
            "* Left-Click Heatmap: Places spatial marker to display frequency spectrum at that coordinate.\n"
            "* Middle-Click + Drag: Pan spatial viewport.\n"
            "* Mouse Wheel: Zoom in/out over PCB region.\n\n",
            "body",
        )

        text.insert(tk.END, "3. Spectrum Plot & Markers\n", "section")
        text.insert(
            tk.END,
            "* Frequency Trace Plot: Shows amplitude vs frequency for all samples or only active spatial markers.\n"
            "* Frequency Range Sliders: Adjust min/max frequency window to isolate specific emissions.\n"
            "* Peak Search: Automatically identifies and marks highest field emissions.\n"
            "* Delta Markers: Measures frequency spacing and amplitude differences between peaks. The distance\n"
            "between frequency markers is a good indication of the fundamental clock frequency of the agressor.\n\n",
            "body",
        )
