# Near Field Scanner

Near field scanner is a tool to determine from where and how much a circuit board is radiating in the RF spectrum. The tool uses a spectrum analyzer + a CNC XY-table to measures and gives a visual image of the RF-emissions from the circuitboard.

---

## 🌟 Key Features

* **Hardware Abstraction Layer**: Connects via PyVISA (GPIB/USB/Ethernet) for spectrum analyzers and PySerial (GRBL/G-code) for CNC motion tables.
* **Background Image Calibration**: Import PCB board photos, align optical pixel coordinates to physical CNC coordinates ($x,y$ in mm), and rotate overlay graphics.
* **Configurable Scan Execution**:
* Customizable scan boundaries, step sizes ($x,y$ steps automatically synced), probe clearance ($z$), and sweep parameters.
* Real-time grid preview, ETA calculator, and live sweep progress tracking.


* **Interactive Result Viewer**:
* Spatial radiation heatmap overlays synced directly on top of PCB background photos.
* Interactive frequency zoom sliders, marker measurements, delta frequency calculations, and image export.


* **Modular Codebase**: Clean, decoupled architecture supporting standalone module testing and easy addition of custom spectrum analyzer drivers.

---

## 🛠️ System Architecture & Hardware Requirements

### Hardware Dependencies

1. **Spectrum Analyzer**: Any instrument supported via PyVISA (e.g., HP 8591 series, Rigol, Siglent, Keysight).
2. **XYZ Motion Table**: CNC router table (e.g., CNC 3018 running GRBL) or custom linear stages accepting serial G-code commands.
3. **RF Near-Field Probe**: Passive or active H-field / E-field probe attached to the CNC $z$-axis spindle head.

---

## 📁 Repository Structure

```text
Nearfield_scanner/
│
├── near_field_scanner.py      # Main application launcher
├── scan_config.py             # Global runtime settings & configuration
│
├── modules/                   # GUI pages and application workflows
│   ├── scan_setup.py          # Tab 0: Hardware configuration & project management
│   ├── scan_calibrate.py      # Tab 1: Image alignment & spatial coordinate calibration
│   ├── scan_execute.py        # Tab 2: Scan boundaries, frequency span & execution
│   ├── scan_result.py         # Tab 3: Heatmap visualization, markers & analysis
│   └── scan_help.py           # F1 Context help manager
│
├── hardware/                  # Instrument drivers
│   ├── xy_scanner.py          # CNC motion table controller (Serial / GRBL)
│   └── HP_8591.py             # HP 8591 series spectrum analyzer driver
│
├── assets/                    # Application icons and help graphics
├── background_images/         # User PCB photos and reference board images
└── results/                   # Saved scan datasets (.nfs) and exported screenshots

```

---

## 🚀 Getting Started

### Prerequisites

* **Python 3.7+** (Python 3.7 is recommended on Windows for PyVISA GPIB driver stability).
* Operating System: Windows, Linux, or macOS.

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/your-username/Nearfield_scanner.git
cd Nearfield_scanner

```


2. **Install required dependencies**:
```bash
pip install matplotlib numpy pillow pyvisa pyserial

```


3. **Verify VISA Backend**:
Ensure [NI-VISA](https://www.google.com/search?q=https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html) or [PyVISA-py](https://www.google.com/search?q=https://pyvisa-py.readthedocs.io/) is installed on your operating system so PyVISA can discover connected VISA instruments.

---

## 💻 Usage

### Running the Application

Launch the complete suite from the root directory:

```bash
python near_field_scanner.py

```

### Running Individual Modules in Standalone Mode

Each feature module in `modules/` can be executed independently for isolated testing or debugging:

```bash
python modules/scan_setup.py
python modules/scan_execute.py

```

---

## 📖 Recommended Workflow

1. **Scan Setup (Tab 1)**: Select your Spectrum Analyzer VISA address and CNC COM port. Click **Test** to verify communication. Create a new project name or copy settings from an existing `.nfs` project file.
2. **Background Calibration (Tab 2)**: Load a PCB image from `background_images/`. Define optical calibration points on the image and pair them with physical CNC probe locations.
3. **Execute Scan (Tab 3)**: Define the $x,y$ scan bounds, step size (mm), frequency span (start/stop), and averaging sweeps. Run the automated scan.
4. **Show Results (Tab 4)**: Inspect localized EMI hot spots over the board photo, analyze peak spectrum frequencies using markers, and export screenshots to `results/`.

---

## 📄 License

This project is licensed under the GNU General Public License v2.0 or later - see the [LICENSE](https://www.google.com/search?q=LICENSE) file for details.

```text
Copyright (C) 2024-2026 Jacob Rengman

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

```

---

## 🤝 Contributing & Credits

* **Initial Author & EMC Lead**: Jacob Rengman ([www.irr.se](https://www.irr.se))
* **Background Research**: Göran Nordahl ([www.lohmega.com](https://www.lohmega.com))
* **Embedded Software**: Stefan Petersen ([www.spe.ciellt.se](https://www.spe.ciellt.se))

Pull requests are welcome! If you write a driver module for an additional spectrum analyzer model, please place it in the `hardware/` folder and submit a PR.