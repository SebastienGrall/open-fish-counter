import cv2
import numpy as np


class MotionDetector:
    def __init__(
        self,
        grid_rows=8,
        grid_cols=8,
        pixel_threshold=25,
    ):
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.pixel_threshold = pixel_threshold

        self.previous_frame = None

    def process_frame(self, frame):
        gray_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY,
        )

        gray_frame = cv2.GaussianBlur(
            gray_frame,
            (5, 5),
            0,
        )

        if self.previous_frame is None:
            self.previous_frame = gray_frame
            return {}

        frame_difference = cv2.absdiff(
            self.previous_frame,
            gray_frame,
        )

        _, movement_mask = cv2.threshold(
            frame_difference,
            self.pixel_threshold,
            255,
            cv2.THRESH_BINARY,
        )

        movement_mask = cv2.morphologyEx(
            movement_mask,
            cv2.MORPH_OPEN,
            np.ones((3, 3), dtype=np.uint8),
        )

        height, width = movement_mask.shape

        motion_levels = {}

        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                cell_id = row * self.grid_cols + col

                x1 = col * width // self.grid_cols
                x2 = (col + 1) * width // self.grid_cols

                y1 = row * height // self.grid_rows
                y2 = (row + 1) * height // self.grid_rows

                cell_mask = movement_mask[y1:y2, x1:x2]

                total_pixels = cell_mask.size

                if total_pixels == 0:
                    motion_percentage = 0.0
                else:
                    moving_pixels = cv2.countNonZero(
                        cell_mask
                    )

                    motion_percentage = (
                        moving_pixels
                        / total_pixels
                        * 100
                    )

                motion_levels[cell_id] = motion_percentage

        self.previous_frame = gray_frame

        return motion_levels

    def reset(self):
        self.previous_frame = None