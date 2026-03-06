import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()

    # --- TRAY ---
    tray = QSystemTrayIcon()
    tray.setIcon(QIcon.fromTheme("printer"))
    tray.setToolTip("KDE Epson Fax")

    # Rende il tray disponibile alla finestra
    window.tray = tray

    menu = QMenu()

    open_action = QAction("Apri")
    open_action.triggered.connect(window.show)

    def quit_app():
        tray.hide()
        app.quit()

    quit_action = QAction("Esci")
    quit_action.triggered.connect(quit_app)

    menu.addAction(open_action)
    menu.addSeparator()
    menu.addAction(quit_action)

    tray.setContextMenu(menu)

    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if window.isVisible():
                window.hide()
            else:
                window.show()
                window.raise_()
                window.activateWindow()

    tray.activated.connect(on_tray_activated)

    tray.show()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
