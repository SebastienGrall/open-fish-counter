from datetime import datetime
from pathlib import Path
import json
import cv2
import re
import unicodedata

def make_safe_filename(value):
        value = str(value).strip()

        if not value:
            return "Station"

        # Transforme les caractères accentués :
        # "à" devient "a", "é" devient "e", etc.
        normalized_value = unicodedata.normalize(
            "NFKD",
            value,
        )

        ascii_value = normalized_value.encode(
            "ascii",
            "ignore",
        ).decode("ascii")

        # Les espaces et séparateurs deviennent
        # des underscores.
        safe_value = re.sub(
            r"[\s\-]+",
            "_",
            ascii_value,
        )

        # Retire les caractères incompatibles
        # ou risqués dans un nom de fichier.
        safe_value = re.sub(
            r"[^A-Za-z0-9_]",
            "",
            safe_value,
        )

        # Évite les underscores successifs.
        safe_value = re.sub(
            r"_+",
            "_",
            safe_value,
        )

        safe_value = safe_value.strip(
            "._"
        )

        if not safe_value:
            return "Station"

        return safe_value

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
        self.station_name = "Station"
        self.writer = None
        self.output_path = None
        self.frame_size = None
        self.frame_count = 0
        self.video_start_time = None
        self.event_detection_time = None

    @property
    def is_recording(self):
        return self.writer is not None

    def start(
        self,
        pre_event_frames,
        video_start_time=None,
        fps=None,
        station_name="Station",
        ):
        if self.is_recording:
            return False

        if not pre_event_frames:
            print(
                "Impossible de démarrer : "
                "le pré-buffer est vide."
            )
            return False

        if fps is not None and fps > 0:
            self.fps = float(fps)

        first_frame = pre_event_frames[0]

        height, width = first_frame.shape[:2]

        self.video_start_time = video_start_time
        self.event_detection_time = datetime.now().astimezone()

        self.frame_size = (width, height)

        if video_start_time is None:
            video_start_time = datetime.now().astimezone()

        day_directory = (
            self.recordings_directory
            / video_start_time.strftime("%Y-%m-%d")
        )

        day_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.station_name = (
            str(station_name).strip()
            or "Station"
        )

        safe_station_name = make_safe_filename(
            self.station_name
        )

        filename = (
            f"{safe_station_name}_"
            f"{video_start_time.strftime('%H-%M-%S-%f')[:-3]}"
            ".mp4"
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

        print(
            f"FPS utilisés pour le fichier : "
            f"{self.fps:.2f}"
        )

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
        video_start_time = self.video_start_time
        video_end_time = datetime.now().astimezone()

        self.writer.release()

        print(
            f"Enregistrement terminé : "
            f"{output_path}"
        )

        print(
            f"Nombre d'images enregistrées : "
            f"{frame_count}"
        )

        try:
            self._write_metadata(
                output_path=output_path,
                video_start_time=video_start_time,
                video_end_time=video_end_time,
                frame_count=frame_count,
            )

        except OSError as error:
            print(
                f"Impossible d'enregistrer "
                f"les métadonnées : {error}"
            )

        self.writer = None
        self.output_path = None
        self.frame_size = None
        self.frame_count = 0
        self.video_start_time = None
        self.event_detection_time = None
        self.station_name = "Station"

        return output_path

    def _write_metadata(
        self,
        output_path,
        video_start_time,
        video_end_time,
        frame_count,
    ):
        if video_start_time is not None:
            start_time_text = video_start_time.isoformat(
                timespec="milliseconds"
            )
        else:
            start_time_text = None

        if self.event_detection_time is not None:
            detection_time_text = (
                self.event_detection_time.isoformat(
                    timespec="milliseconds"
                )
            )
        else:
            detection_time_text = None

        end_time_text = video_end_time.isoformat(
            timespec="milliseconds"
        )

        if self.frame_size is not None:
            frame_width, frame_height = self.frame_size
        else:
            frame_width = None
            frame_height = None

        metadata = {
            "station_name": self.station_name,
            "video_file": output_path.name,
            "video_start_time": start_time_text,
            "event_detection_time": detection_time_text,
            "video_end_time": end_time_text,
            "frame_count": frame_count,
            "recording_fps": round(self.fps, 3),
            "frame_width": frame_width,
            "frame_height": frame_height,
        }

        metadata_path = output_path.with_suffix(
            ".json"
        )

        temporary_path = metadata_path.with_suffix(
            ".json.tmp"
        )

        with temporary_path.open(
            "w",
            encoding="utf-8",
        ) as metadata_file:
            json.dump(
                metadata,
                metadata_file,
                indent=4,
                ensure_ascii=False,
            )

        temporary_path.replace(metadata_path)

        print(
            f"Métadonnées sauvegardées : "
            f"{metadata_path}"
        )