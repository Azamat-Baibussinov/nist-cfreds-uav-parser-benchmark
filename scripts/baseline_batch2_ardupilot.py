#!/usr/bin/env python3
"""Batch-2: pymavlink + GRYPHON на ArduPilot + Yuneec (зелёный корпус NIST)."""
import subprocess, os, sys, json, time, glob

PY = os.path.expanduser("~/miniforge3/envs/uav/bin/python")
BASE = os.path.expanduser("~/uav/forensic_tools")
NE = "/mnt/datasets/nist_extracted"
OUT = os.path.expanduser("~/uav/forensic_tools/test_results/baseline2")
os.makedirs(OUT, exist_ok=True)

# --- файлы ---
files = []
# ArduPilot: DF056 SkyViper DATAFLASH .BIN
for f in sorted(glob.glob(f"{NE}/DF056_SkyViper*/telemetry_and_logs/img_DF056.E01/DATAFLASH__*.BIN")):
    files.append((f, "ArduPilot_BIN", "DF056_SkyViper"))
# ArduPilot: DF057 Mission Planner .log
for f in sorted(glob.glob(f"{NE}/DF057_ArduPilot_DIY/telemetry_and_logs/2018_June/Mission_Planner_Logs/*.log")):
    files.append((f, "ArduPilot_LOG", "DF057_DIY"))
for f in sorted(glob.glob(f"{NE}/DF057_ArduPilot_DIY/telemetry_and_logs/2018_June/Mission_Planner_Logs/*.bin.log")):
    if (f, "ArduPilot_LOG", "DF057_DIY") not in files:
        files.append((f, "ArduPilot_LOG", "DF057_DIY"))
# Yuneec: DF014 Typhoon H Sensor .bin
for f in sorted(glob.glob(f"{NE}/DF014_Yuneec_Typhoon_H/extracted_data/FlightLog/Sensor/Sensor_*.bin")):
    files.append((f, "Yuneec_BIN", "DF014_TyphoonH"))

print(f"Файлов: {len(files)}")
print(f"Форматы: { {fmt: sum(1 for _,f2,_ in files if f2==fmt) for fmt in set(f2 for _,f2,_ in files)} }")

def pymav_extract(fpath, timeout=60):
    """Извлекает GPS через pymavlink."""
    code = '''
import sys, time, json
from pymavlink import mavutil
f = sys.argv[1]
t0 = time.time()
try:
    mlog = mavutil.mavlink_connection(f)
    total = 0; gps = 0; lat = []; lon = []
    while True:
        m = mlog.recv_match(blocking=False)
        if m is None: break
        total += 1
        t = m.get_type()
        if t in ('GPS', 'GPS2', 'GLOBAL_POSITION_INT'):
            gps += 1
            try:
                la = getattr(m, 'Lat', None) or getattr(m, 'lat', None)
                lo = getattr(m, 'Lng', None) or getattr(m, 'lon', None)
                if la and lo:
                    la = float(la); lo = float(lo)
                    if la > 1000: la /= 1e7  # GLOBAL_POSITION_INT uses 1e7
                    if lo > 1000: lo /= 1e7
                    if abs(la) > 0.01 and abs(lo) > 0.01 and -90 <= la <= 90:
                        lat.append(la); lon.append(lo)
            except: pass
    res = {"total": total, "gps": gps, "gps_valid": len(lat), "elapsed": round(time.time()-t0, 2)}
    if lat:
        res["lat_min"] = round(min(lat),5); res["lat_max"] = round(max(lat),5)
        res["lon_min"] = round(min(lon),5); res["lon_max"] = round(max(lon),5)
    print(json.dumps(res))
except Exception as e:
    print(json.dumps({"error": str(e), "total": 0, "gps": 0, "gps_valid": 0}))
'''
    try:
        r = subprocess.run([PY, "-c", code, fpath], capture_output=True, text=True, timeout=timeout)
        return json.loads(r.stdout.strip()) if r.stdout.strip() else {"error": r.stderr[:200], "total": 0, "gps": 0, "gps_valid": 0}
    except Exception as e:
        return {"error": str(e)[:200], "total": 0, "gps": 0, "gps_valid": 0}

def gryphon_extract(fpath, timeout=60):
    """Запускает GRYPHON, парсит stdout."""
    try:
        r = subprocess.run([PY, f"{BASE}/gryphon_dft/gryphon_cli.py", fpath],
                           capture_output=True, text=True, timeout=timeout)
        out = r.stdout + r.stderr
        sections = [s.strip() for s in out.split(">") if s.strip()]
        gps_loss = "No GPS signal loss" in out
        alt_anom = "No Alt Anomaly" in out
        crc_ok = "CRC" in out
        return {"parsed": True, "sections": len(sections), "gps_signal_ok": gps_loss,
                "alt_anomaly_free": alt_anom, "crc_checked": crc_ok}
    except subprocess.TimeoutExpired:
        return {"parsed": False, "error": "TIMEOUT"}
    except Exception as e:
        return {"parsed": False, "error": str(e)[:200]}

# --- main ---
results = []
total = len(files) * 2  # pymavlink + GRYPHON per file
done = 0; t_start = time.time()

for fpath, fmt, dataset in files:
    bn = os.path.basename(fpath)
    sz_mb = os.path.getsize(fpath) / 1048576

    # pymavlink
    done += 1
    pct = done / total * 100
    el = time.time() - t_start
    eta = (el / done * (total - done)) if done > 0 else 0
    print(f"\r[{done}/{total}] {pct:5.1f}% | ETA {int(eta)}с | pymavlink | {bn[:40]:40s} ({sz_mb:.1f}МБ)   ", end="", flush=True)
    pm = pymav_extract(fpath)

    # GRYPHON
    done += 1
    pct = done / total * 100
    el = time.time() - t_start
    eta = (el / done * (total - done)) if done > 0 else 0
    print(f"\r[{done}/{total}] {pct:5.1f}% | ETA {int(eta)}с | GRYPHON   | {bn[:40]:40s} ({sz_mb:.1f}МБ)   ", end="", flush=True)
    gr = gryphon_extract(fpath)

    results.append({
        "file": bn, "format": fmt, "dataset": dataset, "size_mb": round(sz_mb, 1),
        "pymavlink_total_msgs": pm.get("total", 0),
        "pymavlink_gps": pm.get("gps", 0),
        "pymavlink_gps_valid": pm.get("gps_valid", 0),
        "pymavlink_lat_min": pm.get("lat_min"), "pymavlink_lat_max": pm.get("lat_max"),
        "pymavlink_lon_min": pm.get("lon_min"), "pymavlink_lon_max": pm.get("lon_max"),
        "pymavlink_elapsed": pm.get("elapsed", 0),
        "pymavlink_error": pm.get("error", ""),
        "gryphon_parsed": gr.get("parsed", False),
        "gryphon_gps_ok": gr.get("gps_signal_ok", None),
        "gryphon_alt_ok": gr.get("alt_anomaly_free", None),
        "gryphon_error": gr.get("error", ""),
    })

elapsed_total = time.time() - t_start
print(f"\n\nГотово за {int(elapsed_total)}с. Записываю отчёт...")

# JSON
rp = f"{OUT}/_baseline2_report.json"
with open(rp, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"JSON: {rp}")

# Summary
print(f"\n{'='*110}")
print(f"{'ФАЙЛ':<35} {'FMT':<15} {'msgs':>7} {'GPS':>5} {'valid':>5} {'GRY':>4} {'GPS_OK':>6} {'ALT_OK':>6}")
print(f"{'-'*110}")
for r in results:
    gry = "OK" if r["gryphon_parsed"] else "FAIL"
    gps_ok = "yes" if r.get("gryphon_gps_ok") else ("no" if r.get("gryphon_gps_ok") == False else "?")
    alt_ok = "yes" if r.get("gryphon_alt_ok") else ("no" if r.get("gryphon_alt_ok") == False else "?")
    print(f"{r['file'][:34]:<35} {r['format']:<15} {r['pymavlink_total_msgs']:>7} {r['pymavlink_gps']:>5} {r['pymavlink_gps_valid']:>5} {gry:>4} {gps_ok:>6} {alt_ok:>6}")
print(f"{'='*110}")

# Cross-format summary
print(f"\nПо форматам:")
for fmt in sorted(set(r['format'] for r in results)):
    fr = [r for r in results if r['format'] == fmt]
    n = len(fr)
    total_gps = sum(r['pymavlink_gps_valid'] for r in fr)
    gryphon_ok = sum(1 for r in fr if r['gryphon_parsed'])
    print(f"  {fmt}: {n} файлов, pymavlink GPS valid: {total_gps}, GRYPHON parsed: {gryphon_ok}/{n}")
