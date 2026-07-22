#!/usr/bin/env python3

"""
Elso inditas varazslo a Filmek Adatbazishoz.

Egyelore egyetlen oldal:
- Uj ures adatbazis letrehozasa (alapertelmezett helyre)
- Letezo adatbazis megnyitasa (fajlvalasztoval)

Bovitheto: kesobb ide johet pl. udvozlo oldal, tema valasztas, stb.
"""

from __future__ import annotations

from pathlib import Path
import shutil

from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)


class WizardPageId:
    """Oldal-azonositok, kesobbi bovitheto sorrendhez."""
    DATABASE_CHOICE = 0


class DatabaseChoicePage(QWizardPage):
    def __init__(self, default_db_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Adatbazis beallitasa")
        self.setSubTitle("Ez ugy tunik, eloszor inditod a programot. Valassz egyet az alabbiak kozul.")

        self._default_db_path = default_db_path
        self._chosen_path: str | None = None

        self.rb_new = QRadioButton("Uj, ures adatbazis letrehozasa")
        self.rb_existing = QRadioButton("Letezo adatbazis megnyitasa")
        self.rb_new.setChecked(True)

        self.lbl_existing_path = QLabel("(nincs kivalasztva)")
        self.lbl_existing_path.setWordWrap(True)

        self.btn_browse = QPushButton("Tallozas...")
        self.btn_browse.clicked.connect(self._browse_existing)
        self.btn_browse.setEnabled(False)

        self.rb_existing.toggled.connect(self.btn_browse.setEnabled)

        layout = QVBoxLayout()
        layout.addWidget(self.rb_new)
        layout.addWidget(self.rb_existing)
        layout.addWidget(self.btn_browse)
        layout.addWidget(self.lbl_existing_path)
        layout.addStretch()
        self.setLayout(layout)

    def _browse_existing(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Adatbazis fajl kivalasztasa",
            str(Path.home()),
            "SQLite adatbazisok (*.db *.sqlite *.sqlite3);;Minden fajl (*.*)",
        )
        if file_path:
            self._chosen_path = file_path
            self.lbl_existing_path.setText(file_path)

    def validatePage(self) -> bool:
        if self.rb_existing.isChecked():
            if not self._chosen_path:
                self.lbl_existing_path.setText("Kerlek valassz egy fajlt a Tallozas gombbal!")
                return False

            try:
                self._default_db_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self._chosen_path, self._default_db_path)
            except OSError as e:
                self.lbl_existing_path.setText(f"Hiba a masolas soran: {e}")
                return False

            self.wizard().setProperty("db_path", str(self._default_db_path))
        else:
            self.wizard().setProperty("db_path", str(self._default_db_path))
        return True

class FirstRunWizard(QWizard):
    def __init__(self, default_db_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Filmek Adatbazis - Elso inditas")
        self.setPage(WizardPageId.DATABASE_CHOICE, DatabaseChoicePage(default_db_path, self))

    def chosen_db_path(self) -> str:
        return str(self.property("db_path") or "")
