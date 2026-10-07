from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel

import cv2


class VideoWidget(QLabel):

    def __init__(self):
        super().__init__()

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Aucun flux vidéo")
        self.setMinimumSize(640, 480)

        self.grid_rows = 8
        self.grid_cols = 8
        self.selected_cell = None

        self.frame_width = 0
        self.frame_height = 0

    def set_frame(self, frame):

        frame = frame.copy()

        height, width, _ = frame.shape
        self.frame_width = width
        self.frame_height = height

        cell_width = width // self.grid_cols
        cell_height = height // self.grid_rows

        # Lignes verticales
        for col in range(self.grid_cols + 1):
            x = col * cell_width

            cv2.line(
                frame,
                (x, 0),
                (x, height),
                (0, 255, 0),
                1,
            )

        # Lignes horizontales
        for row in range(self.grid_rows + 1):
            y = row * cell_height

            cv2.line(
                frame,
                (0, y),
                (width, y),
                (0, 255, 0),
                1,
            )

        if self.selected_cell is not None:

            row = self.selected_cell // self.grid_cols
            col = self.selected_cell % self.grid_cols

            x = col * cell_width
            y = row * cell_height

            cv2.rectangle(
                frame,
                (x, y),
                (x + cell_width, y + cell_height),
                (0, 0, 255),
                -1,
            )

            alpha = 0.25

            overlay = frame.copy()

            cv2.rectangle(
                overlay,
                (x, y),
                (x + cell_width, y + cell_height),
                (0, 0, 255),
                -1,
            )

            cv2.addWeighted(
                overlay,
                alpha,
                frame,
                1 - alpha,
                0,
                frame,
            )

        # Numérotation
        cell_id = 0

        for row in range(self.grid_rows):
            for col in range(self.grid_cols):

                x = col * cell_width
                y = row * cell_height

                cv2.putText(
                    frame,
                    str(cell_id),
                    (x + 5, y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1,
                    cv2.LINE_AA,
                )

                cell_id += 1

        # Conversion Qt
        height, width, channels = frame.shape

        bytes_per_line = channels * width

        image = QImage(
            frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_BGR888,
        )

        pixmap = QPixmap.fromImage(image)

        self.setPixmap(
            pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event):

        if self.pixmap() is not None:
            self.setPixmap(
                self.pixmap().scaled(
                    self.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        super().resizeEvent(event)

    def mousePressEvent(self, event):

        if self.frame_width == 0:
            return

        display_width = self.width()
        display_height = self.height()

        x_ratio = event.position().x() / display_width
        y_ratio = event.position().y() / display_height

        col = int(x_ratio * self.grid_cols)
        row = int(y_ratio * self.grid_rows)

        col = min(col, self.grid_cols - 1)
        row = min(row, self.grid_rows - 1)

        self.selected_cell = row * self.grid_cols + col

        print(f"Cellule sélectionnée : {self.selected_cell}")