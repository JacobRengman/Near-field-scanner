# Hewlett Packard 8519 spectrum analyzer driver routines

# HP 8591 - command list :
# IP;       Instrument preset
# SNGLS     Select Single sweep
# TS;       Take sweep
# CF?       Ask Center frequency
# FA        Start frequecy
# FB        Stop frequency
# SP        Span möjligen "SP 934 MZ;"
# SP?       Ask Span frequency?
# MKPK HI;  Place maker on highest peak
# TDF P;    Output format to real (P) binary (B), A-block-format, I-block format, measuremtns units (M) format
# TDF B;    Output format to two byte integers
# MKA?      Send amplitude value of marker to PC
# MKF?      Send frequency of marker to PC
# CONTS;    Set the sweeb back to continous sweep
# TRA?      Trace data amplutudes -75.14,-76.75,-76.61,-76.12,-75.98,-76.98,-76.21,-76.56,-76.35,-77.01,-77.24,-76.89,-75.94,-76.38,-76.61,-76.87,-76.63,-76.87,-77.63,-76.54,-77.19,-76.21,-77.10,-76.03,-76.70,-76.59,-75.17,-76.03,-76.80,-76.87,-76.42,-76.17,-77.38,-76.84,-76.87,-77.19,-76.84,-76.33,-77.08,-76.87,-76.61,-76.80,-76.56,-77.05,-77.01,-77.01,-76.28,-77.05,-76.45,-76.61,-76.49,-76.91,-77.22,-76.77,-76.70,-76.21,-75.91,-76.47,-77.38,-76.63,-76.52,-76.80,-76.98,-76.87,-76.05,-77.35,-77.19,-75.75,-76.73,-76.07,-76.70,-77.31,-76.82,-76.26,-76.84,-77.42,-76.89,-76.94,-76.89,-75.80,-76.66,-76.49,-76.03,-76.40,-76.49,-76.82,-76.89,-77.22,-77.17,-76.84,-76.10,-77.15,-76.75,-77.31,-76.38,-77.08,-76.12,-77.47,-77.33,-77.31,-77.40,-76.38,-76.77,-76.21,-76.26,-76.59,-77.05,-76.42,-76.08,-76.62,-76.41,-77.16,-76.76,-77.04,-75.90,-76.92,-77.20,-76.57,-75.53,-77.11,-76.55,-77.30,-77.25,-77.43,-77.11,-76.76,-76.57,-76.32,-76.55,-76.95,-76.95,-76.76,-77.18,-76.90,-76.57,-76.97,-76.81,-76.69,-76.50,-77.11,-76.92,-77.43,-77.30,-77.41,-76.85,-75.55,-76.27,-73.97,-70.71,-70.48,-76.11,-76.20,-76.36,-76.69,-76.60,-75.95,-77.30,-76.78,-76.22,-76.46,-76.48,-76.90,-76.11,-76.81,-77.53,-76.25,-76.90,-76.85,-76.90,-76.11,-76.34,-76.27,-77.06,-77.32,-77.04,-76.81,-76.95,-76.06,-76.88,-77.16,-76.43,-76.85,-76.74,-76.90,-77.16,-76.67,-76.39,-75.74,-76.08,-77.39,-76.88,-76.64,-76.50,-76.99,-76.29,-77.27,-76.92,-76.83,-76.95,-76.48,-77.09,-76.43,-76.32,-76.55,-75.97,-76.74,-76.71,-76.97,-76.92,-76.76,-77.09,-76.34,-77.36,-77.20,-76.36,-77.30,-76.78,-76.78,-76.85,-75.74,-77.02,-74.41,-76.62,-77.04,-76.99,-76.90,-77.16,-76.90,-76.43,-76.74,-76.67,-77.16,-76.55,-76.74,-77.04,-76.64,-76.18,-76.92,-76.76,-77.16,-77.27,-77.13,-76.92,-77.06,-76.67,-76.71,-76.69,-76.55,-77.25,-77.16,-75.95,-76.97,-76.81,-76.64,-76.95,-76.57,-75.48,-77.20,-76.76,-76.83,-76.81,-77.13,-76.46,-76.06,-76.90,-77.46,-77.32,-76.69,-77.13,-76.22,-76.34,-77.09,-76.74,-77.04,-75.85,-77.48,-77.69,-77.34,-77.20,-77.20,-75.74,-76.83,-77.46,-76.20,-77.13,-76.76,-75.99,-76.48,-76.34,-75.57,-77.20,-77.16,-77.27,-77.64,-76.78,-76.04,-76.50,-75.92,-76.83,-76.85,-76.85,-76.53,-76.50,-76.53,-77.46,-77.16,-76.97,-76.88,-76.85,-77.18,-77.36,-75.88,-76.69,-75.95,-77.53,-76.43,-76.46,-77.06,-76.57,-76.55,-77.13,-77.71,-77.04,-77.02,-76.67,-76.78,-76.95,-75.76,-76.67,-77.11,-76.81,-76.74,-76.74,-76.81,-76.76,-77.13,-76.81,-76.67,-74.39,-71.12,-72.16,-76.53,-76.78,-77.04,-77.09,-77.34,-76.32,-76.74,-76.15,-77.16,-77.64,-76.69,-76.76,-77.04,-77.20,-77.10,-76.61,-76.79,-77.56,-77.12,-76.42,-76.86,-77.17,-77.42,-76.79,-75.40,-72.45,-68.18,-69.10,-71.32,-75.19,-76.77,-76.91,-76.93,-77.03,-76.30,-77.33,-77.35,-77.21,-77.05,-76.77,-75.70,-76.77,-76.56,-77.14,-76.77,-77.03,-76.70,-77.17,-77.37,-76.68,-77.40,-76.44,-77.35,-77.19,-77.37,-77.14,-76.26,-77.00,-77.10,-77.05
# TRA?      binary format ?x01??xE6??x01?E?x01?S?x01??x84??x01??x92??x01?.
# DET POS   Detector POS (positive-peak), PK SMP (sample detection)?
# RB, VB    Resolution Bandwidth / Video Bandwidth
# ST        Sweep time, a number or AUTO
# STB?      Status byte query
# RQS       Service request Mask, 32 = Illegal command, 16 = Command complete, 8= Hardware broken, 4 = End of sweep, 2 = Unit key pressed
#           40 seems like default 40 = 32 + 8 (
# DONE?
# RL?       Reference level (position of the lowest line on the screen in dBm)
# SMP?      Sample detection mode

# General spectrum analyzer constants
min_frequency = 150E3 # 150 kHz
max_frequency = 1800E6 # 1.8 GHz
max_no_of_points = 401
specanalyzer = 0 # global handle for spectrum analyser accesses

def measure_spectrum(sweeps=1): # HP 8591 Measure and retreive the spectrum data from the spectrum analyzer
    if specanalyzer != 0:
        specanalyzer.write("CLRAVG;")
        if sweeps > 1: # Use Max hold
            specanalyzer.write("CLRW TRA;")  # Clear the trace first
            specanalyzer.write("MXMH TRA;")  # Turn on Max Hold for Trace A
        for _ in range(sweeps):
            specanalyzer.write("TS;")        # Execute the specified number of sweeps
        specanalyzer.write("TRA?") # Retrieve the data
        spectrum_str = str(specanalyzer.read_raw(3000))
        spectrum_str_lst = spectrum_str[2:-5].split(",")
        spectrum_lst = []
        for element in spectrum_str_lst:
            spectrum_lst.append(float(element))
    else:
        print("No spectum analyzer connected")
        spectrum_lst = [-70.00] # return dummy value
    return spectrum_lst

def set_span(start, stop): # HP 8591 Setup spectrum analyzer span for measurements, start/stop frequencies in Hz
    if specanalyzer != 0:
        specanalyzer.write("FA "+str(start)+";")
        specanalyzer.write("FB "+str(stop)+";")
        print(start, stop)
    else:
        print("No spectum analyzer connected")
    points = 401 # Default for HP 8591
    step = (stop - start) / (points - 1)
    freq_lst = []
    for i in range(points):
        freq_lst.append(start + i * step)
    return freq_lst

def set_points(points):
    print("HP 8591 doesn't support setting number of points.")
    pass # Im not sure the 8591 support setting number of points

def get_points():
    return 401

def set_average(average):
    if(specanalyzer != 0):
        if(average == 0):
            specanalyzer.write("VAVG OFF;") # Video average off
            print("Video average OFF")
        else:
            specanalyzer.write("VAVG "+str(average)+";") # Video average
            print("Video average "+str(average))
    else:
        print("No spectum analyzer connected")

def set_rbw(rbw, rbw_auto):
    if(specanalyzer != 0):
        if(rbw_auto == 1):
            specanalyzer.write("RB AUTO;") # Resolution bandwidth set to AUTO
        else:
            specanalyzer.write("RB "+str(rbw)+";") # Resolution bandwidth
    else:
        print("No spectum analyzer connected")

def set_peak_detector():
    if(specanalyzer != 0):
        specanalyzer.write("DET POS;") # Positive peak detection
    else:
        print("No spectum analyzer connected")

def set_sample_detector():
    if(specanalyzer != 0):
        specanalyzer.write("DET SMP;") # Sample detection
    else:
        print("No spectum analyzer connected")

def set_sweep_time(sweep_time):
    if(specanalyzer != 0):
        specanalyzer.write("ST "+str(sweep_time)+";") # Sweep time, longer time gives smother curves
    else:
        print("No spectum analyzer connected")

def local():
    if(specanalyzer != 0):
        specanalyzer.write("CONTS;") # Back to continous sweep
        specanalyzer.write("VAVG 0;") # Video average
    else:
        print("No spectum analyzer connected")

def write(command):
    if(specanalyzer != 0):
        specanalyzer.write(command) # Write the debug command
    else:
        print("No spectum analyzer connected")

#Spectrum Analyzer HP_8591 connection
def init(rm, address):
    global specanalyzer
    try:
        specanalyzer = rm.open_resource(address)
        specanalyzer.timeout = 20000
        #specanalyzer.write('*IDN?') # NOT supported by this old instrumnet :-(
        #idn = specanalyzer.read()
        #if idn == "":
        print("Spectrum Analyzer connected")
        specanalyzer.write("SNGLS;") # Single sweep
        specanalyzer.write("TDF P;") # Transfer data format "real"
        #specanalyzer.write("DET PK;") # Detector peak (default)
        specanalyzer.write("ST 0.2") # Sweep time
        return 1
    except:
        print("Spectrum Analyzer failed")
        return 0
