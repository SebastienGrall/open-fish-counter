from datetime import datetime, timedelta
from pathlib import Path
import json
import re
import unicodedata

import cv2

from logging_utils.log_manager import get_logger


def make_safe_filename(value):
    value = str(value).strip()

    if not value:
        return "Station"

    normalized_value = unicodedata.normalize(
        "NFKD",
        value,
    )

    ascii_value = normalized_value.encode(
        "ascii",
        "ignore",
    ).decode("ascii")

    safe_value = re.sub(
        r"[\s\-]+",
        "_",
        ascii_value,
    )

    safe_value = re.sub(
        r"[^A-Za-z0-9_]",
        "",
        safe_value,
    )

    safe_value = re.sub(
        r"_+",
        "_",
        safe_value,
    )

    safe_value = safe_value.strip("._")

    return safe_value or "Station"


class VideoRecorder:
    METADATA_SCHEMA_VERSION = 1

    def __init__(
        self,
        recordings_directory,
        fps=25.0,
        max_video_duration_seconds=600.0,
    ):
        self.recordings_directory = Path(
            recordings_directory
        )

        self.fps = max(0.001, float(fps))
        self.max_video_duration_seconds = max(
            1.0,
            float(max_video_duration_seconds),
        )

        self.logger = get_logger("recorder")

        # Etat de la partie vidéo courante.
        self.writer = None
        self.output_path = None
        self.frame_size = None
        self.frame_count = 0
        self.part_start_time = None
        self.part_number = 0

        # Etat global de l'événement.
        self.station_name = "Station"
        self.safe_station_name = "Station"
        self.video_start_time = None
        self.event_detection_time = None
        self.event_id = None
        self.event_base_name = None
        self.event_manifest_path = None
        self.videos_directory = None
        self.event_total_frame_count = 0
        self.event_part_paths = []
        self.event_max_video_duration_seconds = None
        self.event_max_frames_per_part = None

    @property
    def is_recording(self):
        return self.writer is not None

    def set_max_video_duration_seconds(self, value):
        """Configure la durée des prochains événements."""
        self.max_video_duration_seconds = max(
            1.0,
            float(value),
        )

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
            self.logger.warning(
                "Impossible de démarrer : le pré-buffer est vide."
            )
            return False

        if fps is not None and fps > 0:
            self.fps = float(fps)

        first_frame = pre_event_frames[0]
        height, width = first_frame.shape[:2]
        self.frame_size = (width, height)

        if video_start_time is None:
            video_start_time = datetime.now().astimezone()

        self.video_start_time = video_start_time
        self.event_detection_time = datetime.now().astimezone()

        self.station_name = (
            str(station_name).strip()
            or "Station"
        )
        self.safe_station_name = make_safe_filename(
            self.station_name
        )

        event_timestamp = self.video_start_time.strftime(
            "%Y%m%d_%H%M%S_%f"
        )[:-3]

        self.event_id = (
            f"{self.safe_station_name}_{event_timestamp}"
        )
        self.event_base_name = (
            f"{self.safe_station_name}_"
            f"{self.video_start_time.strftime('%Y%m%d_%H%M%S')}"
        )

        station_directory = (
            self.recordings_directory
            / self.safe_station_name
        )
        day_directory = (
            station_directory
            / self.video_start_time.strftime("%Y-%m-%d")
        )
        self.videos_directory = day_directory / "videos"
        snapshots_directory = day_directory / "snapshots"

        self.videos_directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        snapshots_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.event_manifest_path = (
            self.videos_directory
            / f"{self.event_base_name}_event.json"
        )

        # La durée est figée pour tout l'événement.
        self.event_max_video_duration_seconds = (
            self.max_video_duration_seconds
        )
        self.event_max_frames_per_part = max(
            1,
            int(round(
                self.event_max_video_duration_seconds
                * self.fps
            )),
        )

        self.event_total_frame_count = 0
        self.event_part_paths = []
        self.part_number = 0

        if not self._open_next_part():
            self._reset_event_state()
            return False

        self.logger.info(
            "Démarrage événement | event_id=%s | fps=%.3f | "
            "resolution=%dx%d | durée_max_partie=%.1f s",
            self.event_id,
            self.fps,
            self.frame_size[0],
            self.frame_size[1],
            self.event_max_video_duration_seconds,
        )

        for frame in pre_event_frames:
            if not self.write_frame(frame):
                self.stop()
                return False

        return True

    def write_frame(self, frame):
        if not self.is_recording:
            return False

        if (
            self.frame_count
            >= self.event_max_frames_per_part
        ):
            if not self._rotate_part():
                return False

        height, width = frame.shape[:2]

        if (width, height) != self.frame_size:
            frame = cv2.resize(
                frame,
                self.frame_size,
            )

        self.writer.write(frame)
        self.frame_count += 1
        self.event_total_frame_count += 1

        return True

    def stop(self):
        if not self.is_recording:
            return None

        event_end_time = datetime.now().astimezone()
        last_output_path = self.output_path

        self._close_current_part(
            continues_in_next=False,
            part_end_time=event_end_time,
        )

        part_count = len(self.event_part_paths)

        try:
            self._finalize_part_metadata(
                part_count=part_count,
            )
            self._write_event_manifest(
                event_end_time=event_end_time,
            )
        except OSError as error:
            self.logger.error(
                "Impossible de finaliser les métadonnées "
                "de l'événement %s : %s",
                self.event_id,
                error,
            )

        self.logger.info(
            "Événement terminé | event_id=%s | parties=%d | "
            "images=%d",
            self.event_id,
            part_count,
            self.event_total_frame_count,
        )

        self._reset_event_state()

        return last_output_path

    def _open_next_part(self):
        self.part_number += 1
        self.frame_count = 0

        self.part_start_time = (
            self.video_start_time
            + timedelta(
                seconds=(
                    self.event_total_frame_count
                    / self.fps
                )
            )
        )

        filename = (
            f"{self.event_base_name}_"
            f"part{self.part_number:03d}.mp4"
        )
        self.output_path = (
            self.videos_directory / filename
        )

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(self.output_path),
            fourcc,
            self.fps,
            self.frame_size,
        )

        if not writer.isOpened():
            writer.release()
            self.logger.error(
                "Impossible d'ouvrir la partie vidéo : %s",
                self.output_path,
            )
            self.writer = None
            self.output_path = None
            self.part_number -= 1
            return False

        self.writer = writer
        self.event_part_paths.append(
            self.output_path
        )

        self.logger.info(
            "Partie vidéo démarrée | event_id=%s | "
            "partie=%d | fichier=%s",
            self.event_id,
            self.part_number,
            self.output_path,
        )

        return True

    def _rotate_part(self):
        next_part_start_time = (
            self.video_start_time
            + timedelta(
                seconds=(
                    self.event_total_frame_count
                    / self.fps
                )
            )
        )

        self._close_current_part(
            continues_in_next=True,
            part_end_time=next_part_start_time,
        )

        return self._open_next_part()

    def _close_current_part(
        self,
        continues_in_next,
        part_end_time,
    ):
        if self.writer is None:
            return

        output_path = self.output_path
        part_number = self.part_number
        part_frame_count = self.frame_count
        part_start_time = self.part_start_time

        self.writer.release()
        self.writer = None

        self._write_part_metadata(
            output_path=output_path,
            part_number=part_number,
            part_start_time=part_start_time,
            part_end_time=part_end_time,
            frame_count=part_frame_count,
            continues_in_next=continues_in_next,
            part_count=None,
        )

        self.logger.info(
            "Partie vidéo terminée | event_id=%s | "
            "partie=%d | fichier=%s | images=%d",
            self.event_id,
            part_number,
            output_path,
            part_frame_count,
        )

        self.output_path = None
        self.frame_count = 0
        self.part_start_time = None

    def _write_part_metadata(
        self,
        output_path,
        part_number,
        part_start_time,
        part_end_time,
        frame_count,
        continues_in_next,
        part_count,
    ):
        frame_width, frame_height = self.frame_size

        metadata = {
            "schema_version": self.METADATA_SCHEMA_VERSION,
            "record_type": "video_part",
            "event_id": self.event_id,
            "station_name": self.station_name,
            "video_file": output_path.name,
            "part_number": part_number,
            "part_count": part_count,
            "continued_from_previous": part_number > 1,
            "continues_in_next": bool(continues_in_next),
            "event_start_time": self._isoformat(
                self.video_start_time
            ),
            "event_detection_time": self._isoformat(
                self.event_detection_time
            ),
            "video_start_time": self._isoformat(
                part_start_time
            ),
            "video_end_time": self._isoformat(
                part_end_time
            ),
            "frame_count": frame_count,
            "recording_fps": round(self.fps, 3),
            "frame_width": frame_width,
            "frame_height": frame_height,
        }

        self._write_json_atomic(
            output_path.with_suffix(".json"),
            metadata,
        )

    def _finalize_part_metadata(self, part_count):
        for index, video_path in enumerate(
            self.event_part_paths,
            start=1,
        ):
            metadata_path = video_path.with_suffix(
                ".json"
            )

            with metadata_path.open(
                "r",
                encoding="utf-8",
            ) as metadata_file:
                metadata = json.load(metadata_file)

            metadata["part_count"] = part_count
            metadata["continues_in_next"] = (
                index < part_count
            )

            self._write_json_atomic(
                metadata_path,
                metadata,
            )

    def _write_event_manifest(self, event_end_time):
        parts = []

        for index, video_path in enumerate(
            self.event_part_paths,
            start=1,
        ):
            parts.append({
                "part_number": index,
                "video_file": video_path.name,
                "metadata_file": (
                    video_path.with_suffix(".json").name
                ),
            })

        manifest = {
            "schema_version": self.METADATA_SCHEMA_VERSION,
            "record_type": "event_manifest",
            "event_id": self.event_id,
            "station_name": self.station_name,
            "event_start_time": self._isoformat(
                self.video_start_time
            ),
            "event_detection_time": self._isoformat(
                self.event_detection_time
            ),
            "event_end_time": self._isoformat(
                event_end_time
            ),
            "recording_fps": round(self.fps, 3),
            "total_frame_count": (
                self.event_total_frame_count
            ),
            "part_count": len(self.event_part_paths),
            "max_part_duration_seconds": (
                self.event_max_video_duration_seconds
            ),
            "parts": parts,
        }

        self._write_json_atomic(
            self.event_manifest_path,
            manifest,
        )

        self.logger.info(
            "Manifeste événement sauvegardé : %s",
            self.event_manifest_path,
        )

    @staticmethod
    def _write_json_atomic(output_path, data):
        temporary_path = output_path.with_suffix(
            output_path.suffix + ".tmp"
        )

        with temporary_path.open(
            "w",
            encoding="utf-8",
        ) as output_file:
            json.dump(
                data,
                output_file,
                indent=4,
                ensure_ascii=False,
            )

        temporary_path.replace(output_path)

    @staticmethod
    def _isoformat(value):
        if value is None:
            return None

        return value.isoformat(
            timespec="milliseconds"
        )

    def _reset_event_state(self):
        self.writer = None
        self.output_path = None
        self.frame_size = None
        self.frame_count = 0
        self.part_start_time = None
        self.part_number = 0

        self.station_name = "Station"
        self.safe_station_name = "Station"
        self.video_start_time = None
        self.event_detection_time = None
        self.event_id = None
        self.event_base_name = None
        self.event_manifest_path = None
        self.videos_directory = None
        self.event_total_frame_count = 0
        self.event_part_paths = []
        self.event_max_video_duration_seconds = None
        self.event_max_frames_per_part = None
