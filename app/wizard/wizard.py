#!/usr/bin/env python3

"""
Új bejegyzés varázsló (wizard) oldalai + fő AddItemWizard osztály.

Oldalak / ID-k:

0. oldal: TypeSelectPage      – Film / Sorozat
1. oldal: FilmModePage        – Helyi / Online (csak filmnél használjuk)
2. oldal: FilmBasicPage       – Film címe, Méret, Tárolás
3. oldal: FilmMetaPage        – Megjelenés éve, műfajok, Időtartam, Rész, Rész címe
4. oldal: FilmVideoPage       – Felbontás, Formátum
5. oldal: FilmAudioPage       – Hang, Felirat, Szolgáltató (online filmnél)
6. oldal: SeriesInfoPage      – Sorozat alapadatok
7. oldal: SeriesSeasonPage    – Sorozat típus + évadok száma
8. oldal: DetailsPage         – Alapadatok + több részes Részek mező
9. oldal: ExtraPage           – Egyéb adatok
10. oldal: SummaryPage        – Összegzés

"""

# --- Importok: -------

from __future__ import annotations

from enum import IntEnum
from typing import Any

from config import LOGGER, normalize_cover_path, resolve_cover_path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)
from utils.utils import parse_first_int

logger = LOGGER.getChild("Wizard")

class WizardPageId(IntEnum):
    TYPE_SELECT = 0          # TypeSelectPage – Film / Sorozat
    FILM_MODE = 1            # FilmModePage – Helyi / Online
    FILM_BASIC = 2           # FilmBasicPage
    FILM_META = 3            # FilmMetaPage
    FILM_PARTS = 4           # FilmPartsPage
    FILM_VIDEO = 5           # FilmVideoPage
    FILM_AUDIO = 6           # FilmAudioPage
    SERIES_INFO = 7          # SeriesInfoPage
    SERIES_SEASON = 8        # SeriesSeasonPage
    DETAILS = 9              # DetailsPage
    EXTRA = 10                # ExtraPage
    SUMMARY = 11             # SummaryPage – összegzés



# -------- HELPER függvények ---------------

def tune_spinbox(spin: QSpinBox) -> None:
    """Növeli a fel/le nyilak kattintható felületét."""
    spin.setMinimumWidth(90)
    spin.setButtonSymbols(QAbstractSpinBox.UpDownArrows)
    spin.setStyleSheet(
        """
        QSpinBox::up-button, QSpinBox::down-button {
            width: 25px;
        }
        """
    )






# ------------ HELPER függvények vége ------------------------



def build_cover_picker(parent: QWidget) -> tuple[QGroupBox, QLabel, QPushButton, QPushButton]:
    """Közös borítókép-választó blokk a wizard oldalaihoz."""
    cover_group = QGroupBox("Borítókép")
    cover_layout = QHBoxLayout(cover_group)

    lbl_cover_preview = QLabel("Nincs borító")
    lbl_cover_preview.setFixedSize(140, 200)
    lbl_cover_preview.setAlignment(Qt.AlignCenter)
    lbl_cover_preview.setScaledContents(True)
    cover_layout.addWidget(lbl_cover_preview)

    btn_layout = QVBoxLayout()
    btn_cover_browse = QPushButton("Tallózás…")
    btn_cover_clear = QPushButton("Eltávolítás")

    btn_cover_browse.clicked.connect(lambda: browse_cover_for_page(parent))
    btn_cover_clear.clicked.connect(lambda: clear_cover_for_page(parent))

    btn_layout.addWidget(btn_cover_browse)
    btn_layout.addWidget(btn_cover_clear)
    btn_layout.addStretch()
    cover_layout.addLayout(btn_layout)

    return cover_group, lbl_cover_preview, btn_cover_browse, btn_cover_clear


def browse_cover_for_page(page: QWidget) -> None:
    path, _ = QFileDialog.getOpenFileName(
        page,
        "Borítókép kiválasztása",
        "",
        "Képfájlok (*.jpg *.jpeg *.png *.webp *.bmp);;Minden fájl (*)",
    )
    if not path:
        return

    setattr(page, "_cover_path", path)
    update_cover_preview_for_page(page)


def clear_cover_for_page(page: QWidget) -> None:
    setattr(page, "_cover_path", None)
    update_cover_preview_for_page(page)


def update_cover_preview_for_page(page: QWidget) -> None:
    label = getattr(page, "lbl_cover_preview", None)

    if label is None:
        return

    cover_path = getattr(page, "_cover_path", None)

    if cover_path:
        resolved_cover_path = resolve_cover_path(cover_path)

        if resolved_cover_path and resolved_cover_path.is_file():
            pix = QPixmap(str(resolved_cover_path))
        else:
            pix = QPixmap()

        if not pix.isNull():
            label.setPixmap(pix)
            label.setText("")
            return

        label.setPixmap(QPixmap())
        label.setText("Nem sikerült betölteni a képet.")
        return

    label.setPixmap(QPixmap())
    label.setText("Nincs borító")



class AddItemWizard(QWizard):
    def __init__(self, dbm:Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.dbm = dbm

        self.setPage(WizardPageId.TYPE_SELECT, TypeSelectPage(self))
        self.setPage(WizardPageId.FILM_MODE, FilmModePage(self))
        self.setPage(WizardPageId.FILM_BASIC, FilmBasicPage(self))
        self.setPage(WizardPageId.FILM_META, FilmMetaPage(self))
        self.setPage(WizardPageId.FILM_PARTS, FilmPartsPage(self))
        self.setPage(WizardPageId.FILM_VIDEO, FilmVideoPage(self))
        self.setPage(WizardPageId.FILM_AUDIO, FilmAudioPage(self))
        self.setPage(WizardPageId.SERIES_INFO, SeriesInfoPage(self))
        self.setPage(WizardPageId.SERIES_SEASON, SeriesSeasonPage(self))
        self.setPage(WizardPageId.DETAILS, DetailsPage(self))
        self.setPage(WizardPageId.EXTRA, ExtraPage(self))
        self.setPage(WizardPageId.SUMMARY, SummaryPage(self))

        self.setStartId(WizardPageId.TYPE_SELECT)

        self.setWindowTitle("Új bejegyzés – varázsló")



    def collect_data(self) -> dict[str, Any]:
        """
        A wizard-ban megadott adatok összegyűjtése és egyetlen
        adatbázis-sor formájába öntése.

        A visszatérő dict kulcsai illeszkednek az EditDialog.save() által használt
        row-struktúrához, hogy a dbm.insert(row) gond nélkül működjön.
        """

        item_type = self.property("item_type") or "film"
        #film_mode = self.property("film_mode") or "local"





        # --- FILM ÁG ---

        if item_type == "film":


            title = str(self.property("title") or "").strip()
            year = parse_first_int(self.property("year"))
            size_raw = str(self.property("size_gb") or "").strip()
            storage = str(self.property("storage") or "").strip()
            cover_path = normalize_cover_path(self.property("cover_path"))

            genres = str(self.property("genres") or "").strip()
            duration_min = parse_first_int(self.property("duration_min"))

            is_part = bool(self.property("is_part"))
            part_number = self.property("part_number") if is_part else None
            part_title = (
                str(self.property("part_title") or "").strip() if is_part else ""
            )

            resolution = str(self.property("resolution") or "").strip()
            video_format = str(self.property("video_format") or "").strip()

            audio = str(self.property("audio") or "").strip()
            subtitle = str(self.property("subtitle") or "").strip()
            provider = str(self.property("provider") or "").strip()

            # Méret és időtartam string formátumba (DB-ben szövegként tároljuk)
            if size_raw:
                size_str = f"{size_raw} GB"
            else:
                size_str = ""

            duration_str = f"{duration_min} perc" if duration_min else ""

            is_multi = bool(self.property("is_multi_part"))

            row = {
                "type": "film",
                "title": title,
                "part": None if is_multi else part_number,
                "year": year,
                "is_seasonal": 0,
                "seasonal_type": self.get_seasonal_type(),   # ÚJ !!!
                "genre": genres,
                "duration": duration_str,
                "size": "" if is_multi else size_str,
                "storage_location": storage,
                "format_type": resolution,
                "format": video_format,
                "episode_title": "" if is_multi else part_title,
                "audio_tracks": audio,
                "subtitle_tracks": subtitle,
                "provider": provider,
                "cover_path": cover_path,
                "parts_count": int(self.property("parts_count") or 1),
                "storage_breakdown": self.property("storage_breakdown") or [],
            }
            return row







        # --- SOROZAT ÁG ---

        # Cím: a DetailsPage-en megadott cím elsőbbséget élvez
        title_field = str(self.field("title") or "").strip()
        series_title = str(self.property("series_title") or "").strip()
        title = title_field or series_title

        # Megjelenés év: a kezdő év
        start_year = self.property("series_start_year")
        year = parse_first_int(start_year)

        # Műfaj: DetailsPage-ről
        genres = str(self.field("genre") or "").strip()

        # Évadok száma – csak összegzéshez kell, a DB-ben nem "méret" lesz.
        #seasons_count = self.property("series_season_count")

        # Tárolás, felbontás, formátum (DetailsPage)
        storage = str(self.field("storage") or "").strip()
        cover_path = normalize_cover_path(self.property("cover_path"))
        resolution = str(self.field("resolution") or "").strip()   # pl. "1080p"
        format_txt = str(self.field("length") or "").strip() # sorozatnál: Formátum mező (Pl. "MKV")

        # SOROZATNÁL:
        # - Időtartam (duration) legyen üres
        # - Méret (size) legyen üres
        # - Felbontás (format_type) → pl. "1080p"
        # - Formátum / konténer (format) → pl. "MKV"
        row = {
            "type": "sorozat",
            "title": title,
            "part": None,
            "year": year,
            "is_seasonal": 0,
            "seasonal_type": self.get_seasonal_type(),   # ÚJ !!!
            "genre": genres,
            "duration": "",          # NEM töltjük sorozatnál
            "size": "",              # NEM töltjük sorozatnál
            "storage_location": storage,
            "format_type": resolution,   # "1080p"
            "format": format_txt,        # "MKV"
            "episode_title": "",
            "audio_tracks": "",
            "subtitle_tracks": "",
            "provider": "",
            "cover_path": cover_path,
        }
        return row




    def get_seasonal_type(self) -> str:
        """Karácsonyi / Szilveszteri / mindkettő / egyik sem."""
        page = self.page(WizardPageId.EXTRA)
        christmas = page.chk_christmas.isChecked()
        newyear = page.chk_newyear.isChecked()

        if christmas and newyear:
            return "mindkettő"
        if christmas:
            return "karácsonyi"
        if newyear:
            return "szilveszteri"
        return "none"




    # Mentés:
    def accept(self) -> None:
        """
        Befejezés gomb – adatok összegyűjtése és beszúrás az adatbázisba.
        """
        try:
            row = self.collect_data()
            logger.debug("Wizard collect_data() → %r", row)

            title = (row.get("title") or "").strip()
            if not title:
                QMessageBox.warning(self, "Hiba", "A cím mező megadása kötelező.")
                return

            item_type = (row.get("type") or "").lower()

            if item_type == "sorozat":
                # Hány évadot adott meg a felhasználó?
                # 1) SeriesInfoPage spinbox (series_seasons property)
                seasons = parse_first_int(self.property("series_seasons"))

                # 2) ha valamiért ez nincs meg, próbáljuk a SeriesSeasonPage-et
                if seasons is None or seasons <= 0:
                    try:
                        series_page = self.page(WizardPageId.SERIES_SEASON)
                        seasons = parse_first_int(series_page.season_edit.text())
                    except Exception:
                        seasons = None

                # 3) ha továbbra sincs értelmes szám, legyen legalább 1
                if seasons is None or seasons <= 0:
                    seasons = 1

                inserted = 0
                for season in range(1, seasons + 1):
                    season_row = dict(row)          # alapadatok másolása
                    season_row["part"] = season     # 1., 2., 3. évad, ...

                    # Később EditDialogból tudod módosítani külön
                    # az Időtartam / Méret mezőket évadonként.
                    self.dbm.insert(season_row)
                    inserted += 1

                logger.info(
                    "Új sorozat beszúrva a wizardból: %s (%s) – %s évad sor beszúrva",
                    title,
                    row.get("year"),
                    inserted,
                )

            else:
                # FILM: ha parts_count > 1, akkor részenként külön rekordot szúrunk be
                try:
                    parts_count = int(row.get("parts_count") or 1)
                except Exception:
                    parts_count = 1
                parts_count = max(1, parts_count)

                breakdown = self.property("storage_breakdown") or []
                if not isinstance(breakdown, list):
                    breakdown = []

                by_part: dict[int, dict[str, Any]] = {}
                for it in breakdown:
                    if isinstance(it, dict) and "part" in it:
                        try:
                            by_part[int(it["part"])] = it
                        except Exception:
                            pass

                if parts_count > 1:
                    inserted = 0
                    for part_no in range(1, parts_count + 1):
                        part_row = dict(row)
                        part_row["part"] = part_no
                        part_row["parts_count"] = parts_count

                        it = by_part.get(part_no, {})
                        part_row["episode_title"] = str(it.get("subtitle") or "").strip()

                        size_gb = it.get("size_gb")
                        if size_gb is not None and str(size_gb).strip() != "":
                            part_row["size"] = f"{size_gb} GB"
                        else:
                            part_row["size"] = ""

                        loc = str(it.get("loc") or "").strip()
                        if loc:
                            part_row["storage_location"] = loc

                        self.dbm.insert(part_row)
                        inserted += 1

                    logger.info(
                        "Új többrészes film beszúrva a wizardból: %s (%s) – %s rész sor beszúrva",
                        title,
                        row.get("year"),
                        inserted,
                    )
                else:
                    self.dbm.insert(row)
                    logger.info(
                        "Új bejegyzés beszúrva a wizardból: %s (%s)",
                        title,
                        row.get("year"),
                    )


        except Exception as e:
            logger.exception("Hiba a wizard mentés közben")
            QMessageBox.critical(
                self,
                "Hiba",
                f"Nem sikerült elmenteni az új bejegyzést.\n\n{e}",
            )
            return

        # Ha idáig eljutottunk, minden rendben → zárjuk a varázslót
        super().accept()













# ---- 0.oldal: ------ Film / Sorozat oldal ----------

class TypeSelectPage(QWizardPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Tartalom típusa")
        self.setSubTitle("Válaszd ki, hogy filmet vagy sorozatot szeretnél felvenni.")

        self.film_radio = QRadioButton("Film")
        self.series_radio = QRadioButton("Sorozat")
        self.film_radio.setChecked(True)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Mit szeretnél felvenni?"))
        layout.addWidget(self.film_radio)
        layout.addWidget(self.series_radio)
        layout.addStretch()
        self.setLayout(layout)

    def validatePage(self) -> bool:
        """
        Itt elmentjük a wizard szintű state-et: 'film' vagy 'sorozat'.
        """
        if self.film_radio.isChecked():
            self.wizard().setProperty("item_type", "film")
        else:
            self.wizard().setProperty("item_type", "sorozat")
        return True

    def nextId(self) -> int:
        """
        Ha film, megyünk a FilmModePage-re,
        ha sorozat, ugrunk a SeriesInfoPage-re.
        """
        item_type = self.wizard().property("item_type")
        if item_type == "sorozat":
            return WizardPageId.SERIES_INFO
        return WizardPageId.FILM_MODE








# -------- 1. oldal – Film módja: helyi fájl vagy online. ----------

class FilmModePage(QWizardPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Film módja")
        self.setSubTitle("Add meg, hogy helyi fájlként vagy online forrásként kezeled a filmet.")

        self.local_radio = QRadioButton("Helyi (saját fájl)")
        self.online_radio = QRadioButton("Online (streaming, link, stb.)")
        self.local_radio.setChecked(True)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Válaszd ki a film módját:"))
        layout.addWidget(self.local_radio)
        layout.addWidget(self.online_radio)
        layout.addStretch()
        self.setLayout(layout)

    def validatePage(self) -> bool:
        """
        Elmentjük a kiválasztott film módot: 'local' vagy 'online'.
        """
        if self.local_radio.isChecked():
            self.wizard().setProperty("film_mode", "local")
        else:
            self.wizard().setProperty("film_mode", "online")
        return True

    def nextId(self) -> int:
        """
        Következő oldal: FilmBasicPage.
        """
        return WizardPageId.FILM_BASIC







# ------- 2.oldal: – Film alapadatok: cím, méret, tárolás.

class FilmBasicPage(QWizardPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Film alapadatok")
        self.setSubTitle("Add meg a film alapvető adatait.")

        self.title_edit = QLineEdit()
        self.size_edit = QLineEdit()
        self.storage_edit = QLineEdit()
        self._cover_path: str | None = None

        self.title_edit.setPlaceholderText("Pl.: A remény rabjai")
        self.size_edit.setPlaceholderText("Pl.: 2.1 (GB)")
        self.storage_edit.setPlaceholderText("Pl.: NAS / külső HDD / mappa elérési út")

        form = QFormLayout()
        form.addRow("Cím:", self.title_edit)
        form.addRow("Méret (GB):", self.size_edit)
        form.addRow("Tárolás / hely:", self.storage_edit)

        (
            self.cover_group,
            self.lbl_cover_preview,
            self.btn_cover_browse,
            self.btn_cover_clear,
        ) = build_cover_picker(self)

        form.addRow(self.cover_group)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addStretch()
        self.setLayout(layout)

    def validatePage(self) -> bool:
        """
        Az itt megadott adatokat wizard-szinten eltároljuk.
        """
        title = self.title_edit.text().strip()
        if not title:
            self.title_edit.setFocus()
            return False

        self.wizard().setProperty("title", title)
        self.wizard().setProperty("size_gb", self.size_edit.text().strip())
        self.wizard().setProperty("storage", self.storage_edit.text().strip())
        self.wizard().setProperty("cover_path", self._cover_path or "")
        return True

    def initializePage(self) -> None:
        self._cover_path = str(self.wizard().property("cover_path") or "").strip() or None
        update_cover_preview_for_page(self)

    def nextId(self) -> int:
        """
        Következő oldal: FilmMetaPage.
        """
        return WizardPageId.FILM_META







# -------- 3.oldal: Film részletes metaadatok:
#    megjelenés éve, műfaj(ok), időtartam, rész-információk.

class FilmMetaPage(QWizardPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Film részletes adatok")
        self.setSubTitle("Add meg a film részletes adatait (év, műfaj, időtartam, rész).")

        # --- Widgetek ---
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1900, 2100)
        self.year_spin.setValue(2000)
        tune_spinbox(self.year_spin)

        self.genres_edit = QLineEdit()
        self.genres_edit.setPlaceholderText("Pl.: Dráma, Thriller")

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 1000)
        self.duration_spin.setSuffix(" perc")
        tune_spinbox(self.duration_spin)


        self.is_part_combo = QComboBox()
        self.is_part_combo.addItems(["Nem", "Igen"])

        self.part_number_spin = QSpinBox()
        self.part_number_spin.setRange(1, 999)
        self.part_number_spin.setEnabled(False)
        tune_spinbox(self.part_number_spin)

        self.part_title_edit = QLineEdit()
        self.part_title_edit.setPlaceholderText("Pl.: 1. rész – A kezdet")
        self.part_title_edit.setEnabled(False)

        # Rész mezők engedélyezése a lenyíló alapján
        self.is_part_combo.currentIndexChanged.connect(self._on_part_changed)

        # --- Layout ---
        form = QFormLayout()
        form.addRow("Megjelenés éve:", self.year_spin)
        form.addRow("Műfaj(ok):", self.genres_edit)
        form.addRow("Időtartam:", self.duration_spin)
        form.addRow("Többrészes film?", self.is_part_combo)
        form.addRow("Részek száma:", self.part_number_spin)
        form.addRow("Rész címe:", self.part_title_edit)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addStretch()
        self.setLayout(layout)

    def _on_part_changed(self, index: int) -> None:
        """
        Ha 'Igen' a választás, engedélyezzük a rész/epizód mezőket.
        """
        is_part = index == 1  # 0 = Nem, 1 = Igen
        self.part_number_spin.setEnabled(is_part)
        self.part_title_edit.setEnabled(is_part)

    def initializePage(self) -> None:
        """
        Oldal megnyitásakor hívódik – szinkronizáljuk a mezők engedélyezését.
        """
        self._on_part_changed(self.is_part_combo.currentIndex())

    def validatePage(self) -> bool:
        """
        Metaadatok elmentése wizard-szintű property-ként.
        """
        self.wizard().setProperty("year", self.year_spin.value())
        self.wizard().setProperty("genres", self.genres_edit.text().strip())
        self.wizard().setProperty("duration_min", self.duration_spin.value())

        # Nálad ez jelenti a többrészes filmet
        is_multi = self.is_part_combo.currentIndex() == 1
        self.wizard().setProperty("is_multi_part", is_multi)

        if is_multi:
            # A spinbox értéke = részek száma
            self.wizard().setProperty("parts_count", int(self.part_number_spin.value()))
        else:
            self.wizard().setProperty("parts_count", 1)
            # ha visszalépés volt, töröljük az esetleg korábban felvitt részeket
            self.wizard().setProperty("storage_breakdown", [])

        # (Opcionális) meghagyhatod a régi property-ket kompatibilitás miatt,
        # de innentől a "part_number" ne legyen üzleti logika része.
        self.wizard().setProperty("is_part", is_multi)
        if is_multi:
            self.wizard().setProperty("part_number", self.part_number_spin.value())
            self.wizard().setProperty("part_title", self.part_title_edit.text().strip())
        else:
            self.wizard().setProperty("part_number", None)
            self.wizard().setProperty("part_title", "")

        return True


    def nextId(self) -> int:
        """
        Következő oldal: FilmVideoPage.
        """
        is_multi = self.is_part_combo.currentIndex() == 1
        return WizardPageId.FILM_PARTS if is_multi else WizardPageId.FILM_VIDEO






# -----4.oldal: Részek:

class FilmPartsPage(QWizardPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Részek adatai")
        self.setSubTitle("Add meg a részek alcímét, méretét és tárolási helyét.")

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Rész", "Alcím", "Méret (GB)", "Tárolás"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        self.setLayout(layout)

    def initializePage(self) -> None:
        w = self.wizard()
        parts_count = int(w.property("parts_count") or 1)
        parts_count = max(1, parts_count)

        # meglévő (visszalépésnél) adatok betöltése
        existing = w.property("storage_breakdown") or []
        if not isinstance(existing, list):
            existing = []

        by_part = {}
        for it in existing:
            if isinstance(it, dict) and "part" in it:
                try:
                    by_part[int(it["part"])] = it
                except Exception:
                    pass

        self.table.setRowCount(parts_count)

        for i in range(parts_count):
            part_no = i + 1

            item_part = QTableWidgetItem(str(part_no))
            item_part.setFlags(item_part.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 0, item_part)

            it = by_part.get(part_no, {})

            subtitle = QTableWidgetItem(str(it.get("subtitle") or ""))
            self.table.setItem(i, 1, subtitle)

            size_val = it.get("size_gb")
            size_txt = "" if size_val is None else str(size_val)
            size_item = QTableWidgetItem(size_txt)
            self.table.setItem(i, 2, size_item)

            loc_item = QTableWidgetItem(str(it.get("loc") or ""))
            self.table.setItem(i, 3, loc_item)

        self.table.resizeColumnsToContents()

    def validatePage(self) -> bool:
        # összegyűjtjük a breakdown listát
        breakdown: list[dict[str, Any]] = []
        for row in range(self.table.rowCount()):
            part_no = row + 1

            subtitle = (self.table.item(row, 1).text().strip()
                        if self.table.item(row, 1) else "")
            size_txt = (self.table.item(row, 2).text().strip()
                        if self.table.item(row, 2) else "")
            loc = (self.table.item(row, 3).text().strip()
                   if self.table.item(row, 3) else "")

            entry: dict[str, Any] = {"part": part_no}
            if subtitle:
                entry["subtitle"] = subtitle

            if size_txt:
                try:
                    entry["size_gb"] = round(float(size_txt.replace(",", ".")), 2)
                except Exception:
                    QMessageBox.warning(
                        self,
                        "Hiba",
                        f"A(z) {part_no}. rész mérete nem szám: '{size_txt}'",
                    )
                    return False

            if loc:
                entry["loc"] = loc

            # csak akkor tegyük bele, ha van bármilyen adat
            if len(entry.keys()) > 1:
                breakdown.append(entry)

        self.wizard().setProperty("storage_breakdown", breakdown)
        return True

    def nextId(self) -> int:
        return WizardPageId.FILM_VIDEO


# ------ 5.oldal: Videó adatok:
#  ------  felbontás, formátum / konténer.

class FilmVideoPage(QWizardPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Videó adatok")
        self.setSubTitle("Add meg a film videóval kapcsolatos adatait.")

        # --- Widgetek ---
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(
            [
                "",
                "480p",
                "576p",
                "720p",
                "1080p",
                "1440p",
                "4K",
                "8K",
            ]
        )

        self.format_combo = QComboBox()
        self.format_combo.setEditable(True)
        self.format_combo.addItems(
            [
                "",
                "MP4",
                "MKV",
                "AVI",
                "MOV",
                "WMV",
                "MPEG",
            ]
        )

        # Placeholder a szerkeszthető mezőhöz
        self.format_combo.setCurrentText("")

        form = QFormLayout()
        form.addRow("Felbontás:", self.resolution_combo)
        form.addRow("Videó formátum / konténer:", self.format_combo)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addStretch()
        self.setLayout(layout)

    def validatePage(self) -> bool:
        """
        Videó adatok elmentése wizard-szinten.
        """
        resolution = self.resolution_combo.currentText().strip()
        video_format = self.format_combo.currentText().strip()

        self.wizard().setProperty("resolution", resolution)
        self.wizard().setProperty("video_format", video_format)
        return True

    def nextId(self) -> int:
        """
        Következő oldal: FilmAudioPage.
        """
        return WizardPageId.FILM_AUDIO







# ---- 6.oldal: Audio és felirat adatok.
# ------  Helyi filmnél: hang + felirat.
# ---------- Online filmnél: hang + felirat + szolgáltató.

class FilmAudioPage(QWizardPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Audio és felirat")
        self.setSubTitle(
            "Add meg a film hang- és feliratinformációit. "
            "Online filmnél a szolgáltatót is."
        )

        self.audio_edit = QLineEdit()
        self.audio_edit.setPlaceholderText("Pl.: magyar 5.1, angol 2.0")

        self.subtitle_edit = QLineEdit()
        self.subtitle_edit.setPlaceholderText("Pl.: magyar, angol")

        self.provider_edit = QLineEdit()
        self.provider_edit.setPlaceholderText("Pl.: Netflix, HBO Max…")

        form = QFormLayout()
        form.addRow("Hang:", self.audio_edit)
        form.addRow("Felirat:", self.subtitle_edit)
        form.addRow("Szolgáltató (csak online film):", self.provider_edit)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addStretch()
        self.setLayout(layout)

    def initializePage(self) -> None:
        """
        A film módjától függően engedélyezés.
        """
        film_mode = self.wizard().property("film_mode")
        is_online = film_mode == "online"

        self.provider_edit.setEnabled(is_online)
        if not is_online:
            self.provider_edit.clear()

    def validatePage(self) -> bool:
        """
        Adatok tárolása wizard-szinten.
        """
        self.wizard().setProperty("audio", self.audio_edit.text().strip())
        self.wizard().setProperty("subtitle", self.subtitle_edit.text().strip())

        film_mode = self.wizard().property("film_mode")
        if film_mode == "online":
            self.wizard().setProperty("provider", self.provider_edit.text().strip())
        else:
            self.wizard().setProperty("provider", "")

        return True

    def nextId(self) -> int:
        """
        Film esetén ez az utolsó oldal → itt akár vissza is adhatnál -1-et,
        de a mostani flow-ban külön SummaryPage van, ezért:
        """
        return WizardPageId.EXTRA







# -- 7.oldal: Sorozat alapadatok:
# ------  cím, év, műfaj(ok), évadok száma, megjegyzés.

class SeriesInfoPage(QWizardPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Sorozat alapadatok")
        self.setSubTitle("Add meg a sorozat fő adatait.")

        # --- Widgetek ---
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Pl.: Breaking Bad")

        self.start_year_spin = QSpinBox()
        self.start_year_spin.setRange(1900, 2100)
        self.start_year_spin.setValue(2008)
        tune_spinbox(self.start_year_spin)

        self.end_year_spin = QSpinBox()
        self.end_year_spin.setRange(1900, 2100)
        self.end_year_spin.setValue(2013)
        tune_spinbox(self.end_year_spin)

        self.finished_check = QCheckBox("Befejezett sorozat")
        self.finished_check.setChecked(True)
        self.finished_check.toggled.connect(self._on_finished_toggled)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "Egyéb megjegyzés a sorozatról (nem kötelező)."
        )
        self._cover_path: str | None = None

        # --- Layout ---
        form = QFormLayout()
        form.addRow("Sorozat címe:", self.title_edit)
        form.addRow("Kezdő év:", self.start_year_spin)
        form.addRow("Befejező év:", self.end_year_spin)
        form.addRow("Befejezve:", self.finished_check)
        form.addRow("Megjegyzés:", self.notes_edit)

        (
            self.cover_group,
            self.lbl_cover_preview,
            self.btn_cover_browse,
            self.btn_cover_clear,
        ) = build_cover_picker(self)

        form.addRow(self.cover_group)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addStretch()
        self.setLayout(layout)

    def _on_finished_toggled(self, checked: bool) -> None:
        """
        Ha nincs befejezve, a befejező év mező inaktív.
        """
        self.end_year_spin.setEnabled(checked)

    def validatePage(self) -> bool:
        """
        A megadott sorozat-adatokat wizard property-ként tároljuk.
        """
        title = self.title_edit.text().strip()
        if not title:
            self.title_edit.setFocus()
            return False

        start_year = int(self.start_year_spin.value())
        finished = self.finished_check.isChecked()
        end_year = int(self.end_year_spin.value()) if finished else 0

        w = self.wizard()
        w.setProperty("series_title", title)
        w.setProperty("series_start_year", start_year)
        w.setProperty("series_end_year", end_year)
        w.setProperty("series_finished", finished)
        w.setProperty("series_notes", self.notes_edit.toPlainText().strip())
        w.setProperty("cover_path", self._cover_path or "")
        return True

    def initializePage(self) -> None:
        self._cover_path = str(self.wizard().property("cover_path") or "").strip() or None
        update_cover_preview_for_page(self)

    def nextId(self) -> int:
        """
        Következő oldal: SeriesSeasonPage.
        """
        return WizardPageId.SERIES_SEASON















# ---- 8.oldal:  Sorozat típus + évadok száma

class SeriesSeasonPage(QWizardPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Sorozat adatai")
        self.setSubTitle("Add meg az évadok számát és a sorozat típusát.")

        layout = QFormLayout()

        # Sorozat típusa
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Normál sorozat", "Minisorozat"])

        # Évadok száma
        self.season_edit = QLineEdit()
        self.season_edit.setPlaceholderText("Pl.: 3")

        layout.addRow("Sorozat típusa:", self.type_combo)
        layout.addRow("Évadok száma:", self.season_edit)

        self.setLayout(layout)

    def validatePage(self) -> bool:
        """Érvényesíti, hogy az évadok száma szám legyen, és elmenti property-ként."""
        val = self.season_edit.text().strip()

        if not val.isdigit():
            QMessageBox.warning(
                self,
                "Hiba",
                "Az évadok számának egy pozitív egész számnak kell lennie."
            )
            return False

        seasons_count = int(val)
        w = self.wizard()
        w.setProperty("series_type", self.type_combo.currentText().strip())
        w.setProperty("series_season_count", seasons_count)
        return True

    def nextId(self) -> int:
        """Tovább lép a következő oldalra (DetailsPage)."""
        return WizardPageId.DETAILS









# ----- 9.oldal: Alapadatok + több részes mezők

class DetailsPage(QWizardPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Alapadatok")
        self.setSubTitle("Add meg a film / sorozat alapadatait.")

        form = QFormLayout()

        # Cím
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Kötelező mező")

        # Eredeti cím (nem kötelező)
        self.orig_title_edit = QLineEdit()
        self.orig_title_edit.setPlaceholderText("Opcionális")

        # Év
        self.year_edit = QLineEdit()
        self.year_edit.setPlaceholderText("Pl.: 2020")

        # Hossz (alapértelmezésben percben – filmnél így marad)
        self.length_edit = QLineEdit()
        self.length_edit.setPlaceholderText("Pl.: 120")

        # Műfaj (saját kategória)
        self.genre_combo = QComboBox()
        self.genre_combo.setEditable(True)
        self.genre_combo.setInsertPolicy(QComboBox.NoInsert)
        self.genre_combo.addItems(
            [
                "",
                "Akció",
                "Vígjáték",
                "Dráma",
                "Sci-fi",
                "Animáció",
                "Dokumentum",
            ]
        )

        # Tárolás
        self.storage_edit = QLineEdit()
        self.storage_edit.setPlaceholderText("Pl.: HDD1, NAS, Blu-ray, stb.")

        # Felbontás
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["", "SD", "720p", "1080p", "4K"])

        # Több részes jelölő (csak filmnél érdekes)
        self.multi_part_check = QCheckBox("Több részes (pl. 2 részben)")
        # Részek mező (csak ha be van pipálva)
        self.parts_edit = QLineEdit()
        self.parts_edit.setPlaceholderText("Pl.: 1–2 vagy 1–3, 5")
        self.parts_edit.setEnabled(False)

        self.multi_part_check.toggled.connect(self.parts_edit.setEnabled)

        # Mezők felvétele az űrlapra
        form.addRow("Cím:", self.title_edit)
        form.addRow("Eredeti cím:", self.orig_title_edit)
        form.addRow("Év:", self.year_edit)
        form.addRow("Hossz (perc):", self.length_edit)
        form.addRow("Műfaj:", self.genre_combo)
        form.addRow("Tárolás:", self.storage_edit)
        form.addRow("Felbontás:", self.resolution_combo)
        form.addRow(self.multi_part_check)
        form.addRow("Részek:", self.parts_edit)

        self.setLayout(form)
        self.form_layout = form  # később kell a labelForField-hez

        # Field-ek regisztrálása
        self.registerField("title*", self.title_edit)
        self.registerField("orig_title", self.orig_title_edit)
        self.registerField("year", self.year_edit)
        self.registerField("length", self.length_edit)
        self.registerField("genre", self.genre_combo, "currentText", "currentTextChanged")
        self.registerField("storage", self.storage_edit)
        self.registerField("resolution", self.resolution_combo, "currentText", "currentTextChanged")
        self.registerField("multi_part", self.multi_part_check)
        self.registerField("parts", self.parts_edit)

    def initializePage(self) -> None:
        """
        Itt döntjük el, hogy filmről vagy sorozatról van szó.
        Sorozat esetén elrejtjük a második 'Cím' mezőt és az 'Év' mezőt,
        valamint a 'Több részes' részt.
        """
        item_type = self.wizard().property("item_type") or "film"

        # Film: minden mező látszik, 'Hossz (perc)'
        if item_type == "film":
            # visszakapcsoljuk, ha előzőleg sorozat volt
            for w in (
                self.title_edit,
                self.year_edit,
                self.multi_part_check,
                self.parts_edit,
            ):
                w.setVisible(True)

            # cím + év label vissza
            lbl_title = self.form_layout.labelForField(self.title_edit)
            if lbl_title:
                lbl_title.setVisible(True)
            lbl_year = self.form_layout.labelForField(self.year_edit)
            if lbl_year:
                lbl_year.setVisible(True)

            # hossz label vissza „Hossz (perc):”
            lbl_length = self.form_layout.labelForField(self.length_edit)
            if lbl_length:
                lbl_length.setText("Hossz (perc):")

        else:
            # --- SOROZAT ÁG ---

            # A már megadott sorozat címet ide automatikusan bemásoljuk,
            # de a mezőt elrejtjük, hogy ne láss újabb "Cím" mezőt.
            series_title = self.wizard().property("series_title") or ""
            self.title_edit.setText(str(series_title))

            # Cím + Év + Több részes + Részek elrejtése
            lbl_title = self.form_layout.labelForField(self.title_edit)
            if lbl_title:
                lbl_title.setVisible(False)
            self.title_edit.setVisible(False)

            lbl_year = self.form_layout.labelForField(self.year_edit)
            if lbl_year:
                lbl_year.setVisible(False)
            self.year_edit.setVisible(False)

            self.multi_part_check.setVisible(False)
            lbl_parts = self.form_layout.labelForField(self.parts_edit)
            if lbl_parts:
                lbl_parts.setVisible(False)
            self.parts_edit.setVisible(False)

            # A hossz mezőt sorozatnál inkább formátumként használjuk
            lbl_length = self.form_layout.labelForField(self.length_edit)
            if lbl_length:
                lbl_length.setText("Formátum:")
            self.length_edit.setPlaceholderText("Pl.: MKV, MP4, AVI vagy '45 perc/epizód'")

    def validatePage(self) -> bool:
        """
        Filmnél: cím kötelező, év/hossz ha meg van adva, legyen szám.
        Sorozatnál: a címet már korábban megadtuk, itt nem kérjük újra,
        nem ellenőrizzük az évet és a hossz/formátumot.
        """
        item_type = self.wizard().property("item_type") or "film"

        title = self.title_edit.text().strip()
        year = self.year_edit.text().strip()
        length = self.length_edit.text().strip()

        if item_type == "film":
            if not title:
                QMessageBox.warning(self, "Hiba", "A cím megadása kötelező.")
                return False

            if year and not year.isdigit():
                QMessageBox.warning(self, "Hiba", "Az év mezőnek számnak kell lennie (pl. 2020).")
                return False

            if length and not length.isdigit():
                QMessageBox.warning(
                    self,
                    "Hiba",
                    "A hossz mezőnek számnak kell lennie percben (pl. 120).",
                )
                return False

        # Sorozatnál nem tartunk szigorú ellenőrzést ezen az oldalon.
        return True

    def nextId(self) -> int:
        """
        Következő oldal:
        - filmnél: ExtraPage (Egyéb adatok),
        - sorozatnál: közvetlenül az összegzés (ExtraPage kimarad).
        """
        item_type = self.wizard().property("item_type") or "film"
        if item_type == "sorozat":
            return WizardPageId.SUMMARY
        return WizardPageId.EXTRA











# ---------- 10.oldal: Egyéb adatok ------

class ExtraPage(QWizardPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Egyéb adatok")
        self.setSubTitle("Add meg a további, opcionális információkat.")

        layout = QFormLayout()

        # Rendező
        self.director_edit = QLineEdit()
        self.director_edit.setPlaceholderText("Pl.: Ridley Scott")

        # Szereplők
        self.actors_edit = QLineEdit()
        self.actors_edit.setPlaceholderText("Főbb szereplők vesszővel elválasztva")

        # IMDB azonosító / link
        self.imdb_edit = QLineEdit()
        self.imdb_edit.setPlaceholderText("Pl.: tt1234567 vagy teljes URL")

        # Megnézve jelölő
        self.watched_check = QCheckBox("Már megnézve")

        # Értékelés (1–10)
        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(0, 10)
        self.rating_spin.setSpecialValueText("Nincs megadva")
        self.rating_spin.setValue(0)

        # Megjegyzés / saját komment
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Saját megjegyzések, kommentek…")

        layout.addRow("Rendező:", self.director_edit)
        layout.addRow("Szereplők:", self.actors_edit)
        layout.addRow("IMDB:", self.imdb_edit)
        layout.addRow(self.watched_check)
        layout.addRow("Értékelés (1–10):", self.rating_spin)
        layout.addRow("Megjegyzés:", self.notes_edit)

        self.setLayout(layout)


        # --- Vízszintes elválasztó vonal ---
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addRow(line)

        # --- Szezonális jelölők ---
        self.chk_christmas = QCheckBox("Karácsonyi")
        self.chk_newyear = QCheckBox("Szilveszteri")

        # Két checkbox egymás mellett
        seasonal_layout = QHBoxLayout()
        seasonal_layout.addWidget(self.chk_christmas)
        seasonal_layout.addWidget(self.chk_newyear)
        seasonal_layout.addStretch()

        layout.addRow("Időszakos:", seasonal_layout)

        # Field regisztrálása, hogy SummaryPage is lássa (nem kötelező, de hasznos)
        self.registerField("christmas", self.chk_christmas)
        self.registerField("newyear", self.chk_newyear)


        # Field-ek regisztrálása
        self.registerField("director", self.director_edit)
        self.registerField("actors", self.actors_edit)
        self.registerField("imdb", self.imdb_edit)
        self.registerField("watched", self.watched_check)
        self.registerField("rating", self.rating_spin)
        self.registerField("notes", self.notes_edit, "plainText", "textChanged")

    def validatePage(self) -> bool:
        """Itt most csak minimális ellenőrzést végzünk."""
        return True

    def nextId(self) -> int:
        """Következő oldal: összegző oldal."""
        return WizardPageId.SUMMARY












# ---------- 11.oldal: Összegzés -----------

class SummaryPage(QWizardPage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Összegzés")
        self.setSubTitle("Ellenőrizd az adatokat a mentés előtt.")

        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()
        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addStretch()
        self.setLayout(self.main_layout)

    def _clear_layout(self, layout: QLayout) -> None:
        """Segédfüggvény: kiüríti a layoutot, hogy initializePage-ben újra tudjuk építeni."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def initializePage(self) -> None:
        """Az oldal megnyitásakor összegyűjti az előző oldalak adatait és kiírja."""
        self._clear_layout(self.form_layout)

        def add_row(label: str, value: str, allow_empty: bool = False) -> None:
            val = (value or "").strip()
            if val or allow_empty:
                lbl = QLabel(val if val else "–")
                lbl.setWordWrap(True)
                self.form_layout.addRow(label, lbl)

        item_type = self.wizard().property("item_type") or "film"

        # DetailsPage field-jei (általános kijelzéshez)
        title = self.field("title") or ""
        orig_title = self.field("orig_title") or ""
        year = self.field("year") or ""
        length = self.field("length") or ""
        genre = self.field("genre") or ""
        storage = self.field("storage") or ""
        resolution = self.field("resolution") or ""

        if item_type == "film":
            # ---- FILM ÖSSZEGZÉS ----
            add_row("Cím:", title)
            add_row("Eredeti cím:", orig_title)
            add_row("Év:", year)
            add_row("Hossz:", length)
            add_row("Műfaj:", genre)
            add_row("Tárolás:", storage)
            add_row("Felbontás:", resolution)

            # Többrészes FILM: a FilmMetaPage property-i az igazság forrásai
            w = self.wizard()
            is_multi = bool(w.property("is_multi_part"))
            try:
                parts_count = int(w.property("parts_count") or 1)
            except Exception:
                parts_count = 1

            multi = is_multi or (parts_count > 1)
            add_row("Több részes:", "Igen" if multi else "Nem", allow_empty=True)
            if multi:
                add_row("Részek száma:", str(parts_count), allow_empty=True)

            # ExtraPage field-jei (filmhez)
            director = self.field("director") or ""
            actors = self.field("actors") or ""
            imdb = self.field("imdb") or ""
            watched = bool(self.field("watched"))
            rating = int(self.field("rating") or 0)
            film_notes = self.field("notes") or ""

            add_row("Rendező:", director)
            add_row("Szereplők:", actors)
            add_row("IMDB:", imdb)
            add_row("Már megnézve:", "Igen" if watched else "Nem", allow_empty=True)
            add_row(
                "Értékelés (1–10):",
                "Nincs megadva" if rating == 0 else str(rating),
                allow_empty=True,
            )

            # Időszakos jelölés
            is_christmas = bool(self.field("christmas"))
            is_newyear = bool(self.field("newyear"))
            if is_christmas or is_newyear:
                labels: list[str] = []
                if is_christmas:
                    labels.append("🎄 Karácsonyi")
                if is_newyear:
                    labels.append("🎆 Szilveszteri")
                add_row("Időszakos:", ", ".join(labels))

            film_notes = film_notes.strip()
            if film_notes:
                notes_label = QLabel(film_notes)
                notes_label.setWordWrap(True)
                self.form_layout.addRow("Megjegyzés:", notes_label)

        else:
            # ---- SOROZAT ÖSSZEGZÉS ----
            w = self.wizard()
            series_title = w.property("series_title") or ""
            start_year = int(w.property("series_start_year") or 0)
            end_year = int(w.property("series_end_year") or 0)
            finished = bool(w.property("series_finished"))
            series_notes = w.property("series_notes") or ""
            series_type = str(w.property("series_type") or "")
            seasons_count = int(w.property("series_season_count") or 0)

            title_to_show = title or series_title

            add_row("Cím:", title_to_show)
            if orig_title:
                add_row("Eredeti cím:", orig_title)

            if start_year:
                add_row("Megjelenés éve:", str(start_year))
            if end_year:
                add_row("Befejezés éve:", str(end_year))
            add_row("Befejezett:", "Igen" if finished else "Nem")

            add_row("Műfaj:", genre)
            add_row("Tárolás:", storage)
            add_row("Felbontás:", resolution)

            if seasons_count:
                add_row("Évadok száma:", str(seasons_count))
                add_row("Több évados:", "Igen" if seasons_count > 1 else "Nem")

            if series_type:
                add_row("Sorozat típusa:", series_type)

            series_notes = (series_notes or "").strip()
            if series_notes:
                notes_label = QLabel(series_notes)
                notes_label.setWordWrap(True)
                self.form_layout.addRow("Megjegyzés:", notes_label)



    def isFinalPage(self) -> bool:
        """Ez az utolsó oldal, innen már csak a Befejezés gomb aktív."""
        return True
