
# EC-SERS Analyzer

**Current release: v2.1**

EC-SERS Analyzer is an open-source Python desktop application for reproducible Raman, SERS, and electrochemical SERS (EC-SERS) data analysis.

The application provides transparent, recipe-driven spectral preprocessing setting, spectra custom vendor from LightField SPE files import, electrochemistry data from custom vendor Aftermath program file import, interactive visualization, Excel export, processing recommendations and local reference-library search.

The project is designed to help remove friction between chemical wet lab work and data processing aspect. EC-SERS Analyzer is a desktop spectral data analysis tool for Raman spectroscopy and electrochemistry data.


## Active application

The active desktop UI is:

qt_ecsers_ui_dynamic.py


The active UI uses:

PySide6
PyQtGraph

Older Tkinter UI files are archived/reference only and are not the active development target.

## Main features

### Custome spectral vendor file import

- Load Raman spectra from `.csv` files.
- Load LightField / FERGIE `.spe` files directly.
- Automatically parse metadata from filenames when possible.
- Backend loaders support metadata overrides.
- Preserve raw and processed data separately.

### Electrochemistry file import

- Load AfterMath `.paax` files.
- Select study/session and trace.
- Plot electrochemical traces such as current, potential, or charge versus time.
- Export selected PAAX traces to CSV or Excel.

![Electrochemistry Data Visualization](<assets/Screenshots/Electrochemistry Data Visualization Feature.png>)

### Single-spectrum processing

The single spectral data is processed through recipe-driven data-processing technique:

raw spectrum
→ optional despiking / cosmic-ray removal

![Despiking feature](<assets/Screenshots/Despike Feature.png>)

→ baseline correction

![Baseline Correction](<assets/Screenshots/Baseline Correction Feature.png>)

→ Savitzky-Golay smoothing

![Smoothing feature](<assets/Screenshots/Smoothing Feature.png>)


→ normalization
→ processed spectrum

### Batch processing

Support batch of spectras processing with overlay style and stacked style for charting batch spectras. 

![Batch Processing Overlay](<assets/Screenshots/Batch Processing Overlay.png>) 


![Batch Processing Stacked](<assets/Screenshots/Batch Processing Stacked.png>)


Supported processing methods:

- Despiking by median-filter residual threshold.
- Baseline correction:
  - airPLS
  - ALS
  - polynomial baseline
  - none
- Smoothing:
  - Savitzky-Golay smoothing by point window
  - optional cm⁻¹-based smoothing width
  - editable polynomial order
- Normalization:
  - none
  - max
  - area
  - vector / L2
  - power-time normalization using laser power and acquisition time

The processed spectrum stores a processing recipe so the processing option can be recommended later.

### Batch Raman workflow

- Select a folder of `.csv` and/or `.spe` spectra.
- Process selected files using the same recipe as single mode.
- Plot processed spectra as:
  - overlay
  - stacked
  - reference-subtracted stacked
- Choose a reference spectrum for background/reference subtraction.
- Choose which spectrum appears at the bottom of a stacked plot.
- Skip the reference spectrum in corrected plots when appropriate.

### Plotting workspace

The UI workspace supports:

- raw vs processed display
- estimated baseline display
- overlay and stacked plotting
- clean figure mode
- adjustable x-axis range
- trace visibility and label editing
- interactive cursor readout
- peak markers
- ROI / region markers
- peak intensity table
- plot copy and PNG export

Typical report x-range:

400–1700 cm⁻¹


### Excel export

The app can export ready-made Excel workbooks with native Excel charts.

Single Raman export includes:

- `spectrum` sheet
- `metadata` sheet
- `preprocess` sheet
- `plot` sheet with an Excel-native XY scatter chart

Batch Raman export includes:

- `summary` sheet
- overlay or stacked data sheet
- Excel-native overlay/stacked chart
- one sheet per processed spectrum with data and chart

Chart formatting is designed for clean and ready figures:

- Raman x-axis label: `Raman Shift (cm⁻¹)`
- x-axis number format: 0 decimals, no thousands separator
- outside tick marks
- no chart gridlines
- optional y-axis label override
- optional chart title control

PAAX Excel export includes:

- `ec_trace` sheet
- `metadata` sheet
- `plot` sheet

PAAX chart axis formatting:

- x-axis: number, 0 decimals, no thousands separator
- y-axis: number, 2 decimals, no thousands separator

---

## Installation

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```cmd
.\.venv\Scripts\activate.bat
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Expected core dependencies:

numpy
scipy
matplotlib
pandas
xlsxwriter
openpyxl
PySide6
pyqtgraph


---

## Run the app

From the project root:
run
```bash
python qt_ecsers_ui_dynamic.py
```


---

## Basic workflow

### Single spectrum

1. Open the app.
2. Go to the **Single** tab.
3. Click **Open CSV/SPE**.
4. Adjust processing settings in the **Processing** tab.
5. Click **Run Processing**.
6. Inspect raw, processed, and optional baseline traces.
7. Use **Clean figure mode** for a cleaner presentation view.
8. Export the processed spectrum from the **Export** tab.

### Batch spectra

1. Go to the **Batch** tab.
2. Click **Select Batch Folder**.
3. Select spectra to include.
4. Choose plot mode:
   - overlay
   - stacked
   - reference-subtracted stacked
5. Adjust processing settings in the **Processing** tab.
6. Click **Run Batch Processing + Plot**.
7. Inspect the stacked or overlay plot.
8. Export the batch workbook from the **Export** tab.

### PAAX electrochemistry traces

1. Go to the **EC/PAAX** tab.
2. Click **Open PAAX…**.
3. Select the study/session and trace.
4. Click **Plot selected EC trace**.
5. Export selected trace as CSV or Excel.

---


## Processing recommendations

For Raman SERS spectra, a good starting point is:

Despike: on
Despike window: 7
Despike threshold: 5.5–7.0

Baseline: airPLS
airPLS lambda: 1e5
airPLS max_iter: 80–100

Smoothing: Savitzky-Golay
Smoothing width: 16–22 cm⁻¹
Polyorder: 2

Normalization:
- none for checking real intensity
- power_time for quantitative comparison
- max for visual overlay comparison

Avoid over-smoothing. Strong smoothing can make spectra look cleaner, but it can also flatten weak SERS peaks.

For peak preservation, v2.1 now uses safer preprocessing defaults: despiking and Savitzky-Golay smoothing start **off**. When despiking is enabled, only isolated positive spike candidates up to the configured maximum width are removed; wider multi-point features are preserved as possible Raman/SERS bands. Accepted spike points are repaired by interpolation rather than local-median flattening. The cm⁻¹-to-point smoothing conversion no longer forces an 11-point minimum.

Recommended processing order:

despike → baseline correction → moderate smoothing → normalization

---

## Runtime data location

By default, local runtime data is stored under the project-level `data/` folder instead of inside the Python package:

```text
data/user_history/processing_runs.jsonl
data/spectral_library/
```

Optional environment-variable overrides are available for advanced/local deployment use:

```text
ECSERS_DATA_DIR
ECSERS_HISTORY_PATH
ECSERS_LIBRARY_DIR
```

Runtime logs and local library data are user data, not source code. Avoid committing generated JSONL logs or private reference-library spectra.

---

## Testing

Run a syntax check for the full repo:

```bash
python -m compileall -q .
```

Run the discoverable test suite:

```bash
python -m unittest discover -s tests -v
```

The default tests cover the shared processing pipeline, Processing Advisor, spectral library search, SPE import, and PAAX import using the files in `examples/`.

Optional real CSV smoke test:

```bash
# Windows PowerShell
$env:EC_SERS_REAL_CSV="C:\path\to\real_spectrum.csv"
python -m unittest tests.test_real_csv -v
```

---

## Development notes

The current cleanup introduced:

- `ProcessingRecipe` in `ecsers_analyzer/domain/recipe.py`
- `Spectrum` in `ecsers_analyzer/domain/spectrum.py`
- shared processing through `ecsers_analyzer/processing/pipeline.py`
- file import modules under `ecsers_analyzer/io/`
- backend workflow services under `ecsers_analyzer/services/`
- single and batch processing routed through the same recipe-driven path
- project-root-based defaults for local history and spectral-library data
- discoverable unit tests for core non-GUI behavior
- archived duplicate UI prototypes under `archive/old_ui/`

This makes future features easier to add without duplicating logic between single and batch modes.

---

