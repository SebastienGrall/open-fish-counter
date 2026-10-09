import sys

import cv2

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
   QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QCheckBox,
    QVBoxLayout
)

from ui.video_widget import VideoWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Open Fish Counter")
        self.resize(1200, 800)

        self.video_widget = VideoWidget()
        self.video_widget.cell_selected.connect(
        self.on_cell_selected
)

        self.cell_label = QLabel("Cellule : aucune")

        self.enabled_checkbox = QCheckBox("Activée")
        self.enabled_checkbox.setChecked(True)

        self.threshold_spinbox = QSpinBox()
        self.threshold_spinbox.setRange(0, 100)
        self.threshold_spinbox.setValue(10)

        main_widget = QWidget()

        layout = QHBoxLayout(main_widget)

        side_panel = QWidget()

        side_layout = QVBoxLayout(side_panel)

        side_layout.addWidget(self.cell_label)
        side_layout.addWidget(self.enabled_checkbox)

        side_layout.addWidget(QLabel("Seuil (%)"))
        side_layout.addWidget(self.threshold_spinbox)

        side_layout.addStretch()

        layout.addWidget(self.video_widget, 4)
        layout.addWidget(side_panel, 1)

        self.setCentralWidget(main_widget)

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

    def on_cell_selected(self, cell_id):

        self.cell_label.setText(
            f"Cellule : {cell_id}"
        )

        cell = self.video_widget.cells[cell_id]

        self.enabled_checkbox.setChecked(
            cell["enabled"]
        )

        self.threshold_spinbox.setValue(
            cell["threshold"]
        )


app = QApplication(sys.argv)

window = MainWindow()
window.show()

sys.exit(app.exec())