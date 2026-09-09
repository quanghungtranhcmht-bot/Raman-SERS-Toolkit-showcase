# EC-SERS Analyzer Architecture

Current checkpoint: EC-SERS Analyzer v2.1

## Active launcher

qt_ecsers_ui_dynamic.py


This file contains the main `SpectralViewer` window and coordinates high-level UI workflows. It is still the active UI entry point.

`SpectralViewer` remains the top-level coordinator. The UI is not fully decoupled yet: `ecsers_analyzer/frontend/` contains extracted tab-building helpers and Qt/PyQtGraph controllers, while the large active UI file still owns high-level workflow orchestration and signal-compatible delegate methods. Scientific computation, import/export logic, reusable helpers, and persistent data handling should live in package modules under `ecsers_analyzer/`.

## Top-level package layout

ecsers_analyzer/
    domain/
    io/
    processing/
    plotting/
    ec/
    export/
    library/
    persistence/
    services/
    frontend/

## Layer responsibilities

### `ecsers_analyzer/domain/`

Core scientific/domain objects.

Examples:

Spectrum
ProcessingRecipe

This layer should not import Qt or PyQtGraph.

### `ecsers_analyzer/io/`

File loading and metadata parsing.

Responsibilities:

CSV Raman import
SPE / FERGIE Raman import
PAAX / AfterMath import
filename metadata parsing

This layer should not import Qt or PyQtGraph.

### `ecsers_analyzer/processing/`

Processing logic and advisor helpers.

Responsibilities:

despike / cosmic-ray removal
baseline correction
smoothing
normalization
processing pipeline
Processing Advisor v1
processing-form parsing
analysis features
advisor workflow formatting

This layer should not import Qt or PyQtGraph.

### `ecsers_analyzer/plotting/`

Pure plotting-data and analysis helpers.

Responsibilities:

trace dictionaries
trace x/y extraction
stack offset calculations
axis label helpers
peak-intensity calculations
ROI validation helpers
robust y-limit calculation

This layer should not draw with PyQtGraph directly. It should stay testable without the UI.

### `ecsers_analyzer/ec/`

Electrochemistry / PAAX trace planning helpers.

Responsibilities:

study list building
trace dropdown planning
selected trace planning
PAAX plot trace dictionaries
PAAX metadata rows
PAAX status messages

This layer should not import Qt or PyQtGraph.

### `ecsers_analyzer/export/`

File export logic.

Responsibilities:

Raman Excel export
PAAX CSV export
PAAX Excel export
export planning
filename helpers
chart title helpers
sheet-name helpers


This layer should not import Qt or PyQtGraph.

### `ecsers_analyzer/library/`

Local SERS spectral library and search logic.

Responsibilities:

reference-library persistence
reference spectrum addition
unknown-vs-reference search
candidate-match scoring
library workflow formatting
search result table formatting


Library search should report candidate matches, best reference matches, or similar spectra. It should not report absolute chemical proof unless experimentally validated.

### `ecsers_analyzer/persistence/`

Local persistent app data.

Responsibilities:

application paths
local user-history JSONL logging


Default runtime data lives under the project-level `data/` directory, not inside `ecsers_analyzer/persistence/`:

data/user_history/processing_runs.jsonl
data/spectral_library/

These defaults can be overridden with `ECSERS_DATA_DIR`, `ECSERS_HISTORY_PATH`, or `ECSERS_LIBRARY_DIR` for local deployments. Runtime logs and private local library spectra should not be committed or included in clean source patches.

### `ecsers_analyzer/services/`

Backend workflow services used by the UI.

Current services:

ImportService
ProcessingService
PaaxService
ExportService
LibraryService
HistoryService

Services should coordinate backend workflows without importing Qt or PyQtGraph.

### `ecsers_analyzer/frontend/qt/tabs/`

Qt widget construction for each left-side tab.

Responsibilities:

```text
Single tab
EC/PAAX tab
Processing tab
Batch tab
Plot tab
Export tab
Library tab
```

Tab modules may import PySide6.

They should build widgets and connect signals, but they should not contain scientific processing logic.

### `ecsers_analyzer/frontend/qt/controllers/`

Qt/PyQtGraph frontend controllers.

Current controllers:

PlotController
AnalysisController

Responsibilities:


plot redraw coordination
trace table coordination
peak marker table coordination
ROI table coordination
copy/save plot image
copy/export peak intensity table

Controllers may import PySide6 and PyQtGraph.

## Dependency rules

Backend modules must not import:

PySide6
pyqtgraph

Allowed Qt/PyQtGraph locations:

qt_ecsers_ui_dynamic.py
ecsers_analyzer/frontend/

Forbidden Qt/PyQtGraph locations:

ecsers_analyzer/domain/
ecsers_analyzer/io/
ecsers_analyzer/processing/
ecsers_analyzer/plotting/
ecsers_analyzer/ec/
ecsers_analyzer/export/
ecsers_analyzer/library/
ecsers_analyzer/persistence/
ecsers_analyzer/services/

This rule protects testability and keeps scientific/backend logic independent from the desktop frontend.

## Processing design

Preferred processing order:

1. despike / cosmic-ray removal (optional; conservative isolated-positive-event detector)
2. baseline correction
3. smoothing (optional; no forced 11-point minimum)
4. normalization

Every processing run should preserve:

raw x/y
processed x/y
estimated baseline when available
baseline-corrected y when available
processing recipe
normalization method
metadata
number of removed spikes

Processing should never silently alter scientific data. Every preprocessing step must be visible, parameterized, reproducible, and stored in the output metadata/recipe.

## UI design principles

The UI should:

- Keep processing explicit
- Warn when settings changed and processing must be rerun
- Avoid hidden preprocessing
- Keep raw vs processed comparison available
- Show estimated baseline when available
- Keep PAAX electrochemistry traces separate from Raman preprocessing
- Use backend services instead of duplicating processing/import/export logic
- Keep signal-connected methods on `SpectralViewer` stable when refactoring

## Processing Advisor design

The Processing Advisor is a transparent scientific assistant, not a black-box AI system.

It should:

- Recommend a `ProcessingRecipe`
- Explain the reasons for each recommendation
- Require the user to explicitly apply settings
- Log accepted/rejected decisions locally
- Never silently change data

## Library-search design

Library search should use transparent similarity metrics such as:

cosine similarity
Pearson correlation

Results should be described as:

best reference match
candidate match
similar spectrum

not as definitive chemical identification.

Future mixture analysis should be treated cautiously. Candidate unmixing such as NNLS may be useful later, but SERS intensity may not be linearly additive due to adsorption competition. Mixture outputs should be reported as candidate spectral contributions unless experimentally validated.

## Testing expectations

Run before packaging or merging a patch:

```powershell
python -m compileall -q .
python -m unittest discover -s tests -v
```

Run the manual QA checklist when UI, plotting, processing, import/export, PAAX, or library behavior changes.
