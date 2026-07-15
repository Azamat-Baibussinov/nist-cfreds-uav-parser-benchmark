# Data Files

Raw JSON outputs from automated benchmark experiments on the NIST CFReDS corpus.

| File | Description | Experiment |
|---|---|---|
| `_baseline_report_fixed.json` | Batch-1: 50 DJI files x 4 tools (DatCon, DROP, DRDP, Fodogu). Per-file: rows, GPS, bbox, errors | 200 runs |
| `_baseline2_report.json` | Batch-2: 35 ArduPilot+Yuneec files x 2 tools (pymavlink, GRYPHON) | 70 runs |
| `cross_matrix_full.json` | Cross-ecosystem matrix: 6 tools x 6 formats, one representative file per format | 36 runs |
| `nist_full_map.json` | NIST CFReDS corpus map: dataset IDs, file paths, sizes, Google Drive IDs | corpus metadata |
| `nist_logs_map.json` | NIST flight log download targets | corpus metadata |

## Reproducing the data

1. Download the NIST CFReDS drone datasets from https://cfreds.nist.gov/
2. Run `scripts/baseline_batch.py` for Batch-1 (DJI)
3. Run `scripts/baseline_batch2_ardupilot.py` for Batch-2 (ArduPilot + Yuneec)
