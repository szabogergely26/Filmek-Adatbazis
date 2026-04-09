# log_window.py

# ---- Importok ------

from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, 
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit, 
    QPushButton, 
    QSizePolicy

)


# ------ Importok vége -------


class LogWindow(QDialog):
    def __init__(self, log_path: Path, parent=None):
        super().__init__(parent)
        self.log_path = Path(log_path)

        self.setWindowTitle("Naplófájl megtekintése")
        self.setMinimumSize(800, 600)

        main_layout = QVBoxLayout(self)

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

        self.close_btn = QPushButton("Bezárás")
        self.close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.close_btn)

        main_layout.addLayout(btn_row)

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
