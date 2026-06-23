#!/usr/bin/env python3

"""
Kártya widget egy címhez (film/sorozat):
- szolgáltató ikon / badge
- összefoglaló metaadatok
- Részletek / Új rész / Teljes törlés gombok

Támogatott layoutok:
- Standard kártya (jelenlegi megoldás – BORÍTÓ NÉLKÜL)

- Borítós kártya:
  (cím felül, alatta bal oldalon borító,
  jobbra 4 sor: műfaj, felbontás, méret, tárolás)

A layout választását a show_cover_on_card flag határozza meg:
- False → standard kártya (eddigi viselkedés, borító nélkül)
- True  → új borítós kártya

Jelenleg a flaget kívülről még nem kötjük be a Beállításokhoz,
de a MovieCard alá van készítve hozzá.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from config import (
    APP_NAME,
    APP_ORG,
    CARD_HEIGHT_FIXED,
    CARD_WIDTH_MIN,
    COLOR_BG_CARD,
    COLOR_BORDER_CARD,
    COVER_DIR,
    ENABLE_PROVIDER_BADGES,
    NO_COVER_TEXT,
    SHOW_COVER_ON_CARD,
)
from dialogs.details_dialog import open_details_dialog
from dialogs.edit_dialog import EditDialog
from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QFontMetrics, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)
from themes.icons import PROVIDER_EMOJI, norm, provider_pixmap
from utils.utils import (
    as_int,
    format_tracks,
    join_unique,
    pretty_size,
    sum_sizes_gb,
)

logger = logging.getLogger(__name__)


# ---------------- Segéd badge-ek ----------------


def provider_pix(name: str, h: int = 18) -> QPixmap | None:
    """Egységes provider QPixmap helper a kártyákhoz."""
    return provider_pixmap(name, None, h=h)


def make_provider_badge(provider_display: str) -> QLabel:
    """Szolgáltató jelvény: próbál ikont, különben emoji+szöveg kapszula."""
    pm = provider_pix(provider_display, h=30)
    if pm:
        lbl = QLabel()
        lbl.setPixmap(pm)
        lbl.setToolTip(provider_display)
        lbl.setContentsMargins(6, 0, 0, 0)
        return lbl
    # Fallback: emoji + szöveg
    key = norm(provider_display)
    emoji = PROVIDER_EMOJI.get(key, "")
    txt = f"{emoji} {provider_display}".strip()
    lbl = QLabel(txt)
    lbl.setStyleSheet(
        "QLabel { padding:2px 8px; border-radius:10px; "
        "background:#404040; color:#eaeaea; font-weight:600; }"
    )
    lbl.setToolTip(provider_display)
    return lbl


def set_elided_text(label: QLabel, text: str, max_px: int) -> None:
    """Hosszú szöveg elvágása '...' jellel, tooltipben teljes szöveggel."""
    fm = QFontMetrics(label.font())
    label.setText(fm.elidedText(text, Qt.ElideRight, max_px))
    label.setToolTip(text)


# ---------------- Fő kártya widget ----------------


class MovieCard(QFrame):
    """
    Egyetlen film/sorozat megjelenítése kártyaként.

    Konstruktor:
        MovieCard(title, items, main_window=self, parent=self.cards_holder,
                  show_cover_on_card: bool = False)

    - title: cím szövege
    - items: az adott címhez tartozó adatbázis-sorok listája
    - main_window: főablak referenciája (db műveletekhez, reload_data, stb.)
    - show_cover_on_card: ha True, akkor az ÚJ borítós layoutot használjuk
                          (cím felül, alatta bal oldalon a borító)
    """

    def __init__(
        self,
        title: str,
        items: list[dict[str, Any]],
        main_window,
        parent=None,
        show_cover_on_card: bool | None = None,
    ) -> None:
        super().__init__(parent)

        self._hover_enabled = True
        self.setAttribute(Qt.WA_StyledBackground, True)  # biztosan kapjon hover eventet
        self.setObjectName("movieCard")

        # ha a főablak tudja, hogy be van-e kapcsolva a hover
        if main_window is not None and hasattr(main_window, "hover_effect_enabled"):
            self._hover_enabled = bool(main_window.hover_effect_enabled)

        # Pixmap cache:
        self._cover_pixmap: QPixmap | None = None

        # Hover effekt
        self.setObjectName("movieCard")
        self.setAttribute(Qt.WA_Hover, True)

        # ha kell, hogy ne legyen klasszikus frame:
        self.setFrameShape(QFrame.NoFrame)
        self.setFrameShadow(QFrame.Plain)

        self.title: str = title
        self.items: list[dict[str, Any]] = items or []
        self.main_window = main_window

        # Ezeket a builder-ek töltik ki (borítós layoutnál fontos)
        self.cover_label: QLabel | None = None
        self.provider_icon: QLabel | None = None

        first = items[0] if items else {}

        cover_path = first.get("cover_path") or first.get("cover_file") or first.get("cover")
        cover_path = (cover_path or "").strip() or None

        logger.debug(
            "[MovieCard] title=%r id=%r cover_path=%r exists=%r cover_label=%s",
            first.get("title"),
            first.get("id"),
            cover_path,
            bool(cover_path and Path(cover_path).is_file()),
            (self.cover_label.size() if self.cover_label else None),
        )

        # --- BORÍTÓ FLAG ELDÖNTÉSE ---

        if show_cover_on_card is None:
            # Ugyanazt a QSettings-et használjuk, mint a SettingsDialog:
            # QSettings(APP_ORG, APP_NAME)
            settings = QSettings(APP_ORG, APP_NAME)

            # A SettingsDialog ezt írja:
            # s.setValue("show_cover_on_card", self.chk_show_cover_on_card.isChecked())
            raw = settings.value("show_cover_on_card", SHOW_COVER_ON_CARD)

            if isinstance(raw, str):
                self.show_cover_on_card = raw.lower() in ("1", "true", "yes", "on")
            else:
                self.show_cover_on_card = bool(raw)
        else:
            # ha kívülről kaptunk flaget (teszt, speciális használat)
            self.show_cover_on_card = bool(show_cover_on_card)

        logger.debug(
            "MovieCard init – show_cover_on_card=%s (title=%r)",
            self.show_cover_on_card,
            self.title,
        )

        # --- Layout választás csak itt! ---
        if self.show_cover_on_card:
            logger.debug("MovieCard layout: COVER (title=%r)", self.title)
            self._build_cover_card()
        else:
            logger.debug("MovieCard layout: STANDARD (title=%r)", self.title)
            self._build_standard_card()

    # --------- Közös keret-stílus, méretezés ---------

    def _apply_common_frame_style(self) -> None:
        """Közös háttér, keret, hover, gomb-stílusok."""
        self.setObjectName("movieCard")

        # Téma lekérése – ugyanaz a QSettings, mint máshol
        settings = QSettings(APP_ORG, APP_NAME)
        theme = settings.value("theme", "standard")

        if theme == "standard":
            # KLASSZIKUS: régi, beégetett szürke kártya + kék hover keret
            self.setStyleSheet(
                f"""
                QFrame#movieCard {{
                    background-color: {COLOR_BG_CARD};
                    border: 1px solid {COLOR_BORDER_CARD};
                    border-radius: 10px;
                    padding: 10px;
                }}
                QFrame#movieCard:hover {{
                    background-color: #2b2b2b;     /* kicsit világosabb háttér */
                    border: 1px solid #6aa6ff;     /* kékes keret */
                }}
                """
            )
        else:
            # MODERN: semmi lokális QSS – mindent a style.css kezel
            # (különösen: QFrame#movieCard[hoverEnabled="true"]:hover)
            self.setStyleSheet("")

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setMinimumHeight(CARD_HEIGHT_FIXED)
        self.setMinimumWidth(CARD_WIDTH_MIN)
        self.mouseDoubleClickEvent = lambda e: self.open_details()

    def _build_buttons_row(self, parent_layout: QVBoxLayout) -> None:
        """Közös gombsor: Részletek / Új rész / Teljes törlés."""
        gl = QHBoxLayout()
        gl.addStretch()
        btn_details = QPushButton("Részletek")
        btn_details.setProperty("class", "detailBtn")
        btn_add = QPushButton("Új rész ehhez")
        btn_add.setProperty("class", "addBtn")
        btn_del_all = QPushButton("Törlés (teljes cím)")
        btn_del_all.setProperty("class", "delAllBtn")

        btn_details.clicked.connect(self.open_details)
        btn_add.clicked.connect(self.add_part_here)
        btn_del_all.clicked.connect(self.delete_all_title)

        gl.addWidget(btn_details)
        gl.addWidget(btn_add)
        gl.addWidget(btn_del_all)
        parent_layout.addLayout(gl)

    def _parse_breakdown(self, raw: Any) -> list[dict[str, Any]]:
        if not raw:
            return []
        if isinstance(raw, list):
            return [x for x in raw if isinstance(x, dict)]
        if isinstance(raw, str):
            s = raw.strip()
            if not s:
                return []
            try:
                val = json.loads(s)
                if isinstance(val, list):
                    return [x for x in val if isinstance(x, dict)]
            except Exception:
                return []
        return []

    def _total_gb_from_item(self, it: dict[str, Any]) -> float | None:
        # 1) ha DB már kiszámolta:
        v = it.get("total_size_gb")
        try:
            if v is not None and str(v).strip() != "":
                return float(v)
        except Exception:
            pass

        # 2) különben számoljuk breakdown-ból:
        bd = self._parse_breakdown(it.get("storage_breakdown"))
        total = 0.0
        have = False
        for p in bd:
            try:
                sg = p.get("size_gb", None)
                if sg is None or str(sg).strip() == "":
                    continue
                total += float(str(sg).replace(",", "."))
                have = True
            except Exception:
                continue
        return round(total, 2) if have else None

    def _parts_count_from_item(self, it: dict[str, Any]) -> int:
        try:
            pc = int(it.get("parts_count") or 0)
            if pc > 0:
                return pc
        except Exception:
            pass
        bd = self._parse_breakdown(it.get("storage_breakdown"))
        return (
            len({int(x.get("part")) for x in bd if str(x.get("part") or "").isdigit()}) if bd else 0
        )

    def _storage_from_item(self, it: dict[str, Any]) -> str:
        # 1) régi mező
        s = (it.get("storage_location") or "").strip()
        if s:
            return s

        # 2) breakdown loc-ok
        bd = self._parse_breakdown(it.get("storage_breakdown"))
        locs = []
        seen = set()
        for p in bd:
            loc = (p.get("loc") or "").strip()
            if not loc:
                continue
            key = loc.lower()
            if key not in seen:
                seen.add(key)
                locs.append(loc)

        if not locs:
            return ""
        if len(locs) == 1:
            return locs[0]
        # több különböző hely esetén
        return " / ".join(locs)

    # --------- STANDARD kártya (BORÍTÓ NÉLKÜL) ---------

    def _build_standard_card(self) -> None:
        """
        Eredeti kártya-layout BORÍTÓ NÉLKÜL:

        - fejléc: provider ikon, típus emoji, cím, karácsonyfa / szilveszter ikonok
        - badge sor szolgáltatókkal
        - meta sorok (műfaj, formátum, méret / évadok, év, seasonal)
        - tárolás / szolgáltató
        - hang / felirat
        - gombsor: Részletek / Új rész / Törlés
        """
        lay = QVBoxLayout(self)
        lay.setSpacing(6)

        self._apply_common_frame_style()

        first = self.items[0] if self.items else {}
        kind = (first.get("type") or "").strip().lower()
        is_film = kind in ("film", "movie")
        is_christmas = self._is_christmas()
        is_newyear = self._is_newyear()

        # --- Fejléc: szolgáltató ikon + típus emoji + cím + seasonal ikonok ---
        header = QHBoxLayout()
        header.setSpacing(8)

        self.provider_icon = QLabel()
        self.provider_icon.setFixedSize(22, 22)
        self.provider_icon.setAlignment(Qt.AlignCenter)

        type_lbl = QLabel("🎬" if is_film else "📺")
        type_lbl.setFixedWidth(26)
        type_lbl.setAlignment(Qt.AlignCenter)
        type_lbl.setStyleSheet("font-size:22px;")

        title_label = QLabel(self.title)
        title_label.setProperty("class", "title")
        title_label.setStyleSheet("font-size:16px; font-weight:bold;")
        title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        header.addWidget(self.provider_icon)
        header.addSpacing(4)
        header.addWidget(type_lbl)

        # jelzés ikonok
        if is_christmas:
            christmas_lbl = QLabel("🎄")
            christmas_lbl.setToolTip("Karácsonyi tartalom")
            christmas_lbl.setFixedWidth(24)
            christmas_lbl.setAlignment(Qt.AlignCenter)
            christmas_lbl.setStyleSheet("font-size:18px;")
            header.addWidget(christmas_lbl)

        if is_newyear:
            newyear_lbl = QLabel("🎆")
            newyear_lbl.setToolTip("Szilveszteri tartalom")
            newyear_lbl.setFixedWidth(24)
            newyear_lbl.setAlignment(Qt.AlignCenter)
            newyear_lbl.setStyleSheet("font-size:18px;")
            header.addWidget(newyear_lbl)

        header.addSpacing(6)
        header.addWidget(title_label, 1)
        lay.addLayout(header)

        # --- BADGE sor: további szolgáltatók ---
        badges_row = QHBoxLayout()
        badges_row.setSpacing(6)
        badges_row.addSpacing(58)  # igazítás a header ikonpárhoz

        if ENABLE_PROVIDER_BADGES:
            seen = set()
            providers: list[str] = []
            for it in self.items or []:
                val = (it.get("provider") or "").strip()
                if not val:
                    continue
                for part in val.split(","):
                    name = part.strip()
                    key = name.lower()
                    if key not in seen:
                        seen.add(key)
                        providers.append(name)

            header_provider = (self._extract_provider_name() or "").strip().lower()
            for p in providers:
                if p.lower() == header_provider:
                    continue
                badges_row.addWidget(make_provider_badge(p))

        badges_row.addStretch()
        lay.addLayout(badges_row)

        # --- META sorok ---

        genre = join_unique([it.get("genre") for it in self.items]).strip()
        fmt = join_unique([it.get("format_type") for it in self.items]).strip()

        first = self.items[0] if self.items else {}

        # Film multi-part támogatás: részek száma + összméret breakdown alapján
        if is_film:
            parts_count = max(self._parts_count_from_item(first), len(self.items))

            total_gb_override = self._total_gb_from_item(first)
            total_gb = (
                total_gb_override if total_gb_override is not None else sum_sizes_gb(self.items)
            )
            size_txt = pretty_size(total_gb) if total_gb is not None else ""

        else:
            parts_count = 0
            size_txt = ""

        years = [as_int(it.get("year"), 0) for it in self.items if it.get("year") is not None]
        years = [y for y in years if y > 0]
        year_span = (
            f"{min(years)}–{max(years)}"
            if years and len(set(years)) > 1
            else (str(years[0]) if years else "")
        )

        line1_bits: list[str] = []

        if is_film:
            if parts_count > 1:
                line1_bits.append(f"{parts_count} rész")
        if genre:
            line1_bits.append(genre)
        if fmt:
            line1_bits.append(fmt)
        if size_txt:
            line1_bits.append(size_txt)

        else:
            # --- season_count mindig legyen definiálva ---
            seasons = set()
            for it in self.items:
                s = it.get("season") or it.get("season_number") or it.get("season_no")
                try:
                    s_int = int(s)
                except (TypeError, ValueError):
                    continue
                if s_int > 0:
                    seasons.add(s_int)
            season_count = len(seasons)

            if season_count:
                line1_bits.append(f"{season_count} évad")
            if year_span:
                line1_bits.append(year_span)
            if self._is_christmas():
                line1_bits.append("🎄 Karácsonyi")
            if self._is_newyear():
                line1_bits.append("🎆 Szilveszteri")

        line1 = QLabel(" • ".join([b for b in line1_bits if b]))
        line1.setProperty("class", "meta")
        lay.addWidget(line1)

        storage = (
            self._storage_from_item(first)
            if is_film
            else join_unique([it.get("storage_location") for it in self.items]).strip()
        )

        provider = join_unique([it.get("provider") for it in self.items]).strip()
        line2_txt = ""
        if storage:
            line2_txt = f"Tárolás: {storage}"
        elif provider:
            line2_txt = f"Szolgáltató: {provider}"
        line2 = QLabel(line2_txt)
        line2.setProperty("class", "meta")
        lay.addWidget(line2)

        aud = format_tracks(join_unique([it.get("audio_tracks") for it in self.items]))
        subs = format_tracks(join_unique([it.get("subtitle_tracks") for it in self.items]))
        line3_bits: list[str] = []
        if aud:
            line3_bits.append(f"Hang: {aud}")
        if subs:
            line3_bits.append(f"Felirat: {subs}")
        line3 = QLabel("   ".join(line3_bits))
        line3.setProperty("class", "meta")
        lay.addWidget(line3)

        # NINCS borító a kártyán ebben a layoutban

        # --- Gombok ---
        self._build_buttons_row(lay)

        # --- ikon frissítése ---
        self._refresh_provider_icon()

    # --------- ÚJ borítós kártya (kapcsolóhoz későbbre) ---------

    def _build_cover_card(self) -> None:
        """
        Modern kártya borítóval:

        Felépítés:
        - Felül cím (plusz típus emoji, opcionálisan karácsony/szilveszter ikon, provider ikon)
        - Alatta vízszintes layout:
            bal: borítókép
            jobb: 4 sor egymás alatt:
                1. műfajok ("Sci-Fi, Vígjáték")
                2. felbontás(oka) "HD 1080p / HD 720p"
                3. méret ("23 GB")
                4. tárolás ("4_1 TB" – felirat nélkül)
        - Alul a szokásos gombsor (Részletek / Új rész / Törlés)
        """

        lay = QVBoxLayout(self)
        lay.setSpacing(6)

        self._apply_common_frame_style()

        first = self.items[0] if self.items else {}
        kind = (first.get("type") or "").strip().lower()
        is_film = kind in ("film", "movie")
        is_christmas = self._is_christmas()
        is_newyear = self._is_newyear()

        # --- Fejléc: provider ikon + típus emoji + cím + seasonal ikonok ---
        header = QHBoxLayout()
        header.setSpacing(8)

        self.provider_icon = QLabel()
        self.provider_icon.setFixedSize(22, 22)
        self.provider_icon.setAlignment(Qt.AlignCenter)

        type_lbl = QLabel("🎬" if is_film == "film" else "📺")
        type_lbl.setFixedWidth(26)
        type_lbl.setAlignment(Qt.AlignCenter)
        type_lbl.setStyleSheet("font-size:22px;")

        title_label = QLabel(self.title)
        title_label.setProperty("class", "title")
        title_label.setStyleSheet("font-size:16px; font-weight:bold;")
        title_label.setWordWrap(True)
        title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        header.addWidget(self.provider_icon)
        header.addSpacing(4)
        header.addWidget(type_lbl)

        if is_christmas:
            christmas_lbl = QLabel("🎄")
            christmas_lbl.setToolTip("Karácsonyi tartalom")
            christmas_lbl.setFixedWidth(24)
            christmas_lbl.setAlignment(Qt.AlignCenter)
            christmas_lbl.setStyleSheet("font-size:18px;")
            header.addWidget(christmas_lbl)

        if is_newyear:
            newyear_lbl = QLabel("🎆")
            newyear_lbl.setToolTip("Szilveszteri tartalom")
            newyear_lbl.setFixedWidth(24)
            newyear_lbl.setAlignment(Qt.AlignCenter)
            newyear_lbl.setStyleSheet("font-size:18px;")
            header.addWidget(newyear_lbl)

        header.addSpacing(6)
        header.addWidget(title_label, 1)
        lay.addLayout(header)

        # --- Alsó fő rész: borító + info blokk ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(8)
        lay.addLayout(bottom_layout)

        # 1) Borító bal oldalt
        self.cover_label = QLabel(NO_COVER_TEXT)
        self.cover_label.setObjectName("cardCover")
        self.cover_label.setFixedSize(96, 140)  # finomhangolható
        self.cover_label.setAlignment(Qt.AlignCenter)

        # ne legyen rajta keret, csak egy halvány szöveg
        self.cover_label.setStyleSheet(
            "QLabel#cardCover { border: none; color: #bbbbbb; font-style: italic; }"
        )

        # Skálázás kézzel, vagy autómatikus (True: auto, False: manual)
        self.cover_label.setScaledContents(False)

        bottom_layout.addWidget(self.cover_label)

        # 2) Infó blokk jobb oldalt (4 sor)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        bottom_layout.addLayout(info_layout)

        # --- Műfajok ---
        genre = join_unique([it.get("genre") for it in self.items]).strip()
        if genre:
            lbl = QLabel(genre)
            lbl.setProperty("class", "meta")
            info_layout.addWidget(lbl)

        # --- Felbontás / formátum: "HD 1080p / HD 720p" ---
        fmt_raw = join_unique([it.get("format_type") for it in self.items]).strip()
        fmt_text = fmt_raw.replace(", ", " / ") if fmt_raw else ""
        if fmt_text:
            lbl = QLabel(fmt_text)
            lbl.setProperty("class", "meta")
            info_layout.addWidget(lbl)

        # --- Méret ---
        first = self.items[0] if self.items else {}

        # --- Méret ---
        if is_film:
            total_gb_override = self._total_gb_from_item(first)
            total_gb = (
                total_gb_override if total_gb_override is not None else sum_sizes_gb(self.items)
            )
            size_txt = pretty_size(total_gb) if total_gb is not None else ""
        else:
            total_gb = sum_sizes_gb(self.items)
            size_txt = pretty_size(total_gb) if total_gb is not None else ""

        if size_txt:
            lbl = QLabel(size_txt)
            lbl.setProperty("class", "meta")
            info_layout.addWidget(lbl)

        # --- Tárolás (nyers érték – NINCS "Tárolás:" prefix) ---
        storage = (
            self._storage_from_item(first)
            if is_film
            else join_unique([it.get("storage_location") for it in self.items]).strip()
        )

        if storage:
            lbl = QLabel(storage)
            lbl.setProperty("class", "meta")
            info_layout.addWidget(lbl)

        info_layout.addStretch(1)

        # --- Cover beállítása ---
        self._update_cover_label_pixmap()

        # --- Gombok alul ---
        self._build_buttons_row(lay)

        # --- Provider ikon frissítése ---
        self._refresh_provider_icon()

    # -------- Segédfüggvények: seasonal, cover, provider --------

    def _is_christmas(self) -> bool:
        """
        Karácsonyi jelölés – db.py-val egyezően:
            - seasonal_type: 'karácsonyi'
            - seasonal_tag: tartalmaz 'karácsony'
            - legacy: is_seasonal = 1 és seasonal_type üres/'none'
        """

        for it in self.items or []:
            st = (it.get("seasonal_type") or "").strip().lower()
            tag = (it.get("seasonal_tag") or "").strip().lower()
            legacy = bool(it.get("is_seasonal"))

            if st in ("karácsonyi", "mindkettő"):
                return True
            if "karácsony" in tag:
                return True
            if legacy and (not st or st == "none"):
                return True

        return False

    def _is_newyear(self) -> bool:
        """
        Szilveszteri jelölés – db.py-val egyezően:
            - seasonal_type: 'szilveszteri'
            - seasonal_tag: tartalmaz 'szilveszter'
        """

        for it in self.items or []:
            st = (it.get("seasonal_type") or "").strip().lower()
            tag = (it.get("seasonal_tag") or "").strip().lower()

            if st in ("szilveszteri", "mindkettő"):
                return True
            if "szilveszter" in tag:
                return True

        return False

    def _slug_from_title(self) -> str:
        """
        Egyszerű 'slug' képzése a címről: szóköz -> aláhúzás, speciális jelek törlése.
        Pl.: 'Kémkölykök 2' -> 'Kémkölykök_2'
        """
        title = (self.title or "").strip()
        title = title.replace(" ", "_")
        title = re.sub(r"[^\wÁÉÍÓÖŐÚÜŰáéíóöőúüű0-9_.-]", "", title)
        return title

    def _load_cover_pixmap(self) -> QPixmap | None:
        """Borító betöltése: először DB cover_path, fallback: COVER_DIR + slug."""
        first = self.items[0] if self.items else {}

        cover_path = (
            first.get("cover_path") or first.get("cover_file") or first.get("cover") or ""
        ).strip()

        if cover_path and Path(cover_path).is_file():
            pm = QPixmap(cover_path)
            if not pm.isNull():
                return pm

        slug = self._slug_from_title()
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            path = COVER_DIR / f"{slug}{ext}"
            if path.is_file():
                pm = QPixmap(str(path))
                if not pm.isNull():
                    return pm

        return None

    def _update_cover_label_pixmap(self) -> None:
        """Borító betöltése az aktuális self.cover_label-re, ha létezik."""
        if not self.cover_label:
            return

        logger.debug("[CARD COVER] title=%r label_size=%s", self.title, self.cover_label.size())

        pm = self._load_cover_pixmap()
        if pm and not pm.isNull():
            # Mivel fix méretet adsz a cover_label-nek (96x140), itt már lesz értelmes size().
            target = self.cover_label.size()
            scaled = pm.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.cover_label.setPixmap(scaled)
            self.cover_label.setText("")
        else:
            self.cover_label.setPixmap(QPixmap())
            self.cover_label.setText(NO_COVER_TEXT)

    def _extract_provider_name(self) -> str | None:
        """
        Szolgáltató név kinyerése (első nem üres érték, első vessző előtti rész).
        """
        for it in self.items or []:
            val = it.get("provider") or it.get("service") or it.get("szolgaltato")
            if val and str(val).strip():
                return str(val).split(",")[0].strip()
        return None

    def _refresh_provider_icon(self) -> None:
        """
        Ikon/emoji beállítása: QPixmap ha van, különben emoji.
        """
        if not self.provider_icon:
            return

        name = self._extract_provider_name()
        pm = provider_pixmap(name, None, h=18) if name else None
        if pm and not pm.isNull():
            self.provider_icon.setPixmap(pm)
            self.provider_icon.setText("")
        else:
            self.provider_icon.setPixmap(QPixmap())
            self.provider_icon.setText(PROVIDER_EMOJI.get(norm(name or ""), ""))

    # --- Műveletek ---

    def open_details(self) -> None:
        if not self.items:
            return
        movie = self.items[0]
        open_details_dialog(self.main_window, movie, style="modern")

    def add_part_here(self) -> None:
        """Új rész felvétele ugyanahhoz a címhez."""
        base = self.items[0] if self.items else {}
        preset = {"type": base.get("type"), "title": base.get("title")}
        dlg = EditDialog(self.main_window.dbm, row=None, preset=preset, parent=self)
        if dlg.exec():
            QTimer.singleShot(0, self.main_window.reload_data)

    def delete_all_title(self) -> None:
        """Teljes cím törlése az adatbázisból."""
        reply = QMessageBox.question(
            self,
            "Törlés (teljes cím)",
            f"Biztosan törlöd a(z) „{self.title}” összes elemét?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.main_window.dbm.delete_by_title(self.title)
            QTimer.singleShot(0, self.main_window.reload_data)

    def setHoverEnabled(self, enabled: bool) -> None:
        """Be-/kikapcsolja a hover-effektet erre a kártyára."""
        self._hover_enabled = bool(enabled)

        # QSS-nek is jelezzük (ez a lényeg)
        self.setProperty("hoverEnabled", self._hover_enabled)

        # Stílus újrapolírozás, hogy azonnal frissüljön
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _refresh_style(self) -> None:
        """Segédfüggvény: újrapolírozza a QSS-t a property változás után."""
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self.update()

    def enterEvent(self, event):
        """Egér belép a kártya területére."""
        if self._hover_enabled:
            self.setProperty("hover", True)
            self._refresh_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Egér kilép a kártya területéről."""
        if self._hover_enabled:
            self.setProperty("hover", False)
            self._refresh_style()
        super().leaveEvent(event)
