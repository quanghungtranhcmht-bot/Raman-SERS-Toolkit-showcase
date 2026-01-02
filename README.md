# Raman-SERS-Toolkit

Python desktop application for Raman/SERS spectrum processing end-to-end:

**Load CSV → robust metadata extraction → preprocessing (baseline, smoothing, normalization incl. Intensity/(mW·s)) → QC (noise, SNR) → publication-ready Excel export (Excel-native charts).**

> 🔒 Source code is currently private (research workflow + packaging details).  
> ✅ This repo provides a full demo: screenshots, sample data, and example outputs.  
> 📩 Code access / executable available upon request.

---

## Demo

- 🎥 Demo video (60–90s): [link here]
- 🖼️ Screenshots:
  - `assets/screenshots/ui_main.png`
  - `assets/screenshots/overlay_plot.png`
  - `assets/screenshots/metadata_editor.png`
  - `assets/screenshots/excel_export.png`

---

## Key features

### Data ingestion
- Loads Raman/SERS CSV spectra (2-column wavenumber + intensity)
- Batch folder mode + multi-spectrum overlays

### Metadata handling (messy filenames)
- Best-effort filename parsing (supports inconsistent naming)
- Editable metadata table inside the app
- Sidecar `metadata.csv` to preserve corrected metadata for reproducible re-runs

### Preprocessing (reproducible + parameterized)
- Baseline correction: stable airPLS (plus ALS / polynomial options)
- Smoothing: Savitzky–Golay
- Normalization options:
  - Max / area / vector (configurable)
  - **Power × time normalization:** `Intensity / (mW·s)` for cross-run comparability

### QC metrics
- Noise estimation (robust methods)
- SNR calculation for peak-based assessment
- QC summary table across batches

### Export
- Publication-ready Excel workbook:
  - raw vs processed spectra
  - QC tables
  - Excel-native charts (easy to tweak without Python)

### Deployment
- Can be packaged as a Windows standalone `.exe` (PyInstaller)

---

## Try the demo (no code needed)

1) Download sample spectra from:
- `examples/sample_data/`

2) View example outputs:
- `examples/example_outputs/`

3) (Optional) Request the demo build:
- “Available upon request” (include what you want: `.exe` zip / walkthrough call)

---

## Input format

CSV with columns:
- `wavenumber` (cm⁻¹)
- `intensity` (a.u.)

The demo data is synthetic/anonymized and safe to share.

---

## Roadmap (near-term)

- Presets per instrument / acquisition settings
- Baseline visualization overlay (baseline + corrected view)
- More robust filename parsing rules + importable parsing templates
- CLI mode for automation (optional)

---

## Data privacy

See `docs/data-privacy.md`.

---

## License

MIT License

Copyright (c) 2026- Quang Hung Tran 

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

