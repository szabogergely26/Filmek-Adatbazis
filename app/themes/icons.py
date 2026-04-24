# /app/themes/icons.py
# ---------------------
"""
Ikonok beállításai
"""

import logging, unicodedata, re
from pathlib import Path
from PySide6.QtGui import QIcon, QImageReader, QPixmap
from PySide6.QtCore import QFileInfo, Qt

from config import PANIC_NO_ICONS


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PROVIDERS_DIR = BASE_DIR.parent / "ikonok" / "providers"


# Fallback emojik – ha nincs ikonfájl
PROVIDER_EMOJI = {
    "netflix": "🅽",
    "disney": "🅳",
    "max": "Ⓜ",
    "hbo": "ⓗ",
}


# --- ALIASOK/SZINONIMÁK A PROVIDER NEVEKRE ---
# bal oldalt a "nyers" név normalizált kulcsa, jobb oldalt a fájlnév-tő (kiterjesztés nélkül)
PROVIDER_ALIASES = {
    "disney": "disneyplus",
    "disneyplus": "disneyplus",
    "disney-plus": "disneyplus",
    "disney+": "disneyplus",
    "hbo": "hbo",  # ha 'max.png' kell HBO Max-hoz, akkor: "hbo": "max"
    "hbomax": "max",
    "max": "max",
    "netflix": "netflix",
    "local": "hdd",
    "hdd": "hdd",
}


_slug_re = re.compile(r"[^a-z0-9]+")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    return _slug_re.sub("-", s).strip("-")


def best_provider_key(provider_name: str) -> str:
    """Normalizált kulcs + alias feloldás (eltávolítja a felesleges kötőjelet is)."""
    if not provider_name:
        return ""
    key = norm(provider_name)
    # pl. 'disney-' → 'disney'
    key = key.strip("-")
    # alias feloldás
    return PROVIDER_ALIASES.get(key, key)


def safe_icon(path: str | Path) -> QIcon:
    """Biztonságos ikon betöltés. Soha ne dobjon kivételt."""
    if PANIC_NO_ICONS:
        logging.debug("ICON OFF: %s", path); return QIcon()
    if not path:
        logging.debug("ICON MISSING PATH"); return QIcon()
    p = Path(path)
    if not p.exists():
        logging.debug("ICON NOT FOUND: %s", p); return QIcon()

    reader = QImageReader(str(p))
    reader.setAutoTransform(True)
    img = reader.read()
    if img.isNull():
        fmt = reader.format().data().decode("ascii", "ignore") if reader.format() else "?"
        logging.debug("ICON BAD IMAGE: %s (fmt=%s)", p, fmt)
        return QIcon()
    return QIcon(QPixmap.fromImage(img))


def provider_icon_path(
    provider_name: str, providers_dir: str | Path | None = None
) -> Path | None:
    """Visszaadja a legjobb ikonfájl útvonalát a szolgáltatóhoz (svg/png)."""
    if not provider_name:
        return None
    base = Path(providers_dir) if providers_dir else DEFAULT_PROVIDERS_DIR
    cand = [
        base / f"{norm(provider_name)}.svg",
        base / f"{norm(provider_name)}.png",
        base / f"{provider_name}.svg",
        base / f"{provider_name}.png",
    ]
    for c in cand:
        if c.exists():
            return c
    return None


def storage_icon_path(storage_name: str, storage_dir: str | Path) -> Path | None:
    base = Path(storage_dir)
    cand = [
        base / f"{norm(storage_name)}.svg",
        base / f"{norm(storage_name)}.png",
    ]
    for c in cand:
        if c.exists():
            return c
    return None


def provider_icon(provider_name: str, providers_dir: str | Path) -> QIcon:
    p = provider_icon_path(provider_name, providers_dir)
    return safe_icon(p) if p else QIcon()


def storage_icon(storage_name: str, storage_dir: str | Path) -> QIcon:
    p = storage_icon_path(storage_name, storage_dir)
    return safe_icon(p) if p else QIcon()


def debug_print_paths(providers_dir: str | Path, storage_dir: str | Path) -> None:
    logging.info("PROVIDERS_DIR: %s", Path(providers_dir))
    logging.info("STORAGE_DIR:   %s", Path(storage_dir))


# --- ÚJ: egységes QPixmap helper a kártyákhoz ---
def provider_pixmap(
    provider_name: str, providers_dir: str | Path | None = None, *, h: int = 18
) -> QPixmap | None:
    """Betölti és méretezi a szolgáltató ikonját (QPixmap). Ha nincs: None."""
    if PANIC_NO_ICONS or not provider_name:
        return None
    p = provider_icon_path(provider_name, providers_dir)
    if not p:
        return None
    pm = QPixmap(str(p))
    if pm.isNull():
        return None
    return pm.scaledToHeight(h, Qt.SmoothTransformation)
