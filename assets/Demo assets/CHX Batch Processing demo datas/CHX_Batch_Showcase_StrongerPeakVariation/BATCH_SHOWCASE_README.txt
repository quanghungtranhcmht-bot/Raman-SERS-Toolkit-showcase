EC-SERS Analyzer — Batch Showcase with Stronger Peak-Intensity Variation
========================================================================

PURPOSE
-------
This dataset is a revised batch-processing showcase derived from the user's real CHX
experimental SPE spectrum. It is designed to make Overlay mode more visually obvious.

IMPORTANT
---------
These files are controlled synthetic demonstration variants. They are not six
independent experimental measurements and should be described as showcase/test data.

WHY THIS VERSION EXISTS
-----------------------
The previous batch showcase already demonstrated shared batch processing, but the
spectra were still very similar in normalized overlay view. This revised version
introduces clearer differences in MULTIPLE CHX peak intensities while keeping the
peak positions aligned.

The strongest intentional differences are around:
- ~801 cm^-1
- ~1028 cm^-1
- ~1158 cm^-1
- ~1268 cm^-1
- ~1445 cm^-1

RECOMMENDED EC-SERS ANALYZER SETTINGS
-------------------------------------
Baseline: airPLS
airPLS lambda: 1e5
airPLS max iterations: 80

Remove cosmic-ray spikes: OFF
Apply Savitzky-Golay smoothing: OFF
Normalization: max

WHY MAX NORMALIZATION
---------------------
For Overlay mode, max normalization is recommended because it removes trivial total-
intensity scaling and makes relative peak-height differences easier to see.

HOW TO SHOWCASE OVERLAY
-----------------------
1. Open EC-SERS Analyzer.
2. Go to Batch.
3. Select this folder.
4. Ensure all six spectra are selected.
5. In Processing, apply the recommended settings above.
6. In Batch, choose Plot mode = overlay.
7. Run batch processing and plotting.
8. In Plot, inspect approximately 400–1700 cm^-1.

What to point out:
- one shared ProcessingRecipe was applied to the entire batch
- peak positions remain aligned across the series
- multiple peaks change in relative intensity, especially near 801, 1028, 1158,
  1268, and 1445 cm^-1
- overlay is now visually more informative because the spectra are not merely
  scaled copies

HOW TO SHOWCASE STACKED
-----------------------
Use the same files and the same processing recipe, then switch Plot mode to stacked.

What to point out:
- stacked mode makes each spectrum easier to inspect individually
- the same relative peak-intensity changes are easier to trace across the series
- overlay and stacked modes answer different visual-comparison needs

SUGGESTED SHOWCASE CAPTION
--------------------------
"Controlled batch-processing demonstration derived from an experimental CHX Raman
spectrum. Six synthetic variants with stronger multi-peak intensity differences are
processed using one shared recipe and visualized in Overlay and Stacked modes to
demonstrate reproducible multi-spectrum analysis."
