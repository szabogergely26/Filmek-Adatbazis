# log_window.py

# ---- Importok ------

from pathlib import Path

from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
)

# ------ Importok vége -------


class LogWindow(QDialog):
    def __init__(self, log_path: Path, parent=None):
        super().__init__(parent)
        self.log_path = Path(log_path)

        self.setWindowTitle("Naplófájl megtekintése")
        self.setMinimumSize(800, 600)

        main_layout = QVBoxLayout(self)

        # --- kereső sáv ---
        search_row = QHBoxLayout()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Keresés a naplóban…")
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        self.search_edit.returnPressed.connect(self.find_next)
        search_row.addWidget(self.search_edit)

        self.btn_find_prev = QPushButton("◀ Előző")
        self.btn_find_prev.clicked.connect(self.find_prev)
        search_row.addWidget(self.btn_find_prev)

        self.btn_find_next = QPushButton("Következő ▶")
        self.btn_find_next.clicked.connect(self.find_next)
        search_row.addWidget(self.btn_find_next)

        self.match_label = QLabel("")
        self.match_label.setMinimumWidth(90)
        search_row.addWidget(self.match_label)

        main_layout.addLayout(search_row)

        # --- szövegmező ---
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.text)

        # --- gombsor: jobb oldalra igazított Frissítés + Bezárás ---
        btn_row = QHBoxLayout()

        # EZ A LÉNYEG: először a stretch → gombok jobbra kerülnek
        btn_row.addStretch()

        self.refresh_btn = QPushButton("Frissítés")
        self.refresh_btn.clicked.connect(self.load_log)
        btn_row.addWidget(self.refresh_btn)

        self.btn_clear = QPushButton("Napló törlése")
        self.btn_clear.setObjectName("dangerButton")
        self.btn_clear.clicked.connect(self.clear_log)
        btn_row.addWidget(self.btn_clear)

        self.close_btn = QPushButton("Bezárás")
        self.close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.close_btn)

        main_layout.addLayout(btn_row)

        # kereséshez tárolt állapot
        self._matches: list[QTextCursor] = []
        self._current_match_index: int = -1

        # első betöltés
        self.load_log()

    def load_log(self):
        """Log tartalmának betöltése a QTextEdit-be."""
        try:
            if self.log_path.exists():
                content = self.log_path.read_text(encoding="utf-8", errors="ignore")
                self.text.setPlainText(content)
            else:
                self.text.setPlainText(f"A logfájl nem található:\n{self.log_path}")
        except Exception as e:
            self.text.setPlainText(f"Hiba történt a log fájl olvasásakor:\n{e}")

        # frissítés után a kereső állapotot is újraszámoljuk
        self._recompute_matches()

    def clear_log(self) -> None:
        """A naplófájl tartalmának törlése, majd a nézet frissítése."""

        answer = QMessageBox.question(
            self,
            "Napló törlése",
            "Biztosan törölni szeretnéd a napló tartalmát?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            log_path = Path(self.log_path)

            if log_path.exists():
                log_path.write_text("", encoding="utf-8")

            self.text.setPlainText("A napló törölve lett.")
            self._recompute_matches()

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Hiba",
                f"Nem sikerült törölni a naplót:\n\n{exc}",
            )

    # ---------------- Keresés ----------------

    def _on_search_text_changed(self, _text: str) -> None:
        self._recompute_matches()

    def _recompute_matches(self) -> None:
        """Megkeresi az összes egyezést, és kiemeli őket a szövegben."""
        needle = self.search_edit.text()

        # előző kiemelések törlése
        self.text.setExtraSelections([])
        self._matches = []
        self._current_match_index = -1

        if not needle:
            self.match_label.setText("")
            return

        doc = self.text.document()
        cursor = QTextCursor(doc)
        matches: list[QTextCursor] = []

        while True:
            cursor = doc.find(needle, cursor, QTextDocument.FindFlag(0))
            if cursor.isNull():
                break
            matches.append(QTextCursor(cursor))

        self._matches = matches

        if not matches:
            self.match_label.setText("0 találat")
            return

        self._current_match_index = 0
        self._highlight_matches()
        self._goto_current_match()

    def _highlight_matches(self) -> None:
        """Minden találatot halványan, az aktuálisat erősebben kiemeli."""
        selections = []

        normal_fmt = QTextCharFormat()
        normal_fmt.setBackground(QColor("#5a4a00"))  # halvány sárgás

        current_fmt = QTextCharFormat()
        current_fmt.setBackground(QColor("#ffb300"))  # erős narancssárga
        current_fmt.setForeground(QColor("#000000"))

        for idx, match_cursor in enumerate(self._matches):
            sel = QTextEdit.ExtraSelection()
            sel.cursor = match_cursor
            sel.format = current_fmt if idx == self._current_match_index else normal_fmt
            selections.append(sel)

        self.text.setExtraSelections(selections)

    def _goto_current_match(self) -> None:
        if not self._matches or self._current_match_index < 0:
            return

        cursor = self._matches[self._current_match_index]
        self.text.setTextCursor(cursor)
        self.text.ensureCursorVisible()
        self.match_label.setText(
            f"{self._current_match_index + 1}/{len(self._matches)} találat"
        )

    def find_next(self) -> None:
        if not self._matches:
            self._recompute_matches()
            return

        self._current_match_index = (self._current_match_index + 1) % len(self._matches)
        self._highlight_matches()
        self._goto_current_match()

    def find_prev(self) -> None:
        if not self._matches:
            self._recompute_matches()
            return

        self._current_match_index = (self._current_match_index - 1) % len(self._matches)
        self._highlight_matches()
        self._goto_current_match()
