#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fő ablak:
- menüsor (Fájl / Adatok / Súgó)
- bal oldali navigáció (Kezdőoldal / Adatbázis)
- jobb oldalon stack (kezdő HTML + adatbázis oldal)
- adatbázis oldalon: kártya / lista nézet váltás
"""

from __future__ import annotations

from typing import Any, Dict, List
import os
import shutil
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QGridLayout,
    QSizePolicy,
    QStackedWidget,
    QTextBrowser,
    QFileDialog,
    QLineEdit,
    QDialog,
    QDialogButtonBox,
    QMessageBox,
    QApplication,
    QToolBar,
    QToolButton,
    QMenu,
)
from PySide6.QtGui import QAction, QIcon, QActionGroup
from PySide6.QtCore import Qt, QEvent, QTimer, QSettings

from config import (
    APP_NAME,
    APP_DISPLAY_NAME,
    APP_VERSION,
    APP_ORG,
    ICON_PATH, 
    DB_PATH, 
    ui, 
    USE_WIZARD_FOR_NEW, 
    LOG_PATH
)

from db import DatabaseManager
from wizard.wizard import AddItemWizard
from dialogs.edit_dialog import EditDialog
from views.movie_card import MovieCard
from dialogs.log_window import LogWindow
from views.list_view import ListViewWidget
from dialogs.settings_dialog import SettingsDialog
from themes.theme_utils import apply_theme_from_settings
from dialogs.details_dialog import ModernDetailDialog


# --------------------------------------------------------------------------------------------------

CHRISTMAS_ALIASES = {
    "karácsonyi", "karacsonyi", "karácsony", "karacsony", "christmas", "xmas",
}

NEWYEAR_ALIASES = {
    "szilveszteri", "szilveszter", "newyear", "new_year", "new-year",
}

BOTH_ALIASES = {
    "mindkettő", "both", "karácsony+szilveszter", "mixed",
}

# --------------------------------------------------------------------------------------------------







LOGGER = logging.getLogger("FilmekAdatbazis")




class MainWindow(QMainWindow):
    def __init__(self, dbm: DatabaseManager):
        super().__init__()
        self.db = dbm          # kompatibilitásért
        self.dbm = dbm         # új név
        self.all_rows: List[Dict[str, Any]] = []
        self.grouped: Dict[str, List[Dict[str, Any]]] = {}


        # --- UI beállítások (hover, stb.) ---
        self.hover_effect_enabled = True  # alapértelmezés
        self.load_ui_settings()

        # --- Induló nézet beolvasása QSettings-ből ---
        settings = QSettings(APP_ORG, APP_NAME)
        saved_view = settings.value("view_mode", "cards")
        if isinstance(saved_view, str) and saved_view in ("cards", "list"):
            self.current_db_view = saved_view
        else:
            self.current_db_view = "cards"



        self.view_toolbar = QToolBar("Nézet", self)
        self.view_toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, self.view_toolbar)


        # Ablak alap
        self.setWindowTitle(f"{APP_DISPLAY_NAME} {APP_VERSION}")
        self.resize(1500, 900)   # 1.érték: X tengely, 2.érték: Y tengely
        self.setWindowIcon(QIcon(str(ICON_PATH)))

        # Menüsor
        menubar = self.menuBar()

        # - Fájl menü
        file_menu = menubar.addMenu("Fájl")

        act_new = QAction("Új", self)
        act_new.triggered.connect(self.on_add_clicked)
        file_menu.addAction(act_new)

        settings_action = QAction("Beállítások…", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()
        act_quit = QAction("Kilépés", self)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # - Adatok menü
        data_menu = menubar.addMenu("Adatok")
        act_import = QAction("Importálás...", self)
        act_import.triggered.connect(self.import_db)
        act_export = QAction("Exportálás...", self)
        act_export.triggered.connect(self.export_db)
        data_menu.addAction(act_import)
        data_menu.addAction(act_export)

        # - Súgó menü
        help_menu = menubar.addMenu("Súgó")
        act_topics = QAction("Témakörök", self)
        act_topics.triggered.connect(self.show_topics)
        act_about = QAction("Névjegy", self)
        act_about.triggered.connect(self.show_about)
        help_menu.addAction(act_topics)
        help_menu.addAction(act_about)

        act_changelog = QAction("Változásnapló…", self)
        act_changelog.triggered.connect(self.show_changelog)
        help_menu.addAction(act_changelog)

        log_action = QAction("Log megnyitása", self)
        log_action.triggered.connect(self.open_log_window)
        help_menu.addAction(log_action)



        # Központi elrendezés: bal navigáció + jobb stack
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(12)

        # Bal oldal: gombok
        left = QVBoxLayout()
        self.btn_home = QPushButton("Kezdőoldal")
        self.btn_db = QPushButton("Adatbázis")
        left.addWidget(self.btn_home)
        left.addWidget(self.btn_db)
        left.addStretch()
        root.addLayout(left)

        # Jobb oldal: stack
        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        # Kezdőoldal (HTML)
        self.home = QTextBrowser()
        self.home.setHtml(
            """
            <h1>Filmek Adatbázis</h1>
            <p>Üdvözöl a helyi, offline film/sorozat katalógus. Bal oldalt válaszd az „Adatbázis” lapot.</p>
            <ul>
              <li><b>Fájl → Új</b>: új film/sorozat (vagy rész/évad) felvétele</li>
              <li><b>Adatok → Importálás/Exportálás</b>: teljes adatbázis mentése/helyreállítása</li>
              <li><b>Súgó</b>: témakörök, névjegy, változásnapló</li>
            </ul>
            """
        )
        self.stack.addWidget(self.home)

        # --- Adatbázis oldal ---
        self.db_page = QWidget()
        db_v = QVBoxLayout(self.db_page)
        db_v.setContentsMargins(8, 8, 8, 8)
        db_v.setSpacing(6)

        # keresősáv
        filter_row = QHBoxLayout()
        filter_label = QLabel("Keresés:")
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(
            "Írj be címet, műfajt, tárolást, felbontást…"
        )
        self.filter_edit.textChanged.connect(self.apply_filter)
        filter_row.addWidget(filter_label)
        filter_row.addWidget(self.filter_edit)
        db_v.addLayout(filter_row)


        # Nézetváltó akciók (kártya / lista)
        self.act_view_cards = QAction("Kártyanézet", self)
        self.act_view_list = QAction("Lista nézet", self)
        self.act_view_cards.setCheckable(True)
        self.act_view_list.setCheckable(True)

        view_group = QActionGroup(self)
        view_group.setExclusive(True)
        view_group.addAction(self.act_view_cards)
        view_group.addAction(self.act_view_list)


        self.filter_type = "all"          # "all" | "movie" | "series"
        self.filter_quality = set()       # pl. {"4k", "1080p"} ; üres = mind
        self.filter_seasonal = set()      # pl. {"karacsonyi", "szilveszteri"} ; üres = mind



        # Induláskori állapot a beállítások alapján
        if self.current_db_view == "list":
            self.act_view_list.setChecked(True)
            self.act_view_cards.setChecked(False)
            initial_button_text = "Lista nézet"
        else:
            self.act_view_cards.setChecked(True)
            self.act_view_list.setChecked(False)
            initial_button_text = "Kártyanézet"

        # Lenyíló gomb – KERESŐ ALATT, jobb oldalon
        self.view_mode_button = QToolButton()
        self.view_mode_button.setText(initial_button_text)
        self.view_mode_button.setPopupMode(QToolButton.InstantPopup)



        # --- Típus szűrő (Filmek / Sorozatok / Mind)
        self.type_group = QActionGroup(self)
        self.type_group.setExclusive(True)

        self.act_type_all = QAction("Mind", self, checkable=True)
        self.act_type_movies = QAction("Filmek", self, checkable=True)
        self.act_type_series = QAction("Sorozatok", self, checkable=True)

        self.type_group.addAction(self.act_type_all)
        self.type_group.addAction(self.act_type_movies)
        self.type_group.addAction(self.act_type_series)

        self.type_filter_button = QToolButton()

        # --- Típus szűrő lenyíló gomb ---
        self.type_filter_button.setText("Mind")
        self.type_filter_button.setPopupMode(QToolButton.InstantPopup)

        type_menu = QMenu(self.type_filter_button)
        type_menu.addAction(self.act_type_movies)
        type_menu.addAction(self.act_type_series)
        type_menu.addAction(self.act_type_all)
        self.type_filter_button.setMenu(type_menu)





        self.act_type_all.setChecked(True)


        # --- Minőség szűrő (multi-select) ---
        self.quality_filter_button = QToolButton()
        self.quality_filter_button.setText("Minőség: Mind")
        self.quality_filter_button.setPopupMode(QToolButton.InstantPopup)

        self.act_q_all = QAction("Mind", self, checkable=False)
        self.act_q_4k = QAction("4K", self, checkable=True)
        self.act_q_1080 = QAction("1080p", self, checkable=True)
        self.act_q_720 = QAction("720p", self, checkable=True)
        self.act_q_sd = QAction("SD", self, checkable=True)

        quality_menu = QMenu(self.quality_filter_button)
        quality_menu.addAction(self.act_q_all)
        quality_menu.addSeparator()
        quality_menu.addAction(self.act_q_4k)
        quality_menu.addAction(self.act_q_1080)
        quality_menu.addAction(self.act_q_720)
        quality_menu.addAction(self.act_q_sd)
        self.quality_filter_button.setMenu(quality_menu)

        self.act_q_all.triggered.connect(self.clear_quality_filter)
        self.act_q_4k.toggled.connect(lambda on: self.toggle_quality("4k", on))
        self.act_q_1080.toggled.connect(lambda on: self.toggle_quality("1080p", on))
        self.act_q_720.toggled.connect(lambda on: self.toggle_quality("720p", on))
        self.act_q_sd.toggled.connect(lambda on: self.toggle_quality("sd", on))





        # --- Időszakos szűrő (multi-select) ---
        self.seasonal_filter_button = QToolButton()
        self.seasonal_filter_button.setText("Időszakos: Mind")
        self.seasonal_filter_button.setPopupMode(QToolButton.InstantPopup)

        self.act_s_all = QAction("Mind", self, checkable=False)
        self.act_s_kar = QAction("Karácsonyi", self, checkable=True)
        self.act_s_szil = QAction("Szilveszteri", self, checkable=True)

        season_menu = QMenu(self.seasonal_filter_button)
        season_menu.addAction(self.act_s_all)
        season_menu.addSeparator()
        season_menu.addAction(self.act_s_kar)
        season_menu.addAction(self.act_s_szil)
        self.seasonal_filter_button.setMenu(season_menu)

        self.act_s_all.triggered.connect(self.clear_seasonal_filter)
        self.act_s_kar.toggled.connect(lambda on: self.toggle_seasonal("karacsonyi", on))
        self.act_s_szil.toggled.connect(lambda on: self.toggle_seasonal("szilveszteri", on))




















        self.act_type_movies.triggered.connect(lambda: self.set_type_filter("movie"))
        self.act_type_series.triggered.connect(lambda: self.set_type_filter("series"))
        self.act_type_all.triggered.connect(lambda: self.set_type_filter("all"))














        view_menu = QMenu(self.view_mode_button)
        view_menu.addAction(self.act_view_cards)
        view_menu.addAction(self.act_view_list)
        self.view_mode_button.setMenu(view_menu)

        # Kapcsolás a logikára (amikor majd megvan a listanézet stack):
        self.act_view_cards.triggered.connect(self.show_cards_view)
        self.act_view_list.triggered.connect(self.show_list_view)


        # Keresősáv alatti sor: nézetváltó + Mindent töröl (jobb oldalon)
        clear_row = QHBoxLayout()
        clear_row.setContentsMargins(0, 0, 0, 0)
        clear_row.setSpacing(8)

        #  itt már BIZTOSAN létezik clear_row, ide jöhetnek a gombok felrakása
        clear_row.addWidget(self.type_filter_button)
        clear_row.addWidget(self.quality_filter_button)
        clear_row.addWidget(self.seasonal_filter_button)

        # jobb oldalra tolás
        clear_row.addStretch(1)

        # Jobb oldali nézet + törlés
        clear_row.addWidget(self.view_mode_button)

        self.clear_db_button = QPushButton("Mindent töröl")
        self.clear_db_button.clicked.connect(self.on_clear_database)
        clear_row.addWidget(self.clear_db_button)


        # 3) és itt fűzöd be a fő layoutba
       # main_layout.addLayout(clear_row)



        clear_row.addStretch()
        clear_row.addWidget(self.type_filter_button)
        clear_row.addWidget(self.view_mode_button)



        # Szerkesztés gomb – mindig a DB nézet részeként
       # self.btn_edit_item = QPushButton("Szerkesztés…")
       # self.btn_edit_item.clicked.connect(self.on_edit_selected_item)
       # clear_row.addWidget(self.btn_edit_item)






        clear_row.addWidget(self.seasonal_filter_button)



        db_v.addLayout(clear_row)



        # --- Kártyanézet komponensei ---
        self.cards_holder = QWidget()
        self.cards_holder.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.cards_holder.setMinimumSize(0, 0)

        self.grid = QGridLayout(self.cards_holder)
        self.grid.setContentsMargins(6, 6, 6, 6)
        self.grid.setSpacing(12)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        self.grid.setColumnStretch(2, 1)
        self.grid.setSizeConstraint(QGridLayout.SetMinAndMaxSize)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setFocusPolicy(Qt.StrongFocus)
        self.scroll_area.setWidget(self.cards_holder)
        self.scroll_area.viewport().installEventFilter(self)




        # --- Lista nézet widget ---
        self.list_view = ListViewWidget(self.dbm, parent=self)
        # jobb klikk / menü: EditDialog
        if hasattr(self.list_view, "editRequested"):
            self.list_view.editRequested.connect(self.on_edit_item_from_list)

        # dupla kattintás: Részletek ablak
        if hasattr(self.list_view, "detailsRequested"):
            self.list_view.detailsRequested.connect(self.on_show_details_from_list)







        # --- Belső stack: kártyanézet vs. lista nézet ---
        self.db_views_stack = QStackedWidget()
        self.db_views_stack.addWidget(self.scroll_area)  # index 0 – kártya
        self.db_views_stack.addWidget(self.list_view)    # index 1 – lista
        self.db_views_stack.setCurrentIndex(0)

        db_v.addWidget(self.db_views_stack)

        # DB oldal a fő stack-be
        self.stack.addWidget(self.db_page)

        # Navigáció akciók
        self.btn_home.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_db.clicked.connect(self.show_db)

        # Start
        self.stack.setCurrentIndex(0)




        print("TOOLBARS:", [tb.windowTitle() for tb in self.findChildren(QToolBar)])










    def load_ui_settings(self) -> None:
        settings = QSettings(APP_ORG, APP_NAME)
        # bool típusra kérjük vissza
        self.hover_effect_enabled = settings.value(
            "ui/hover_effect_enabled",
            True,
            bool,
        )






    def _update_seasonal_button_text(self) -> None:
        if not self.filter_seasonal:
            self.seasonal_filter_button.setText("Időszakos: Mind")
        else:
            mapping = {"karacsonyi": "Karácsonyi", "szilveszteri": "Szilveszteri"}
            nice = ", ".join(mapping.get(x, x) for x in sorted(self.filter_seasonal))
            self.seasonal_filter_button.setText(f"Időszakos: {nice}")

    def toggle_seasonal(self, key: str, enabled: bool) -> None:
        if enabled:
            self.filter_seasonal.add(key)
        else:
            self.filter_seasonal.discard(key)
        self._update_seasonal_button_text()
        self.reload_data()

    def clear_seasonal_filter(self) -> None:
        self.filter_seasonal.clear()
        for act in (self.act_s_kar, self.act_s_szil):
            act.blockSignals(True)
            act.setChecked(False)
            act.blockSignals(False)
        self._update_seasonal_button_text()
        self.reload_data()







    # --- Beállítások ablak ---
    def open_settings_dialog(self) -> None:
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            app = QApplication.instance()
            if app is not None:
                apply_theme_from_settings(app)


            # UI beállítások (hover) újraolvasása
            self.load_ui_settings()

            # A mentett nézet beolvasása újra
            settings = QSettings(APP_ORG, APP_NAME)
            saved_view = settings.value("view_mode", "cards")
            if isinstance(saved_view, str) and saved_view in ("cards", "list"):
                self.current_db_view = saved_view
            else:
                self.current_db_view = "cards"

            # Adatok + kártyák újraépítése
            self.reload_data()

            if self.current_db_view == "list":
                self.show_list_view()
            else:
                self.show_cards_view()



    # --- Új felvétel varázslóval / sima dialógussal ---
    def on_add_clicked(self) -> None:
        """Fájl → Új menüpont. Kapcsolótól függően wizard vagy sima dialog."""
        if USE_WIZARD_FOR_NEW:
            wiz = AddItemWizard(self.dbm, parent=self)
            if wiz.exec() == QDialog.DialogCode.Accepted:
                QTimer.singleShot(0, self.reload_data)
        else:
            self.new_item()

    # --- Adatbázis oldal megjelenítése ---
    def show_db(self) -> None:
        if hasattr(self, "filter_edit"):
            self.filter_edit.blockSignals(True)
            self.filter_edit.clear()
            self.filter_edit.blockSignals(False)

        self.reload_data()
        self.stack.setCurrentIndex(1)

          # Belső nézet állapot az aktuális beállítás alapján
        if self.current_db_view == "list":
            self.show_list_view()
        else:
            self.show_cards_view()


    # --- Nézetváltás: kártya / lista ---
    def show_cards_view(self) -> None:
        self.current_db_view = "cards"
        if hasattr(self, "db_views_stack"):
            self.db_views_stack.setCurrentIndex(0)
        self.act_view_cards.setChecked(True)
        self.act_view_list.setChecked(False)
        self.view_mode_button.setText("Kártyanézet")


    def show_list_view(self) -> None:
        self.current_db_view = "list"
        if hasattr(self, "db_views_stack"):
            self.db_views_stack.setCurrentIndex(1)
        self.act_view_list.setChecked(True)
        self.act_view_cards.setChecked(False)
        self.view_mode_button.setText("Lista nézet")






    def set_type_filter(self, value: str) -> None:
        self.filter_type = value

        # ha van gomb (QToolButton) és azon a feliratot is akarod:
        if hasattr(self, "type_filter_button"):
            label = {"all": "Mind", "movie": "Filmek", "series": "Sorozatok"}.get(value, "Mind")
            self.type_filter_button.setText(label)


        # Mentés QSettings-be
        settings = QSettings(APP_ORG, APP_NAME)
        settings.setValue("filter/type", value)



        # ÚJRAÉPÍTÉS (ettől változik a GUI)
        self.reload_data()













    # --- Kijelölt elem szerkesztése (toolbar gomb) ---
    def on_edit_selected_item(self) -> None:
        # csak lista nézetben értelmes
        if self.current_db_view != "list":
            QMessageBox.information(
                self,
                "Szerkesztés",
                "Szerkeszteni a lista nézetben tudsz (dupla kattintás vagy ez a gomb).",
            )
            return

        if not hasattr(self.list_view, "get_selected_id"):
            return

        item_id = self.list_view.get_selected_id()
        if item_id is None:
            QMessageBox.information(self, "Szerkesztés", "Nincs kijelölt sor.")
            return

        self.on_edit_item_from_list(item_id)




    # --- Dupla kattintás / jelzés a ListViewWidget-ből ---
    def on_edit_item_from_list(self, item_id: int) -> None:
        LOGGER.debug("[MAIN editRequested] received id=%r", item_id)

        row = self.dbm.get_by_id(item_id)  # TELJES sor DB-ből
        if not row:
            QMessageBox.warning(
                self,
                "Szerkesztés",
                "Nem található a kijelölt sor az adatbázisban.",
            )
            return

        dlg = EditDialog(self.dbm, row=row, parent=self)
        if dlg.exec():
            self.reload_data()




    def on_save_notes_from_details(self, item_id: int, notes: str) -> None:
        """
        Megjegyzés mentése a részletek ablakból.
        """
        try:
            self.db.update(item_id, {"notes": notes})
        except Exception as e:
            LOGGER.exception("Megjegyzés mentése sikertelen (id=%s)", item_id)
            return

        # opcionális: UI frissítés
       # self.refresh_current_view()

        self.reload_data()





    def on_show_details_from_list(self, item_id: int) -> None:
        """
        Lista nézet – dupla kattintás → modern Részletek ablak.
        """
        ui_log = logging.getLogger("FilmekAdatbazis.ui")
        LOGGER.debug("[MAIN detailsRequested] received id=%r", item_id)

        # 1) Biztos forrás: DB
        row = self.dbm.get_by_id(item_id)
        if not row:
            QMessageBox.warning(self, "Részletek", f"Nem található a sor az adatbázisban (id={item_id}).")
            return

        if ui_log.isEnabledFor(logging.DEBUG):
            cover_path = row.get("cover_path") or row.get("cover_file") or row.get("cover")
            ui_log.debug(
                "[DETAILS OPEN/LIST] id=%r title=%r cover=%r keys=%s",
                row.get("id"),
                row.get("title"),
                cover_path,
                sorted([k for k in row.keys() if "cover" in k.lower()]),
            )

        from details_dialog import open_details_dialog
        open_details_dialog(self, row)












    def load_items_filtered(self):
        items = self.db.list_all_items()  # vagy ami nálad van

        # 1) Film/Sorozat
        if self.filter_type != "all":
            items = [x for x in items if (x.get("type") == self.filter_type)]

        # 2) Minőség (resolution mező alapján)
        if self.filter_quality != "all":
            items = [x for x in items if self._match_quality(x)]

        return items


    def _match_quality(self, row: Dict[str, Any]) -> bool:
        selected = getattr(self, "filter_quality", set()) or set()
        if not selected:
            return True

        # itt azt kell nézni, hogy nálad a DB-ben melyik mező hordozza a minőséget
        # tipikusan: row.get("format") vagy row.get("format_type") vagy row.get("resolution")
        raw = " ".join([
            str(row.get("format_type") or ""),
            str(row.get("format") or ""),
        ]).strip().lower()
        return any(q in raw for q in selected)



    def _match_seasonal(self, row: Dict[str, Any]) -> bool:
        selected = getattr(self, "filter_seasonal", set()) or set()
        if not selected:
            return True

        # itt attól függ, hogy később:
        # - lesz külön mező (pl. row["seasonal_tag"] = "karacsonyi"),
        # - vagy most csak boolean (is_seasonal)
        tag = (row.get("seasonal_tag") or "").strip().lower()   # jövőálló
        if tag:
            return tag in selected

        # ha még nincs tag, csak boolean:
        # akkor "időszakos" szűrés csak akkor passzoljon, ha row.is_seasonal True,
        # de ez nem tudja megkülönböztetni karácsony/szilveszter között
        is_seasonal = bool(row.get("is_seasonal"))
        return is_seasonal





    def _match_type(self, row: dict) -> bool:
        ft = getattr(self, "filter_type", "all")
        if ft == "all":
            return True

        t = (row.get("type") or "").strip().lower()

        if ft == "movie":
            return t in ("film", "movie")
        if ft == "series":
            return t in ("sorozat", "series")


        return True



    def _update_quality_button_text(self) -> None:
        if not self.filter_quality:
            self.quality_filter_button.setText("Minőség: Mind")
        else:
            nice = ", ".join(sorted(self.filter_quality))
            self.quality_filter_button.setText(f"Minőség: {nice}")

    def toggle_quality(self, key: str, enabled: bool) -> None:
        if enabled:
            self.filter_quality.add(key)
        else:
            self.filter_quality.discard(key)
        self._update_quality_button_text()
        self.reload_data()

    def clear_quality_filter(self) -> None:
        self.filter_quality.clear()
        # pipák törlése (blokkoljuk, hogy ne hívogassa egymást)
        for act in (self.act_q_4k, self.act_q_1080, self.act_q_720, self.act_q_sd):
            act.blockSignals(True)
            act.setChecked(False)
            act.blockSignals(False)
        self._update_quality_button_text()
        self.reload_data()


















    # --- Segéd: sor keresése ID alapján a cache-ben ---
    def _find_row_by_id(self, item_id: int) -> Dict[str, Any] | None:
        for r in self.all_rows:
            try:
                if int(r.get("id", -1)) == int(item_id):
                    return r
            except Exception:
                continue
        return None




    # --- Csoportosítás címenként (pontos egyezés) ---
    def group_by_title(self) -> None:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for r in self.all_rows:
            title = (r.get("title") or "").strip()
            if not title:
                continue
            grouped.setdefault(title, []).append(r)
        self.grouped = grouped







    # --- Görgő delegálása a scrollnak ---
    def eventFilter(self, obj, event):
        if (
            hasattr(self, "scroll_area")
            and obj == self.scroll_area.viewport()
            and event.type() == QEvent.Wheel
        ):
            self.scroll_area.verticalScrollBar().event(event)
            return True
        return super().eventFilter(obj, event)






        # --- Kereső (kártyák + lista) ---
    def apply_filter(self, text: str) -> None:
        t = (text or "").strip().lower()

        # Kártyák szűrése
        if hasattr(self, "_card_widgets"):
            if t:
                for card, keywords in self._card_widgets:
                    card.setVisible(t in keywords)
            else:
                for card, _ in self._card_widgets:
                    card.setVisible(True)

        # Lista nézet szűrése (ha támogatja)
        if hasattr(self, "list_view") and hasattr(self.list_view, "apply_filter"):
            self.list_view.apply_filter(t)




    def refresh_current_view(self) -> None:
        items = self.load_items_filtered()   # DB-ből vagy memóriából
        if self.is_list_view_active:
            self.list_view.set_items(items)
        else:
            self.cards_view.set_items(items)





    def clear_cards(self) -> None:
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w:
                w.setParent(None)




    def reload_data(self) -> None:
        try:
            self.cards_holder.setUpdatesEnabled(False)
        except Exception:
            pass

        try:
            rows = self.db.fetch_all()
            ui.debug("fetch_all → %d sor", len(rows))

            # Teljes cache (később más szűrőknek is jó)
            self._rows_cache = rows

            # Itt jön a TÍPUS (és később a minőség) szűrés:

            #filtered = [r for r in rows if self._match_type(r)]
            filtered = [
                r for r in rows
                if self._match_type(r) and self._match_quality(r) and self._match_seasonal(r)
            ]



            # ha már van minőségi szűrőd is, ide be lehet kötni:
            # filtered = [r for r in filtered if self._match_quality(r)]

            self.all_rows = filtered

            self.group_by_title()
            ui.debug("group_by_title → %d cím", len(self.grouped))

            self.populate_cards()

            # Lista nézet frissítés – ha tud fogadni items-t, akkor szűrten adjuk át
            if hasattr(self, "list_view"):
                if hasattr(self.list_view, "set_items"):
                    self.list_view.set_items(self.all_rows)
                elif hasattr(self.list_view, "reload_data"):
                    self.list_view.reload_data()

            # Kereső szöveg újra-alkalmazása, hogy a szűrés+keresés együtt működjön
            if hasattr(self, "filter_edit"):
                self.apply_filter(self.filter_edit.text())

        finally:
            try:
                self.cards_holder.setUpdatesEnabled(True)
                self.cards_holder.update()
            except Exception:
                pass









    # Kártyák építése:

    def populate_cards(self) -> int:
        ui.debug("Kártyák építése indul…")
        count = 0
        try:
            try:
                self.cards_holder.setUpdatesEnabled(False)
            except Exception:
                pass

            self.clear_cards()
            self._card_widgets: List[tuple[QWidget, str]] = []

            titles = sorted(self.grouped.keys(), key=lambda s: s.lower())
            cols = 3
            row = col = 0

            for title in titles:
                items = self.grouped[title]

                # --- Kártya létrehozása ---
                card = MovieCard(
                    title, items, main_window=self, parent=self.cards_holder
                )


                # ------------ COVER DEBUG (kártyaépítés) ------------

                first = items[0] if items else {}
                cover = (
                    first.get("cover_path")
                    or first.get("cover_file")
                    or first.get("cover")
                )
                ui.debug(
                    "[CARD BUILD] title=%r id=%r cover=%r cover_keys=%s",
                    first.get("title"),
                    first.get("id"),
                    cover,
                    [k for k in first.keys() if "cover" in k.lower()],
                )
                # --------------------------------------------------------------------





                # Opcionális, de nem árt:
                card.setMouseTracking(True)


                # DEBUG
               # print("CARD DEBUG:", card, 
                #      "name=", card.objectName(),
                #      "hover=", card.property("hoverEnabled"))






                # --- Hover stílushoz szükséges beállítások ---
                # objektumnév a QSS-hez (#movieCard selector)
                card.setObjectName("movieCard")

                # property a [hoverEnabled="true"] selectorhoz
                hover_enabled = bool(getattr(self, "hover_effect_enabled", True))
                card.setProperty("hoverEnabled", hover_enabled)

                # egérkövetés, hogy hover eseményre is frissüljön
                card.setMouseTracking(True)

                # QSS újraszámolása a property miatt
                style = card.style()
                style.unpolish(card)
                style.polish(card)

                # --- Kereshető szöveg felépítése (régi logika + seasonal) ---

                genres = " ".join({str(it.get("genre") or "") for it in items})
                storage = " ".join(
                    {str(it.get("storage_location") or "") for it in items}
                )
                fmt = " ".join({str(it.get("format_type") or "") for it in items})
                aud_kw = " ".join({str(it.get("audio_tracks") or "") for it in items})
                subs_kw = " ".join(
                    {str(it.get("subtitle_tracks") or "") for it in items}
                )
                prov_kw = " ".join({str(it.get("provider") or "") for it in items})




                # --- ÚJ: szezonális mezők hozzáadása a kereshető szöveghez ---
                seasonal_keywords: set[str] = set()

                for it in items:
                    st = (it.get("seasonal_type") or "").strip().lower()
                    if not st or st == "none":
                        continue

                    # Karácsonyi típusok → magyar kulcsszó is
                    if st in CHRISTMAS_ALIASES:
                        seasonal_keywords.add("karácsony")
                        seasonal_keywords.add("karácsonyi")

                    # Szilveszteri típusok
                    if st in NEWYEAR_ALIASES:
                        seasonal_keywords.add("szilveszter")
                        seasonal_keywords.add("szilveszteri")

                    # Nyers érték is (angol kereséshez)
                    seasonal_keywords.add(st)






                # Tag-ek is menjenek bele (ha használsz ilyet)
                for it in items:
                    tag = (it.get("seasonal_tag") or it.get("seasonal_type") or "").strip().lower()
                    if tag:
                        seasonal_keywords.add(tag)


                seasonal_kw = " ".join(sorted(seasonal_keywords)).strip()

                searchable = (
                    f"{title} {genres} {storage} {fmt} "
                    f"{aud_kw} {subs_kw} {prov_kw} {seasonal_kw}"
                ).lower()

                self._card_widgets.append((card, searchable))
                self.grid.addWidget(card, row, col)

                col += 1
                if col >= cols:
                    col = 0
                    row += 1

            # ha volt szűrőszöveg, akkor azt is újra alkalmazzuk
           # if hasattr(self, "filter_edit"):
           #     self.apply_filter(self.filter_edit.text())

            try:
                self.cards_holder.adjustSize()
            except Exception:
                pass

            count = len(self._card_widgets)
            ui.info("Felépült %d kártya", count)

        finally:
            try:
                self.cards_holder.setUpdatesEnabled(True)
            except Exception:
                pass

        return count




    # --- Régi "Új" (egyszerű EditDialog) – megtartjuk, ha kellene ---
    def new_item(self) -> None:
        dlg = EditDialog(self.db, row=None, parent=self)
        if dlg.exec():
            self.reload_data()

    # --- Import/Export (Adatok menü) ---
    def export_db(self) -> None:
        fname, _ = QFileDialog.getSaveFileName(
            self, "Exportálás", "movies_backup.db", "SQLite (*.db)"
        )
        if not fname:
            return
        try:
            shutil.copy2(DB_PATH, fname)
            QMessageBox.information(self, "Export", "Sikeres export.")
        except Exception as e:
            QMessageBox.critical(self, "Export hiba", str(e))

    def import_db(self) -> None:
        fname, _ = QFileDialog.getOpenFileName(
            self, "Importálás", "", "SQLite (*.db)"
        )
        if not fname:
            return

        try:
            # biztonsági mentés a jelenlegi DB-ről
            if DB_PATH.exists():
                bak_path = DB_PATH.parent / (DB_PATH.name + ".bak")
                shutil.copy2(DB_PATH, bak_path)

            # kiválasztott DB bemásolása a helyére
            shutil.copy2(fname, DB_PATH)

            # újracsatlakozás
            self.db.close()
            self.db.connect()
            self.reload_data()

            QMessageBox.information(self, "Import", "Sikeres import.")
        except Exception as e:
            QMessageBox.critical(self, "Import hiba", str(e))



    # --- Súgó menü (Témakörök, Névjegy, Változásnapló) ---
    def show_topics(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Súgó – Témakörök")
        dlg.resize(800, 560)
        v = QVBoxLayout(dlg)
        tb = QTextBrowser()
        tb.setHtml(
            """
            <h2>Témakörök</h2>
            <ul>
              <li><b>Film, több rész:</b> ugyanazzal a címmel több sor, a <i>Rész/Évad</i> mezőben a sorszám (1..N).</li>
              <li><b>Sorozat:</b> ugyanazzal a címmel több sor, a <i>Rész/Évad</i> mezőben az évad száma (1..N).</li>
              <li><b>Rész címe</b> (opcionális): az adott rész/film alcíme. A kártyacím ettől nem változik.</li>
              <li>A kártyán az összesítő (részek/évadok, év-tartomány, összméret) automatikusan számolódik.</li>
              <li><b>Részletek</b> ablakban tételes lista + szerkesztés/törlés a kijelölt elemre.</li>
            </ul>
            """
        )
        v.addWidget(tb)
        okb = QDialogButtonBox(QDialogButtonBox.Ok)
        okb.accepted.connect(dlg.accept)
        v.addWidget(okb)
        dlg.exec()


    # Névjegy:

    def show_about(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Névjegy")
        dlg.resize(420, 300)
        v = QVBoxLayout(dlg)
        tb = QTextBrowser()
        tb.setHtml(
            f"""
            <h2>{APP_NAME}</h2>
            <p>Helyi, offline Python/PySide6 alkalmazás.</p>
            <p>Verzió: {APP_VERSION}</p>
            <p>(kártyanézet, CRUD, import/export, autó keresés)</p>
            <p>Adatbázis: <code>{DB_PATH}</code></p>
            """
        )
        v.addWidget(tb)
        okb = QDialogButtonBox(QDialogButtonBox.Ok)
        okb.accepted.connect(dlg.accept)
        v.addWidget(okb)
        dlg.exec()





    def show_changelog(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Verziótörténet")
        dlg.resize(720, 560)

        v = QVBoxLayout(dlg)
        tb = QTextBrowser()

        # changelog.html betöltése a modul mappájából
        try:
            base = Path(__file__).resolve().parent
            path = base / "changelog.html"
            if path.exists():
                html = path.read_text(encoding="utf-8")
            else:
                html = (
                    f"<h1>Változásnapló</h1><p>Nem található: <code>{path}</code></p>"
                )
        except Exception as e:
            html = f"<h1>Változásnapló</h1><p>Hiba: <code>{e!r}</code></p>"

        tb.setHtml(html)
        v.addWidget(tb)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dlg.reject)
        buttons.accepted.connect(dlg.accept)
        v.addWidget(buttons)

        dlg.exec()

    def open_log_window(self):
        dlg = LogWindow(LOG_PATH, self)
        dlg.exec()

    def closeEvent(self, e):
        try:
            if hasattr(self, "db") and self.db:
                self.db.close()
        except Exception:
            pass
        super().closeEvent(e)








    def on_clear_database(self) -> None:
        """
        „Mindent töröl” gomb eseménykezelője.
        Megerősítés után kiüríti az adatbázist és frissíti az UI-t.
        """
        reply = QMessageBox.warning(
            self,
            "Adatbázis ürítése",
            (
                "Biztosan törölni szeretnéd az ÖSSZES filmet és sorozatot "
                "az adatbázisból?\n\n"
                "Ez a művelet NEM vonható vissza!"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            LOGGER.info("Adatbázis ürítés megszakítva a felhasználó által.")
            return

        try:
            deleted = self.dbm.clear_all_movies()

            # Memória / kártyák ürítése
            self.all_rows = []
            self.grouped = {}
            self.clear_cards()

            msg = f"Adatbázis ürítve. Törölt sorok: {deleted}."
            LOGGER.info(msg)

            sb = self.statusBar()
            if sb is not None:
                sb.showMessage(msg, 5000)

            QMessageBox.information(self, "Adatbázis ürítve", msg)

        except Exception as e:
            LOGGER.exception("Hiba az adatbázis ürítése közben")
            QMessageBox.critical(
                self,
                "Hiba",
                f"Nem sikerült üríteni az adatbázist.\n\n{e}",
            )