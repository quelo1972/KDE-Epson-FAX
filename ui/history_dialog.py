from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QHBoxLayout, QFileDialog,
    QLabel, QDateEdit, QComboBox, QLineEdit, QApplication, QMenu,
    QToolButton, QWidget, QSpinBox, QCheckBox, QColorDialog
)
from PyQt6.QtCore import Qt, QTimer, QDate, QSettings
from PyQt6.QtGui import QShortcut, QKeySequence, QAction, QIcon, QColor
from PyQt6.QtWidgets import QHeaderView
from core.app_logging import get_logger
from core.database import get_history, update_status
from core.fax_sender import cancel_fax
from core.validation import is_valid_fax_number, is_pdf_file
from core.fax_sender import send_fax_async
import os
import csv
import subprocess
from datetime import datetime


class NumericTableItem(QTableWidgetItem):
    def __init__(self, numeric_value, text):
        super().__init__(text)
        self._numeric_value = numeric_value

    def __lt__(self, other):
        if isinstance(other, NumericTableItem):
            return (self._numeric_value or 0) < (other._numeric_value or 0)
        return super().__lt__(other)


class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.logger = get_logger()
        self.settings = QSettings("KDE Epson Fax", "KDE Epson Fax Pro")
        self.setWindowTitle("Fax History")
        self.resize(1100, 600)

        self.parent_window = parent
        self._last_rows = None

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

        filter_layout.addWidget(QLabel("Stato:"))
        self.status_filter = QComboBox()
        self.status_filter.addItem("Tutti", "")
        for status in ["QUEUED", "PROCESSING", "COMPLETED", "FAILED", "CANCELLED"]:
            self.status_filter.addItem(status, status)
        self.status_filter.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.status_filter)

        filter_layout.addWidget(QLabel("Cerca:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nome, numero, file...")
        self.search_input.textChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.search_input)
        self.search_input.setClearButtonEnabled(True)

        filter_layout.addWidget(QLabel("Soglia min:"))
        self.age_threshold = QSpinBox()
        self.age_threshold.setRange(5, 720)
        self.age_threshold.setSingleStep(5)
        self.age_threshold.setSuffix(" min")
        self.age_threshold.valueChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.age_threshold)

        self.highlight_toggle = QCheckBox("Evidenzia")
        self.highlight_toggle.setChecked(True)
        self.highlight_toggle.stateChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.highlight_toggle)

        filter_layout.addWidget(QLabel("Colore:"))
        self.highlight_color = QComboBox()
        self.highlight_color.addItem("Giallo", "yellow")
        self.highlight_color.addItem("Arancione", "orange")
        self.highlight_color.addItem("Rosso chiaro", "salmon")
        self.highlight_color.addItem("Personalizzato", "custom")
        self.highlight_color.currentIndexChanged.connect(self.on_highlight_color_changed)
        filter_layout.addWidget(self.highlight_color)

        self.over_threshold_only = QCheckBox("Solo oltre soglia")
        self.over_threshold_only.stateChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.over_threshold_only)

        filter_button = QPushButton("Filtra")
        filter_button.clicked.connect(self.load_history)

        clear_button = QPushButton("Reset")
        clear_button.clicked.connect(self.reset_filters)

        filter_layout.addWidget(filter_button)
        filter_layout.addWidget(clear_button)

        layout.addLayout(filter_layout)

        # ===== TABELLA =====

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Date", "Printer", "Recipient", "File", "Job ID", "Status", "Durata", "Eta", "Azioni"
        ])
        self.table.horizontalHeaderItem(7).setToolTip(self._age_header_tooltip())
        self.table.horizontalHeaderItem(8).setToolTip("Azioni: apri file o reinvia fax")
        self.table.horizontalHeader().sectionClicked.connect(self._header_clicked)
        self.table.setSortingEnabled(True)
        self.table.cellDoubleClicked.connect(self.handle_double_click)
        self.table.itemSelectionChanged.connect(self.update_action_state)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setWordWrap(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.table)

        self.refresh_label = QLabel("Aggiornato")
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(self.refresh_label)
        legend_layout.addSpacing(20)
        self.count_label = QLabel("Risultati: 0")
        legend_layout.addWidget(self.count_label)
        legend_layout.addSpacing(20)
        self.threshold_label = QLabel()
        self.threshold_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.threshold_label.setToolTip("Clicca per cambiare la soglia")
        self.threshold_label.mousePressEvent = self._threshold_label_clicked
        legend_layout.addWidget(self.threshold_label)
        legend_layout.addSpacing(20)
        self.over_threshold_label = QLabel("Oltre soglia: 0")
        legend_layout.addWidget(self.over_threshold_label)
        legend_layout.addSpacing(20)
        legend_layout.addWidget(QLabel("Legenda:"))
        legend_layout.addWidget(QLabel("FAILED = rosso"))
        legend_layout.addWidget(QLabel("COMPLETED = verde"))
        legend_layout.addWidget(QLabel("CANCELLED = giallo"))
        legend_layout.addWidget(QLabel("QUEUED = ciano"))
        legend_layout.addWidget(QLabel("PROCESSING = blu"))
        legend_layout.addWidget(QLabel("ETA oltre soglia = rosso"))
        legend_layout.addWidget(QLabel("Riga evidenziata = oltre soglia"))
        legend_layout.addStretch()

        layout.addLayout(legend_layout)

        # ===== BOTTONI =====

        button_layout = QHBoxLayout()

        resend_button = QPushButton("Reinvia")
        resend_button.clicked.connect(self.resend_selected)
        resend_button.setToolTip("Reinvio disponibile solo per fax COMPLETED o FAILED.")

        open_button = QPushButton("Apri File")
        open_button.clicked.connect(self.open_selected_file)

        open_dir_button = QPushButton("Apri Cartella")
        open_dir_button.clicked.connect(self.open_selected_folder)

        cancel_button = QPushButton("Annulla")
        cancel_button.clicked.connect(self.cancel_selected)

        export_button = QPushButton("Esporta CSV")
        export_button.clicked.connect(self.export_csv)

        refresh_button = QPushButton("Aggiorna")
        refresh_button.clicked.connect(self.load_history)

        self.resend_button = resend_button
        self.open_button = open_button
        self.open_dir_button = open_dir_button
        self.cancel_button = cancel_button
        self.export_button = export_button
        self.refresh_button = refresh_button

        button_layout.addWidget(self.resend_button)
        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.open_dir_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.export_button)
        button_layout.addWidget(self.refresh_button)

        layout.addLayout(button_layout)

        # ===== TIMER AGGIORNAMENTO =====

        self.timer = QTimer()
        self.timer.timeout.connect(self.load_history)
        self.timer.start(5000)  # aggiorna ogni 5 secondi

        self._bind_shortcuts()
        self.restore_filters()
        self.load_history()

    # ================= LOAD HISTORY =================

    def load_history(self):
        rows = get_history()

        date_from_str = self.date_from.date().toString("yyyy-MM-dd")
        date_to_str = self.date_to.date().toString("yyyy-MM-dd")

        filtered_rows = []
        over_threshold_count = 0

        search_text = self.search_input.text().strip().lower()
        threshold_seconds = self.age_threshold.value() * 60

        now = datetime.now()

        for row in rows:
            _, sent_at, printer, recipient, file, job_id, status, completed_at = row

            if not (date_from_str <= sent_at[:10] <= date_to_str):
                continue

            status_filter = self.status_filter.currentData()
            if status_filter and status != status_filter:
                continue

            if search_text:
                haystack = f"{printer} {recipient} {file} {job_id or ''}".lower()
                if search_text not in haystack:
                    continue

            age_seconds = self._age_seconds(sent_at, completed_at, now, status)
            if age_seconds is not None and status in {"QUEUED", "PROCESSING"} and age_seconds > threshold_seconds:
                over_threshold_count += 1
            if self.over_threshold_only.isChecked():
                if age_seconds is None:
                    continue
                if not (status in {"QUEUED", "PROCESSING"} and age_seconds > threshold_seconds):
                    continue

            filtered_rows.append(row)

        if self._last_rows == filtered_rows:
            self.refresh_label.setText("Aggiornato")
            self.count_label.setText(f"Risultati: {len(filtered_rows)}")
            self.over_threshold_label.setText(f"Oltre soglia: {over_threshold_count}")
            self._update_threshold_label()
            self.update_action_state()
            return
        self._last_rows = list(filtered_rows)
        self.refresh_label.setText("Aggiornato (modifiche)")
        self.count_label.setText(f"Risultati: {len(filtered_rows)}")
        self.over_threshold_label.setText(f"Oltre soglia: {over_threshold_count}")
        self._update_threshold_label()

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(filtered_rows))

        for row_index, row_data in enumerate(filtered_rows):
            _, sent_at, printer, recipient, file, job_id, status, completed_at = row_data

            date_item = QTableWidgetItem(sent_at)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_index, 0, date_item)

            printer_item = QTableWidgetItem(printer)
            self.table.setItem(row_index, 1, printer_item)

            recipient_item = QTableWidgetItem(recipient)
            self.table.setItem(row_index, 2, recipient_item)

            file_item = QTableWidgetItem(file)
            file_item.setToolTip(file)
            self.table.setItem(row_index, 3, file_item)

            job_text = job_id if job_id else ""
            job_value = None
            if job_text:
                digits = "".join(ch for ch in job_text if ch.isdigit())
                if digits:
                    job_value = int(digits)
            job_item = NumericTableItem(job_value, job_text)
            job_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_index, 4, job_item)

            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            status_icon = self._get_status_icon(status)
            if status_icon:
                status_item.setIcon(status_icon)

            # 🔴 Evidenzia FAILED
            if status == "FAILED":
                status_item.setForeground(Qt.GlobalColor.red)

            # 🟢 Evidenzia COMPLETED
            if status == "COMPLETED":
                status_item.setForeground(Qt.GlobalColor.darkGreen)

            # 🟠 Evidenzia CANCELLED
            if status == "CANCELLED":
                status_item.setForeground(Qt.GlobalColor.darkYellow)

            # 🟦 Evidenzia stati attivi
            if status == "QUEUED":
                status_item.setForeground(Qt.GlobalColor.darkCyan)
            if status == "PROCESSING":
                status_item.setForeground(Qt.GlobalColor.blue)

            self.table.setItem(row_index, 5, status_item)

            duration_seconds = self._duration_seconds(sent_at, completed_at, now, status)
            duration_text = self._format_duration_seconds(duration_seconds, status, completed_at)
            duration_item = NumericTableItem(duration_seconds, duration_text)
            duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            duration_item.setToolTip(
                self._duration_tooltip(sent_at, completed_at, now, status)
            )
            self.table.setItem(row_index, 6, duration_item)

            age_seconds = self._age_seconds(sent_at, completed_at, now, status)
            age_text = self._format_duration_seconds(age_seconds, status, completed_at)
            age_item = NumericTableItem(age_seconds, age_text)
            age_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            age_item.setToolTip(self._age_tooltip(sent_at, completed_at, now, status))
            threshold_seconds = self.age_threshold.value() * 60
            highlight_row = (
                self.highlight_toggle.isChecked()
                and age_seconds is not None
                and age_seconds > threshold_seconds
                and status in {"QUEUED", "PROCESSING"}
            )
            if highlight_row:
                age_item.setForeground(Qt.GlobalColor.red)
                color_name = self.highlight_color.currentData()
                color = Qt.GlobalColor.yellow
                custom_hex = None
                if color_name == "orange":
                    color = Qt.GlobalColor.darkYellow
                elif color_name == "salmon":
                    color = Qt.GlobalColor.red
                elif color_name == "custom":
                    custom_hex = self.settings.value("history/highlight_color_custom", "#ffcc66", type=str)
                for col in range(0, 8):
                    item = self.table.item(row_index, col)
                    if item is not None:
                        if custom_hex:
                            item.setBackground(QColor(custom_hex))
                        else:
                            item.setBackground(color)
            self.table.setItem(row_index, 7, age_item)

            actions_widget = self._create_actions_widget(
                printer=printer,
                recipient=recipient,
                file_path=file,
                status=status
            )
            if highlight_row:
                bg = self._highlight_background_color()
                actions_widget.setStyleSheet(
                    f"background-color: {bg};"
                )
            self.table.setCellWidget(row_index, 8, actions_widget)

        self.table.setSortingEnabled(True)
        self.update_action_state()

    # ================= FILTRI =================

    def reset_filters(self):
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_to.setDate(QDate.currentDate())
        self.status_filter.setCurrentIndex(0)
        self.search_input.clear()
        self.age_threshold.setValue(60)
        self.highlight_toggle.setChecked(True)
        self.highlight_color.setCurrentIndex(0)
        self.settings.setValue("history/highlight_color_custom", "#ffcc66")
        self.over_threshold_only.setChecked(False)
        self.save_filters()
        self.load_history()

    # ================= STATO AZIONI =================

    def update_action_state(self):
        row = self.table.currentRow()
        if row < 0:
            self.resend_button.setEnabled(False)
            self.open_button.setEnabled(False)
            self.open_dir_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            return

        job_id_item = self.table.item(row, 4)
        status_item = self.table.item(row, 5)
        file_item = self.table.item(row, 3)

        job_id = job_id_item.text().strip() if job_id_item else ""
        status = status_item.text().strip() if status_item else ""
        file_path = file_item.text().strip() if file_item else ""

        resend_ok = bool(file_path) and is_pdf_file(file_path) and status in {"COMPLETED", "FAILED"}
        self.resend_button.setEnabled(resend_ok)
        self.open_button.setEnabled(bool(file_path))
        self.open_dir_button.setEnabled(bool(file_path))

        cancellable = bool(job_id) and status not in {"COMPLETED", "FAILED", "CANCELLED"}
        self.cancel_button.setEnabled(cancellable)

    # ================= FILTRI SETTINGS =================

    def on_filter_changed(self):
        self.save_filters()
        self.load_history()

    def on_highlight_color_changed(self):
        if self.highlight_color.currentData() == "custom":
            self._pick_custom_color()
        self.on_filter_changed()

    def _pick_custom_color(self):
        current = self.settings.value("history/highlight_color_custom", "#ffcc66", type=str)
        color = QColorDialog.getColor(initial=QColor(current), parent=self)
        if not color.isValid():
            return
        hex_color = color.name()
        self.settings.setValue("history/highlight_color_custom", hex_color)

    def _update_threshold_label(self):
        if not self.highlight_toggle.isChecked():
            self.threshold_label.setText("Soglia: disattivata")
            self.table.horizontalHeaderItem(7).setToolTip(self._age_header_tooltip())
            return
        self.threshold_label.setText(f"Soglia: {self.age_threshold.value()} min")
        self.table.horizontalHeaderItem(7).setToolTip(self._age_header_tooltip())

    def _threshold_label_clicked(self, event):
        self.age_threshold.setFocus()
        self.age_threshold.selectAll()

    def _highlight_background_color(self):
        color_name = self.highlight_color.currentData()
        if color_name == "orange":
            return "#ffd28a"
        if color_name == "salmon":
            return "#ffb3b3"
        if color_name == "custom":
            return self.settings.value("history/highlight_color_custom", "#ffcc66", type=str)
        return "#fff2a8"

    def _header_clicked(self, logical_index):
        if logical_index == 7:
            self.age_threshold.setFocus()
            self.age_threshold.selectAll()

    def _age_header_tooltip(self):
        if not self.highlight_toggle.isChecked():
            return "Tempo in coda/in corso. Evidenziazione disattivata."
        return f"Tempo in coda/in corso. Soglia evidenziazione: {self.age_threshold.value()} min."

    # ================= SCORCIATOIE =================

    def _bind_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.focus_search)
        QShortcut(QKeySequence("Escape"), self, activated=self.clear_search)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.resend_selected)
        QShortcut(QKeySequence("Ctrl+D"), self, activated=self.cancel_selected)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self.open_selected_file)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self, activated=self.open_selected_folder)
        QShortcut(QKeySequence("Ctrl+C"), self, activated=self.copy_selected_cell)

    def focus_search(self):
        self.search_input.setFocus()
        self.search_input.selectAll()

    def clear_search(self):
        if self.search_input.text():
            self.search_input.clear()
        else:
            self.search_input.clearFocus()

    def save_filters(self):
        self.settings.setValue("history/date_from", self.date_from.date().toString("yyyy-MM-dd"))
        self.settings.setValue("history/date_to", self.date_to.date().toString("yyyy-MM-dd"))
        self.settings.setValue("history/status", self.status_filter.currentData() or "")
        self.settings.setValue("history/search", self.search_input.text())
        self.settings.setValue("history/age_threshold_min", self.age_threshold.value())
        self.settings.setValue("history/highlight_enabled", self.highlight_toggle.isChecked())
        self.settings.setValue("history/over_threshold_only", self.over_threshold_only.isChecked())
        self.settings.setValue("history/highlight_color", self.highlight_color.currentData())
        if self.highlight_color.currentData() == "custom":
            # Custom color already stored when picked
            pass

    def restore_filters(self):
        date_from = self.settings.value("history/date_from", "", type=str)
        date_to = self.settings.value("history/date_to", "", type=str)
        status = self.settings.value("history/status", "", type=str)
        search = self.settings.value("history/search", "", type=str)
        age_threshold = self.settings.value("history/age_threshold_min", 60, type=int)
        highlight_enabled = self.settings.value("history/highlight_enabled", True, type=bool)
        over_threshold_only = self.settings.value("history/over_threshold_only", False, type=bool)
        highlight_color = self.settings.value("history/highlight_color", "yellow", type=str)
        custom_color = self.settings.value("history/highlight_color_custom", "#ffcc66", type=str)

        if date_from:
            self.date_from.setDate(QDate.fromString(date_from, "yyyy-MM-dd"))
        if date_to:
            self.date_to.setDate(QDate.fromString(date_to, "yyyy-MM-dd"))
        if status:
            index = self.status_filter.findData(status)
            if index >= 0:
                self.status_filter.setCurrentIndex(index)
        if search:
            self.search_input.setText(search)
        self.age_threshold.setValue(age_threshold)
        self.highlight_toggle.setChecked(highlight_enabled)
        self.over_threshold_only.setChecked(over_threshold_only)
        index = self.highlight_color.findData(highlight_color)
        if index >= 0:
            self.highlight_color.blockSignals(True)
            self.highlight_color.setCurrentIndex(index)
            self.highlight_color.blockSignals(False)
        if highlight_color == "custom":
            self.settings.setValue("history/highlight_color_custom", custom_color)

    # ================= REINVIO =================

    def resend_selected(self, *args):
        row = self.table.currentRow()
        if row < 0:
            return

        printer = self.table.item(row, 1).text()
        recipient = self.table.item(row, 2).text()
        file_path = self.table.item(row, 3).text()
        self._resend_record(printer, recipient, file_path)

    # ================= DOPPIO CLICK =================

    def handle_double_click(self, row, column):
        if column == 3:
            self.open_selected_file()
            return
        if column == 8:
            return

        status_item = self.table.item(row, 5)
        status = status_item.text().strip() if status_item else ""
        if status in {"COMPLETED", "FAILED"}:
            self.resend_selected()
        else:
            QMessageBox.information(
                self,
                "Info",
                "Reinvio disponibile solo per fax COMPLETED o FAILED."
            )

    # ================= AZIONI WIDGET =================

    def _create_actions_widget(self, printer, recipient, file_path, status):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        open_btn = QToolButton()
        open_btn.setIcon(QIcon.fromTheme("document-open"))
        open_btn.setToolTip("Apri file")
        open_btn.clicked.connect(lambda: self._open_file_path(file_path))

        resend_btn = QToolButton()
        resend_btn.setIcon(QIcon.fromTheme("view-refresh"))
        resend_btn.setToolTip("Reinvia (solo COMPLETED/FAILED)")
        resend_ok = bool(file_path) and is_pdf_file(file_path) and status in {"COMPLETED", "FAILED"}
        resend_btn.setEnabled(resend_ok)
        if not resend_ok:
            resend_btn.setVisible(False)
        resend_btn.clicked.connect(lambda: self._resend_record(printer, recipient, file_path))

        layout.addWidget(open_btn)
        layout.addWidget(resend_btn)
        layout.addStretch()
        return container

    def _open_file_path(self, file_path):
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Errore", "File originale non trovato.")
            return

        if not is_pdf_file(file_path):
            QMessageBox.warning(self, "Errore", "Il file non e un PDF valido.")
            return

        result = subprocess.run(["xdg-open", file_path], capture_output=True, text=True)
        if result.returncode != 0:
            self.logger.warning("Open file failed: %s", file_path)
            QMessageBox.warning(self, "Errore", "Impossibile aprire il file.")

    def _resend_record(self, printer, recipient, file_path):
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Errore", "File originale non trovato.")
            return
        if not is_pdf_file(file_path):
            QMessageBox.warning(self, "Errore", "Il file non e un PDF valido.")
            return
        if not is_valid_fax_number(recipient):
            QMessageBox.warning(self, "Errore", "Numero fax non valido.")
            return

        confirm = QMessageBox.question(
            self,
            "Conferma Reinvio",
            f"Reinvia fax a {recipient} usando stampante {printer}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            self.logger.info("Resend requested: %s -> %s (%s)", printer, recipient, file_path)
            send_fax_async(
                printer,
                recipient,
                file_path,
                self.parent_window.notify if self.parent_window else None
            )

    # ================= APRI FILE =================

    def open_selected_file(self):
        row = self.table.currentRow()
        if row < 0:
            return

        file_path = self.table.item(row, 3).text()
        self._open_file_path(file_path)

    def open_selected_folder(self):
        row = self.table.currentRow()
        if row < 0:
            return

        file_path = self.table.item(row, 3).text()

        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Errore", "File originale non trovato.")
            return

        folder_path = os.path.dirname(file_path)
        result = subprocess.run(["xdg-open", folder_path], capture_output=True, text=True)
        if result.returncode != 0:
            self.logger.warning("Open folder failed: %s", folder_path)
            QMessageBox.warning(self, "Errore", "Impossibile aprire la cartella.")

    # ================= CONTEST MENU =================

    def show_context_menu(self, position):
        row = self.table.currentRow()
        if row < 0:
            return

        menu = QMenu(self)

        copy_job = QAction("Copia Job ID", self)
        copy_job.triggered.connect(self.copy_job_id)
        menu.addAction(copy_job)

        copy_recipient = QAction("Copia Numero Fax", self)
        copy_recipient.triggered.connect(self.copy_recipient)
        menu.addAction(copy_recipient)

        copy_file = QAction("Copia Percorso File", self)
        copy_file.triggered.connect(self.copy_file_path)
        menu.addAction(copy_file)

        menu.exec(self.table.viewport().mapToGlobal(position))

    def copy_job_id(self):
        row = self.table.currentRow()
        if row < 0:
            return
        job_id_item = self.table.item(row, 4)
        if not job_id_item:
            return
        job_id = job_id_item.text().strip()
        if not job_id:
            return
        QApplication.clipboard().setText(job_id)

    def copy_recipient(self):
        row = self.table.currentRow()
        if row < 0:
            return
        recipient_item = self.table.item(row, 2)
        if not recipient_item:
            return
        recipient = recipient_item.text().strip()
        if not recipient:
            return
        QApplication.clipboard().setText(recipient)

    def copy_file_path(self):
        row = self.table.currentRow()
        if row < 0:
            return
        file_item = self.table.item(row, 3)
        if not file_item:
            return
        file_path = file_item.text().strip()
        if not file_path:
            return
        QApplication.clipboard().setText(file_path)

    def copy_selected_cell(self):
        item = self.table.currentItem()
        if not item:
            return
        text = item.text().strip()
        if text:
            QApplication.clipboard().setText(text)

    # ================= ANNULLA =================

    def cancel_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return

        job_id_item = self.table.item(row, 4)
        status_item = self.table.item(row, 5)

        job_id = job_id_item.text().strip() if job_id_item else ""
        status = status_item.text().strip() if status_item else ""

        if not job_id:
            QMessageBox.warning(self, "Errore", "Job ID non disponibile.")
            return

        if status in {"COMPLETED", "FAILED", "CANCELLED"}:
            QMessageBox.information(self, "Info", "Il fax non e annullabile.")
            return

        confirm = QMessageBox.question(
            self,
            "Conferma Annulla",
            f"Annullare il fax con Job ID {job_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        if cancel_fax(job_id):
            self.logger.info("Cancel confirmed: %s", job_id)
            update_status(job_id, "CANCELLED")
            self.load_history()
        else:
            self.logger.warning("Cancel failed in UI: %s", job_id)
            QMessageBox.warning(self, "Errore", "Annullamento non riuscito.")

    # ================= ICONE STATO =================

    def _get_status_icon(self, status):
        icons = {
            "COMPLETED": "dialog-ok",
            "FAILED": "dialog-error",
            "CANCELLED": "dialog-warning",
            "PROCESSING": "mail-send",
            "QUEUED": "mail-outbox",
        }
        icon_name = icons.get(status)
        if not icon_name:
            return None
        icon = QIcon.fromTheme(icon_name)
        return icon if not icon.isNull() else None

    def _duration_seconds(self, sent_at, completed_at, now, status):
        try:
            sent_dt = datetime.strptime(sent_at, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

        end_dt = None
        if completed_at:
            try:
                end_dt = datetime.strptime(completed_at, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                end_dt = None

        if end_dt is None:
            if status in {"COMPLETED", "FAILED", "CANCELLED"}:
                return None
            end_dt = now

        delta = end_dt - sent_dt
        total_seconds = max(int(delta.total_seconds()), 0)
        return total_seconds

    def _format_duration_seconds(self, seconds, status, completed_at):
        if seconds is None:
            return "—" if completed_at or status in {"COMPLETED", "FAILED", "CANCELLED"} else ""
        hours, rem = divmod(seconds, 3600)
        minutes, secs = divmod(rem, 60)
        if hours > 0:
            return f"{hours:d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _duration_tooltip(self, sent_at, completed_at, now, status):
        try:
            sent_dt = datetime.strptime(sent_at, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return ""

        if completed_at:
            try:
                completed_dt = datetime.strptime(completed_at, "%Y-%m-%d %H:%M:%S")
                delta = completed_dt - sent_dt
                total_seconds = max(int(delta.total_seconds()), 0)
                text = self._format_duration_seconds(total_seconds, status, completed_at)
                return f"Completato in {text}"
            except ValueError:
                pass

        if status in {"COMPLETED", "FAILED", "CANCELLED"}:
            return ""

        delta = now - sent_dt
        total_seconds = max(int(delta.total_seconds()), 0)
        text = self._format_duration_seconds(total_seconds, status, completed_at)
        return f"In corso da {text}"

    def _age_seconds(self, sent_at, completed_at, now, status):
        try:
            sent_dt = datetime.strptime(sent_at, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

        if status in {"COMPLETED", "FAILED", "CANCELLED"} and completed_at:
            try:
                completed_dt = datetime.strptime(completed_at, "%Y-%m-%d %H:%M:%S")
                return max(int((completed_dt - sent_dt).total_seconds()), 0)
            except ValueError:
                return None

        return max(int((now - sent_dt).total_seconds()), 0)

    def _age_tooltip(self, sent_at, completed_at, now, status):
        seconds = self._age_seconds(sent_at, completed_at, now, status)
        text = self._format_duration_seconds(seconds, status, completed_at)
        if not text:
            return ""
        if status in {"COMPLETED", "FAILED", "CANCELLED"}:
            return f"Durata totale: {text}"
        return f"In coda da {text}"

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
            writer.writerow(["Date", "Printer", "Recipient", "File", "Job ID", "Status", "Completed At", "Duration", "Age"])
            for row in rows:
                _, sent_at, printer, recipient, file_path, job_id, status, completed_at = row
                duration_seconds = self._duration_seconds(sent_at, completed_at, datetime.now(), status)
                duration = self._format_duration_seconds(duration_seconds, status, completed_at)
                age_seconds = self._age_seconds(sent_at, completed_at, datetime.now(), status)
                age = self._format_duration_seconds(age_seconds, status, completed_at)
                writer.writerow([sent_at, printer, recipient, file_path, job_id, status, completed_at, duration, age])
