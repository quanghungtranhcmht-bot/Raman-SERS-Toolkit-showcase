# Changelog

All notable changes to **Raman-SERS-Toolkit** will be documented here.

The project follows semantic versioning: MAJOR.MINOR.PATCH.

## [Unreleased]
### Added
- Public showcase repo: demo assets, sample data, example outputs
### Changed
### Fixed

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

