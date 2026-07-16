# NIST CFReDS UAV Parser Benchmark

Replication package for the paper:

**"No Single Tool Fits All: A Cross-Ecosystem Benchmark of Open-Source UAV
Flight Log Parsers on the NIST CFReDS Corpus"**

Submitted to: Forensic Science International: Digital Investigation (Elsevier)

## Structure

| Directory | Contents |
|---|---|
| `data/` | Raw JSON metrics from 235 automated tool runs (NIST CFReDS corpus) |
| `scripts/` | Batch experiment scripts for full reproducibility |
| `figures/` | Publication-ready figures (PDF) |

## Dataset

All experiments use the publicly available NIST CFReDS drone forensics corpus:
https://cfreds.nist.gov/

## Tools Tested

| Tool | Version | Target Format |
|---|---|---|
| DatCon | 3.5.0 | DJI V1 |
| DROP (Clark et al., 2017) | latest | DJI V1 |
| DRDP (Zhao et al., 2024) | latest | DJI V3 |
| Fodogu | latest | DJI V1 |
| pymavlink | 2.4.49 | ArduPilot |
| GRYPHON (Mantas & Patsakis, 2019) | latest | ArduPilot |

## Key Findings

- No single tool parses more than 2 of 7 UAV log formats
- DatCon and DROP extract complementary GPS data (divergence up to 18.3x)
- Clark et al. (2017) DROP superiority claim does not reproduce on 22 files
- DRDP fails on all 22 V1 files (targets V3 only)
- Dual-tool processing is mandatory for forensically sound analysis

## Reproducibility

1. Download NIST CFReDS drone datasets from https://cfreds.nist.gov/
2. Run `scripts/baseline_batch.py` for DJI experiments (Batch-1)
3. Run `scripts/baseline_batch2_ardupilot.py` for ArduPilot+Yuneec (Batch-2)
4. Compare outputs with JSON files in `data/`

## License

MIT License. See [LICENSE](LICENSE).

## Citation

If you use this data or code, please cite the paper (citation will be updated after publication).
