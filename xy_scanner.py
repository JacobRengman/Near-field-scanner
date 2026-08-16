# CNC-mill xyz-table driver originally developed for CNC 3018 with GRBL-control board
# The GRBL-control board accept G-code
# The driver send one command at the time and wait for "Idle"-state to appear
try:
    import serial
except:
    print("Please install pyserial via the \'pip install pyserial\' command.")
    exit(0)
import time

scanner_handle = 0

def write(gcode): # Writes one g-code string to the GRBL-controller over COM-port
    if(scanner_handle != 0):
        inbuff = b""
        timeout = 10000
        if (scanner_handle.in_waiting > 0):
            scanner_handle.read(scanner_handle.in_waiting)
        print("To scanner: " + gcode.replace("\n", ""))
        scanner_handle.write(bytes(gcode, 'utf-8'))
        while (inbuff != b"ok\r\n") and (timeout > 0):
            timeout -= 1
            if(scanner_handle.in_waiting > 0):
                temp = scanner_handle.read(scanner_handle.in_waiting)
                inbuff += temp
        # Wait for the command to finnish (status == Idle)
        inbuff = b"<Run,M"
        while (inbuff[1:5] != b"Idle") and (timeout > 0):
            time.sleep(0.1)
            if (scanner_handle.in_waiting > 0):
                scrap = scanner_handle.read(scanner_handle.in_waiting)
            scanner_handle.write(b"?")
            time.sleep(0.1)
            inbuff = b"<Run,M"
            timeout -= 1
            if(scanner_handle.in_waiting > 0):
                inbuff = scanner_handle.read(scanner_handle.in_waiting)
    else:
        print("Gcode printout (no scanner connected): " + gcode.replace("\n", ""))

def init(comport):
    global scanner_handle
    try: # connecting to scanner
        scanner_handle = serial.Serial(comport, 115200)
        print("Serial port created")
        time.sleep(3) # Wait for GRBL to ???
        if(scanner_handle.in_waiting > 0):
            scanner_handle.read(scanner_handle.in_waiting)
        # Init GRBL-based scanner (CNC 3018 Pro in my case)
        write("G17\n") # Draw arcs in XY-plane
        write("G21\n") # Distances are in millimeters
        write("G90\n") # All distances and positions are Absolute values from the current origin.
        write("G94\n") # Units/min mode at the current F rate.
        return 1
    except:
        print("Serial port to scanner not found")
        return 0

def close():
    scanner_handle.close()

if __name__ == '__main__':
    # Standalone xy_scanner module
    pass
    print("xy-scanner module")
