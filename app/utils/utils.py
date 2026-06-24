# /apps/utils/utils.py
# ------------------------

# -*- coding: utf-8 -*-

"""
Közös segédfüggvények a Filmek Adatbázis apphoz.
- méret (GB) feldolgozás
- évad/rész tartományok kezelése
- listák összefésülése
- hangsáv / felirat formázás
- sorozat évadok összegző nézete
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

# ---------------- Méret (GB) segédek ----------------


def parse_size_to_gb(size_str: Any) -> float | None:
    """'12.3 GB' -> 12.3 (float), hibás/üres esetén None."""
    if not size_str:
        return None
    m = re.search(r"([\d.,]+)\s*GB", str(size_str), flags=re.IGNORECASE)
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except Exception:
            return None
    return None


def pretty_size(total_gb: float | None) -> str:
    """GB értékből szépen formázott szöveg."""
    return "" if total_gb is None else f"{total_gb:.1f} GB"


def sum_sizes_gb(items: list[dict[str, Any]]) -> float | None:
    """Több elem 'size' mezőjét összegzi GB-ban (ha lehet)."""
    vals: list[float] = []
    for it in items:
        g = parse_size_to_gb(it.get("size") or "")
        if g is not None:
            vals.append(g)
    return sum(vals) if vals else None


# ---------------- Általános listakezelő segédek ----------------


def join_unique(items: list[str]) -> str:
    """Sorozat/film meta mezők összefűzésére – duplikátumok nélkül."""
    seen: list[str] = []
    for it in items:
        if it and it not in seen:
            seen.append(it)
    return ", ".join(seen)


def as_int(x: Any, default: int = 0) -> int:
    """Biztonságos int-konverzió."""
    try:
        if x is None:
            return default
        return int(str(x).strip())
    except Exception:
        return default


def parse_first_int(txt: Any) -> int | None:
    """Szövegből az első előforduló számot adja vissza (vagy None)."""
    if not txt:
        return None
    m = re.search(r"\d+", str(txt))
    return int(m.group(0)) if m else None


def expand_parts(text: str) -> list[int]:
    """
    '1-3,5, 7-8' -> [1, 2, 3, 5, 7, 8]
    '4'           -> [4]
    üres / hibás darab -> kihagyjuk
    """
    if not text:
        return []
    # egységesítsük az elválasztót: en-dash -> sima kötőjel
    t = str(text).replace("–", "-")
    out: set[int] = set()
    for chunk in t.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            a, _, b = chunk.partition("-")
            try:
                start = int(a.strip())
                end = int(b.strip())
                if start > end:
                    start, end = end, start
                for v in range(start, end + 1):
                    out.add(v)
            except Exception:
                # rossz darab -> kihagyjuk
                pass
        else:
            try:
                out.add(int(chunk))
            except Exception:
                pass
    return sorted(out)


# ---------------- Hang / felirat formázás ----------------

LANG_MAP = {
    "hu": "magyar",
    "en": "angol",
    "de": "német",
    "fr": "francia",
    "it": "olasz",
    "es": "spanyol",
    "pt": "portugál",
    "pl": "lengyel",
    "ru": "orosz",
    "cs": "cseh",
    "sk": "szlovák",
    "ja": "japán",
    "ko": "koreai",
    "zh": "kínai",
}


def format_tracks(raw: str | None) -> str:
    """
    Hangsáv/felirat mezők emberbarát formázása.
    Pl. 'hu 5.1; en 2.0' -> 'magyar 5.1, angol 2.0'
    """
    if not raw:
        return ""
    txt = str(raw).strip()
    for sep in [";", "/", "|"]:
        txt = txt.replace(sep, ",")
    parts = [p.strip() for p in txt.split(",") if p.strip()]
    out: list[str] = []
    for p in parts:
        tokens = p.split()
        if not tokens:
            continue
        first = tokens[0].lower()
        if first in LANG_MAP:
            tokens[0] = LANG_MAP[first]
            out.append(" ".join(tokens))
        else:
            out.append(p)
    seen: list[str] = []
    for it in out:
        if it not in seen:
            seen.append(it)
    return ", ".join(seen)


def pretty_genre_pair(
    general: str | None,
    official: str | None,
    fallback: str | None = None,
) -> str:
    """
    Általános + hivatalos műfaj kombinálása egy szép szövegbe.
    """
    gen = (general or "").strip()
    off = (official or "").strip()
    if gen and off:
        return f"{gen} (hiv.: {off})"
    if gen:
        return gen
    if off:
        return f"(hiv.: {off})"
    return (fallback or "").strip()


# ---------------- Sorozat évadok összegzése megjelenítéshez ----------------


def _norm_str(s: str | None) -> str:
    return (s or "").strip()


def _norm_str_low(s: str | None) -> str:
    return _norm_str(s).lower()


def group_seasons_for_display(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sorozat-részek összegzése megjelenítéshez:

    - kulcs: (storage_location VAGY provider, format_type normalizálva)
    - part (évad) szerinti folytonos szegmensek (pl. 1–3)
    - méret összeadás (GB), ha lehet; különben az első nem üres méretszöveg
    """
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for it in items:
        storage = _norm_str(it.get("storage_location"))
        provider = _norm_str(it.get("provider"))
        storage_or_provider = (
            storage or provider
        )  # ha nincs tárolás, essen vissza szolgáltatóra
        fmt_type_low = _norm_str_low(it.get("format_type"))
        key = (storage_or_provider, fmt_type_low)
        buckets[key].append(it)

    rows: list[dict[str, Any]] = []
    for (storage_or_provider, fmt_type_low), arr in buckets.items():
        # parts összegyűjtése
        parts = sorted(
            [p for p in (as_int(x.get("part"), None) for x in arr) if p is not None]
        )

        # folytonos szegmensek képzése
        segments: list[list[int | None]] = []
        if parts:
            seg: list[int] = [parts[0]]
            for p in parts[1:]:
                if p == seg[-1] + 1:
                    seg.append(p)
                else:
                    segments.append(seg)
                    seg = [p]
            segments.append(seg)
        else:
            segments = [[None]]

        # emberbarát formátum-címke (próbáljuk az eredeti casing-et megőrizni)
        fmt_label = ""
        for x in arr:
            cand = (x.get("format_type") or x.get("format") or "").strip()
            if cand:
                fmt_label = cand
                break

        for seg in segments:
            # címke
            if seg == [None]:
                label = "—"
            elif len(seg) == 1:
                label = f"{seg[0]}. évad"
            else:
                label = f"{seg[0]}–{seg[-1]}. évad"

            # méretösszegzés
            sizes_gb: list[float] = []
            first_size_text = ""
            for x in arr:
                p = as_int(x.get("part"), None)
                if (seg == [None] and p is None) or (p in seg):
                    s_txt = (x.get("size") or "").strip()
                    if not first_size_text and s_txt:
                        first_size_text = s_txt
                    g = parse_size_to_gb(s_txt)
                    if g is not None:
                        sizes_gb.append(g)

            size_total = f"{sum(sizes_gb):.0f} GB" if sizes_gb else first_size_text

            rows.append(
                {
                    "label": label,  # pl. "1–7. évad"
                    "storage": storage_or_provider,  # "/Multim_3" vagy "Netflix"
                    "size": size_total,  # "110 GB"
                    "fmt": fmt_label,  # "HD 720p" stb.
                    "sort_key": (seg[0] if seg and seg[0] is not None else 10**9),
                }
            )

    rows.sort(key=lambda r: r["sort_key"])
    return rows
