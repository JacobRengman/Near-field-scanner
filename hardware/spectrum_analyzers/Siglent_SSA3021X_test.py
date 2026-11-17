# Test of the Siglent SSA3021X driver. Run on a PC with the instrument connected (USB or LAN):
#   python Siglent_SSA3021X_test.py                       (lists VISA resources and asks which to use)
#   python Siglent_SSA3021X_test.py TCPIP0::192.168.1.12::INSTR
# Results are printed and saved to Siglent_SSA3021X_test_log.txt - please send that file back.
import sys, os, time, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyvisa
import Siglent_SSA3021X as sa

log = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Siglent_SSA3021X_test_log.txt"), "w")
def out(*a):
    s = " ".join(str(x) for x in a)
    print(s); log.write(s + "\n"); log.flush()

def check(name, ok, info=""):
    out(("PASS  " if ok else "FAIL  ") + name + ("  " + str(info) if info != "" else ""))

def q(cmd): # raw query helper, never raises
    try:
        return sa.specanalyzer.query(cmd).strip()
    except Exception as e:
        return "ERROR: " + str(e)

def errs(step): # Read and clear the whole error queue, so we can see which step caused an error
    found = []
    for _ in range(20):
        e = q(":SYSTem:ERRor?")
        if e.startswith("0,") or e.startswith("ERROR"):
            if e.startswith("ERROR"): found.append(e)
            break
        found.append(e)
    out("  errors after '" + step + "':", found if found else "none")

rm = pyvisa.ResourceManager()
if len(sys.argv) > 1:
    address = sys.argv[1]
else:
    res = rm.list_resources()
    out("VISA resources:", res)
    address = input("Address to use: ").strip() if len(res) != 1 else res[0]
out("Using", address)

try:
    check("init", sa.init(rm, address) == 1)
    errs("init")
    out("IDN:", q("*IDN?"))
    out("Instrument state BEFORE test (left from earlier use): start", q(":FREQuency:STARt?"), "stop", q(":FREQuency:STOP?"))
    out("Min/max start frequency:", q(":FREQuency:STARt? MIN"), q(":FREQuency:STARt? MAX"), " stop max:", q(":FREQuency:STOP? MAX"))
    errs("limit queries")
    out("Assumed driver limits:", sa.min_frequency, sa.max_frequency)
    out("Points query (may be unsupported):", q(":SWEep:POINts?"))
    errs("points query")

    freqs = sa.set_span(100e6, 200e6); errs("set_span")
    sa.set_rbw(100e3, 0); errs("set_rbw")
    sa.set_sweep_time(0.1); errs("set_sweep_time")
    sa.set_peak_detector(); errs("set_peak_detector")
    out("RBW readback:", q(":BWIDth?"), " sweep time readback:", q(":SWEep:TIME?"), " detector:", q(":DETector:TRACe1?"))
    t = time.time(); data = sa.measure_spectrum(1); dt = time.time() - t
    check("single sweep returns data", len(data) > 1, "%d points in %.2f s" % (len(data), dt))
    check("point count equals driver assumption (751)", len(data) == sa.get_points(), len(data))
    errs("single sweep")
    out("Min/max of trace [dBm?]:", min(data), max(data), " first 5:", data[:5])
    check("trace values plausible dBm (-150..+30)", -150 < min(data) and max(data) < 30)
    out("Start/stop readback:", q(":FREQuency:STARt?"), q(":FREQuency:STOP?"))

    sa.set_sample_detector()
    out("Detector readback:", q(":DETector:TRACe1?"))
    errs("set_sample_detector")
    sa.set_average(3)
    t = time.time(); data = sa.measure_spectrum(1); dt = time.time() - t
    check("averaged measurement (3)", len(data) > 1, "%d points in %.2f s" % (len(data), dt))
    errs("average")
    sa.set_average(0)
    t = time.time(); data = sa.measure_spectrum(3); dt = time.time() - t
    check("max hold measurement (3 sweeps)", len(data) > 1, "%d points in %.2f s" % (len(data), dt))

    errs("max hold")
    sa.set_rbw(0, 1); sa.set_sweep_time(0.5)
    t = time.time(); data = sa.measure_spectrum(1); dt = time.time() - t
    check("auto RBW, 0.5 s sweep", len(data) > 1, "%d points in %.2f s" % (len(data), dt))

    errs("auto RBW")
    sa.local(); errs("local")
    time.sleep(1)
    out("Continuous sweep after local():", q(":INITiate:CONTinuous?"), "(1 = back in continuous mode; please check the screen sweeps)")
    errs("end")
    # Optional: can the number of points be changed? (not documented in the programming guide)
    out("Trying :SWEep:POINts 1001 (an error here is fine, it just means it is not supported)")
    sa.write(":SWEep:POINts 1001"); time.sleep(0.5)
    out("  points readback:", q(":SWEep:POINts?")); errs("set points")
    sa.write(":SWEep:POINts 751"); errs("restore points")
except Exception:
    out("EXCEPTION:\n" + traceback.format_exc())
out("Done. Please send Siglent_SSA3021X_test_log.txt back.")
log.close()
