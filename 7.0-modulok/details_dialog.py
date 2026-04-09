#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
details_dialog.py – Movies 7.0 (letisztított modern részletek ablak)

Tartalom:
- InfoRow: kulcs–érték megjelenítő sor
- Modern tabok: Áttekintés, Videó, Hang/Felirat, Megjegyzés, Technikai
- ModernDetailDialog: egyetlen modern, tabos részletek dialógus
- open_details_dialog: egységes belépési pont
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional, Dict, List
import re

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QTextEdit,
    QPushButton,
    QFormLayout,
)

from pathlib import Path

LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Segédek
# ---------------------------------------------------------------------

def _load_cover_pixmap(movie: Mapping[str, Any]) -> Optional[QPixmap]:
    """
    cover_path/cover_file/cover → QPixmap (ha nincs/hibás, akkor None).
    """
    path = (
        (movie.get("cover_path") or "")
        or (movie.get("cover_file") or "")
        or (movie.get("cover") or "")
    )
    path = str(path).strip()
    if not path:
        return None

    pm = QPixmap(path)
    if pm.isNull():
        LOGGER.warning("Nem sikerült betölteni a borítóképet: %s", path)
        return None

    return pm


def _build_seasonal_label(movie: Mapping[str, Any]) -> str:
    """
    Időszakos badge felirat – ha van explicit seasonal_label, azt használjuk,
    különben az is_seasonal + cím/műfaj alapján próbálunk.
    """
    label = (movie.get("seasonal_label") or "").strip()
    if label:
        return label

    if not bool(movie.get("is_seasonal")):
        return ""

    title = (movie.get("title") or "").lower()
    genre = (movie.get("genre") or movie.get("genre_general") or "").lower()

    if "karácsony" in title or "karácsony" in genre:
        return "Időszakos: karácsonyi"
    if "szilveszter" in title or "szilveszter" in genre:
        return "Időszakos: szilveszteri"

    return "Időszakos tartalom"


def _human_type(movie: Mapping[str, Any]) -> str:
    raw = (movie.get("type") or "").strip().lower()
    if raw in ("movie", "film"):
        return "Film"
    if raw in ("series", "sorozat"):
        return "Sorozat"
    return raw.capitalize() if raw else "Ismeretlen"







_SIZE_RE = re.compile(r"^\s*([\d.,]+)\s*(tb|gb|mb)\s*$", re.IGNORECASE)

def _parse_size_text_to_gb(size_text: Optional[str]) -> Optional[float]:
    if not size_text:
        return None
    s = size_text.strip().lower().replace(",", ".")
    m = _SIZE_RE.match(s)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2).lower()
    if unit == "mb":
        return val / 1024.0
    if unit == "gb":
        return val
    if unit == "tb":
        return val * 1024.0
    return None



def _find_db_conn_from_widget(w: Any):
    """
    Visszaad egy sqlite3.Connection-t, ha talál a widget szülőláncban olyan objektumot,
    aminek van .db.conn attribútuma.
    """



    # 0) top-level ablakon (legbiztosabb)
    try:
        win = w.window() if hasattr(w, "window") else None
        if win is not None:
            db = getattr(win, "db", None)
            conn = getattr(db, "conn", None)
            if conn is not None:
                return conn
    except Exception:
        pass



    # 1) közvetlenül w-n
    try:
        db = getattr(w, "db", None)
        conn = getattr(db, "conn", None)
        if conn is not None:
            return conn
    except Exception:
        pass




    # 2) widget szülőlánc bejárása
    try:
        cur = w
        for _ in range(12):  # elég mély
            if cur is None:
                break
            db = getattr(cur, "db", None)
            conn = getattr(db, "conn", None)
            if conn is not None:
                return conn
            # Qt: parentWidget() vagy parent()
            nxt = None
            if hasattr(cur, "parentWidget"):
                nxt = cur.parentWidget()
            if nxt is None and hasattr(cur, "parent"):
                nxt = cur.parent()
            cur = nxt
    except Exception:
        pass

    return None







def _enrich_movie_with_parts(parent: Any, movie: Dict[str, Any]) -> None:
    """
    Többrészes FILM régi modellhez:
    - Ha ugyanarra a címre több sor van (>=2), akkor a Details-ben listázzuk részenként.
    - Ha a 'part' mező hiányos (NULL/0), szintetikus 1..N sorszámot adunk csak megjelenítéshez.
    A movie dict-be betesszük:
      movie["_parts_rows"]
      movie["_parts_total_gb"]
      movie["_parts_count_found"]
    """
    try:
        if (movie.get("type") or "").strip() != "film":
            return

        title = (movie.get("title") or "").strip()
        if not title:
            return

        conn = _find_db_conn_from_widget(parent)
        if conn is None:
            return

        cur = conn.cursor()
        try:
            # Ne szűrjünk part-ra itt – a part lehet NULL/0 régi adatoknál
            cur.execute(
                """
                SELECT id, part, year, size, storage_location, parts_count
                FROM movies
                WHERE type='film'
                  AND TRIM(title) = TRIM(?) COLLATE NOCASE
                ORDER BY id
                """,
                (title,),
            )
            rows = cur.fetchall()
        finally:
            cur.close()

        # Ha nincs legalább 2 rekord, nem tekintjük többrészesnek
        if len(rows) < 2:
            return

        # Döntsük el: tényleg többrészes-e?
        # (vagy van part valahol, vagy parts_count jelez)
        def _to_int(v) -> int:
            try:
                return int(v)
            except Exception:
                return 0

        movie_parts_count = _to_int(movie.get("parts_count") or 1)
        any_row_parts_count = any(_to_int(r[5]) > 1 for r in rows)
        any_has_part = any(_to_int(r[1]) > 0 for r in rows)

        if not (any_has_part or movie_parts_count > 1 or any_row_parts_count):
            # ugyanaz a cím többször, de nincs part/parts_count jelzés → ne csoportosítsunk
            return

        # Rendezés: ha van explicit part, akkor part szerint, különben id szerint
        if any_has_part:
            rows_sorted = sorted(rows, key=lambda r: (_to_int(r[1]) if _to_int(r[1]) > 0 else 999999, _to_int(r[0])))
        else:
            rows_sorted = sorted(rows, key=lambda r: _to_int(r[0]))

        total = 0.0
        parts_rows: List[Dict[str, Any]] = []

        # Szintetikus sorszám, ha nincs part
        synth = 1

        for rid, part, year, size, loc, pcount in rows_sorted:
            part_i = _to_int(part)
            if part_i <= 0:
                part_i = synth
                synth += 1

            parts_rows.append(
                {
                    "id": rid,
                    "part": part_i,
                    "year": year,
                    "size": size,
                    "storage_location": loc,
                }
            )

            gb = _parse_size_text_to_gb(size)
            if gb is not None:
                total += gb

        movie["_parts_rows"] = parts_rows
        movie["_parts_total_gb"] = round(total, 2)
        movie["_parts_count_found"] = len(parts_rows)

        # megjelenítéshez igazítsuk a parts_count-ot is
        if _to_int(movie.get("parts_count") or 1) < len(parts_rows):
            movie["parts_count"] = len(parts_rows)

        # opcionális debug:
        # print("[DETAILS enrich]", title, "rows=", len(parts_rows), "total=", movie["_parts_total_gb"])

    except Exception:
        return







def _format_gb(gb: Optional[float]) -> str:
    if gb is None:
        return ""
    # 2 tized, de kulturáltan (23.00 -> 23)
    s = f"{gb:.2f}".rstrip("0").rstrip(".")
    return f"{s} GB"


def _build_parts_lines(movie: Mapping[str, Any]) -> List[str]:
    rows = movie.get("_parts_rows")
    if not isinstance(rows, list) or not rows:
        return []
    lines: List[str] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        part = r.get("part")
        size = (r.get("size") or "").strip()
        loc = (r.get("storage_location") or "").strip()
        part_txt = f"{part}. rész" if part not in (None, "", 0) else "Rész"
        size_txt = size if size else "—"
        loc_txt = loc if loc else "—"
        lines.append(f"{part_txt} — {size_txt} — {loc_txt}")
    return lines





def _load_cover_pixmap(movie: Mapping[str, Any]) -> Optional[QPixmap]:
    path = (
        (movie.get("cover_path") or "")
        or (movie.get("cover_file") or "")
        or (movie.get("cover") or "")
    )
    path = str(path).strip()
    if not path:
        return None

    p = Path(path)

    # fallback: régi ékezetes projektmappa -> új ékezet nélküli
    if not p.exists():
        fixed = path.replace("Filmek-Adatbázis", "Filmek-Adatbazis")
        if fixed != path and Path(fixed).exists():
            path = fixed
            p = Path(path)

    pm = QPixmap(path)
    if pm.isNull():
        LOGGER.warning("Nem sikerült betölteni a borítóképet: %s", path)
        return None

    return pm







# ------ Segédek vége ------------





# ---------------------------------------------------------------------
# InfoRow
# ---------------------------------------------------------------------

class InfoRow(QWidget):
    """
    Újrafelhasználható egy soros „címke + érték” widget.
    """

    def __init__(
        self,
        label_text: str,
        value_text: str | None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("infoRow")

        self._label = QLabel(label_text)
        self._label.setObjectName("detailsLabel")
        self._label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._value = QLabel(value_text or "")
        self._value.setObjectName("detailsValue")
        self._value.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self._value.setWordWrap(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._label, 0)
        layout.addWidget(self._value, 1)

    def set_value(self, text: str | None) -> None:
        self._value.setText(text or "")

    def value(self) -> str:
        return self._value.text()








# ---------------------------------------------------------------------
# Tabok
# ---------------------------------------------------------------------

class ModernVideoTab(QWidget):
    def __init__(self, movie: Mapping[str, Any], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Videóinfók"))

        format_type = movie.get("format_type")
        if format_type:
            layout.addWidget(InfoRow("Felbontás:", str(format_type)))

        container = movie.get("format")
        if container:
            layout.addWidget(InfoRow("Konténer:", str(container)))

        aspect_ratio = movie.get("aspect_ratio")
        if aspect_ratio:
            layout.addWidget(InfoRow("Képarány:", str(aspect_ratio)))

        video_codec = movie.get("video_codec")
        if video_codec:
            layout.addWidget(InfoRow("Videó kodek:", str(video_codec)))

        video_bitrate = movie.get("video_bitrate")
        if video_bitrate:
            layout.addWidget(InfoRow("Bitráta:", str(video_bitrate)))

        frame_rate = movie.get("frame_rate")
        if frame_rate:
            layout.addWidget(InfoRow("Képfrissítés:", str(frame_rate)))

        layout.addStretch(1)


class ModernAudioTab(QWidget):
    def __init__(self, movie: Mapping[str, Any], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Hang és feliratok"))

        audio_tracks = movie.get("audio_tracks")
        if audio_tracks:
            layout.addWidget(InfoRow("Hang sávok:", str(audio_tracks)))

        subtitle_tracks = movie.get("subtitle_tracks")
        if subtitle_tracks:
            layout.addWidget(InfoRow("Feliratok:", str(subtitle_tracks)))

        layout.addStretch(1)


class ModernNotesTab(QWidget):
    """
    Megjegyzések tab:
      - Szerkeszthető QTextEdit
      - Placeholder csak vizuális segítség (nem kerül be tartalomként)
      - get_notes_text() helper a mentéshez
    """

    def __init__(self, movie: Mapping[str, Any], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._movie = movie

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Megjegyzések"))

        notes_raw = (
            movie.get("notes")
            or movie.get("comment")
            or movie.get("remarks")
            or ""
        )

        self.txt_notes = QTextEdit(self)
        self.txt_notes.setObjectName("detailsNotesEdit")
        self.txt_notes.setReadOnly(False)  # <- ez volt a blokkoló pont
        self.txt_notes.setPlaceholderText("Ide írhatsz megjegyzést ehhez a filmhez/sorozathoz…")
        self.txt_notes.setText(str(notes_raw).strip())
        layout.addWidget(self.txt_notes)

        layout.addStretch(1)

    def get_notes_text(self) -> str:
        """Mentéshez: tisztított notes szöveg (üresen is visszaadhat)."""
        return self.txt_notes.toPlainText().strip()


class ModernTechnicalTab(QWidget):
    TECH_FIELDS = [
        "id", "type", "part", "episode_title", "year", "end_year",
        "is_completed", "is_seasonal", "seasonal_label",
        "genre", "genre_general", "genre_official",
        "storage_location", "provider",
        "format_type", "format",
        "video_codec", "video_bitrate", "frame_rate", "aspect_ratio",
        "audio_tracks", "subtitle_tracks",
    ]

    def __init__(self, movie: Mapping[str, Any], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Technikai adatok"))

        for key in self.TECH_FIELDS:
            val = movie.get(key)
            if val in (None, "", [], {}):
                continue
            layout.addWidget(InfoRow(f"{key}:", str(val)))

        layout.addStretch(1)













# ---------------------------------------------------------------------
# ModernDetailDialog – egyetlen modern dialógus
# ---------------------------------------------------------------------

class ModernDetailDialog(QDialog):
    edit_requested = Signal(int)
    notes_save_requested = Signal(int, str)

    def __init__(self, movie: Mapping[str, Any], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._movie: Mapping[str, Any] = movie

        self.setModal(True)
        self.setObjectName("ModernDetailDialog")
        self.resize(1000, 800)  # X, Y

        self._init_ui()
        self._populate()

     #   self.setObjectName("infoRow")





    # --- UI váz
    def _init_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(12)

        # Top: cover + header
        top = QWidget(self)
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(0, 0, 0, 0)
        top_lay.setSpacing(16)

        # Cover
        self.lbl_cover = QLabel(top)
        self.lbl_cover.setObjectName("detailsCoverLabel")
        self.lbl_cover.setAlignment(Qt.AlignCenter)
        self.lbl_cover.setMinimumSize(220, 320)
        self.lbl_cover.setMaximumSize(260, 380)
        self.lbl_cover.setScaledContents(False)
        self.lbl_cover.setFrameShape(QFrame.NoFrame)
        self.lbl_cover.setStyleSheet("border: none; background: transparent;")

        # Header right
        header = QWidget(top)
        header.setObjectName("detailsHeader")
        header_lay = QVBoxLayout(header)
        header_lay.setContentsMargins(0, 0, 0, 0)
        header_lay.setSpacing(6)

        self.lbl_title = QLabel()
        self.lbl_title.setObjectName("detailsTitle")
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lbl_title.setAlignment(Qt.AlignCenter)

        meta = QHBoxLayout()
        meta.setContentsMargins(0, 0, 0, 0)
        meta.setSpacing(8)

        self.lbl_type = QLabel()
        self.lbl_type.setObjectName("detailsTypeLabel")

        self.lbl_year = QLabel()
        self.lbl_year.setObjectName("detailsYearLabel")

        self.lbl_seasonal = QLabel()
        self.lbl_seasonal.setObjectName("detailsSeasonalBadge")
        self.lbl_seasonal.setVisible(False)

        meta.addWidget(self.lbl_type)
        meta.addWidget(self.lbl_year)
        meta.addWidget(self.lbl_seasonal)
        meta.addStretch(1)

        header_lay.addWidget(self.lbl_title)
        header_lay.addLayout(meta)

        top_lay.addWidget(self.lbl_cover, 0)
        top_lay.addWidget(header, 1)
        main.addWidget(top)

        # Separator
        line = QFrame(self)
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setObjectName("detailsHeaderLine")
        main.addWidget(line)

        # Tabs
        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("detailsTabs")
        main.addWidget(self.tabs, 1)

        # Bottom buttons
        bottom = QWidget(self)
        bottom_lay = QHBoxLayout(bottom)
        bottom_lay.setContentsMargins(0, 12, 0, 0)
        bottom_lay.setSpacing(8)
        bottom_lay.addStretch(1)

        self.btn_edit = QPushButton("Szerkesztés…", bottom)
        self.btn_edit.setObjectName("detailsEditButton")
        self.btn_edit.clicked.connect(self._on_edit_clicked)

        self.btn_save_notes = QPushButton("Mentés", bottom)
        self.btn_save_notes.setObjectName("detailsSaveButton")
        self.btn_save_notes.clicked.connect(self._on_save_notes_clicked)

        self.btn_close = QPushButton("Bezárás", bottom)
        self.btn_close.setObjectName("detailsCloseButton")
        self.btn_close.clicked.connect(self.reject)


        bottom_lay.addWidget(self.btn_save_notes)
        bottom_lay.addWidget(self.btn_edit)
        bottom_lay.addWidget(self.btn_close)
        main.addWidget(bottom)






    # --- Tartalom feltöltés

    def _populate(self) -> None:
        m = self._movie

        title = (m.get("title") or "Ismeretlen cím").strip()
        episode_title = (m.get("episode_title") or "").strip()
        display_title = f"{title} – {episode_title}" if episode_title else title
        self.lbl_title.setText(display_title)

        self.lbl_type.setText(_human_type(m))

        year = m.get("year")
        end_year = m.get("end_year")
        if year and end_year and end_year != year:
            self.lbl_year.setText(f"{year} – {end_year}")
        elif year:
            self.lbl_year.setText(str(year))
        else:
            self.lbl_year.setText("Nincs megadva")

        seasonal = _build_seasonal_label(m)
        if seasonal:
            self.lbl_seasonal.setText(seasonal)
            self.lbl_seasonal.setVisible(True)
        else:
            self.lbl_seasonal.setVisible(False)



        # Cover
        pm = _load_cover_pixmap(m)
        if pm is None:
            self.lbl_cover.setPixmap(QPixmap())
            self.lbl_cover.setText("Nincs borítókép")
        else:
            self.lbl_cover.setText("")
            scaled = pm.scaled(
                self.lbl_cover.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        self.lbl_cover.setPixmap(scaled)




        # Tabs – mindig újraépítjük tisztán
        self.tabs.clear()

        self.tab_overview = self._build_overview_tab(m)
        self.tab_video = ModernVideoTab(m, parent=self.tabs)
        self.tab_audio = ModernAudioTab(m, parent=self.tabs)
        self.tab_notes = ModernNotesTab(m, parent=self.tabs)
        self.tab_tech = ModernTechnicalTab(m, parent=self.tabs)

        self.tabs.addTab(self.tab_overview, "Áttekintés")
        self.tabs.addTab(self.tab_video, "Videó")
        self.tabs.addTab(self.tab_audio, "Hang / felirat")
        self.tabs.addTab(self.tab_notes, "Megjegyzés")
        self.tabs.addTab(self.tab_tech, "Technikai adatok")


        # Title bar
        self.setWindowTitle(f"Részletek – {title}")

    def _build_overview_tab(self, movie: Mapping[str, Any]) -> QWidget:
        tab = QWidget(self.tabs)
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Csak a ténylegesen hasznos összefoglaló mezők
        def add(label: str, key: str) -> None:
            val = movie.get(key)
            if val in (None, "", [], {}):
                return
            layout.addWidget(InfoRow(label, str(val)))

        add("Műfaj (általános):", "genre_general")
        add("Műfaj (részletes):", "genre_official")
        if not (movie.get("genre_general") or movie.get("genre_official")):
            add("Műfaj:", "genre")

        add("Időtartam:", "duration")

        # Összméret: ha többrészes (régi modell: több sor, part-tal), akkor az összeget mutassuk
        parts_total = movie.get("_parts_total_gb")
        total_size_gb = movie.get("total_size_gb")

        def _format_gb(gb) -> str:
            try:
                v = float(gb)
            except Exception:
                return ""
            s = f"{v:.2f}".rstrip("0").rstrip(".")
            return f"{s} GB"

        if parts_total not in (None, "", 0):
            layout.addWidget(InfoRow("Összméret:", _format_gb(parts_total)))
        elif total_size_gb not in (None, "", 0):
            layout.addWidget(InfoRow("Összméret:", _format_gb(total_size_gb)))
        else:
            add("Összméret:", "size")

        # Részek listázása (ha van)
        parts_rows = movie.get("_parts_rows")
        if isinstance(parts_rows, list) and parts_rows:
            box = QFrame(tab)
            box.setObjectName("detailsPartsBox")
            box_lay = QVBoxLayout(box)
            box_lay.setContentsMargins(0, 0, 0, 0)
            box_lay.setSpacing(6)

            box_lay.addWidget(QLabel("Részek:"))
            for r in parts_rows:
                if not isinstance(r, dict):
                    continue

                part = r.get("part")
                size = (r.get("size") or "").strip()
                loc = (r.get("storage_location") or "").strip()

                part_txt = f"{part}. rész" if part not in (None, "", 0) else "Rész"
                size_txt = size if size else "—"
                loc_txt = loc if loc else "—"

                lbl = QLabel(f"{part_txt} — {size_txt} — {loc_txt}")
                lbl.setWordWrap(True)
                lbl.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
                box_lay.addWidget(lbl)


            layout.addWidget(box)

        add("Tárolás / hely:", "storage_location")

        add("Szolgáltató:", "provider")
        add("Rendező:", "director")

        is_completed = movie.get("is_completed")
        if is_completed is not None and is_completed != "":
            layout.addWidget(InfoRow("Befejezett sorozat:", "Igen" if bool(is_completed) else "Nem"))

        layout.addStretch(1)
        return tab

    # --- Edit signal

    def _on_edit_clicked(self) -> None:
        movie_id = self._movie.get("id")
        if movie_id is None:
            return
        try:
            self.edit_requested.emit(int(movie_id))
        except (TypeError, ValueError):
            return




    def _on_save_notes_clicked(self) -> None:
        movie_id = self._movie.get("id")
        if movie_id is None:
            return
        try:
            mid = int(movie_id)
        except (TypeError, ValueError):
            return

        # Notes tab biztosan létezik a _populate() után, de legyen védett
        if not hasattr(self, "tab_notes") or self.tab_notes is None:
            return

        notes = self.tab_notes.get_notes_text()

        # Külső mentést kérünk (MainWindow / DB réteg)
        self.notes_save_requested.emit(mid, notes)






















# ---------------------------------------------------------------------
# Egységes belépési pont
# ---------------------------------------------------------------------

def open_details_dialog(parent: QWidget, movie: dict, *, style: str = "modern") -> None:
    # A valódi főablak kinyerése (MovieCard -> MainWindow)
    real_parent = parent.window() if hasattr(parent, "window") else parent

    _enrich_movie_with_parts(real_parent, movie)
    if "_parts_rows" in movie:
        print("[DETAILS enrich]", movie.get("title"),
            "rows=", len(movie.get("_parts_rows", [])),
            "total=", movie.get("_parts_total_gb"))
    else:
        print("[DETAILS enrich] skipped", movie.get("title"),
            "type=", (movie.get("type") or "").strip())


    # 1) Dialog kiválasztás – jelenleg csak modern van
    dlg = ModernDetailDialog(movie, parent=real_parent)

    # 2) EDIT / NOTES bekötés a MainWindow-ra (ha létezik)
    edit_cb = getattr(real_parent, "on_edit_item_from_list", None)
    if callable(edit_cb):
        dlg.edit_requested.connect(edit_cb)

    notes_cb = getattr(real_parent, "on_save_notes_from_details", None)
    if callable(notes_cb):
        dlg.notes_save_requested.connect(notes_cb)

    # 3) Megnyitás modálisan
    dlg.exec()



# Kompatibilitás: ha valahol véletlenül DetailDialog néven hívod
DetailDialog = ModernDetailDialog
