# Changelog

All notable changes to **Raman-SERS-Toolkit** will be documented here.

### Added
- Public release: demo assets, sample data,screenshots of example outputs. 

## [0.1.0] - 2026-01-02

### Added
- CSV spectrum loading (single file + batch folder mode)
- Best-effort metadata extraction from filenames + editable metadata table
- Sidecar `metadata.csv` for reproducible metadata corrections
- Preprocessing pipeline:
  - baseline correction (airPLS + alternatives)
  - Savitzky–Golay smoothing
  - normalization including power×time normalization `Intensity/(mW·s)`
- QC metrics: noise estimation + SNR
- Export to publication-ready Excel with Excel-native charts
- Windows packaging support via PyInstaller

## [0.2.0] - 2026-09-08

### Added
- PySide6 + PyQtGraph desktop UI
- Spectra custom vendor import (Lightfield program)
- Electrochemistry data from custom vendor import (Aftermath program)
- ProcessingRecipe model which store recommended setting for later use. 
- Shared single/batch processing pipeline
- Despiking feature
- Excel export for custome vendor spectra and electrochemistry data. 
- stacked and reference-subtracted plotting feature for batch processing. 
- Interactive feature for data analysis. 

### Changed
- Replaced Tkinter application with PySide6/PyQtGraph UI
- Reorganized scientific functionality into ecsers_analyzer package
- Unified single and batch processing

