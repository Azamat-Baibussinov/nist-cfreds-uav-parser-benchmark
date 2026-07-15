#!/usr/bin/env python3
"""
Систематический baseline: 4 инструмента x все файлы NIST CFReDS.
Результат: JSON-отчёт + сводная таблица.
"""
import subprocess, os, sys, json, csv, time, glob, tempfile, shutil

PY = os.path.expanduser("~/miniforge3/envs/uav/bin/python")
BASE = os.path.expanduser("~/uav/forensic_tools")
NE = "/mnt/datasets/nist_extracted"
OUT = os.path.expanduser("~/uav/forensic_tools/test_results/baseline")
os.makedirs(OUT, exist_ok=True)

# --- файлы ---
files = []
# V1
for f in sorted(glob.glob(f"{NE}/DF001_DJI_Phantom_3/flight_logs/FLY*.DAT")):
    files.append((f, "V1", "DF001_P3"))
# V3 (DF005 Phantom 4)
for f in sorted(glob.glob(f"{NE}/DF005_DJI_Phantom4/flight_logs/FLY*.DAT")):
    files.append((f, "V3", "DF005_P4"))
# V3 (DRDP sample)
files.append((os.path.expanduser("~/uav/forensic_tools/DRDP/dats/20-07-10-08-31-09_FLY256.DAT"), "V3", "DRDP_sample"))
# LOGH export
for f in sorted(glob.glob(f"{NE}/DF050_DJI_MavicAir/assistant/extracted/dji_assistant_export/*.DAT")):
    files.append((f, "LOGH", "DF050_WM230"))
for f in sorted(glob.glob(f"{NE}/DF069_DJI_Mavic2Pro/assistant/extracted/*.DAT")):
    files.append((f, "LOGH", "DF069_WM240"))
# Raw DFLY
for f in sorted(glob.glob(f"{NE}/DF080_DJI_Mavic2Enterprise/dji_flight/DFLY*.DAT")):
    files.append((f, "DFLY", "DF080_Ent"))
# TXT
for f in glob.glob(f"{NE}/DF062_DJI_Phantom_4_Pro_V2/telemetry_and_logs/dji_extracted/*/Media01/sdcard/DJI/dji.go.v4/FlightRecord/DJIFlightRecord*.txt"):
    files.append((f, "TXT", "DF062_P4PV2"))

print(f"Файлов: {len(files)}, прогонов: {len(files)*4}")
print(f"Форматы: { {fmt: sum(1 for _,f2,_ in files if f2==fmt) for fmt in ['V1','V3','LOGH','DFLY','TXT']} }")

def count_gps(csv_path):
    """Считает GPS-точки из CSV (обрабатывает англ. и кит. заголовки)."""
    try:
        with open(csv_path, newline='', encoding='utf-8', errors='replace') as f:
            r = csv.reader(f)
            h = [c.strip().lower() for c in next(r)]
            # поиск lat/lon колонок
            li = oi = None
            for i, c in enumerate(h):
                if any(k in c for k in ['latitude', 'lat', '纬度']): li = i
                if any(k in c for k in ['longitude', 'long', 'lon', '经度']): oi = i
            if li is None or oi is None:
                rows = sum(1 for _ in r)
                return {"rows": rows, "gps": 0, "note": "no GPS cols"}
            lat = []; lon = []; rows = 0
            for row in r:
                rows += 1
                try:
                    a, o = float(row[li]), float(row[oi])
                    if abs(a) > 0.01 and abs(o) > 0.01 and -90 <= a <= 90 and -180 <= o <= 180:
                        lat.append(a); lon.append(o)
                except: pass
            res = {"rows": rows, "gps": len(lat)}
            if lat:
                res["lat_min"] = round(min(lat), 5)
                res["lat_max"] = round(max(lat), 5)
                res["lon_min"] = round(min(lon), 5)
                res["lon_max"] = round(max(lon), 5)
            return res
    except Exception as e:
        return {"rows": 0, "gps": 0, "error": str(e)}

def run_tool(tool, fpath, out_csv, timeout=120):
    """Запускает инструмент, возвращает (success, elapsed, info)."""
    t0 = time.time()
    try:
        if tool == "DatCon":
            cmd = ["java", "-cp", "/tmp:build:lib/ia_math.jar", "DatDriver", fpath, out_csv]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                               cwd=f"{BASE}/DatCon/DatCon")
        elif tool == "DROP":
            cmd = [PY, "DROP.py", fpath, "-o", out_csv]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                               cwd=f"{BASE}/DROP")
        elif tool == "DRDP":
            # DRDP reads from ./dats/ — symlink file there, run, collect CSV
            dats_dir = f"{BASE}/DRDP/dats"
            bn = os.path.basename(fpath)
            link = f"{dats_dir}/{bn}"
            csv_expected = f"{dats_dir}/{bn}.csv"
            # clean old CSV
            if os.path.exists(csv_expected): os.remove(csv_expected)
            # symlink
            if os.path.exists(link) and os.path.islink(link): os.remove(link)
            elif os.path.exists(link): pass  # original file, don't touch
            else: os.symlink(fpath, link)
            cmd = [PY, "main.py", "-d"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                               cwd=f"{BASE}/DRDP")
            if os.path.exists(csv_expected):
                shutil.copy2(csv_expected, out_csv)
            # cleanup symlink
            if os.path.islink(link): os.remove(link)
        elif tool == "Fodogu":
            out_dir = out_csv + "_dir"
            os.makedirs(out_dir, exist_ok=True)
            cmd = [PY, "run_cli.py", fpath, out_dir]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                               cwd=f"{BASE}/Fodogu")
            # find output CSV
            csvs = glob.glob(f"{out_dir}/*.csv")
            if csvs:
                shutil.copy2(csvs[0], out_csv)
        else:
            return False, 0, "unknown tool"

        elapsed = time.time() - t0
        ok = os.path.exists(out_csv) and os.path.getsize(out_csv) > 10
        stderr_short = (r.stderr or "")[-200:]
        return ok, elapsed, stderr_short
    except subprocess.TimeoutExpired:
        return False, time.time() - t0, "TIMEOUT"
    except Exception as e:
        return False, time.time() - t0, str(e)[-200:]

# --- main ---
tools = ["DatCon", "DROP", "DRDP", "Fodogu"]
results = []
total = len(files) * len(tools)
done = 0
t_start = time.time()

for fpath, fmt, dataset in files:
    bn = os.path.basename(fpath)
    sz_mb = os.path.getsize(fpath) / 1048576
    for tool in tools:
        done += 1
        tag = f"{bn}_{tool}"
        out_csv = f"{OUT}/{tag}.csv"
        pct = done / total * 100
        elapsed_total = time.time() - t_start
        eta = (elapsed_total / done * (total - done)) if done > 0 else 0
        print(f"\r[{done}/{total}] {pct:5.1f}% | ETA {int(eta)}с | {tool:8s} | {bn[:35]:35s} ({sz_mb:.0f}МБ)   ", end="", flush=True)

        ok, elapsed, info = run_tool(tool, fpath, out_csv)
        gps_info = count_gps(out_csv) if ok else {"rows": 0, "gps": 0, "error": info[:100]}

        results.append({
            "file": bn, "format": fmt, "dataset": dataset, "size_mb": round(sz_mb, 1),
            "tool": tool, "success": ok, "elapsed_s": round(elapsed, 1),
            "rows": gps_info.get("rows", 0), "gps": gps_info.get("gps", 0),
            "lat_min": gps_info.get("lat_min"), "lat_max": gps_info.get("lat_max"),
            "lon_min": gps_info.get("lon_min"), "lon_max": gps_info.get("lon_max"),
            "note": gps_info.get("error", gps_info.get("note", ""))
        })

print(f"\n\nГотово за {int(time.time()-t_start)}с. Записываю отчёт...")

# JSON
report_path = f"{OUT}/_baseline_report.json"
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"JSON: {report_path}")

# Summary table
print(f"\n{'='*100}")
print(f"{'ФАЙЛ':<30} {'FMT':<5} {'ИНСТРУМ.':<9} {'СТРОК':>8} {'GPS':>8} {'ВРЕМЯ':>6} {'СТАТ'}")
print(f"{'-'*100}")
for r in results:
    stat = "OK" if r["success"] and r["gps"] > 0 else ("PARSE" if r["success"] else "FAIL")
    print(f"{r['file'][:29]:<30} {r['format']:<5} {r['tool']:<9} {r['rows']:>8} {r['gps']:>8} {r['elapsed_s']:>5.1f}с {stat}")
print(f"{'='*100}")

# Cross-matrix summary
print(f"\nКросс-матрица (GPS-точки):")
print(f"{'Формат':<6} {'N':>3} {'DatCon':>10} {'DROP':>10} {'DRDP':>10} {'Fodogu':>10}")
for fmt in ['V1','V3','LOGH','DFLY','TXT']:
    fmt_results = [r for r in results if r['format'] == fmt]
    n_files = len(set(r['file'] for r in fmt_results))
    row = f"{fmt:<6} {n_files:>3}"
    for tool in tools:
        tool_gps = [r['gps'] for r in fmt_results if r['tool'] == tool]
        total_gps = sum(tool_gps)
        ok_count = sum(1 for g in tool_gps if g > 0)
        row += f" {total_gps:>7}({ok_count})"
    print(row)
