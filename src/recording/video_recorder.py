from datetime import datetime
from pathlib import Path

import cv2


class VideoRecorder:
    def __init__(
        self,
        recordings_directory,
        fps=25.0,
    ):
        self.recordings_directory = Path(
            recordings_directory
        )

        self.fps = float(fps)

        self.writer = None
        self.output_path = None
        self.frame_size = None
        self.frame_count = 0

    @property
    def is_recording(self):
        return self.writer is not None

    def start(self, pre_event_frames):
        if self.is_recording:
            return False

        if not pre_event_frames:
            print(
                "Impossible de démarrer : "
                "le pré-buffer est vide."
            )
            return False

        first_frame = pre_event_frames[0]

        height, width = first_frame.shape[:2]

        self.frame_size = (width, height)

        now = datetime.now()

        day_directory = (
            self.recordings_directory
            / now.strftime("%Y-%m-%d")
        )

        day_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = (
            f"event_{now.strftime('%H-%M-%S-%f')[:-3]}"
            f".mp4"
        )

        self.output_path = (
            day_directory / filename
        )

        fourcc = cv2.VideoWriter_fourcc(
            *"mp4v"
        )

        self.writer = cv2.VideoWriter(
            str(self.output_path),
            fourcc,
            self.fps,
            self.frame_size,
        )

        if not self.writer.isOpened():
            print(
                "Impossible d'ouvrir le fichier vidéo : "
                f"{self.output_path}"
            )

            self.writer.release()
            self.writer = None
            self.output_path = None
            self.frame_size = None

            return False

        self.frame_count = 0

        for frame in pre_event_frames:
            self.write_frame(frame)

        print(
            f"Enregistrement démarré : "
            f"{self.output_path}"
        )

        return True

    def write_frame(self, frame):
        if not self.is_recording:
            return

        height, width = frame.shape[:2]

        if (width, height) != self.frame_size:
            frame = cv2.resize(
                frame,
                self.frame_size,
            )

        self.writer.write(frame)
        self.frame_count += 1

    def stop(self):
        if not self.is_recording:
            return None

        output_path = self.output_path
        frame_count = self.frame_count

        self.writer.release()

        self.writer = None
        self.output_path = None
        self.frame_size = None
        self.frame_count = 0

        print(
            f"Enregistrement terminé : "
            f"{output_path}"
        )

        print(
            f"Nombre d'images enregistrées : "
            f"{frame_count}"
        )

        return output_path