# /app/views/home_page.py
# --------------------------

from pathlib import Path

from PySide6.QtCore import Qt, QEvent

from PySide6.QtGui import QPixmap

from PySide6.QtWidgets import (
    QWidget, 
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QFrame
)



class HomePage(QWidget):
    def __init__(self, dbm, parent=None):
        super().__init__(parent)
        self.dbm = dbm
        self.main_window = parent

        layout = QVBoxLayout(self)

        title = QLabel("Kezdőoldal")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.viewport().installEventFilter(self)

        self.container = QWidget()
        self.content = QVBoxLayout(self.container)
        self.content.setSpacing(16)

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        self.reload()

    def reload(self) -> None:
        self._clear_content()

        rows = self.dbm.fetch_all()
        latest = rows[-10:] if rows else []
        latest = list(reversed(latest))

        self._add_section("Legutóbb hozzáadott", latest)

        self.content.addStretch()

    def _add_section(self, title: str, rows: list[dict]) -> None:
        section_title = QLabel(title)
        section_title.setObjectName("sectionTitle")
        self.content.addWidget(section_title)

        if not rows:
            empty = QLabel("Még nincs megjeleníthető elem.")
            self.content.addWidget(empty)
            return

        row_widget = QWidget()
        row_widget.setObjectName("homeCardRow")

        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)

        for item in rows:
            card = self._create_mini_card(item)
            row_layout.addWidget(card)

        row_layout.addStretch()

        self.content.addWidget(row_widget)

    def _create_mini_card(self, item: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("homeMiniCard")
        card.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(card)

        cover_path = (
            item.get("cover_path")
            or item.get("cover_file")
            or item.get("cover")
        )

        cover_label = QLabel()
        cover_label.setObjectName("homeMiniCardCover")
        cover_label.setAlignment(Qt.AlignCenter)
        cover_label.setFixedHeight(160)

        if cover_path and Path(str(cover_path)).exists():
            pix = QPixmap(str(cover_path))
            cover_label.setPixmap(
                pix.scaled(
                    120,
                    160,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
        else:
            cover_label.setText("Nincs borító")

        layout.addWidget(cover_label)


        title = QLabel(item.get("title") or "Cím nélkül")
        title.setObjectName("homeMiniCardTitle")
        title.setWordWrap(True)

        item_type = QLabel(item.get("type") or "")
        item_type.setObjectName("homeMiniCardMeta")

        year = QLabel(str(item.get("year") or ""))
        year.setObjectName("homeMiniCardMeta")

        layout.addWidget(title)
        layout.addWidget(item_type)
        layout.addWidget(year)
        layout.addStretch()

        # KATTINTÁS
        item_id = item.get("id")
        card.mousePressEvent = lambda event, item_id=item_id: self._open_details(item_id)

        return card

    def _open_details(self, item_id: int | None) -> None:
        if item_id is None:
            return

        if self.main_window and hasattr(self.main_window, "on_show_details_from_list"):
            self.main_window.on_show_details_from_list(int(item_id))

    def _clear_content(self) -> None:
        while self.content.count():
            item = self.content.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()




    def eventFilter(self, obj, event):
        if obj == self.scroll.viewport() and event.type() == QEvent.Wheel:
            if event.angleDelta().y() != 0:
                self.scroll.horizontalScrollBar().setValue(
                    self.scroll.horizontalScrollBar().value() - event.angleDelta().y()
                )
                return True

        return super().eventFilter(obj, event)