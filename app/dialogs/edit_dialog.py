# /apps/dialogs/edit_dialog.py
# ------------------------------

# -*- coding: utf-8 -*-


# Szerkesztő / új bejegyzés párbeszédablak (egyszerű, egyoldalas form).


from __future__ import annotations

import re
from typing import Any, Dict, Optional

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from db import DatabaseManager




#  ----- Segédfüggvények:

def parse_first_int(text: str) -> Optional[int]:
    """
    Szövegből kinyeri az első előforduló egész számot.
    Üres / nem számos input esetén None-t ad vissza.
    """
    text = (text or "").strip()
    if not text:
        return None

    m = re.search(r"\d+", text)
    if not m:
        return None
    try:
        return int(m.group(0))
    except ValueError:
        return None













class EditDialog(QDialog):
    def __init__(
        self,
        db: DatabaseManager,
        row: Optional[Dict[str, Any]] = None,
        preset: Optional[Dict[str, Any]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.db = db
        self.row = row
        self.preset = preset or {}
        self.setWindowTitle("Szerkesztés" if row else "Új hozzáadása")

        # --- ÚJ: borító elérési út (ha a row-ban már van ilyen mező) ---
        self._cover_path: Optional[str] = None
        if self.row is not None:
            self._cover_path = self.row.get("cover_path") or None

        # --- méret: normál, a többi gördül ---
        self.setMinimumSize(480, 420)
        self.resize(800, 600)

        self.init_ui()

    def init_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        # --- FORM tartalom külön widget + görgethető ---
        form_container = QWidget(self)
        form = QFormLayout(form_container)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.type_cb = QComboBox()
        self.type_cb.addItems(["film", "sorozat"])
        self.type_cb.setCurrentText(
            (self.row.get("type") if self.row else self.preset.get("type")) or "film"
        )

        self.title_edit = QLineEdit(
            (self.row.get("title") if self.row else self.preset.get("title")) or ""
        )
        if self.preset.get("title"):
            # „Új rész ehhez” esetén ne lehessen átírni a főcímet
            self.title_edit.setReadOnly(True)

        self.part_edit = QLineEdit(
            ""
            if not self.row or self.row.get("part") is None
            else str(self.row.get("part"))
        )
        self.year_edit = QLineEdit(
            ""
            if not self.row or self.row.get("year") is None
            else str(self.row.get("year"))
        )
        self.episode_title_edit = QLineEdit(
            "" if not self.row else (self.row.get("episode_title") or "")
        )
        self.genre_edit = QLineEdit(
            "" if not self.row else (self.row.get("genre") or "")
        )
        self.duration_edit = QLineEdit(
            "" if not self.row else (self.row.get("duration") or "")
        )
        self.size_edit = QLineEdit("" if not self.row else (self.row.get("size") or ""))
        self.storage_edit = QLineEdit(
            "" if not self.row else (self.row.get("storage_location") or "")
        )
        self.fmt_type_edit = QLineEdit(
            "" if not self.row else (self.row.get("format_type") or "")
        )
        self.fmt_edit = QLineEdit(
            "" if not self.row else (self.row.get("format") or "")
        )
        self.ed_audio = QLineEdit(
            "" if not self.row else (self.row.get("audio_tracks") or "")
        )
        self.ed_subs = QLineEdit(
            "" if not self.row else (self.row.get("subtitle_tracks") or "")
        )

        # --- meglévő mezők ugyanabban a sorrendben ---
        form.addRow("Hangsáv(ok):", self.ed_audio)
        form.addRow("Felirat(ok):", self.ed_subs)

        # Online szolgáltató
        self.ed_provider = QLineEdit(
            "" if not self.row else (self.row.get("provider") or "")
        )
        form.addRow("Szolgáltató (online):", self.ed_provider)

        form.addRow("Típus:", self.type_cb)
        form.addRow("Cím:", self.title_edit)
        form.addRow("Rész/Évad (szám):", self.part_edit)
        form.addRow("Rész címe (opcionális):", self.episode_title_edit)
        form.addRow("Év (szám):", self.year_edit)
        form.addRow("Műfaj:", self.genre_edit)
        form.addRow("Időtartam:", self.duration_edit)
        form.addRow("Méret:", self.size_edit)
        form.addRow("Tárolás:", self.storage_edit)
        form.addRow("Felbontás:", self.fmt_type_edit)
        form.addRow("Formátum:", self.fmt_edit)

        # --- ÚJ: borítókép blokk a form végén ---
        self._build_cover_section(form)

        # --- Vízszintes elválasztó az időszakos jelölők előtt ---
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        form.addRow(line)

        # --- Szezonális jelölők: Karácsonyi / Szilveszteri ---
        self.chk_christmas = QCheckBox("Karácsony")
        self.chk_newyear = QCheckBox("Szilveszter")

        seasonal_layout = QHBoxLayout()
        seasonal_layout.addWidget(self.chk_christmas)
        seasonal_layout.addWidget(self.chk_newyear)
        seasonal_layout.addStretch()

        form.addRow("Időszakos:", seasonal_layout)

        # Meglévő rekord esetén beolvassuk a DB-ből a seasonal_type mezőt
        seasonal_type = (
            (self.row.get("seasonal_type") or "none").lower()
            if self.row
            else "none"
        )
        self._set_seasonal_type_to_ui(seasonal_type)

        # --- ScrollArea a komplett form-ra ---
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(form_container)
        main_layout.addWidget(scroll)

        # --- Gombok alul, scroll alatt ---
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.save)
        btns.rejected.connect(self.reject)

         # Feliratok magyarosítása
        ok_btn = btns.button(QDialogButtonBox.Ok)
        if ok_btn is not None:
            ok_btn.setText("OK")          # vagy "Mentés", ha azt jobban szeretnéd

        cancel_btn = btns.button(QDialogButtonBox.Cancel)
        if cancel_btn is not None:
            cancel_btn.setText("Mégse")


        main_layout.addWidget(btns)







    # === BORÍTÓKÉP RÉSZ ===

    def _build_cover_section(self, form: QFormLayout) -> None:
        """
        Borítókép előnézet + tallózás + eltávolítás.
        """
        cover_group = QGroupBox("Borítókép")
        cover_layout = QHBoxLayout(cover_group)

        # Előnézet
        self.lbl_cover_preview = QLabel()
        self.lbl_cover_preview.setFixedSize(140, 200)
        self.lbl_cover_preview.setScaledContents(True)
        cover_layout.addWidget(self.lbl_cover_preview)

        # Gombok
        btn_layout = QVBoxLayout()
        self.btn_cover_browse = QPushButton("Tallózás…")
        self.btn_cover_clear = QPushButton("Eltávolítás")

        self.btn_cover_browse.clicked.connect(self._on_browse_cover)
        self.btn_cover_clear.clicked.connect(self._on_clear_cover)

        btn_layout.addWidget(self.btn_cover_browse)
        btn_layout.addWidget(self.btn_cover_clear)
        btn_layout.addStretch()
        cover_layout.addLayout(btn_layout)

        form.addRow(cover_group)

        self._update_cover_preview()

    def _on_browse_cover(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Borítókép kiválasztása",
            "",
            "Képfájlok (*.jpg *.jpeg *.png *.webp *.bmp);;Minden fájl (*)",
        )
        if not path:
            return

        self._cover_path = path
        self._update_cover_preview()

    def _on_clear_cover(self) -> None:
        self._cover_path = None
        self._update_cover_preview()

    def _update_cover_preview(self) -> None:
        if self._cover_path:
            pix = QPixmap(self._cover_path)
            if not pix.isNull():
                self.lbl_cover_preview.setPixmap(pix)
                self.lbl_cover_preview.setText("")
            else:
                self.lbl_cover_preview.setPixmap(QPixmap())
                self.lbl_cover_preview.setText("Nem sikerült betölteni a képet.")
        else:
            self.lbl_cover_preview.setPixmap(QPixmap())
            self.lbl_cover_preview.setText("Nincs borító")

    # === IDŐSZAKOS FLAG-KEK ===

    def _set_seasonal_type_to_ui(self, seasonal_type: str) -> None:
        st = (seasonal_type or "none").strip().lower()

        self.chk_christmas.setChecked(False)
        self.chk_newyear.setChecked(False)

        if st in ("karácsonyi", "christmas"):
            self.chk_christmas.setChecked(True)
        elif st in ("szilveszteri", "newyear"):
            self.chk_newyear.setChecked(True)
        elif st in ("mindkettő", "both"):
            self.chk_christmas.setChecked(True)
            self.chk_newyear.setChecked(True)


    def _get_seasonal_type_from_ui(self) -> str:
        christmas = self.chk_christmas.isChecked()
        newyear = self.chk_newyear.isChecked()

        if christmas and newyear:
            return "mindkettő"
        if christmas:
            return "karácsonyi"
        if newyear:
            return "szilveszteri"
        return "none"





    def save(self) -> None:
        seasonal_type = self._get_seasonal_type_from_ui()
        is_seasonal = 1 if seasonal_type != "none" else 0

        row = {
            "type": self.type_cb.currentText().strip(),
            "title": self.title_edit.text().strip(),
            "part": parse_first_int(self.part_edit.text()),
            "year": parse_first_int(self.year_edit.text()),
            "is_seasonal": is_seasonal,
            "seasonal_type": seasonal_type,
            "genre": self.genre_edit.text().strip(),
            "duration": self.duration_edit.text().strip(),
            "size": self.size_edit.text().strip(),
            "storage_location": self.storage_edit.text().strip(),
            "format_type": self.fmt_type_edit.text().strip(),
            "format": self.fmt_edit.text().strip(),
            "episode_title": self.episode_title_edit.text().strip(),
            "audio_tracks": self.ed_audio.text().strip(),
            "subtitle_tracks": self.ed_subs.text().strip(),
            "provider": self.ed_provider.text().strip(),
        }

        # --- Opcionális: borítókép mentése, ha a régi row-ban már volt ilyen mező ---
        if self.row is not None and "cover_path" in self.row:
            row["cover_path"] = self._cover_path or ""

        if not row["title"]:
            QMessageBox.warning(self, "Hiányzó mező", "A Cím mező kötelező.")
            return

        if self.row and self.row.get("id"):
            self.db.update(self.row["id"], row)
        else:
            self.db.insert(row)

        self.accept()
