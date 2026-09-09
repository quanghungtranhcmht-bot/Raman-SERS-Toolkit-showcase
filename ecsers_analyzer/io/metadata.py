import os
import re
from typing import Dict, Any, List, Optional

# Fields we try to extract from filenames
STANDARD_FIELDS = [
    "sample_code",
    "analyte_concentration_M",
    "aggregating_salt",
    "salt_concentration_M",
    "laser_nm",
    "objective",
    "integration_time_s",
]

# Regex patterns for loose parsing
_RE_LASER_NM = re.compile(r"(?P<nm>\d{3,4})\s*nm\b", re.IGNORECASE)
_RE_OBJECTIVE = re.compile(r"(?P<obj>\d{1,3})\s*[xX]\b")
_RE_TIME_S = re.compile(r"(?P<t>\d+(?:\.\d+)?)\s*s(?:ec)?\b", re.IGNORECASE)
_RE_CONC_M = re.compile(
    r"(?P<c>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*M\b",
    re.IGNORECASE,
)

# Common Raman lasers (helps when filename has bare "785" token)
_COMMON_LASERS = {532, 633, 785, 830, 1064}


def _safe_float(s: str) -> Optional[float]:
    try:
        v = float(s)
        if v != v:  # NaN
            return None
        return v
    except Exception:
        return None


def _parse_conc_m(token: str) -> Optional[float]:
    """Parse concentration token like 5E-5M, 0.1M, 1e-1M, etc."""
    t = str(token).strip().replace(" ", "")
    if t.lower().endswith("mol"):
        t = t[:-3]
    if t.lower().endswith("m"):
        t = t[:-1]
    return _safe_float(t)


def parse_metadata_from_filename_strict(filepath: str) -> Dict[str, Any]:
    """Strict 7-part pattern:
    Q_5E-5M_AgNO3_1E-1M_785nm_50x_25s.csv
    """
    name = os.path.splitext(os.path.basename(filepath))[0]
    parts = name.split("_")
    if len(parts) < 7:
        raise ValueError(f"Filename '{name}' does not match expected 7-part pattern.")

    laser_token = parts[4]
    obj_token = parts[5]
    time_token = parts[6]

    laser_nm = int(re.sub(r"[^0-9]", "", laser_token))
    objective = obj_token.lower().replace("X", "x")
    t = re.sub(r"[^0-9.+-eE]", "", time_token)

    md = {
        "sample_code": parts[0],
        "analyte_concentration_M": _parse_conc_m(parts[1]),
        "aggregating_salt": parts[2],
        "salt_concentration_M": _parse_conc_m(parts[3]),
        "laser_nm": laser_nm,
        "objective": objective,
        "integration_time_s": _safe_float(t),
        "filename_stem": name,
        "parse_mode": "strict",
        "parse_warnings": [],
        "missing_fields": [],
        "parse_confidence": 1.0,
    }

    missing = [k for k in STANDARD_FIELDS if md.get(k) is None]
    md["missing_fields"] = missing
    md["parse_confidence"] = (len(STANDARD_FIELDS) - len(missing)) / float(len(STANDARD_FIELDS))
    return md


def parse_metadata_best_effort(filepath: str) -> Dict[str, Any]:
    """Best-effort parser for messy filenames.

    Returns a dict with STANDARD_FIELDS (where possible) plus:
      - filename_stem
      - parse_mode
      - parse_confidence (0..1)
      - missing_fields (list)
      - parse_warnings (list)

    This function never raises due to format mismatch.
    """
    name = os.path.splitext(os.path.basename(filepath))[0]
    raw_parts = [p for p in re.split(r"[_\s]+", name) if p]
    warnings: List[str] = []

    sample_code = raw_parts[0] if raw_parts else name

    laser_nm: Optional[int] = None
    objective: Optional[str] = None
    integration_time_s: Optional[float] = None
    concs: List[float] = []
    salt: Optional[str] = None

    # Handle cases where units are split into separate tokens, e.g. '25 sec', '785 nm', '50 x'.
    for i in range(len(raw_parts) - 1):
        a = raw_parts[i]
        b = raw_parts[i + 1].lower()
        if b == "nm" and laser_nm is None and a.isdigit():
            try:
                v = int(a)
                if v > 100:
                    laser_nm = v
            except Exception:
                pass
        if b == "x" and objective is None and a.isdigit():
            try:
                objective = f"{int(a)}x"
            except Exception:
                pass
        if b in ("s", "sec", "secs", "second", "seconds") and integration_time_s is None:
            try:
                integration_time_s = float(a)
            except Exception:
                pass

    def is_consumed_token(tok: str) -> bool:
        if _RE_LASER_NM.search(tok):
            return True
        if _RE_OBJECTIVE.search(tok):
            return True
        if _RE_TIME_S.search(tok):
            return True
        if _RE_CONC_M.search(tok):
            return True
        if tok.isdigit() and int(tok) in _COMMON_LASERS:
            return True
        return False

    # Pass 1: extract laser/objective/time/concentrations
    for tok in raw_parts:
        m = _RE_LASER_NM.search(tok)
        if m and laser_nm is None:
            laser_nm = int(m.group("nm"))
            continue

        if laser_nm is None and tok.isdigit():
            try:
                v = int(tok)
                if v in _COMMON_LASERS:
                    laser_nm = v
                    continue
            except Exception:
                pass

        m = _RE_OBJECTIVE.search(tok)
        if m and objective is None:
            try:
                objective = f"{int(m.group('obj'))}x"
            except Exception:
                objective = m.group("obj") + "x"
            continue

        m = _RE_TIME_S.search(tok)
        if m and integration_time_s is None:
            integration_time_s = _safe_float(m.group("t"))
            continue

        m = _RE_CONC_M.search(tok)
        if m:
            v = _safe_float(m.group("c"))
            if v is not None:
                concs.append(v)
            continue

        # Extra: tokens like '5E-5M' with odd characters
        if ("m" in tok.lower()) and any(ch.isdigit() for ch in tok):
            v = _parse_conc_m(tok)
            if v is not None and not is_consumed_token(tok):
                concs.append(v)

    # Pass 2: pick a likely salt token
    for tok in raw_parts[1:]:
        if tok == sample_code:
            continue
        if is_consumed_token(tok):
            continue
        if re.search(r"[A-Za-z]", tok) and re.search(r"\d", tok):
            salt = tok
            break

    if salt is None:
        for tok in raw_parts[1:]:
            if tok == sample_code:
                continue
            if is_consumed_token(tok):
                continue
            if re.fullmatch(r"[A-Za-z]{2,10}", tok):
                salt = tok
                break

    analyte_conc = concs[0] if len(concs) >= 1 else None
    salt_conc = concs[1] if len(concs) >= 2 else None
    if len(concs) > 2:
        warnings.append(f"Found {len(concs)} concentration-like tokens; using first two as analyte/salt.")

    md: Dict[str, Any] = {
        "sample_code": sample_code,
        "analyte_concentration_M": analyte_conc,
        "aggregating_salt": salt,
        "salt_concentration_M": salt_conc,
        "laser_nm": laser_nm,
        "objective": objective,
        "integration_time_s": integration_time_s,
        "filename_stem": name,
        "parse_mode": "best_effort",
        "parse_warnings": warnings,
    }

    missing = [k for k in STANDARD_FIELDS if md.get(k) is None]
    md["missing_fields"] = missing
    md["parse_confidence"] = (len(STANDARD_FIELDS) - len(missing)) / float(len(STANDARD_FIELDS))
    return md


def parse_metadata_from_filename(filepath: str, best_effort: bool = True) -> Dict[str, Any]:
    """Backwards-compatible entrypoint used by loader.

    - Tries strict parsing first.
    - If strict fails and best_effort=True, returns best-effort parse with confidence.
    """
    try:
        return parse_metadata_from_filename_strict(filepath)
    except Exception as e:
        if not best_effort:
            raise
        md = parse_metadata_best_effort(filepath)
        md.setdefault("parse_warnings", []).append(f"Strict parse failed: {e}")
        return md
