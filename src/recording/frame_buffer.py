import time
from collections import deque


class FrameBuffer:
    def __init__(self, duration_seconds=1.0):
        self.duration_seconds = duration_seconds
        self.frames = deque()

    def add_frame(self, frame):
        current_time = time.monotonic()

        # On stocke une copie, car l'image originale
        # pourra ensuite être modifiée par l'affichage.
        self.frames.append(
            (current_time, frame.copy())
        )

        self._remove_old_frames(current_time)

    def _remove_old_frames(self, current_time):
        minimum_time = (
            current_time - self.duration_seconds
        )

        while (
            self.frames
            and self.frames[0][0] < minimum_time
        ):
            self.frames.popleft()

    def get_frames(self):
        return [
            frame.copy()
            for _, frame in self.frames
        ]

    def get_frame_count(self):
        return len(self.frames)

    def get_duration(self):
        if len(self.frames) < 2:
            return 0.0

        first_time = self.frames[0][0]
        last_time = self.frames[-1][0]

        return last_time - first_time

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