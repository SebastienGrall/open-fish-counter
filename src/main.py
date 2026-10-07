import sys

from PySide6.QtWidgets import QApplication, QMainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Open Fish Counter")
        self.resize(1200, 800)


app = QApplication(sys.argv)

window = MainWindow()
window.show()

sys.exit(app.exec())