#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Téma alkalmazása QSettings alapján.

theme = "modern"   -> style.css betöltése
theme = "standard" -> csak sötét Fusion paletta, extra CSS nélkül
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication

# Próbáljuk a config-ból venni az app nevét, de ha nincs, legyen alapértelmezés.
try:
    from config import APP_ORG, APP_NAME
except ImportError:
    APP_ORG = "FilmekAdatbazis"
    APP_NAME = "Movies7"

LOGGER = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent


def setup_dark_theme(app: QApplication) -> None:
    """
    Sötét Fusion paletta beállítása az egész alkalmazásra.
    (Ha már van külön style.py-ben ilyen, ezt nyugodtan össze lehet vonni vele.)
    """
    app.setStyle("Fusion")
    palette = QPalette()

    # Alapszínek
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, QColor(220, 220, 220))
    palette.setColor(QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, QColor(220, 220, 220))
    palette.setColor(QPalette.ToolTipText, QColor(220, 220, 220))
    palette.setColor(QPalette.Text, QColor(220, 220, 220))
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, QColor(220, 220, 220))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))

    # Linkek
    palette.setColor(QPalette.Link, QColor(42, 130, 218))

    # Kijelölés
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(35, 35, 35))

    app.setPalette(palette)


def load_stylesheet() -> str:
    """
    style.css beolvasása a 7.0-modulok mappájából (ahol a theme_utils.py is van).
    Ha nincs vagy nem olvasható, üres stringet ad vissza.
    """
    css_path = BASE_DIR / "style.css"
    try:
        with css_path.open("r", encoding="utf-8") as f:
            css = f.read()
            if not css.strip():
                LOGGER.warning("style.css üres: %s", css_path)
            return css
    except OSError as e:
        LOGGER.warning("Nem sikerült beolvasni a style.css-t: %s (%s)", css_path, e)
        return ""


def apply_theme_from_settings(app: QApplication) -> None:
    """
    Beolvassa a 'theme' beállítást QSettings-ből, és alkalmazza
    a megfelelő témát az egész alkalmazásra.
    """
    settings = QSettings(APP_ORG, APP_NAME)

    # 1) Beolvasás (először a gyökér kulcs, aztán a [General])
    theme = settings.value("theme", None, str)
    if theme is None:
        theme = settings.value("General/theme", "modern", str)

    if theme not in ("modern", "standard"):
        LOGGER.warning(
            "Ismeretlen theme érték a settings-ben: %r, visszaállítunk 'modern'-re",
            theme,
        )
        theme = "modern"

    LOGGER.info("apply_theme_from_settings: theme=%s", theme)

    # 2) Mindig a sötét Fusion palettáról indulunk
    setup_dark_theme(app)

    # 3) Modern -> CSS, Standard -> CSS törlése
    if theme == "modern":
        css = load_stylesheet()
        if css:
            app.setStyleSheet(css)
            LOGGER.info("Téma alkalmazva: modern (style.css feltöltve).")
        else:
            app.setStyleSheet("")
            LOGGER.warning(
                "Téma: modern, de nincs érvényes style.css. "
                "Marad csak a sötét Fusion paletta."
            )
    else:
        app.setStyleSheet("")
        LOGGER.info("Téma alkalmazva: standard (nincs extra CSS).")
