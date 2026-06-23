from __future__ import annotations

import json
import re
from typing import Any

# ---------------------------
# Parsing / formatting helpers
# ---------------------------

_RANGE_RE = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")


def parse_size_text_to_gb(size_text: str | None) -> float | None:
    """
    "23 GB", "23,5 GB", "1024 MB", "1.2 TB" -> GB float
    Ha nem felismerhető, None.
    """
    if not size_text:
        return None
    s = size_text.strip().lower().replace(",", ".")
    # pl: "23 gb", "1.5 tb", "700 mb"
    m = re.match(r"^\s*([\d.]+)\s*(tb|gb|mb)\s*$", s)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2)
    if unit == "mb":
        return val / 1024.0
    if unit == "gb":
        return val
    if unit == "tb":
        return val * 1024.0
    return None


def _norm_loc(loc: str | None) -> str:
    return (loc or "").strip()


def _to_float(x: Any) -> float | None:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _parse_season_range(text: str) -> tuple[int, int] | None:
    m = _RANGE_RE.match(text)
    if not m:
        return None
    a = int(m.group(1))
    b = int(m.group(2))
    if a < 1 or b < 1 or a > b:
        return None
    return a, b


def load_storage_breakdown(raw: str | None) -> list[dict[str, Any]]:
    """
    storage_breakdown TEXT (JSON) -> list of dict
    Hibás/üres esetben [].
    """
    if not raw:
        return []
    try:
        obj = json.loads(raw)
        if isinstance(obj, list):
            # csak dict elemeket tartunk meg
            return [x for x in obj if isinstance(x, dict)]
    except Exception:
        pass
    return []


def dump_storage_breakdown(items: list[dict[str, Any]]) -> str:
    """
    list of dict -> JSON string (compact, stable)
    """
    return json.dumps(items, ensure_ascii=False, separators=(",", ":"))


def calc_total_size_gb(items: list[dict[str, Any]]) -> float:
    """
    Összméret számítása breakdown-ból.
    Csak a size_gb mezőt nézzük (float-ra konvertálva), negatívat ignoráljuk.
    """
    total = 0.0
    for it in items:
        v = _to_float(it.get("size_gb"))
        if v is None or v < 0:
            continue
        total += v
    return round(total, 2)


# ---------------------------
# Validation / normalization
# ---------------------------

def normalize_breakdown_for_movie(
    parts_count: int,
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Film: part-alapú elemeket engedünk: {"part": N, "loc": "...", "size_gb": ...}
    - part 1..parts_count
    - duplikált part: az utolsó nyer (UI szerkesztésnél praktikus)
    - loc normalizálás, size_gb float
    """
    parts_count = max(1, int(parts_count or 1))
    by_part: dict[int, dict[str, Any]] = {}

    for it in items:
        p = it.get("part")
        if p is None:
            continue
        try:
            p = int(p)
        except Exception:
            continue
        if p < 1 or p > parts_count:
            continue

        loc = _norm_loc(it.get("loc"))
        size_gb = _to_float(it.get("size_gb"))
        out = {"part": p, "loc": loc}
        if size_gb is not None:
            out["size_gb"] = round(size_gb, 2)
        by_part[p] = out

    # vissza rendezett listában
    return [by_part[p] for p in sorted(by_part.keys())]


def normalize_breakdown_for_series(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Sorozat: season vagy seasons (tartomány) alapú elemek:
      {"season": N, "loc": "...", "size_gb": ...}
      {"seasons": "1-3", "loc": "...", "size_gb": ...}

    Nem kényszerítjük, hogy minden évad lefedett legyen, és az átfedést sem tiltjuk
    (de később simán lehet warningot adni rá).
    """
    out: list[dict[str, Any]] = []

    for it in items:
        loc = _norm_loc(it.get("loc"))
        size_gb = _to_float(it.get("size_gb"))
        base: dict[str, Any] = {"loc": loc}
        if size_gb is not None:
            base["size_gb"] = round(size_gb, 2)

        if "season" in it and it.get("season") is not None:
            try:
                n = int(it.get("season"))
            except Exception:
                continue
            if n < 1:
                continue
            base["season"] = n
            out.append(base)
            continue

        if "seasons" in it and isinstance(it.get("seasons"), str):
            rng = _parse_season_range(it["seasons"])
            if not rng:
                continue
            a, b = rng
            base["seasons"] = f"{a}-{b}"
            out.append(base)
            continue

    # rendezés: season-ek előre, utána tartományok kezdő szerint
    def _key(x: dict[str, Any]) -> tuple[int, int]:
        if "season" in x:
            return (0, int(x["season"]))
        if "seasons" in x:
            a, _ = _parse_season_range(x["seasons"]) or (10**9, 10**9)
            return (1, a)
        return (2, 10**9)

    out.sort(key=_key)
    return out


# ---------------------------
# Display formatting
# ---------------------------

def format_breakdown_lines_for_movie(items: list[dict[str, Any]]) -> list[str]:
    """
    ["1. rész — 23.0 GB — 4_1 TB", ...]
    """
    lines: list[str] = []
    for it in items:
        p = it.get("part")
        loc = (it.get("loc") or "").strip()
        size_gb = _to_float(it.get("size_gb"))
        size_txt = f"{size_gb:.2f} GB".rstrip("0").rstrip(".") if size_gb is not None else "—"
        loc_txt = loc if loc else "—"
        lines.append(f"{int(p)}. rész — {size_txt} — {loc_txt}")
    return lines


def format_breakdown_lines_for_series(items: list[dict[str, Any]]) -> list[str]:
    """
    ["1–3. évad — 180 GB — 2_4 TB", "4. évad — 55 GB — SSD", ...]
    """
    lines: list[str] = []
    for it in items:
        loc = (it.get("loc") or "").strip()
        size_gb = _to_float(it.get("size_gb"))
        size_txt = f"{size_gb:.2f} GB".rstrip("0").rstrip(".") if size_gb is not None else "—"
        loc_txt = loc if loc else "—"

        if "season" in it:
            lines.append(f"{int(it['season'])}. évad — {size_txt} — {loc_txt}")
        elif "seasons" in it:
            # en-dash
            rng = it["seasons"].replace("-", "–")
            lines.append(f"{rng}. évad — {size_txt} — {loc_txt}")
    return lines
