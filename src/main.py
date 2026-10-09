import sys

import cv2

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMainWindow

from ui.video_widget import VideoWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Open Fish Counter")
        self.resize(1200, 800)

        self.video_widget = VideoWidget()

        self.setCentralWidget(self.video_widget)

        #
        # Pour l'instant :
        # webcam OpenCV par défaut
        #
        self.cap = cv2.VideoCapture(1)

        self.timer = QTimer()

        self.timer.timeout.connect(self.update_frame)

        self.timer.start(30)

    def update_frame(self):
        ok, frame = self.cap.read()

        if not ok:
            return

        self.video_widget.set_frame(frame)

    def closeEvent(self, event):
        self.cap.release()
        super().closeEvent(event)


app = QApplication(sys.argv)

window = MainWindow()
window.show()

sys.exit(app.exec())