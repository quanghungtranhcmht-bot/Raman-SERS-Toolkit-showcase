"""Vendor-format importers for EC-SERS Analyzer.

Adds direct-reading support for:
  - Princeton Instruments SPE 3.0 Raman spectra
  - Pine Research AfterMath/PAAX electrochemistry XML traces

The goal is to convert vendor files into normal Python arrays, then either:
  - return a Spectrum object for Raman-like SPE files, or
  - return TraceData objects for electrochemical PAAX traces.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import unquote
import xml.etree.ElementTree as ET
from ecsers_analyzer.io.metadata import parse_metadata_from_filename
import numpy as np

try:
    from ecsers_analyzer.domain.spectrum import Spectrum
except Exception:  # keeps this module importable during isolated tests
    Spectrum = None  # type: ignore


SPE_HEADER_BYTES = 4100

SPE_PIXEL_DTYPES: Dict[str, str] = {
    "MonochromeUnsigned16": "<u2",
    "MonochromeSigned16": "<i2",
    "MonochromeUnsigned32": "<u4",
    "MonochromeSigned32": "<i4",
    "MonochromeFloating32": "<f4",
    "MonochromeFloating64": "<f8",
}


@dataclass
class TraceData:
    """Generic x-y trace imported from a non-Raman vendor file."""

    x: np.ndarray
    y: np.ndarray
    name: str
    xlabel: str = "x"
    ylabel: str = "y"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def plot(self, *, ax=None, title: Optional[str] = None, linewidth: float = 1.5):
        """Plot the imported trace with matplotlib."""
        import matplotlib.pyplot as plt

        if ax is None:
            _, ax = plt.subplots(figsize=(9, 4.2))
        ax.plot(self.x, self.y, linewidth=linewidth)
        ax.set_xlabel(self.xlabel)
        ax.set_ylabel(self.ylabel)
        ax.set_title(title or self.full_name)
        ax.grid(False)
        return ax

    @property
    def full_name(self) -> str:
        study = self.metadata.get("study_name")
        plot = self.metadata.get("plot_name")
        parts = [p for p in (study, plot, self.name) if p]
        return " / ".join(str(p) for p in parts)


def _local_name(tag: str) -> str:
    """Return XML local tag name without namespace."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _find_first(root: ET.Element, local_name: str) -> Optional[ET.Element]:
    for el in root.iter():
        if _local_name(el.tag) == local_name:
            return el
    return None


def _iter_local(root: ET.Element, local_name: str) -> Iterable[ET.Element]:
    for el in root.iter():
        if _local_name(el.tag) == local_name:
            yield el


def _node_text(el: Optional[ET.Element]) -> str:
    if el is None:
        return ""
    ascii_child = el.find("ascii")
    if ascii_child is not None and ascii_child.text is not None:
        return unquote(ascii_child.text.strip())
    txt = "".join(el.itertext()).strip()
    return unquote(txt)


def _basic_filename_metadata(path: Path) -> Dict[str, Any]:
    """Small filename parser independent of metadata.py.

    This is intentionally conservative. The existing app's metadata.py can still
    do the full strict/best-effort parsing when integrated into the GUI.
    """
    stem = path.stem
    md: Dict[str, Any] = {"filename": path.name, "filename_stem": stem}
    parts = stem.split("_")
    for token in parts:
        low = token.lower()
        if low.endswith("nm"):
            try:
                md["laser_nm"] = float(token[:-2])
            except Exception:
                pass
        elif low.endswith("x"):
            md["objective"] = token
        elif low.endswith("s") and token[:-1].replace(".", "", 1).isdigit():
            try:
                md["integration_time_s"] = float(token[:-1])
            except Exception:
                pass
        elif low == "ocp" or low.endswith("v"):
            md["potential_label"] = token
    if parts:
        md.setdefault("sample_code", parts[0])
    return md


def _as_float_array_from_csv_text(text: str) -> np.ndarray:
    arr = np.fromstring(text or "", sep=",")
    if arr.size == 0:
        # Some XML writers may use whitespace instead of commas.
        arr = np.fromstring(text or "", sep=" ")
    return arr.astype(float)


def load_spe_spectrum(
    filepath: str | Path,
    *,
    laser_power_mw: float = 34.1,
    metadata_override: Optional[Dict[str, Any]] = None,
):
    """Load a Princeton Instruments SPE 3.0 Raman spectrum as a Spectrum.

    For Raman data, the SPE file usually stores scattered wavelength in nm.
    If a laser line is available, this function converts wavelength to Raman
    shift using: shift = (1/laser_nm - 1/scattered_nm) * 1e7.
    """
    if Spectrum is None:
        raise ImportError("Spectrum could not be imported. Run from the EC-SERS project folder.")

    path = Path(filepath)
    raw = path.read_bytes()
    xml_start = raw.find(b"<SpeFormat")
    if xml_start < 0:
        raise ValueError("Could not find SPE 3.0 XML footer '<SpeFormat'.")

    root = ET.fromstring(raw[xml_start:])

    frame_block = None
    region_block = None
    for block in _iter_local(root, "DataBlock"):
        if block.attrib.get("type") == "Frame" and frame_block is None:
            frame_block = block
        if block.attrib.get("type") == "Region" and region_block is None:
            region_block = block

    block_for_size = region_block if region_block is not None else frame_block
    if block_for_size is None:
        raise ValueError("No DataBlock was found in SPE XML footer.")

    pixel_block = frame_block if frame_block is not None else block_for_size
    pixel_format = pixel_block.attrib.get("pixelFormat", "MonochromeUnsigned16")
    dtype = np.dtype(SPE_PIXEL_DTYPES.get(pixel_format, "<u2"))

    # SPE 3.0 has a 4100-byte binary header, followed by frame data, then XML footer.
    data_start = SPE_HEADER_BYTES
    data_stop = xml_start
    frame_bytes = raw[data_start:data_stop]
    y = np.frombuffer(frame_bytes, dtype=dtype)

    width = block_for_size.attrib.get("width")
    height = block_for_size.attrib.get("height", "1")
    if width is not None:
        n_expected = int(width) * int(height)
        if y.size >= n_expected:
            y = y[:n_expected]

    y = y.astype(float)

    wavelength_el = _find_first(root, "Wavelength")
    mapping_el = _find_first(root, "WavelengthMapping")

    x = np.arange(y.size, dtype=float)
    wavelength_nm = None
    laser_line_nm = None
    x_kind = "pixel_index"

    if wavelength_el is not None and wavelength_el.text:
        wavelength_nm = _as_float_array_from_csv_text(wavelength_el.text)
        if wavelength_nm.size == y.size:
            x = wavelength_nm.copy()
            x_kind = "wavelength_nm"

    if mapping_el is not None and mapping_el.attrib.get("laserLine"):
        try:
            laser_line_nm = float(mapping_el.attrib["laserLine"])
        except Exception:
            laser_line_nm = None

    if wavelength_nm is not None and wavelength_nm.size == y.size and laser_line_nm:
        x = (1.0 / laser_line_nm - 1.0 / wavelength_nm) * 1.0e7
        x_kind = "raman_shift_cm-1"

    # Ensure x is ascending for downstream plotting/interpolation.
    if x.size > 1 and np.nanmean(np.diff(x)) < 0:
        x = x[::-1]
        y = y[::-1]

    md = _basic_filename_metadata(path)
    md.update(
        {
            "source_format": "spe",
            "spe_version": root.attrib.get("version", ""),
            "spe_pixel_format": pixel_format,
            "spe_xml_footer_offset": int(xml_start),
            "x_kind": x_kind,
            "laser_line_nm": laser_line_nm,
            "laser_power_mw": float(laser_power_mw),
        }
    )
    if wavelength_nm is not None and wavelength_nm.size:
        md["wavelength_nm_min"] = float(np.nanmin(wavelength_nm))
        md["wavelength_nm_max"] = float(np.nanmax(wavelength_nm))
    if metadata_override:
        for k, v in metadata_override.items():
            if v is not None:
                md[k] = v

    return Spectrum(x=x, y=y, metadata=md)


def _decode_paax_array(el: Optional[ET.Element]) -> np.ndarray:
    if el is None or el.text is None:
        return np.array([], dtype=float)
    raw = base64.b64decode(el.text.strip())
    # PAAX data arrays in the provided file are little-endian float64.
    return np.frombuffer(raw, dtype="<f8").astype(float)


def _unit_label(kind: str, axis: str) -> str:
    kind = (kind or "").lower()
    if axis == "x" and kind == "time":
        return "Time (s)"
    if kind == "current":
        return "Current (A)"
    if kind == "potential":
        return "Potential (V)"
    if kind == "charge":
        return "Charge (C)"
    return f"{axis.upper()} ({kind})" if kind else axis.upper()


def load_paax_traces(filepath: str | Path) -> List[TraceData]:
    """Load all x-y traces from a PAAX XML session file.

    Returns a list of TraceData objects. For the provided AfterMath/Pine PAAX
    file, this extracts Current vs Time, Potential vs Time, Applied Potential
    vs Time, and Charge vs Time traces grouped by study.
    """
    path = Path(filepath)
    root = ET.parse(path).getroot()

    nodes = {n.attrib.get("index"): n for n in root.findall("tree_node")}

    def parent_chain(node: ET.Element) -> List[ET.Element]:
        out = []
        p = node.attrib.get("parent")
        while p and p in nodes:
            parent = nodes[p]
            out.append(parent)
            p = parent.attrib.get("parent")
        return out

    traces: List[TraceData] = []
    for node in root.findall("tree_node"):
        if node.attrib.get("type") != "trace":
            continue
        data = node.find("data")
        if data is None:
            continue

        x_parts = []
        y_parts = []
        for pts in data.findall("points"):
            x_arr = _decode_paax_array(pts.find("X_data"))
            y_arr = _decode_paax_array(pts.find("Y_data"))
            if x_arr.size and y_arr.size:
                n = min(x_arr.size, y_arr.size)
                x_parts.append(x_arr[:n])
                y_parts.append(y_arr[:n])

        if not x_parts or not y_parts:
            continue

        x = np.concatenate(x_parts)
        y = np.concatenate(y_parts)

        name = _node_text(node.find("name")) or f"trace_{node.attrib.get('index')}"
        x_kind = (data.find("X_units").attrib.get("qty_kind", "") if data.find("X_units") is not None else "")
        y_kind = (data.find("Y_units").attrib.get("qty_kind", "") if data.find("Y_units") is not None else "")

        chain = parent_chain(node)
        study_name = ""
        plot_name = ""
        for parent in chain:
            typ = parent.attrib.get("type")
            if typ == "plot" and not plot_name:
                plot_name = _node_text(parent.find("name"))
            if typ == "study" and not study_name:
                study_name = _node_text(parent.find("name"))

        md = {
            "source_format": "paax",
            "filename": path.name,
            "filename_stem": path.stem,
            "node_index": node.attrib.get("index"),
            "parent_index": node.attrib.get("parent"),
            "study_name": study_name,
            "plot_name": plot_name,
            "x_unit_kind": x_kind,
            "y_unit_kind": y_kind,
            "n_points": int(x.size),
        }
        traces.append(
            TraceData(
                x=x,
                y=y,
                name=name,
                xlabel=_unit_label(x_kind, "x"),
                ylabel=_unit_label(y_kind, "y"),
                metadata=md,
            )
        )

    return traces


def find_traces(
    traces: Iterable[TraceData],
    *,
    name_contains: Optional[str] = None,
    study_contains: Optional[str] = None,
    plot_contains: Optional[str] = None,
) -> List[TraceData]:
    """Filter imported PAAX TraceData objects by name/study/plot."""
    out = []
    for tr in traces:
        ok = True
        if name_contains:
            ok &= name_contains.lower() in tr.name.lower()
        if study_contains:
            ok &= study_contains.lower() in str(tr.metadata.get("study_name", "")).lower()
        if plot_contains:
            ok &= plot_contains.lower() in str(tr.metadata.get("plot_name", "")).lower()
        if ok:
            out.append(tr)
    return out
