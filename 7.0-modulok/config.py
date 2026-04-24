#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ------------- #
#   Config      #
# ------------- #


"""
Központi konfiguráció:
- Alap adatok (app név / verzió)
- elérési utak
- DB_PATH

- logolásNaplózás (log)
- Feature kapcsolók (Beállítások ablakból használd!!)
- UI konstansok

"""


# Importok:

import os
import logging
from logging.handlers import RotatingFileHandler
from configparser import ConfigParser
from pathlib import Path
from configparser import NoOptionError, NoSectionError

# -- Importok vége ----------











# ---------------- Alap adatok ----------------

APP_NAME = "FilmekAdatbazis"             # ez kerül: ~/.local/share/Filmekadatbazis/FilmekAdatbázis/
APP_DISPLAY_NAME = "Filmek Adatbázis"
APP_VERSION = "7.0"
APP_ORG = "Filmekadatbazis"



# ------------------------------------ Projekt elérési utak ------------------------------------

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

ICON_PATH = ROOT / "ikonok" / "filmek.ico"
PROVIDERS_DIR = ROOT / "ikonok" / "providers"
COVER_DIR = ROOT / "cover"

# ------------------------------------ App adatkönyvtár (DEV) ------------------------------------

APP_DATA_DIR = ROOT / "_appdata" / "dev"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = APP_DATA_DIR / "Movies7.conf"
DB_PATH = APP_DATA_DIR / "movies.db"
LOG_DIR = APP_DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Globális ConfigParser példány
config: ConfigParser = ConfigParser()
config.read(CONFIG_PATH)



print("COVER_DIR:", COVER_DIR)
print("APP_DATA_DIR:", APP_DATA_DIR)
print("DB_PATH:", DB_PATH)











# ---------------- NAPLÓZÁS ----------------------------------------------------------------

# Környezeti változókkal:
#   FILMEK_LOG_CONSOLE = 0/1
#   FILMEK_LOG_FILE    = 0/1
#   FILMEK_LOG_LEVEL   = DEBUG/INFO/WARNING/ERROR

LOG_TO_CONSOLE = os.environ.get("FILMEK_LOG_CONSOLE", "1") == "1"
LOG_TO_FILE = os.environ.get("FILMEK_LOG_FILE", "1") == "1"  # ALAPBÓL: ÍRJON FÁJLBA
LOG_LEVEL = os.environ.get("FILMEK_LOG_LEVEL", "DEBUG")

LOGGER = logging.getLogger("FilmekAdatbazis")

# ahova írunk
LOG_DIR = APP_DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "app.log"

if not LOGGER.handlers:
    LOGGER.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    if LOG_TO_CONSOLE:
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        LOGGER.addHandler(ch)

    if LOG_TO_FILE:
        fh = RotatingFileHandler(
            LOG_PATH,
            maxBytes=2_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        LOGGER.addHandler(fh)

# UI-specifikus logger (pl. kártyák építése közben)
ui = LOGGER.getChild("ui")  # == "FilmekAdatbazis.ui"
ui.propagate = True  # (alapból is True, de legyen egyértelmű)
ui.setLevel(LOGGER.level)













# ---------------- Feature kapcsolók (ki/be) ----------------

# Ha True: Új → többoldalas varázsló (AddItemWizard)
# Ha False: Új → egyszerű EditDialog
USE_WIZARD_FOR_NEW = True

# Ha True: minden ikon kikapcsolva (debug / ha hiányoznak ikonfájlok)
PANIC_NO_ICONS = False

# Ha False: a kártyákon nem rajzol extra provider badge-eket (csak a fejléc emoji/ikon marad)
ENABLE_PROVIDER_BADGES = True


# Ha True: a kártyákon megjelenik a borítókép (ha van a COVER_DIR-ben)
# Ha False: borító nélkül rajzoljuk a kártyát
SHOW_COVER_ON_CARD = True










# ---------------- UI / Kártya / Gomb konstansok ----------------

# -- Kártya méretek --
CARD_WIDTH_MIN = 320
CARD_HEIGHT_FIXED = 190
CARD_PADDING = 12
BADGE_SPACING_LEFT = 60

# -- Ikon méretek --
ICON_SIZE_PROVIDER = 28
ICON_SIZE_STORAGE = 22
ICON_SIZE_TYPE = 26

# -- Gomb méretek --
BUTTON_HEIGHT = 34
BUTTON_ICON_SIZE = 18

# -- Színek, betűk, margók (későbbi finomhangoláshoz) --
COLOR_BG_CARD = "#2f2f2f"
COLOR_BORDER_CARD = "#3f3f3f"
FONT_SIZE_TITLE = 16
FONT_SIZE_META = 13

# -- Borító hiányában kiírt szöveg --
NO_COVER_TEXT = "Nincs kép"




def get_bool(section: str, key: str, fallback: bool = False) -> bool:
    """Biztonságos bool olvasás a Movies7.conf-ból."""
    try:
        return config.getboolean(section, key)
    except (NoSectionError, NoOptionError, ValueError):
        return fallback


def set_bool(section: str, key: str, value: bool) -> None:
    """Bool beállítása a Movies7.conf-ban."""
    if not config.has_section(section):
        config.add_section(section)
    config.set(section, key, "true" if value else "false")


def save_config() -> None:
    """Jelenlegi config tartalom kiírása a CONFIG_PATH-ra."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        config.write(f)





# Kényelmi gatterek:

def is_cover_enabled() -> bool:
    # régi default: SHOW_COVER_ON_CARD = True → fallback=True
    return get_bool("General", "show_cover_on_card", fallback=True)


def is_provider_badges_enabled() -> bool:
    return get_bool("General", "enable_provider_badges", fallback=True)


def is_wizard_enabled() -> bool:
    return get_bool("General", "use_wizard_for_new", fallback=True)