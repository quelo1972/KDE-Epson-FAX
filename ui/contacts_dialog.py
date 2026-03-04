from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLineEdit
)
from PyQt6.QtCore import pyqtSignal
from core.database import get_contacts, add_contact, delete_contact


class ContactsDialog(QDialog):

    contact_selected_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Rubrica Fax")
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Nome", "Numero Fax"])
        self.table.cellDoubleClicked.connect(self.select_contact)
        layout.addWidget(self.table)

        form_layout = QHBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nome")

        self.fax_input = QLineEdit()
        self.fax_input.setPlaceholderText("Numero Fax")

        add_btn = QPushButton("Aggiungi")
        add_btn.clicked.connect(self.add_contact)

        delete_btn = QPushButton("Elimina")
        delete_btn.clicked.connect(self.delete_selected)

        form_layout.addWidget(self.name_input)
        form_layout.addWidget(self.fax_input)
        form_layout.addWidget(add_btn)
        form_layout.addWidget(delete_btn)

        layout.addLayout(form_layout)

        self.load_contacts()

    def load_contacts(self):
        contacts = get_contacts()
        self.table.setRowCount(len(contacts))

        for row, contact in enumerate(contacts):
            contact_id, name, fax = contact

            item_name = QTableWidgetItem(name)
            item_name.setData(1, contact_id)

            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, QTableWidgetItem(fax))

    def add_contact(self):
        name = self.name_input.text()
        fax = self.fax_input.text()

        if name and fax:
            add_contact(name, fax)
            self.name_input.clear()
            self.fax_input.clear()
            self.load_contacts()

    def delete_selected(self):
        selected = self.table.currentRow()
        if selected >= 0:
            contact_id = self.table.item(selected, 0).data(1)
            delete_contact(contact_id)
            self.load_contacts()

    def select_contact(self, row, column):
        fax_number = self.table.item(row, 1).text()
        self.contact_selected_signal.emit(fax_number)
        self.accept()
