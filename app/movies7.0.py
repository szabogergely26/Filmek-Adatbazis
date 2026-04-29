# Filmek Adatbázis - Fejlesztői (Rolling...)
# ---------------------------------------------


# /app/movies7.0.py - később main.py
# --------------------------------------

from __future__ import annotations

import logging
import logging.handlers
import socket
import sqlite3
import sys
from pathlib import Path

from config import APP_DATA_DIR, APP_NAME, APP_ORG, APP_VERSION, DB_PATH, ICON_PATH, LOGGER
from db.database_manager import DatabaseManager
from main_window import MainWindow
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPalette
from PySide6.QtWidgets import QApplication
from themes.theme_utils import apply_theme_from_settings

# -- Importok vége -----



# Egypéldányos védelem (Linux + Windows): localhost port lock
_SINGLE_INSTANCE_SOCK: socket.socket | None = None
SINGLE_INSTANCE_PORT = 47371  # tetszőleges fix port, csak legyen szabad


def ensure_single_instance() -> bool:
    """
    Gondoskodik róla, hogy csak egy példány fusson.
    Ha nem tudjuk lefoglalni a portot, már fut egy példány.
    """
    global _SINGLE_INSTANCE_SOCK
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # csak a saját gépen, ne hallgasson kívülről
        s.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
        s.listen(1)
    except OSError:
        # a port már foglalt → fut egy példány
        s.close()
        return False

    _SINGLE_INSTANCE_SOCK = s
    return True




def load_stylesheet() -> str:
    """
    style.css betöltése a main7.0.py melletti könyvtárból.
    Ha nincs vagy nem olvasható, üres stringet ad vissza.
    """
    css_path = Path(__file__).resolve().parent / "style.css"

    try:
        return css_path.read_text(encoding="utf-8")
    except OSError:
        # Nem állítjuk meg az appot, csak nem lesz stylesheet
        return ""












# --------- Globális hibalogolás (minden nem kezelt kivétel menjen logba is) ---------

_OLD_EXCEPTHOOK = sys.excepthook  # elmentjük az eredetit


def log_unhandled_exceptions(exc_type, exc_value, exc_tb):
    # Log fájlba:
    LOGGER.error(
        "Nem kezelt kivétel",
        exc_info=(exc_type, exc_value, exc_tb),
    )
    # Konzolra ugyanúgy menjen tovább a klasszikus traceback:
    _OLD_EXCEPTHOOK(exc_type, exc_value, exc_tb)


sys.excepthook = log_unhandled_exceptions


# --------Vége -------------------




# ----- LOG: ------------

def setup_logging() -> None:
    """Naplózás beállítása QSettings alapján."""
    settings = QSettings(APP_ORG, APP_NAME)
    debug_logging = settings.value("developer/debug_logging", False, bool)

    # Ha be van kapcsolva a debug naplózás → DEBUG, különben INFO
    log_level = logging.DEBUG if debug_logging else logging.INFO


    log_dir = APP_DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "root.log"


    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Régi handlerek törlése, hogy ne duplázódjon
    root_logger.handlers.clear()

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(fmt, datefmt))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(fmt, datefmt))

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logger = logging.getLogger(__name__)
    logger.info(
        "Naplózás inicializálva. Szint: %s",
        logging.getLevelName(log_level),
    )



# --------- BOOTSTRAP / SÉMA + MIGRÁCIÓ ---------


def ensure_schema_fresh(path: str) -> None:
    """Létrehozza az alap sémát, ha még nincs DB vagy nincs movies tábla."""
    with sqlite3.connect(path) as con:
        cur = con.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                title TEXT NOT NULL,
                part INTEGER,
                year INTEGER,
                end_year INTEGER,
                is_completed BOOLEAN,
                is_seasonal BOOLEAN,
                genre TEXT,
                duration TEXT,
                size TEXT,
                storage_location TEXT,
                format_type TEXT,
                format TEXT,
                director TEXT,
                audio_tracks TEXT,
                subtitle_tracks TEXT,
                episode_title TEXT,
                provider TEXT
            )
        """
        )
        con.commit()


def migrate_schema_raw(path: str) -> None:
    """Hiányzó oszlopok pótlása (idempotens)."""
    with sqlite3.connect(path) as con:
        cur = con.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='movies'"
        )
        if not cur.fetchone():
            return
        cur.execute("PRAGMA table_info(movies)")
        cols = {r[1] for r in cur.fetchall()}

        needed = {
            "audio_tracks": "TEXT",
            "subtitle_tracks": "TEXT",
            "episode_title": "TEXT",
            "end_year": "INTEGER",
            "is_completed": "BOOLEAN",
            "provider": "TEXT",
            "notes": "TEXT",
        }
        for col, ddl in needed.items():
            if col not in cols:
                cur.execute(f"ALTER TABLE movies ADD COLUMN {col} {ddl}")
        con.commit()


# 1) táblát biztosan létrehozzuk (üres DB esetén)
ensure_schema_fresh(DB_PATH)
# 2) későbbi bővítések pótlása
migrate_schema_raw(DB_PATH)


# --------- Sötét téma ---------
def setup_dark_theme(app: QApplication):
    app.setStyle("Fusion")
    dark = QPalette()
    dark.setColor(QPalette.Window, QColor(45, 45, 45))
    dark.setColor(QPalette.WindowText, QColor(220, 220, 220))
    dark.setColor(QPalette.Base, QColor(20, 20, 20))
    dark.setColor(QPalette.AlternateBase, QColor(55, 55, 55))
    dark.setColor(QPalette.ToolTipBase, QColor(220, 220, 220))
    dark.setColor(QPalette.ToolTipText, QColor(220, 220, 220))
    dark.setColor(QPalette.Text, QColor(220, 220, 220))
    dark.setColor(QPalette.Button, QColor(60, 60, 60))
    dark.setColor(QPalette.ButtonText, QColor(220, 220, 220))
    dark.setColor(QPalette.Link, QColor(100, 180, 255))
    dark.setColor(QPalette.Highlight, QColor(70, 130, 180))
    dark.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    app.setPalette(dark)


# --------- futtatás ---------
def main() -> int:
    setup_logging()

    if not ensure_single_instance():
        print("Már fut a Filmek Adatbázis, új példány nem indul.")
        LOGGER.warning("Második példány próbált indulni, kilépünk.")
        return 0

    print(f"[BOOT] {APP_VERSION}")
    LOGGER.info("Filmek %s indul. DB_PATH=%s", APP_VERSION, DB_PATH)


    app = QApplication(sys.argv)

    # Wayland/KDE: .desktop app-id (NE .desktop kiterjesztéssel)
    QGuiApplication.setDesktopFileName("filmek-adatbazis")

    # app név
    app.setApplicationName(APP_NAME)

    # Alap fallback téma
    setup_dark_theme(app)

   # Téma alkalmazása a beállítások alapján
    apply_theme_from_settings(app)

    # globális ikon
    ic = QIcon(str(ICON_PATH))
    if ic.isNull():
        print(f"Figyelem: ikon nem tölthető: {ICON_PATH}")
        LOGGER.warning("Ikon nem tölthető: %s", ICON_PATH)
    app.setWindowIcon(ic)

    # Egyetlen központi DB-példány az egész appnak
    dbm = DatabaseManager(DB_PATH)

    win = MainWindow(dbm)
    win.show()

    return app.exec()


if __name__ == "__main__":

    sys.exit(main())
