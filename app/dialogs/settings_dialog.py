#!/usr/bin/env python3

"""
Beállítások párbeszédablak a Movies7.0 alkalmazáshoz.

Oldalsávos elrendezés:

[ Általános    ]   [ Általános tartalom   ]
[ Megjelenítés ]   [ Megjelenítés tartalom]
[ Naplózás     ]   [ Naplózás tartalom    ]
[ Fejlesztői   ]   [ Fejlesztői tartalom  ]

Osztályok 1: class SettingsDialog(QDialog)

"""

from __future__ import annotations

import os

from config import APP_NAME, APP_ORG
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class SettingsDialog(QDialog):
    """
    Beállítások párbeszédablak – bal oldali oldalsávval.

    Opcionális paraméterek:
    - default_db_path: alapértelmezett adatbázis útvonal
    - log_file_path: a naplófájl elérési útja (csak megjelenítés)
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        default_db_path: str | None = None,
        log_file_path: str | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Beállítások")

        # QSettings – a config.py-ban definiált globális példányt használjuk
        # Így minden modul ugyanabból a .conf-ból olvas/ír.
        self._settings = QSettings(APP_ORG, APP_NAME)

        self._default_db_path = default_db_path or ""
        self._log_file_path = log_file_path or ""

        # --- Fő layout ---
        main_layout = QVBoxLayout(self)

        # Felső rész: bal oldalt lista, jobb oldalt tartalom
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)

        # Bal oldali navigációs lista
        self._nav_list = QListWidget(self)
        self._nav_list.addItem("Általános")
        self._nav_list.addItem("Megjelenítés")
        self._nav_list.addItem("Naplózás")
        self._nav_list.addItem("Fejlesztői")
        self._nav_list.setFixedWidth(160)

        content_layout.addWidget(self._nav_list)

        # Jobb oldali stack – minden oldal egy-egy QWidget
        self._stack = QStackedWidget(self)
        content_layout.addWidget(self._stack, 1)

        # Oldalak (korábbi „fülek”)
        self._page_general = QWidget()
        self._page_appearance = QWidget()
        self._page_logging = QWidget()
        self._page_developer = QWidget()

        self._stack.addWidget(self._page_general)      # index 0
        self._stack.addWidget(self._page_appearance)   # index 1
        self._stack.addWidget(self._page_logging)      # index 2
        self._stack.addWidget(self._page_developer)    # index 3

        # Oldalak UI-jának felépítése
        self._build_general_page()
        self._build_appearance_page()
        self._build_logging_page()
        self._build_developer_page()

        # Navigáció összekötése a stack-kel
        self._nav_list.currentRowChanged.connect(self._stack.setCurrentIndex)
        self._nav_list.setCurrentRow(0)

        # Gombok: OK / Mégse
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        # Beállítások betöltése
        self._load_settings()

    # ------------------------------------------------------------------
    # 1. oldal: Általános
    # ------------------------------------------------------------------
    def _build_general_page(self) -> None:
        layout = QVBoxLayout(self._page_general)

        form = QFormLayout()
        layout.addLayout(form)

        # Adatbázis elérési útja
        db_layout = QHBoxLayout()
        self.edt_db_path = QLineEdit(self._page_general)
        if self._default_db_path:
            self.edt_db_path.setPlaceholderText(self._default_db_path)
        btn_browse_db = QPushButton("Tallózás…", self._page_general)
        btn_browse_db.clicked.connect(self._browse_db_path)

        db_layout.addWidget(self.edt_db_path)
        db_layout.addWidget(btn_browse_db)

        form.addRow("Adatbázis helye:", db_layout)

        layout.addStretch(1)

    def _browse_db_path(self) -> None:
        current = self.edt_db_path.text().strip()
        start_dir = os.path.dirname(current) if current else os.path.expanduser("~")

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Adatbázis fájl kiválasztása",
            start_dir,
            "SQLite adatbázisok (*.db *.sqlite *.sqlite3);;Minden fájl (*.*)",
        )
        if file_path:
            self.edt_db_path.setText(file_path)

    # ------------------------------------------------------------------
    # 2. oldal: Megjelenítés
    # ------------------------------------------------------------------
    def _build_appearance_page(self) -> None:
        layout = QVBoxLayout(self._page_appearance)

        # Nézet mód (kártya / lista)
        view_group = QGroupBox("Nézet mód", self._page_appearance)
        view_layout = QVBoxLayout(view_group)

        self.rb_view_cards = QRadioButton("Kártyanézet", view_group)
        self.rb_view_list = QRadioButton("Listanézet", view_group)

        view_layout.addWidget(self.rb_view_cards)
        view_layout.addWidget(self.rb_view_list)

        layout.addWidget(view_group)

        # Téma (standard / modern)
        theme_group = QGroupBox("Téma", self._page_appearance)
        theme_layout = QVBoxLayout(theme_group)

        self.rb_theme_standard = QRadioButton("Klasszikus (standard)", theme_group)
        self.rb_theme_modern = QRadioButton("Modern (style.css)", theme_group)

        theme_layout.addWidget(self.rb_theme_standard)
        theme_layout.addWidget(self.rb_theme_modern)

        layout.addWidget(theme_group)

        # Kártyanézet opciók
        cards_group = QGroupBox("Kártyanézet beállításai", self._page_appearance)
        cards_layout = QVBoxLayout(cards_group)

        self.chk_show_cover_on_card = QCheckBox(
            "Borító megjelenítése a kártyákon",
            cards_group,
        )
        cards_layout.addWidget(self.chk_show_cover_on_card)

        # ÚJ: hover-effekt
        self.chk_hover_effect = QCheckBox(
            "Hover-effekt engedélyezése (kártyák + lista)",
            cards_group,
        )
        self.chk_hover_effect.setToolTip(

                "Ha be van kapcsolva, a kártyák és a lista-sorok finom, "
                "3D-s kiemelést kapnak egér fölé húzáskor."

        )
        cards_layout.addWidget(self.chk_hover_effect)

        layout.addWidget(cards_group)

        layout.addStretch(1)




    # ------------------------------------------------------------------
    # 3. oldal: Naplózás
    # ------------------------------------------------------------------
    def _build_logging_page(self) -> None:
        layout = QVBoxLayout(self._page_logging)

        log_group = QGroupBox("Naplózás beállításai", self._page_logging)
        log_layout = QFormLayout(log_group)

        # Globális naplókapcsoló
        self.chk_logging_enabled = QCheckBox(
            "Naplózás engedélyezése",
            log_group,
        )

        # Konzol / fájl log kapcsolók
        self.chk_log_to_console = QCheckBox("Konzol naplózás engedélyezése", log_group)
        self.chk_log_to_file = QCheckBox("Fájl naplózás engedélyezése", log_group)

        # Log szint – DEBUG/INFO/WARNING/ERROR
        self.cmb_log_level = QComboBox(log_group)
        self.cmb_log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])

        # Tooltip magyarázattal
        self.cmb_log_level.setToolTip(
            "Naplózási szint:\n"
            "DEBUG: nagyon részletes fejlesztői napló (hibakereséshez)\n"
            "INFO: általános események (ajánlott)\n"
            "WARNING: gyanús, de nem kritikus problémák\n"
            "ERROR: csak hibák naplózása"
        )

        # Régi névhez alias, hogy _load_settings / _save_settings működjön
        self.combo_log_level = self.cmb_log_level

        # SQL lekérdezések naplózása – ha az adatbázis réteg támogatja
        self.chk_log_sql = QCheckBox("SQL lekérdezések naplózása", log_group)

        # Sorrend a form layoutban
        log_layout.addRow(self.chk_logging_enabled)
        log_layout.addRow(self.chk_log_to_console)
        log_layout.addRow(self.chk_log_to_file)
        log_layout.addRow("Napló szint:", self.cmb_log_level)
        log_layout.addRow(self.chk_log_sql)

        layout.addWidget(log_group)

        # Logfájl helye (read-only információ)
        path_group = QGroupBox("Naplófájl", self._page_logging)
        path_layout = QVBoxLayout(path_group)

        if self._log_file_path:
            text = self._log_file_path
        else:
            text = "A naplófájl elérési útját a napló inicializálása határozza meg."

        self.lbl_log_path = QLabel(text, path_group)
        self.lbl_log_path.setWordWrap(True)
        path_layout.addWidget(self.lbl_log_path)

        layout.addWidget(path_group)
        layout.addStretch(1)

    # ------------------------------------------------------------------
    # 4. oldal: Fejlesztői
    # ------------------------------------------------------------------
    def _build_developer_page(self) -> None:
        layout = QVBoxLayout(self._page_developer)

        # Fejlesztői mód
        self.chk_developer_mode = QCheckBox(
            "Fejlesztői mód (extra naplók, hibakeresési információk)",
            self._page_developer,
        )
        layout.addWidget(self.chk_developer_mode)

        # Fejlesztői naplózás
        dev_log_group = QGroupBox("Fejlesztői naplózás", self._page_developer)
        dev_log_layout = QVBoxLayout(dev_log_group)

        self.chk_debug_logging = QCheckBox(
            "Debug naplózás engedélyezése (DEBUG szint)",
            dev_log_group,
        )
        self.chk_dev_log_sql = QCheckBox(
            "SQL lekérdezések naplózása fejlesztői módban",
            dev_log_group,
        )

        dev_log_layout.addWidget(self.chk_debug_logging)
        dev_log_layout.addWidget(self.chk_dev_log_sql)
        layout.addWidget(dev_log_group)

        # Kísérleti funkciók (ha szeretnéd használni)
        experimental_group = QGroupBox("Kísérleti funkciók", self._page_developer)
        experimental_layout = QVBoxLayout(experimental_group)

        self.chk_enable_experimental = QCheckBox(
            "Kísérleti funkciók engedélyezése",
            experimental_group,
        )
        self.chk_experimental_cover = QCheckBox(
            "Kísérleti: Borító megjelenítése kártya nézetben (teszt)",
            experimental_group,
        )

        experimental_layout.addWidget(self.chk_enable_experimental)
        experimental_layout.addWidget(self.chk_experimental_cover)

        layout.addWidget(experimental_group)
        layout.addStretch(1)

    # ------------------------------------------------------------------
    # Beállítások betöltése / mentése
    # ------------------------------------------------------------------
    def _load_settings(self) -> None:
        s = self._settings

        # --- Általános: adatbázis elérési útja ---
        db_path = s.value("db_path", "", str)
        if isinstance(db_path, str) and db_path:
            self.edt_db_path.setText(db_path)

        # --- Megjelenítés: téma + nézet + borító a kártyán ---

        # Téma: próbáljuk először a gyökér "theme"-et, ha nincs, akkor a "General/theme"-et.
        theme = s.value("theme", None)
        if theme is None:
            theme = s.value("General/theme", "modern")

        if theme == "standard":
            self.rb_theme_standard.setChecked(True)
        else:
            # alapértelmezés: modern
            self.rb_theme_modern.setChecked(True)

        # Nézet mód: kompatibilitás a "General/view_mode"-dal
        view_mode = s.value("view_mode", None)
        if view_mode is None:
            view_mode = s.value("General/view_mode", "cards")

        if view_mode == "list":
            self.rb_view_list.setChecked(True)
        else:
            self.rb_view_cards.setChecked(True)

        # Borító megjelenítése a kártyákon
        # Először az új kulcs: "General/show_cover_on_card",
        # ha nincs, akkor a régi gyökér "show_cover_on_card".
        show_cover = s.value("General/show_cover_on_card", None)
        if show_cover is None:
            show_cover = s.value("show_cover_on_card", False, bool)

        if isinstance(show_cover, str):
            show_cover_bool = show_cover.lower() in ("1", "true", "yes", "on")
        else:
            show_cover_bool = bool(show_cover)

        self.chk_show_cover_on_card.setChecked(show_cover_bool)

        # --- Naplózás ---
        logging_enabled = s.value("logging/enabled", True, bool)
        log_level = s.value("logging/level", "INFO")
        log_sql = s.value("logging/log_sql", False, bool)
        to_console = s.value("logging/to_console", False, bool)
        to_file = s.value("logging/to_file", True, bool)

        self.chk_logging_enabled.setChecked(logging_enabled)
        idx = self.combo_log_level.findText(log_level)
        if idx < 0:
            idx = self.combo_log_level.findText("INFO")
        self.combo_log_level.setCurrentIndex(idx)
        self.chk_log_sql.setChecked(log_sql)
        self.chk_log_to_console.setChecked(to_console)
        self.chk_log_to_file.setChecked(to_file)

        # --- Fejlesztői ---
        dev_mode = s.value("developer/mode", False, bool)
        debug_logging = s.value("developer/debug_logging", False, bool)
        dev_log_sql = s.value("developer/log_sql", False, bool)

        self.chk_developer_mode.setChecked(dev_mode)
        self.chk_debug_logging.setChecked(debug_logging)
        self.chk_dev_log_sql.setChecked(dev_log_sql)

        # Kísérleti funkciók (ha használod)
        enable_experimental = s.value("developer/enable_experimental", False, bool)
        experimental_cover = s.value("developer/experimental_cover", False, bool)

        self.chk_enable_experimental.setChecked(enable_experimental)
        self.chk_experimental_cover.setChecked(experimental_cover)

        # Hover effekt engedélyezése – QSettings-ből
        hover_enabled = s.value("ui/hover_effect_enabled", True, bool)
        self.chk_hover_effect.setChecked(hover_enabled)










    def _save_settings(self) -> None:
        s = self._settings

        # Adatbázis elérési útja
        db_path = self.edt_db_path.text().strip()
        if db_path:
            s.setValue("db_path", db_path)

        # Téma
        theme = "modern" if self.rb_theme_modern.isChecked() else "standard"
        s.setValue("theme", theme)
        # kompatibilitás, ha valahol "General/theme"-et olvasunk:
        s.setValue("General/theme", theme)

        # Alap nézet
        view_mode = "cards" if self.rb_view_cards.isChecked() else "list"
        s.setValue("view_mode", view_mode)
        # kompatibilitás a régi "General/view_mode"-dal:
        s.setValue("General/view_mode", view_mode)

        # Kártya borító – új kulcs + régi kulcs kompatibilitás miatt
        show_cover = self.chk_show_cover_on_card.isChecked()
        s.setValue("General/show_cover_on_card", show_cover)
        s.setValue("show_cover_on_card", show_cover)

        # Naplózás
        s.setValue("logging/enabled", self.chk_logging_enabled.isChecked())
        s.setValue("logging/level", self.combo_log_level.currentText())
        s.setValue("logging/log_sql", self.chk_log_sql.isChecked())
        s.setValue("logging/to_console", self.chk_log_to_console.isChecked())
        s.setValue("logging/to_file", self.chk_log_to_file.isChecked())

        # Fejlesztői beállítások
        s.setValue("developer/mode", self.chk_developer_mode.isChecked())
        s.setValue("developer/debug_logging", self.chk_debug_logging.isChecked())
        s.setValue("developer/log_sql", self.chk_dev_log_sql.isChecked())

        # Kísérleti funkciók
        s.setValue("developer/enable_experimental", self.chk_enable_experimental.isChecked())
        s.setValue("developer/experimental_cover", self.chk_experimental_cover.isChecked())

        # Hover-effekt mentése
        s.setValue("ui/hover_effect_enabled", self.chk_hover_effect.isChecked())

        # Biztonság kedvéért flush
        s.sync()




    # ------------------------------------------------------------------
    # OK gomb kezelése
    # ------------------------------------------------------------------
    def _on_accept(self) -> None:
        self._save_settings()
        self.accept()
