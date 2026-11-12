# TinySA / TinySA Ultra spectrum analyzer driver routines
#
# TinySA Serial CLI Command Summary:
# - sweep <start_hz> <stop_hz> [points] : Set sweep frequency range and point count
# - data [0|1]                          : Query measured power values in dBm
# - rbw <freq|auto>                     : Set Resolution Bandwidth
# - pause / resume                      : Pause/resume internal sweep loop
# - info / deviceid                     : Query hardware identification
import time
import re
import serial
import serial.tools.list_ports

# General spectrum analyzer constants
# Instrument limits. The defaults are for a tinySA Ultra; init() reads the model
# from the device and sets the real limits (see _identify_model()).
# NOTE: A tinySA Ultra+ (ZS-406) reaches higher than 6 GHz, raise max_frequency below if needed.
min_frequency = 100E3       # 100 kHz
max_frequency = 6E9         # 6 GHz (tinySA Ultra). A tinySA Basic only reaches 960 MHz
min_no_of_points = 51       # Minimum number of sweep points
max_no_of_points = 450      # Maximum number of sweep points (tinySA Ultra). A tinySA Basic has 290
model_name = "unknown"      # Set by init()
specanalyzer = None         # Serial handle

# Internal state tracking
_current_start = 10E6
_current_stop = 100E6
_current_points = 290       # Standard TinySA default points per sweep
_sweep_time_s = 1.0         # Cached measured sweep duration (seconds), updated on span/points/rbw change

def _extract_com_port(address):
    """Convert VISA address (e.g., 'ASRL3::INSTR' or 'COM3') to standard port name."""
    if address.startswith("ASRL") and "::" in address:
        match = re.search(r'\d+', address)
        if match:
            return _format_com_port(int(match.group(0)))
    elif address.upper().startswith("COM"):
        match = re.search(r'\d+', address)
        if match:
            return _format_com_port(int(match.group(0)))
    return address

def _format_com_port(port_number):
    """Format a COM port number for pyserial, using the \\\\.\\ prefix
    required by Windows for COM10 and above."""
    if port_number >= 10:
        return f"\\\\.\\COM{port_number}"
    return f"COM{port_number}"

def _read_until_prompt(timeout=3.0, after=None):
    """Read serial response until tinySA sends its 'ch>' prompt.
    If 'after' is given (the command text that was sent), only a prompt that
    comes AFTER the echo of that command ends the read. This keeps us in step
    with the device even if an old prompt is still waiting in the buffer."""
    buffer = ""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if specanalyzer and specanalyzer.in_waiting > 0:
            chunk = specanalyzer.read(specanalyzer.in_waiting).decode('ascii', errors='ignore')
            buffer += chunk
            search_from = 0
            if after is not None:
                pos = buffer.rfind(after)
                search_from = pos + len(after) if pos >= 0 else len(buffer) + 1
            if "ch>" in buffer[search_from:]:
                break
        time.sleep(0.01)
    return buffer

def _parse_values(resp, after=None):
    """Parse dBm values from a response. Each data line starts with the dBm value
    (scan lines look like '-9.400000e+01 0.000000000'); the command echo and the
    'ch>' prompt are not numbers and are skipped."""
    if after is not None and after in resp:
        resp = resp[resp.rfind(after) + len(after):]  # ignore anything before our echo
    values = []
    # The last piece after the final newline is the prompt, or an incomplete line
    # if the response was cut off. Never use it.
    for line in resp.replace('\r', '').split('\n')[:-1]:
        tokens = line.split()
        if not tokens:
            continue
        try:
            values.append(_to_float(tokens[0]))
        except ValueError:
            pass
    return values

def _to_float(token):
    """float() that also handles a tinySA firmware formatting bug: a value that
    rounds up to 10.000000 in the mantissa is printed as ':.000000' (':' is the
    character after '9'), e.g. '-:.000000e+01' means -10.000000e+01 = -100 dBm."""
    try:
        return float(token)
    except ValueError:
        if ':' in token:
            return float(token.replace(':', '10'))
        raise

def _resync():
    """Get back in step with the device after a failed/cut off response."""
    try:
        time.sleep(0.2)
        specanalyzer.reset_input_buffer()
        specanalyzer.write(b"\r\n")
        _read_until_prompt(timeout=1.0)
        time.sleep(0.1)
        specanalyzer.reset_input_buffer()
    except Exception as e:
        print(f"TinySA resync error: {e}")

def _query_sweep_time():
    """Ask the device how long one sweep takes (seconds) and cache it.
    Uses the documented 'sweeptime' command, avoiding the buggy 'wait' command
    present in some tinySA firmware builds."""
    global specanalyzer, _sweep_time_s
    if specanalyzer and specanalyzer.is_open:
        try:
            specanalyzer.write(b"sweeptime\r\n")
            resp = _read_until_prompt()
            # Without argument the firmware prints its usage text followed by the
            # current sweep time, e.g. "usage: sweeptime 0.003..60" and " 278ms".
            # Only accept numbers that have a unit, so the "0.003..60" range is ignored.
            matches = re.findall(r'(\d+(?:\.\d+)?)\s*(ms|s)\b', resp)
            if matches:
                value, unit = matches[-1]
                _sweep_time_s = float(value) / (1000.0 if unit == "ms" else 1.0)
        except Exception as e:
            print(f"TinySA sweeptime query error: {e}")
    return _sweep_time_s

def _scan_once():
    """One complete single sweep using the 'scan' command.
    'scan' runs exactly one sweep and only returns the data (followed by the
    'ch>' prompt) when the sweep is finished, so no guessing of the sweep time
    is needed. outmask 2 = output only the measured values (dBm).
    Returns a list of values, or None if the response looks wrong."""
    specanalyzer.reset_input_buffer()  # discard stale bytes
    t0 = time.time()
    cmd_text = f"scan {int(_current_start)} {int(_current_stop)} {_current_points} 2"
    specanalyzer.write((cmd_text + "\r\n").encode('ascii'))
    # The timeout is only a safety net, the prompt normally ends the wait.
    resp = _read_until_prompt(timeout=_sweep_time_s * 3.0 + 5.0, after=cmd_text)
    values = _parse_values(resp, after=cmd_text)
    if len(values) != _current_points:
        print(f"TinySA scan returned {len(values)} values, expected {_current_points} "
              f"(waited {time.time() - t0:.1f} s, sweeptime {_sweep_time_s:.3f} s). "
              f"End of response: {resp[-60:]!r}")
        _resync()
        return None
    return values

def _legacy_sweep():
    """Old method: resume, wait the estimated sweep time, pause, read 'data 0'.
    Kept as a fallback if 'scan' is not supported by the firmware."""
    specanalyzer.reset_input_buffer()
    specanalyzer.write(b"resume\r\n")
    _read_until_prompt(after="resume")  # read the reply now so we stay in step
    time.sleep(_sweep_time_s * 1.3 + 0.05)
    specanalyzer.write(b"pause\r\n")
    _read_until_prompt(after="pause")

    specanalyzer.write(b"data 0\r\n")
    raw_response = _read_until_prompt(after="data 0")
    return _parse_values(raw_response, after="data 0")

def measure_spectrum(sweeps=1):
    """Measure and retrieve power data (dBm) from the TinySA."""
    global specanalyzer, _current_points

    if specanalyzer and specanalyzer.is_open:
        try:
            combined_spectrum = []
            for sweep_idx in range(sweeps):
                # Never accept a sweep with the wrong number of points (that would
                # be saved as a corrupt point in the scan file). Retry a few times.
                sweep_data = None
                for attempt in range(3):
                    sweep_data = _scan_once()
                    if sweep_data is None:
                        sweep_data = _legacy_sweep()
                        if len(sweep_data) != _current_points:
                            print(f"TinySA legacy sweep returned {len(sweep_data)} values, "
                                  f"expected {_current_points} (attempt {attempt + 1}/3)")
                            sweep_data = None
                    if sweep_data is not None:
                        break
                if sweep_data is None:
                    raise RuntimeError("no valid sweep from the tinySA after 3 attempts")

                if sweep_idx == 0 or not combined_spectrum:
                    combined_spectrum = sweep_data
                else:
                    combined_spectrum = [max(c, s) for c, s in zip(combined_spectrum, sweep_data)]

            if combined_spectrum:
                return combined_spectrum
        except Exception as e:
            print(f"TinySA data read error: {e}")
        else:
            print("TinySA returned no data, using dummy data (-70 dBm)")
    else:
        print("TinySA NOT connected (serial port closed), using dummy data (-70 dBm)")

    return [-70.00] * _current_points

def set_span(start, stop):
    """Setup TinySA frequency span (Hz) and return frequency list."""
    global specanalyzer, _current_start, _current_stop, _current_points
    _current_start, _current_stop = float(start), float(stop)
    
    if specanalyzer and specanalyzer.is_open:
        try:
            cmd = f"sweep {int(_current_start)} {int(_current_stop)} {_current_points}\r\n"
            specanalyzer.write(cmd.encode('ascii'))
            _read_until_prompt()
            _query_sweep_time()
        except Exception as e:
            print(f"TinySA set_span error: {e}")

    step = (_current_stop - _current_start) / max(1, (_current_points - 1))
    return [_current_start + i * step for i in range(_current_points)]

def set_points(points):
    global specanalyzer, _current_points, _current_start, _current_stop
    requested = int(points)
    _current_points = max(min_no_of_points, min(requested, max_no_of_points))
    if _current_points != requested:
        print(f"TinySA supports {min_no_of_points}..{max_no_of_points} points, using {_current_points} instead of {requested}")
    if specanalyzer and specanalyzer.is_open:
        cmd = f"sweep {int(_current_start)} {int(_current_stop)} {_current_points}\r\n"
        specanalyzer.write(cmd.encode('ascii'))
        _read_until_prompt()
        _query_sweep_time()

def get_points():
    return _current_points

def set_average(average):
    pass

def set_rbw(rbw, rbw_auto):
    global specanalyzer
    if specanalyzer and specanalyzer.is_open:
        cmd = "rbw auto\r\n" if rbw_auto == 1 else f"rbw {int(rbw / 1000)}k\r\n"
        specanalyzer.write(cmd.encode('ascii'))
        _read_until_prompt()
        _query_sweep_time()

def set_peak_detector():
    pass

def set_sample_detector():
    pass

def set_sweep_time(sweep_time):
    """Set the duration of one sweep in seconds (tinySA accepts 0.003..60 s, 0 = leave as is).
    With auto RBW the tinySA adapts its RBW to the sweep time. With a fixed RBW the sweep
    can't be faster than that RBW needs. Call this AFTER set_span/set_points/set_rbw, since
    they can change the sweep time. The sweep time actually in use is read back and printed."""
    global specanalyzer
    if specanalyzer and specanalyzer.is_open and float(sweep_time) > 0:
        wanted = max(0.003, min(float(sweep_time), 60.0))
        cmd_text = f"sweeptime {wanted:g}"
        specanalyzer.reset_input_buffer()
        specanalyzer.write((cmd_text + "\r\n").encode('ascii'))
        _read_until_prompt(after=cmd_text)
        actual = _query_sweep_time()
        if abs(actual - wanted) > 0.05 * wanted + 0.002:
            print(f"TinySA sweep time: asked for {wanted:g} s but the instrument uses {actual:g} s")
        else:
            pass

def local():
    global specanalyzer
    if specanalyzer and specanalyzer.is_open:
        specanalyzer.write(b"resume\r\n")
        _read_until_prompt()

def write(command):
    global specanalyzer
    if specanalyzer and specanalyzer.is_open:
        specanalyzer.write(f"{command}\r\n".encode('ascii'))
        _read_until_prompt()

def _identify_model(info_text):
    """Ask the device which model it is and set the frequency/point limits.
    A tinySA Ultra reports a version like 'tinySA4_v1.4-...', a Basic 'tinySA_v1.3-...'."""
    global min_frequency, max_frequency, min_no_of_points, max_no_of_points, model_name
    specanalyzer.reset_input_buffer()
    specanalyzer.write(b"version\r\n")
    version = _read_until_prompt(after="version")
    lines = [l.strip() for l in version.replace('\r', '').split('\n')]
    version_line = next((l for l in lines if l and l != "version" and not l.startswith("ch>")), "")
    text = (version + info_text).lower()
    if "tinysa4" in text or "ultra" in text:
        model_name = "tinySA Ultra"
        min_frequency, max_frequency = 100E3, 6E9
        min_no_of_points, max_no_of_points = 51, 450
    elif "tinysa" in text:
        model_name = "tinySA Basic"
        min_frequency, max_frequency = 100E3, 960E6
        min_no_of_points, max_no_of_points = 51, 290
    else:
        model_name = "unknown (tinySA Ultra limits assumed)"
        min_frequency, max_frequency = 100E3, 6E9
        min_no_of_points, max_no_of_points = 51, 450
    print(f"TinySA model: {model_name}, version: {version_line!r}, "
          f"frequency {min_frequency/1e6:.1f}..{max_frequency/1e6:.0f} MHz, "
          f"points {min_no_of_points}..{max_no_of_points}")

def init(rm, address):
    """Initialize connection to TinySA via Serial port."""
    global specanalyzer
    if not address:
        return 0

    port_name = _extract_com_port(address)

    # Already connected to this port and still alive: keep the connection.
    # Closing and immediately reopening a COM port often fails on Windows
    # ("Access is denied"), which left the driver without a connection.
    if specanalyzer and specanalyzer.is_open and specanalyzer.port == port_name:
        try:
            specanalyzer.in_waiting  # raises if the device has disappeared
            return 1
        except Exception:
            pass

    # Close any previously open connection before opening a new one,
    # otherwise the OS keeps the old handle locked on the port.
    if specanalyzer and specanalyzer.is_open:
        try:
            specanalyzer.close()
        except Exception as e:
            print(f"TinySA close error: {e}")
        specanalyzer = None

    try:
        # Open serial port directly via PySerial
        specanalyzer = serial.Serial(port_name, baudrate=115200, timeout=1)
        
        # Pause internal sweeps so CLI responds immediately
        specanalyzer.write(b"pause\r\n")
        time.sleep(0.1)
        _read_until_prompt()
        
        # Identification check
        specanalyzer.write(b"info\r\n")
        info = _read_until_prompt()
        _identify_model(info)

        # Cache the device's current sweep time for use in measure_spectrum()
        _query_sweep_time()

        return 1
    except Exception as e:
        print(f"TinySA connection failed on {port_name}: {e}")
        specanalyzer = None
        return 0