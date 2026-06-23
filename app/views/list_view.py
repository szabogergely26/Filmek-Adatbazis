#!/usr/bin/env python3

"""
Lista nézet az adatbázisra (Filmek + Sorozatok).

- Egy nagy táblázatot jelenít meg (QTableWidget).
- Minden sor egy adatbázis-rekord (film vagy sorozat).
- Ez maga a „részletes nézet” – külön Részletek ablak nélkül.
- Dupla kattintás egy sorra → detailRequested(item_id: int) signal,
  amit a főablak kezel (pl. szerkesztő dialógus megnyitására).

Megjegyzés:
    A _columns listában lévő "kulcs" értékeknek
    illeszkedniük kell a db_manager.fetch_all() által visszaadott
    rekordok mezőneveihez (dict key, sqlite3.Row key, attribútum, stb.).
    Ha nálad más a DB mezőneve, módosítsd az itt használt kulcsokat.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from PySide6.QtCore import (
    QEvent,
    QModelIndex,
    QPoint,
    QRect,
    QSortFilterProxyModel,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QMenu,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger(__name__)

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




class HoverRowDelegate(QStyledItemDelegate):
    def __init__(self, view: QTableWidget):
        super().__init__(view)
        self.view = view
        self.hover_row: int = -1

        # Hangold ide a kártya-hover színeidet
        self.hover_bg = QColor(255, 255, 255, 20)
        self.hover_border = QColor(255, 255, 255, 85)




    def paint(self, painter: QPainter, option, index) -> None:

        # NE hover-eljünk kijelölt sort
        if option.state & QStyle.State_Selected:
            super().paint(painter, option, index)
            return

        # Alap rajzolás előtt: ha hover sor, akkor a teljes sor hátterét/keretét
        # csak egyszer rajzoljuk (pl. az első oszlop paint-jénél).
        if index.row() == self.hover_row and index.column() == 0:
            # teljes sor rect: első és utolsó oszlop vizuális téglalapjából
            first = index.siblingAtColumn(0)
            last = index.siblingAtColumn(self.view.columnCount() - 1)

            r1 = self.view.visualRect(first)
            r2 = self.view.visualRect(last)

            full = QRect(r1.left(), r1.top(), r2.right() - r1.left() + 1, r1.height())

            painter.save()
            painter.setRenderHint(QPainter.Antialiasing, True)

            # háttér
            painter.setPen(Qt.NoPen)
            painter.setBrush(self.hover_bg)
            painter.drawRoundedRect(full.adjusted(2, 1, -2, -1), 6, 6)

            # keret (kártyás hover)
            pen = QPen(self.hover_border, 2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(full.adjusted(2, 1, -2, -1), 6, 6)

            painter.restore()

        # Ezután a normál cella rajzolás
        # (fontos: hagyjuk a selection-t a QSS-re, az rá fog ülni rendesen)
        super().paint(painter, option, index)

















class ListViewWidget(QWidget):
    """
    Lista nézet widget.

    Feltételezés:
        - db_manager rendelkezik egy fetch_all() metódussal, ami
          az összes rekordot visszaadja (pl. list[dict] vagy list[sqlite3.Row]).
        - Minden rekordnál elérhető legalább egy 'id' mező, amit
          a szerkesztéshez használunk.
    """





   # Signalok:
    editRequested = Signal(int)             # Szerkesztés
    detailsRequested = Signal(int)          # Részletek







    ID_ROLE = Qt.UserRole + 1

    # ... meglévő signalok, init, stb.

    def _dbg_index(self, index: QModelIndex, tag: str = "CLICK") -> None:
        if not index.isValid():
            log.debug("[LIST %s] invalid index", tag)
            return

        model = index.model()
        disp = index.data(Qt.DisplayRole)
        id_val = index.data(self.ID_ROLE)

        if isinstance(model, QSortFilterProxyModel):
            src_index = model.mapToSource(index)
            src_model = model.sourceModel()
            src_disp = src_index.data(Qt.DisplayRole)
            src_id = src_index.data(self.ID_ROLE)
            log.debug(
                "[LIST %s] proxyRow=%s srcRow=%s "
                "disp=%r srcDisp=%r id=%r srcId=%r "
                "model=%s srcModel=%s",
                tag,
                index.row(),
                src_index.row(),
                index.data(),
                src_index.data(),
                id_val,
                src_id,
                src_disp,
                type(model).__name__,
                type(src_model).__name__,
            )
        else:
            log.debug(
                "[LIST %s] row=%s disp=%r id=%r model=%s",
                tag,
                index.row(),
                disp,
                id_val,
                type(model).__name__,
            )






    ID_ROLE = Qt.UserRole + 1

    def _id_from_index(self, index: QModelIndex) -> int | None:
        if not index.isValid():
            return None

        model = index.model()

        # Proxy eset kezelése
        try:
            if isinstance(model, QSortFilterProxyModel):
                src_index = model.mapToSource(index)
                src_model = model.sourceModel()
                val = src_model.data(src_index, self.ID_ROLE)
            else:
                val = model.data(index, self.ID_ROLE)
        except Exception:
            # Biztonsági fallback
            val = model.data(index, self.ID_ROLE)

        if val is None:
            return None
        try:
            return int(val)
        except (TypeError, ValueError):
            return None




    def __init__(self, db_manager: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = db_manager

        # Oszlopfejlécek definiálása: (fejléc szöveg, mezőnév a rekordban)

        # A mezőneveket igazítsd a saját DB-sémádhoz!
        self._columns: list[tuple[str, str]] = [
             ("Időszakos", "__seasonal__"),
            ("Cím", "title"),
            ("Típus", "type"),                 # "Film" / "Sorozat"
            ("Rész / Évad", "part"),           # DB: 'part' mező
            ("Epizód címe (alcím)", "episode_title"),
            ("Év", "year"),
            ("Időtartam", "duration"),
            ("Méret", "size"),
            ("Felbontás", "format_type"),      # DB: 'format_type' (pl. 1080p)
            ("Formátum", "format"),            # DB: 'format' (pl. MKV)
            # Speciális: tárolás + szolgáltató kombinálva
            ("Tárolás / Szolgáltató", "__storage_or_provider__"),
        ]


        self._setup_ui()
        self.reload_data()










    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(self)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Interactive)

        # Dupla kattintás → szerkesztés kérése
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        # Jobb klikk → saját context menü
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_custom_context_menu)


        self.table.setColumnCount(len(self._columns))
        self.table.setHorizontalHeaderLabels([col[0] for col in self._columns])



        # Új:
        self.table.setObjectName("dbListTable")  # opcionális, de erősen ajánlott

        # Sor-kijelölés (ne cella)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)

        # Hover működéséhez (különben sokszor csak “néha” jön elő)
        self.table.setMouseTracking(True)

        # Ha használsz alternating row colors-t, az néha rondán keveredik a QSS-sel
        self.table.setAlternatingRowColors(False)


        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setMouseTracking(True)

        # Cella szegélyek megjelenésének engedélyezése
        self.table.setShowGrid(True)
        self.table.horizontalHeader().setHighlightSections(True)
        self.table.verticalHeader().setHighlightSections(True)



        self.table.setMouseTracking(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)


        # Hover-delegate bekötés
        self._hover_delegate = HoverRowDelegate(self.table)
        self.table.setItemDelegate(self._hover_delegate)


        # Ha az egér elhagyja a táblát, töröljük a hover sort
        self.table.viewport().installEventFilter(self)


    # ---- Alapértelmezett látható oszlopok beállítása ----
        visible_keys = {
            "__seasonal__",
            "title",
            "type",
            "part",
            "episode_title",
            "format_type",
            "__storage_or_provider__",
        }

        for col_index, (_header, key) in enumerate(self._columns):
            if key not in visible_keys:
                self.table.setColumnHidden(col_index, True)


        # --- FELSŐ sor: csak lista nézetben látható Szerkesztés gomb ---
        top_row = QHBoxLayout()
        top_row.addStretch()

        self.btn_edit = QPushButton("Szerkesztés…")
        self.btn_edit.clicked.connect(self._on_edit_button_clicked)
        top_row.addWidget(self.btn_edit)

        layout.addLayout(top_row)


        layout.addWidget(self.table)














    def eventFilter(self, obj, event):
        if obj is self.table.viewport():
            et = event.type()

            # Egér mozog: mindig számoljuk újra a hover sort
            if et == QEvent.Type.MouseMove:
                idx = self.table.indexAt(event.pos())
                new_row = idx.row() if idx.isValid() else -1
                if self._hover_delegate.hover_row != new_row:
                    self._hover_delegate.hover_row = new_row
                    self.table.viewport().update()
                return False

            # Egér elhagyja a táblát: hover törlése
            if et == QEvent.Type.Leave:
                if self._hover_delegate.hover_row != -1:
                    self._hover_delegate.hover_row = -1
                    self.table.viewport().update()
                return False

        return super().eventFilter(obj, event)





    # -------------------------------------------------------------------------
    # Adattöltés
    # -------------------------------------------------------------------------
    def reload_data(self) -> None:
        """
        Az egész táblát újratölti az adatbázisból.
        Hívd meg, ha módosult az adatbázis (új elem, szerkesztés, törlés).
        """


        records = self._fetch_all_records()

        was_sorting = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)   # <-- KRITIKUS: töltés alatt OFF

        self.table.setRowCount(0)

        for row_index, record in enumerate(records):
            self.table.insertRow(row_index)

            # Elvárás: legyen 'id' mező (int), ezt eltároljuk a sorhoz.
            raw_id = self._get_value(record, "id")
            try:
                item_id = int(raw_id) if raw_id is not None else -1
            except (TypeError, ValueError):
                item_id = -1

            for col_index, (_header, key) in enumerate(self._columns):

                # --- 1) Időszakos oszlop (🎄 / 🎆 / 🎄🎆 / üres) ---
                if key == "__seasonal__":
                    seasonal_type = (self._get_value(record, "seasonal_type") or "").strip().lower()
                    seasonal_tag = (self._get_value(record, "seasonal_tag") or "").strip().lower()

                    icon_text = ""
                    label_text = ""

                    # elsősorban seasonal_type alapján döntünk
                    st = seasonal_type
                    if st:
                        if st in CHRISTMAS_ALIASES:
                            icon_text = "🎄"
                            label_text = "karácsonyi"

                        elif st in NEWYEAR_ALIASES:
                            icon_text = "🎆"
                            label_text = "szilveszteri"

                        elif st in BOTH_ALIASES:
                            icon_text = "🎄🎆"
                    # ha seasonal_type üres, megpróbáljuk seasonal_tag alapján
                    if not icon_text and seasonal_tag:
                        if "karácsony" in seasonal_tag:
                            icon_text = "🎄"
                            label_text = "karácsonyi"
                        elif "szilveszter" in seasonal_tag:
                            icon_text = "🎆"
                            label_text = "szilveszteri"

                    if icon_text and label_text:
                        text = f"{icon_text} {label_text}"
                    else:
                        text = ""

                # --- 2) Tárolás / Szolgáltató összevonva ---
                elif key == "__storage_or_provider__":
                    storage = self._get_value(record, "storage_location") or ""
                    provider = self._get_value(record, "provider") or ""

                    parts: list[str] = []
                    if storage:
                        parts.append(str(storage).strip())
                    if provider:
                        parts.append(str(provider).strip())

                    text = " – ".join(parts)

                # --- 3) Minden más oszlop: közvetlen mezőérték ---
                else:
                    value = self._get_value(record, key)
                    text = "" if value is None else str(value)

                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

                # ID MINDEN cellába:
                if item_id >= 0:
                    item.setData(Qt.UserRole, item_id)

                self.table.setItem(row_index, col_index, item)

        self.table.resizeColumnsToContents()

        # fontos: visszaállítjuk
        self.table.setSortingEnabled(was_sorting)


    # -------------------------------------------------------------------------
    # Külső API a főablak számára
    # -------------------------------------------------------------------------
    def get_current_item_id(self) -> int | None:
        """
        Visszaadja az aktuálisan kiválasztott sorhoz tartozó item_id-t,
        vagy None-t, ha nincs kiválasztás / nincs érvényes id.
        """
        selection = self.table.selectionModel()
        if not selection:
            return None

        rows = selection.selectedRows()
        if not rows:
            return None

        row = rows[0].row()
        return self._get_item_id_for_row(row)



    def get_selected_id(self) -> int | None:
        """Kompatibilitási wrapper a MainWindow számára."""
        return self.get_current_item_id()





    def apply_filter(self, t: str) -> None:
        """
        Szűrés a lista nézetben.
        A MainWindow már lowercase-re alakította a szöveget, t = keresőkifejezés.
        Azon sorokat rejtjük el, ahol a teljes sor szövegében nem szerepel t.
        """
        # Üres kereső – mindent mutatunk
        if not t:
            for row in range(self.table.rowCount()):
                self.table.setRowHidden(row, False)
            return

        for row in range(self.table.rowCount()):
            parts: list[str] = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item is not None:
                    parts.append(item.text())

            row_text = " ".join(parts).lower()
            self.table.setRowHidden(row, t not in row_text)



















    # -------------------------------------------------------------------------
    # Belső segédfüggvények
    # -------------------------------------------------------------------------
    def _fetch_all_records(self) -> list[Any]:
        """
        Belső wrapper a db_manager.fetch_all() köré.
        Ha hiba történik, üres listát ad vissza, hogy ne dőljön el a GUI.
        """
        try:
            records = self._db.fetch_all()
            # elvileg Iterable; konvertáljuk listává
            if isinstance(records, Iterable):
                return list(records)
            return []
        except Exception as exc:  # loggolhatod is, ha akarsz
            print(f"ListViewWidget: fetch_all() hiba: {exc}")
            return []

    def _get_value(self, record: Any, key: str) -> Any:
        """
        Általános mező elérés különböző rekord-típusokhoz:
        - dict
        - sqlite3.Row (dict-szerű)
        - tetszőleges objektum attribútummal
        """
        if record is None:
            return None

        # dict-szerű (pl. sqlite3.Row)
        if isinstance(record, dict):
            return record.get(key)

        # sqlite3.Row vagy hasonló, __getitem__-nel
        try:
            return record[key]  # type: ignore[index]
        except Exception:
            pass

        # objektum attribútum
        return getattr(record, key, None)



    def _get_item_id_for_row(self, row: int) -> int | None:
        # Bármelyik oszlop jó, de legyen biztosan item:
        item = self.table.item(row, 0)
        if item is None:
            # fallback: keress bármelyik oszlopban egy itemet
            for c in range(self.table.columnCount()):
                item = self.table.item(row, c)
                if item is not None:
                    break
        if item is None:
            return None

        val = item.data(Qt.UserRole)
        if val is None:
            return None
        try:
            return int(val)
        except (TypeError, ValueError):
            return None












    # -------------------------------------------------------------------------
    # Eseménykezelők
    # -------------------------------------------------------------------------
    @Slot(int, int)
    def _on_cell_double_clicked(self, row: int, _column: int) -> None:
        """
        Dupla kattintás egy sorra → Részletek ablak kérése.
        """
        item_id = self._get_item_id_for_row(row)
        if item_id is None:
            return

        # NE szerkesztés, hanem részletek:
        self.detailsRequested.emit(item_id)




    @Slot(QPoint)
    def _on_custom_context_menu(self, pos: QPoint) -> None:
        """
        Jobb klikk a táblán → context menü ('Szerkesztés…').
        """
        index = self.table.indexAt(pos)
        row = index.row()
        if row < 0:
            return

        # Sor kijelölése
        self.table.selectRow(row)

        item_id = self._get_item_id_for_row(row)
        if item_id is None:
            return

        menu = QMenu(self)

        act_edit = menu.addAction("Szerkesztés…")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == act_edit:
            self.editRequested.emit(item_id)



    @Slot()
    def _on_edit_button_clicked(self) -> None:
        """
        Felső 'Szerkesztés…' gomb – a kijelölt sor szerkesztése.
        Ugyanazt az editRequested jelet küldi, mint a jobb klikk menü.
        """
        row = self.table.currentRow()
        if row < 0:
            return

        item_id = self._get_item_id_for_row(row)
        if item_id is None:
            return

        self.editRequested.emit(item_id)


