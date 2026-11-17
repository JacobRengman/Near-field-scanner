# Siglent SSA3021X (SSA3000X Plus series) spectrum analyzer driver routines
#
# NOTE: Written from the SSA3000X Plus programming guide, WITHOUT access to the instrument.
#       Run hardware/spectrum_analyzers/Siglent_SSA3021X_test.py on a real instrument to verify.
#
# SCPI commands used:
# *IDN?                          Identification
# *CLS                           Clear status and error queue
# *RST / :SYSTem:PRESet          Reset / preset
# :FREQuency:STARt / :STOP       Start / stop frequency
# :BWIDth[:RESolution] <Hz>      Resolution bandwidth       :BWIDth:AUTO ON|OFF
# :SWEep:TIME <s>                Sweep time                 :SWEep:TIME:AUTO ON|OFF
# :INITiate:CONTinuous OFF|ON    Single / continuous sweep
# :INITiate:IMMediate            Start a sweep
# *OPC?                          Returns 1 when the sweep is finished
# :FORMat ASCii                  Trace data as comma separated text
# :TRACe:DATA? 1                 Read trace 1 (dBm)
# :TRACe1:MODE WRITe|MAXHold|AVERage   Trace mode
# :AVERage:TRACe1:COUNt <n>      Number of averages
# :DETector:TRACe1 POSitive|SAMPle     Detector

# General spectrum analyzer constants
min_frequency = 9E3 # 9 kHz (assumed for the SSA3021X)
max_frequency = 2.1E9 # 2.1 GHz (assumed for the SSA3021X)
min_no_of_points = 751 # The number of points is assumed to be fixed
max_no_of_points = 751
_dummy_warned = False
specanalyzer = 0 # global handle for spectrum analyser accesses
_average = 0 # Number of averages requested (0 = off)
_detector = "POSitive"

def _wait_done(): # Block until the instrument has finished the current operation
    specanalyzer.query("*OPC?")

def measure_spectrum(sweeps=1): # Measure and retrieve the spectrum data from the spectrum analyzer
    if specanalyzer != 0:
        if _average > 0: # Trace average
            specanalyzer.write(":TRACe1:MODE AVERage")
            specanalyzer.write(":AVERage:TRACe1:COUNt " + str(_average))
            specanalyzer.write(":AVERage:TRACe1:CLEar")
            n = max(_average, sweeps)
        elif sweeps > 1: # Use Max hold
            specanalyzer.write(":TRACe1:MODE MAXHold")
            n = sweeps
        else:
            specanalyzer.write(":TRACe1:MODE WRITe")
            n = 1
        for _ in range(n):
            specanalyzer.write(":INITiate:IMMediate") # Take one sweep
            _wait_done()
        spectrum_str = specanalyzer.query(":TRACe:DATA? 1")
        spectrum_lst = []
        for element in spectrum_str.strip().split(","):
            element = element.strip()
            if element != "":
                spectrum_lst.append(float(element))
    else:
        global _dummy_warned
        if not _dummy_warned: # Warn once instead of once per measured point
            print("No spectrum analyzer connected, returning dummy data (-70 dBm)")
            _dummy_warned = True
        spectrum_lst = [-70.00] # return dummy value
    return spectrum_lst

def set_span(start, stop): # Setup spectrum analyzer span for measurements, start/stop frequencies in Hz
    if specanalyzer != 0:
        specanalyzer.write(f":FREQuency:STARt {start:.0f}")
        specanalyzer.write(f":FREQuency:STOP {stop:.0f}")
    points = get_points()
    step = (stop - start) / (points - 1)
    freq_lst = []
    for i in range(points):
        freq_lst.append(start + i * step)
    return freq_lst

def set_points(points):
    pass # The number of points is fixed on this instrument (assumed)

def get_points():
    return 751

def set_average(average):
    global _average
    _average = int(average) # Applied in measure_spectrum

def set_rbw(rbw, rbw_auto):
    if specanalyzer != 0:
        if rbw_auto == 1:
            specanalyzer.write(":BWIDth:AUTO ON") # Resolution bandwidth set to AUTO
        else:
            specanalyzer.write(":BWIDth:AUTO OFF")
            specanalyzer.write(":BWIDth " + str(rbw)) # Resolution bandwidth in Hz

def set_peak_detector():
    if specanalyzer != 0:
        specanalyzer.write(":DETector:TRACe1 POSitive") # Positive peak detection

def set_sample_detector():
    if specanalyzer != 0:
        specanalyzer.write(":DETector:TRACe1 SAMPle") # Sample detection

def set_sweep_time(sweep_time):
    if specanalyzer != 0:
        specanalyzer.write(":SWEep:TIME:AUTO OFF")
        specanalyzer.write(":SWEep:TIME " + str(sweep_time)) # Sweep time in seconds

def local():
    global _average
    _average = 0
    if specanalyzer != 0:
        specanalyzer.write(":TRACe1:MODE WRITe")
        specanalyzer.write(":SWEep:TIME:AUTO ON")
        specanalyzer.write(":INITiate:CONTinuous ON") # Back to continuous sweep

def write(command):
    if specanalyzer != 0:
        specanalyzer.write(command) # Write the debug command

#Spectrum Analyzer Siglent SSA3021X connection
def init(rm, address):
    global specanalyzer
    try:
        specanalyzer = rm.open_resource(address)
        specanalyzer.timeout = 30000
        idn = specanalyzer.query("*IDN?")
        if "SIGLENT" not in idn.upper():
            print("Spectrum analyzer: unexpected instrument at " + str(address) + ": " + idn.strip())
        specanalyzer.write("*CLS") # Clear old status and error queue
        specanalyzer.write(":INITiate:CONTinuous OFF") # Single sweep
        specanalyzer.write(":FORMat ASCii") # Trace data as text
        return 1
    except:
        specanalyzer = 0
        print("Spectrum analyzer: could not open " + str(address))
        return 0
