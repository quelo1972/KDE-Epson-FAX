from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QHBoxLayout, QFileDialog,
    QLabel, QDateEdit
)
from PyQt6.QtCore import Qt, QTimer, QDate
from core.database import get_history
from core.fax_sender import send_fax_async
import os
import csv


class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Fax History")
        self.resize(1100, 600)

        self.parent_window = parent

        layout = QVBoxLayout(self)

        # ===== FILTRI DATA =====

        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Da:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))

        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("A:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())

        filter_layout.addWidget(self.date_to)

        filter_button = QPushButton("Filtra")
        filter_button.clicked.connect(self.load_history)

        filter_layout.addWidget(filter_button)

        layout.addLayout(filter_layout)

        # ===== TABELLA =====

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Date", "Printer", "Recipient", "File", "Job ID", "Status"
        ])
        self.table.cellDoubleClicked.connect(self.resend_selected)

        layout.addWidget(self.table)

        # ===== BOTTONI =====

        button_layout = QHBoxLayout()

        resend_button = QPushButton("Reinvia")
        resend_button.clicked.connect(self.resend_selected)

        export_button = QPushButton("Esporta CSV")
        export_button.clicked.connect(self.export_csv)

        refresh_button = QPushButton("Aggiorna")
        refresh_button.clicked.connect(self.load_history)

        button_layout.addWidget(resend_button)
        button_layout.addWidget(export_button)
        button_layout.addWidget(refresh_button)

        layout.addLayout(button_layout)

        # ===== TIMER AGGIORNAMENTO =====

        self.timer = QTimer()
        self.timer.timeout.connect(self.load_history)
        self.timer.start(5000)  # aggiorna ogni 5 secondi

        self.load_history()

    # ================= LOAD HISTORY =================

    def load_history(self):
        rows = get_history()

        date_from_str = self.date_from.date().toString("yyyy-MM-dd")
        date_to_str = self.date_to.date().toString("yyyy-MM-dd")

        filtered_rows = []

        for row in rows:
            _, datetime, printer, recipient, file, job_id, status = row

            if date_from_str <= datetime[:10] <= date_to_str:
                filtered_rows.append(row)

        self.table.setRowCount(len(filtered_rows))

        for row_index, row_data in enumerate(filtered_rows):
            _, datetime, printer, recipient, file, job_id, status = row_data

            self.table.setItem(row_index, 0, QTableWidgetItem(datetime))
            self.table.setItem(row_index, 1, QTableWidgetItem(printer))
            self.table.setItem(row_index, 2, QTableWidgetItem(recipient))
            self.table.setItem(row_index, 3, QTableWidgetItem(file))
            self.table.setItem(row_index, 4, QTableWidgetItem(job_id if job_id else ""))

            status_item = QTableWidgetItem(status)

            # 🔴 Evidenzia FAILED
            if status == "FAILED":
                status_item.setForeground(Qt.GlobalColor.red)

            # 🟢 Evidenzia COMPLETED
            if status == "COMPLETED":
                status_item.setForeground(Qt.GlobalColor.darkGreen)

            self.table.setItem(row_index, 5, status_item)

    # ================= REINVIO =================

    def resend_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return

        printer = self.table.item(row, 1).text()
        recipient = self.table.item(row, 2).text()
        file_path = self.table.item(row, 3).text()

        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Errore", "File originale non trovato.")
            return

        confirm = QMessageBox.question(
            self,
            "Conferma Reinvio",
            f"Reinvia fax a {recipient} usando stampante {printer}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            send_fax_async(
                printer,
                recipient,
                file_path,
                self.parent_window.notify if self.parent_window else None
            )

    # ================= EXPORT CSV =================

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salva CSV",
            "fax_history.csv",
            "CSV Files (*.csv)"
        )

        if not path:
            return

        rows = get_history()

        with open(path, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Date", "Printer", "Recipient", "File", "Job ID", "Status"])
            for row in rows:
                _, datetime, printer, recipient, file_path, job_id, status = row
                writer.writerow([datetime, printer, recipient, file_path, job_id, status])
