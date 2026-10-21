import time
from collections import deque
from datetime import datetime


class FrameBuffer:
    def __init__(self, duration_seconds=1.0):
        self.duration_seconds = max(
            0.0,
            float(duration_seconds),
        )

        self.frames = deque()

    def add_frame(self, frame):
        monotonic_time = time.monotonic()
        capture_time = datetime.now().astimezone()

        self.frames.append(
            (
                monotonic_time,
                capture_time,
                frame.copy(),
            )
        )

        self._remove_old_frames(
            monotonic_time
        )

    def _remove_old_frames(self, current_monotonic_time):
        minimum_time = (
            current_monotonic_time
            - self.duration_seconds
        )

        while (
            self.frames
            and self.frames[0][0] < minimum_time
        ):
            self.frames.popleft()

    def get_frames(self):
        """
        Renvoie uniquement les images.

        Cette méthode reste compatible avec VideoRecorder.start().
        """
        return [
            frame.copy()
            for _, _, frame in self.frames
        ]

    def get_entries(self):
        """
        Renvoie les horodatages et les images du buffer.

        Chaque entrée est un dictionnaire contenant :
        - monotonic_time
        - capture_time
        - frame
        """
        return [
            {
                "monotonic_time": monotonic_time,
                "capture_time": capture_time,
                "frame": frame.copy(),
            }
            for (
                monotonic_time,
                capture_time,
                frame,
            ) in self.frames
        ]

    def get_estimated_fps(self):
        duration = self.get_duration()
        frame_count = self.get_frame_count()

        if duration <= 0 or frame_count < 2:
            return 0.0

        return (frame_count - 1) / duration

    def get_first_capture_time(self):
        """
        Renvoie l'heure civile de la première image du buffer.
        """
        if not self.frames:
            return None

        return self.frames[0][1]

    def get_last_capture_time(self):
        """
        Renvoie l'heure civile de la dernière image du buffer.
        """
        if not self.frames:
            return None

        return self.frames[-1][1]

    def get_frame_count(self):
        return len(self.frames)

    def get_duration(self):
        if len(self.frames) < 2:
            return 0.0

        first_monotonic_time = self.frames[0][0]
        last_monotonic_time = self.frames[-1][0]

        return (
            last_monotonic_time
            - first_monotonic_time
        )

    def set_duration(self, duration_seconds):
        self.duration_seconds = max(
            0.0,
            float(duration_seconds),
        )

        self._remove_old_frames(
            time.monotonic()
        )

    def clear(self):
        self.frames.clear()