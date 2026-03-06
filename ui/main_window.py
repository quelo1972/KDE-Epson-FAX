from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QFileDialog, QLineEdit, QLabel, QComboBox,
    QSystemTrayIcon, QMenu
)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QProcess, QTimer
from core.fax_sender import send_fax_async, active_jobs
from core.database import init_db, get_contacts, get_history
from ui.history_dialog import HistoryDialog
from ui.contacts_dialog import ContactsDialog
import subprocess


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        init_db()

        self.setWindowTitle("KDE Epson Fax Pro")
        self.resize(600, 450)

        self.selected_file = None

        self.create_menu()
        self.create_ui()
        self.create_tray()

        # Timer stato globale
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_tray_status)
        self.status_timer.start(5000)

    # ================= MENU =================

    def create_menu(self):
        menubar = self.menuBar()

        rubrica_menu = menubar.addMenu("Rubrica")

        manage_contacts_action = QAction("Gestione Contatti", self)
        manage_contacts_action.triggered.connect(self.open_contacts)
        rubrica_menu.addAction(manage_contacts_action)

        history_menu = menubar.addMenu("Storico")

        open_history_action = QAction("Apri Storico", self)
        open_history_action.triggered.connect(self.open_history)
        history_menu.addAction(open_history_action)

    # ================= TRAY =================

    def create_tray(self):
        self.tray = QSystemTrayIcon(QIcon.fromTheme("printer"), self)
        self.tray.setToolTip("KDE Epson Fax")

        tray_menu = QMenu()

        show_action = QAction("Apri", self)
        show_action.triggered.connect(self.showNormal)

        quit_action = QAction("Esci", self)
        quit_action.triggered.connect(self.exit_app)

        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray.setContextMenu(tray_menu)

        # Click sinistro apre finestra
        self.tray.activated.connect(self.tray_clicked)

        self.tray.show()

    def tray_clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()

    def exit_app(self):
        self.tray.hide()
        self.status_timer.stop()
        self.close()
        self.deleteLater()
        import sys
        sys.exit()

    # ================= UI =================

    def create_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)

        layout.addWidget(QLabel("Seleziona stampante:"))
        self.printer_combo = QComboBox()
        layout.addWidget(self.printer_combo)
        self.load_printers()

        layout.addWidget(QLabel("Contatto (opzionale):"))
        self.contact_combo = QComboBox()
        layout.addWidget(self.contact_combo)
        self.contact_combo.currentIndexChanged.connect(self.contact_selected)

        layout.addWidget(QLabel("Numero fax:"))
        self.recipient_input = QLineEdit()
        layout.addWidget(self.recipient_input)

        self.load_contacts()

        select_file_btn = QPushButton("Seleziona PDF")
        select_file_btn.clicked.connect(self.select_file)
        layout.addWidget(select_file_btn)

        self.file_label = QLabel("Nessun file selezionato")
        layout.addWidget(self.file_label)

        send_btn = QPushButton("Invia Fax")
        send_btn.clicked.connect(self.send_fax)
        layout.addWidget(send_btn)

        self.setCentralWidget(central)

    # ================= FUNZIONI =================

    def load_printers(self):
        result = subprocess.run(["lpstat", "-a"], capture_output=True, text=True)
        for p in result.stdout.splitlines():
            self.printer_combo.addItem(p.split()[0])

    def load_contacts(self):
        self.contact_combo.clear()
        self.contact_combo.addItem("— Manuale —", "")
        for contact in get_contacts():
            _, name, fax = contact
            self.contact_combo.addItem(name, fax)

    def contact_selected(self):
        fax = self.contact_combo.currentData()
        if fax:
            self.recipient_input.setText(fax)

    def select_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Seleziona PDF", "", "PDF Files (*.pdf)"
        )
        if file:
            self.selected_file = file
            self.file_label.setText(file)

    def send_fax(self):
        printer = self.printer_combo.currentText()
        recipient = self.recipient_input.text()

        if not printer or not recipient or not self.selected_file:
            self.notify("Errore", "Compila tutti i campi")
            return

        send_fax_async(
            printer,
            recipient,
            self.selected_file,
            self.notify,
            self.update_tray_status
        )

    # ================= STATO TRAY =================

    def update_tray_status(self):
        history = get_history()

        has_failed = any(row[6] == "FAILED" for row in history)
        in_progress = active_jobs > 0

        if has_failed:
            self.tray.setIcon(QIcon.fromTheme("dialog-error"))
        elif in_progress:
            self.tray.setIcon(QIcon.fromTheme("mail-send"))
        else:
            self.tray.setIcon(QIcon.fromTheme("printer"))

        self.tray.setToolTip(
            f"KDE Epson Fax\nFax attivi: {active_jobs}"
        )

    # ================= NOTIFICHE =================

    def notify(self, title, message):
        QProcess.startDetached(
            "notify-send",
            [
                title,
                message,
                "--app-name=KDE Epson Fax",
                "--hint=boolean:resident:true",
                "--hint=boolean:transient:false"
            ]
        )

    # ================= MENU ACTIONS =================

    def open_history(self):
        dialog = HistoryDialog(self)
        dialog.exec()

    def open_contacts(self):
        dialog = ContactsDialog(self)
        dialog.exec()
        self.load_contacts()

    # ================= EVENTI =================

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.status_timer.stop()

    def showEvent(self, event):
        self.status_timer.start(5000)
