from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel

import cv2


class VideoWidget(QLabel):
    cell_selected = Signal(int)

    def __init__(self):
        super().__init__()

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Aucun flux vidéo")
        self.setMinimumSize(640, 480)

        self.display_mode = "full"

        self.grid_rows = 8
        self.grid_cols = 8

        self.motion_levels = {}

        self.current_pixmap = None

        self.displayed_image_width = 0
        self.displayed_image_height = 0
        self.displayed_image_x = 0
        self.displayed_image_y = 0
        
        self.cells = {}

        for cell_id in range(self.grid_rows * self.grid_cols):

            self.cells[cell_id] = {
                "enabled": True,
                "threshold": 10,
            }

        self.selected_cell = None

        self.frame_width = 0
        self.frame_height = 0

    def set_motion_levels(self, motion_levels):
        self.motion_levels = motion_levels

    def set_frame(self, frame):
        frame = frame.copy()

        height, width, _ = frame.shape

        self.frame_width = width
        self.frame_height = height

        # -------------------------------------------------
        # Surbrillance orange des cellules en détection
        # -------------------------------------------------

        if self.display_mode in {
            "full",
            "detections",
        }:
            motion_overlay = frame.copy()

            for row in range(self.grid_rows):
                for col in range(self.grid_cols):
                    cell_id = (
                        row * self.grid_cols + col
                    )

                    cell = self.cells[cell_id]

                    if not cell["enabled"]:
                        continue

                    motion_percentage = (
                        self.motion_levels.get(
                            cell_id,
                            0.0,
                        )
                    )

                    threshold = cell["threshold"]

                    if motion_percentage < threshold:
                        continue

                    x1 = (
                        col * width
                        // self.grid_cols
                    )

                    x2 = (
                        (col + 1) * width
                        // self.grid_cols
                    )

                    y1 = (
                        row * height
                        // self.grid_rows
                    )

                    y2 = (
                        (row + 1) * height
                        // self.grid_rows
                    )

                    cv2.rectangle(
                        motion_overlay,
                        (x1, y1),
                        (x2, y2),
                        (0, 165, 255),
                        -1,
                    )

            cv2.addWeighted(
                motion_overlay,
                0.25,
                frame,
                0.75,
                0,
                frame,
            )

        # -------------------------------------------------
        # Quadrillage complet
        # -------------------------------------------------

        if self.display_mode == "full":
            # Lignes verticales
            for col in range(
                self.grid_cols + 1
            ):
                x = (
                    col * width
                    // self.grid_cols
                )

                cv2.line(
                    frame,
                    (x, 0),
                    (x, height),
                    (0, 255, 0),
                    1,
                )

            # Lignes horizontales
            for row in range(
                self.grid_rows + 1
            ):
                y = (
                    row * height
                    // self.grid_rows
                )

                cv2.line(
                    frame,
                    (0, y),
                    (width, y),
                    (0, 255, 0),
                    1,
                )

        # -------------------------------------------------
        # Cellule sélectionnée en rouge
        # -------------------------------------------------

        if (
            self.display_mode == "full"
            and self.selected_cell is not None
        ):
            row = (
                self.selected_cell
                // self.grid_cols
            )

            col = (
                self.selected_cell
                % self.grid_cols
            )

            x1 = (
                col * width
                // self.grid_cols
            )

            x2 = (
                (col + 1) * width
                // self.grid_cols
            )

            y1 = (
                row * height
                // self.grid_rows
            )

            y2 = (
                (row + 1) * height
                // self.grid_rows
            )

            selection_overlay = frame.copy()

            cv2.rectangle(
                selection_overlay,
                (x1, y1),
                (x2, y2),
                (0, 0, 255),
                -1,
            )

            cv2.addWeighted(
                selection_overlay,
                0.25,
                frame,
                0.75,
                0,
                frame,
            )

        # -------------------------------------------------
        # Numéros et pourcentages
        # -------------------------------------------------

        if self.display_mode == "full":
            for row in range(self.grid_rows):
                for col in range(
                    self.grid_cols
                ):
                    cell_id = (
                        row * self.grid_cols
                        + col
                    )

                    x1 = (
                        col * width
                        // self.grid_cols
                    )

                    y1 = (
                        row * height
                        // self.grid_rows
                    )

                    if self.cells[cell_id]["enabled"]:
                        text_color = (
                            0,
                            255,
                            0,
                        )
                    else:
                        text_color = (
                            128,
                            128,
                            128,
                        )

                    cv2.putText(
                        frame,
                        str(cell_id),
                        (x1 + 5, y1 + 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        text_color,
                        1,
                        cv2.LINE_AA,
                    )

                    motion_percentage = (
                        self.motion_levels.get(
                            cell_id,
                            0.0,
                        )
                    )

                    cv2.putText(
                        frame,
                        f"{motion_percentage:.1f}%",
                        (x1 + 5, y1 + 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.4,
                        (255, 255, 255),
                        1,
                        cv2.LINE_AA,
                    )

        # -------------------------------------------------
        # Conversion OpenCV vers Qt
        # -------------------------------------------------

        height, width, channels = frame.shape
        bytes_per_line = channels * width

        image = QImage(
            frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_BGR888,
        )

        self.current_pixmap = (
            QPixmap.fromImage(
                image.copy()
            )
        )

        self.update_displayed_pixmap()

    def update_displayed_pixmap(self):
        if (
            self.current_pixmap is None
            or self.current_pixmap.isNull()
        ):
            return

        scaled_pixmap = self.current_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.displayed_image_width = (
            scaled_pixmap.width()
        )

        self.displayed_image_height = (
            scaled_pixmap.height()
        )

        # Le QLabel est centré, donc les éventuelles marges
        # sont réparties de chaque côté.
        self.displayed_image_x = (
            self.width()
            - self.displayed_image_width
        ) / 2

        self.displayed_image_y = (
            self.height()
            - self.displayed_image_height
        ) / 2

        self.setPixmap(scaled_pixmap)

    def set_display_mode(self, display_mode):
        allowed_modes = {
            "full",
            "detections",
            "none",
        }

        if display_mode not in allowed_modes:
            display_mode = "full"

        self.display_mode = display_mode

    def resizeEvent(self, event):
        self.update_displayed_pixmap()

        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if self.display_mode != "full":
            return

        if (
            self.displayed_image_width <= 0
            or self.displayed_image_height <= 0
        ):
            return

        mouse_x = event.position().x()
        mouse_y = event.position().y()

        # Coordonnées du clic par rapport à l'image affichée,
        # et non par rapport au QLabel complet.
        image_x = (
            mouse_x
            - self.displayed_image_x
        )

        image_y = (
            mouse_y
            - self.displayed_image_y
        )

        # Ignore les clics dans les marges autour de l'image.
        if (
            image_x < 0
            or image_y < 0
            or image_x >= self.displayed_image_width
            or image_y >= self.displayed_image_height
        ):
            return

        # Position normalisée dans l'image affichée.
        x_ratio = (
            image_x
            / self.displayed_image_width
        )

        y_ratio = (
            image_y
            / self.displayed_image_height
        )

        col = int(
            x_ratio * self.grid_cols
        )

        row = int(
            y_ratio * self.grid_rows
        )

        col = max(
            0,
            min(col, self.grid_cols - 1),
        )

        row = max(
            0,
            min(row, self.grid_rows - 1),
        )

        self.selected_cell = (
            row * self.grid_cols + col
        )

        self.cell_selected.emit(
            self.selected_cell
        )

    def set_camera_message(self, message):
        self.current_pixmap = None

        self.displayed_image_width = 0
        self.displayed_image_height = 0
        self.displayed_image_x = 0
        self.displayed_image_y = 0

        self.clear()
        self.setText(message)