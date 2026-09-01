import sys
import signal

from PySide6 import QtWidgets

from viewer_app.main_window import MainWindow


def handle_sigint(sig, frame):
    """Kümmert sich um Strg+C in der Konsole, damit das Programm
    sauber beendet wird."""
    QtWidgets.QApplication.quit()


def main():
    signal.signal(signal.SIGINT, handle_sigint)

    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
