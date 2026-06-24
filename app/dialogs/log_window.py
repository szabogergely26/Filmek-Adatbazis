# #  /apps/dialogs/log_window.py
# --------------------------------



# ---- Importok ------

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
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


        except Exception as exc:
            QMessageBox.critical(
                self,
                "Hiba",
                f"Nem sikerült törölni a naplót:\n\n{exc}",
            )
