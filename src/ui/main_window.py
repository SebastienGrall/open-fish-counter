import sys
import time
from pathlib import Path
import cv2
import gc
import shutil

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QCheckBox,
    QVBoxLayout,
    QPushButton,
    QComboBox,
    QDialog,
    QMessageBox,
)

from ui.video_widget import VideoWidget
from motion.motion_detector import MotionDetector
from recording.frame_buffer import FrameBuffer
from recording.video_recorder import VideoRecorder
from ui.settings_dialog import SettingsDialog
from config.config_manager import ConfigManager
from config.config_paths import (
    prepare_user_config_file,
)
from camera.camera_manager import CameraManager
from utils.path_utils import (
    prepare_recordings_directory,
)
from version import APP_NAME, APP_VERSION
from logging_utils.log_manager import (
    get_logger,
    setup_logging,
)


PROJECT_ROOT = (
    Path(__file__).resolve()
    .parent
    .parent
    .parent
)


RECORDINGS_DIRECTORY = (
    PROJECT_ROOT
     / "data" 
     / "recordings"
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            f"{APP_NAME} - {APP_VERSION}"
        )
        
        self.resize(1200, 800)

        self.video_widget = VideoWidget()

        (
            self.config_file,
            config_initialization_status,
        ) = prepare_user_config_file()

        self.config_manager = ConfigManager(
            self.config_file
        )

        app_config = self.config_manager.load()

        if config_initialization_status == "new":
            self.config_manager.save(
                app_config
            )

        camera_config = app_config["camera"]
        detection_config = app_config["detection"]
        recording_config = app_config["recording"]
        grid_config = app_config["grid"]
        cells_config = app_config["cells"]
        station_config = app_config["station"]

        self.station_name = str(
            station_config.get(
                "name",
                "Station",
            )
        ).strip()

        if not self.station_name:
            self.station_name = "Station"

        self.video_widget.grid_rows = int(
            grid_config.get(
                "rows",
                8,
            )
        )

        self.video_widget.grid_cols = int(
            grid_config.get(
                "cols",
                8,
            )
        )

        self.video_widget.cells = {}

        cell_count = (
            self.video_widget.grid_rows
            * self.video_widget.grid_cols
        )

        for cell_id in range(cell_count):
            saved_cell = cells_config.get(
                str(cell_id),
                cells_config.get(
                    cell_id,
                    {},
                ),
            )

            self.video_widget.cells[cell_id] = {
                "enabled": bool(
                    saved_cell.get(
                        "enabled",
                        True,
                    )
                ),
                "threshold": int(
                    saved_cell.get(
                        "threshold",
                        10,
                    )
                ),
            }

        # Création du moteur de détection avec les paramètres chargés.
        self.motion_detector = MotionDetector(
            grid_rows=self.video_widget.grid_rows,
            grid_cols=self.video_widget.grid_cols,
            pixel_threshold=int(
                detection_config.get(
                    "pixel_threshold",
                    25,
                )
            ),
        )

        # Paramètres généraux chargés.
        self.camera_index = int(
            camera_config.get(
                "index",
                1,
            )
        )

        self.camera_backend = str(
            camera_config.get(
                "backend",
                "opencv",
            )
        ).strip().lower()

        if self.camera_backend not in (
            "opencv",
            "ic4",
        ):
            self.camera_backend = "opencv"

        configured_camera_serial = (
            camera_config.get(
                "serial",
                None,
            )
        )

        if configured_camera_serial is None:
            self.camera_serial = None
        else:
            self.camera_serial = str(
                configured_camera_serial
            ).strip()

            if not self.camera_serial:
                self.camera_serial = None

        self.camera_width = int(
            camera_config.get(
                "width",
                720,
            )
        )

        self.camera_height = int(
            camera_config.get(
                "height",
                540,
            )
        )

        self.camera_fps = float(
            camera_config.get(
                "fps",
                30.0,
            )
        )

        self.camera_exposure_auto = bool(
            camera_config.get(
                "exposure_auto",
                True,
            )
        )

        self.camera_exposure_time = float(
            camera_config.get(
                "exposure_time",
                5000.0,
            )
        )

        self.camera_gain_auto = bool(
            camera_config.get(
                "gain_auto",
                True,
            )
        )

        self.camera_gain = float(
            camera_config.get(
                "gain",
                0.0,
            )
        )

        self.required_motion_frames = int(
            detection_config.get(
                "required_motion_frames",
                3,
            )
        )

        self.no_motion_delay = float(
            detection_config.get(
                "no_motion_delay",
                1.0,
            )
        )

        self.pre_event_seconds = float(
            recording_config.get(
                "pre_event_seconds",
                1.0,
            )
        )

        self.disk_warning_percent = int(
            recording_config.get(
                "disk_warning_percent",
                90,
            )
        )

        self.disk_stop_percent = int(
            recording_config.get(
                "disk_stop_percent",
                95,
            )
        )

        self.disk_warning_percent = max(
            1,
            min(
                99,
                self.disk_warning_percent,
            ),
        )

        self.disk_stop_percent = max(
            self.disk_warning_percent + 1,
            min(
                100,
                self.disk_stop_percent,
            ),
        )

        self.max_video_duration_minutes = int(
            recording_config.get(
                "max_video_duration_minutes",
                10,
            )
        )

        self.max_video_duration_minutes = max(
            1,
            min(
                1440,
                self.max_video_duration_minutes,
            ),
        )

        self.max_video_duration_seconds = (
            self.max_video_duration_minutes
            * 60.0
        )

        configured_recordings_directory = (
            recording_config.get(
                "output_directory",
                str(
                    PROJECT_ROOT
                    / "data"
                    / "recordings"
                ),
            )
        )

        (
            self.recordings_directory,
            self.recordings_directory_was_replaced,
        ) = prepare_recordings_directory(
            configured_recordings_directory,
            logger=None,
        )

        self.logs_directory = (
            self.recordings_directory
            / "logs"
        )

        self.logs_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.logger = setup_logging(
            self.logs_directory
        )

        self.logger.info(
            "Configuration utilisateur : %s",
            self.config_file,
        )

        if config_initialization_status == "migrated":
            self.logger.info(
                "Ancienne configuration copiée vers "
                "le dossier utilisateur."
            )

        elif config_initialization_status == "new":
            self.logger.info(
                "Aucune ancienne configuration trouvée. "
                "Une nouvelle configuration utilisateur "
                "sera créée."
            )

        if self.recordings_directory_was_replaced:
            self.logger.warning(
                "Le dossier d'enregistrement configuré "
                "a été remplacé."
            )

            self.logger.warning(
                "Ancien dossier : %s",
                configured_recordings_directory,
            )

            self.logger.warning(
                "Nouveau dossier : %s",
                self.recordings_directory,
            )

        self.logger.info(
            "Démarrage de %s version %s",
            APP_NAME,
            APP_VERSION,
        )

        self.logger.info(
            "Station configurée : %s",
            self.station_name,
        )
        
        self.snapshots_enabled = bool(
            recording_config.get(
                "snapshots_enabled",
                False,
            )
        )

        # Buffer créé seulement après avoir défini pre_event_seconds.
        self.frame_buffer = FrameBuffer(
            duration_seconds=self.pre_event_seconds
        )

        # État de la sélection.
        self.current_cell = None

        # État de détection.
        self.event_active = False
        self.motion_frame_count = 0
        self.last_motion_time = None
        self.event_started_this_frame = False

        # État de l'enregistrement.
        self.recording_enabled = True

        # Indique que les enregistrements sont temporairement
        # bloqués en raison de l'occupation du disque.
        self.disk_recording_blocked = False

        # Évite de répéter le même avertissement dans les logs
        # à chaque contrôle du disque.
        self.last_disk_status = None

        # Ouverture de la caméra.
        self.camera_manager = CameraManager(
            camera_index=self.camera_index,
            requested_width=self.camera_width,
            requested_height=self.camera_height,
            requested_fps=self.camera_fps,
            camera_backend=self.camera_backend,
            camera_serial=self.camera_serial,
            exposure_auto=(
                self.camera_exposure_auto
            ),
            exposure_time=(
                self.camera_exposure_time
            ),
            gain_auto=(
                self.camera_gain_auto
            ),
            gain=self.camera_gain,
        )
        
        camera_opened = (
            self.camera_manager.open()
        )

        self.logger.info(
            "Caméra configurée | backend=%s | "
            "index=%d | série=%s",
            self.camera_backend,
            self.camera_index,
            self.camera_serial or "aucune",
        )

        if not camera_opened:
            self.video_widget.setText(
                "Caméra indisponible\n"
                f"{self.camera_manager.last_error}"
            )

        camera_fps = (
            self.camera_manager.get_recording_fps()
        )

        self.video_recorder = VideoRecorder(
            recordings_directory=(
                self.recordings_directory
            ),
            fps=camera_fps,
            max_video_duration_seconds=(
                self.max_video_duration_seconds
            ),
        )
        

        self.logger.info(
            "Fréquence d'enregistrement : %.2f images/s",
            camera_fps,
        )

        # Signal de sélection des cellules.
        self.video_widget.cell_selected.connect(
            self.on_cell_selected
        )

        # Réglages de la cellule sélectionnée.
        self.cell_label = QLabel(
            "Cellule : aucune"
        )

        self.enabled_checkbox = QCheckBox(
            "Activée"
        )

        self.enabled_checkbox.setChecked(True)

        self.enabled_checkbox.checkStateChanged.connect(
            self.on_enabled_changed
        )

        self.threshold_spinbox = QSpinBox()
        self.threshold_spinbox.setRange(0, 100)
        self.threshold_spinbox.setValue(10)

        self.threshold_spinbox.valueChanged.connect(
            self.on_threshold_changed
        )

        # Indicateurs de détection.
        self.buffer_status_label = QLabel(
            "Buffer : 0 image, 0.00 s"
        )

        self.event_status_label = QLabel(
            "État : aucun mouvement"
        )

        self.triggered_cells_label = QLabel(
            "Cellules déclenchées : 0"
        )

        self.max_motion_label = QLabel(
            "Mouvement maximal : 0.0 %"
        )

        self.event_status_label.setStyleSheet(
            "font-weight: bold; color: green;"
        )

        # Contrôles de l'enregistrement.
        self.recording_status_label = QLabel(
            "Enregistrement automatique : ACTIVÉ"
        )

        self.disk_status_label = QLabel(
            "Disque : vérification en cours..."
        )

        self.disk_status_label.setWordWrap(
            True
        )

        self.disk_status_label.setStyleSheet(
            "font-weight: bold; color: gray;"
        )

        self.disk_status_label.setToolTip(
            "Occupation du disque contenant le dossier "
            "d'enregistrement."
        )

        self.recording_status_label.setStyleSheet(
            "font-weight: bold; color: green;"
        )

        self.start_recording_button = QPushButton(
            "Activer l'enregistrement"
        )

        self.stop_recording_button = QPushButton(
            "Arrêter l'enregistrement"
        )

        self.start_recording_button.clicked.connect(
            self.enable_recording
        )

        self.stop_recording_button.clicked.connect(
            self.disable_recording
        )

        self.start_recording_button.setEnabled(False)
        self.stop_recording_button.setEnabled(True)

        # Choix du mode d'affichage.
        self.display_mode_combo = QComboBox()

        self.display_mode_combo.addItem(
            "Grille complète",
            "full",
        )

        self.display_mode_combo.addItem(
            "Détections uniquement",
            "detections",
        )

        self.display_mode_combo.addItem(
            "Image seule",
            "none",
        )

        self.display_mode_combo.currentIndexChanged.connect(
            self.on_display_mode_changed
        )

        # Fenêtre des paramètres généraux.
        self.settings_button = QPushButton(
            "Paramètres"
        )

        self.settings_button.clicked.connect(
            self.open_settings_dialog
        )

        self.best_snapshot_frame = None
        self.best_snapshot_score = 0.0

        main_widget = QWidget()

        layout = QHBoxLayout(main_widget)

        side_panel = QWidget()

        side_layout = QVBoxLayout(side_panel)

        side_layout.addWidget(
            QLabel("Mode d'affichage")
        )

        side_layout.addWidget(
            self.display_mode_combo
        )

        side_layout.addSpacing(20)

        side_layout.addWidget(self.cell_label)
        side_layout.addWidget(self.enabled_checkbox)

        side_layout.addWidget(QLabel("Seuil (%)"))
        side_layout.addWidget(self.threshold_spinbox)

        side_layout.addSpacing(30)

        side_layout.addWidget(QLabel("Détection"))
        side_layout.addWidget(self.event_status_label)
        side_layout.addWidget(self.triggered_cells_label)
        side_layout.addWidget(self.max_motion_label)
        side_layout.addWidget(self.buffer_status_label)

        side_layout.addSpacing(30)

        side_layout.addWidget(
            QLabel("Enregistrement")
        )

        side_layout.addWidget(
            self.recording_status_label
        )

        side_layout.addWidget(
            self.disk_status_label
        )

        side_layout.addWidget(
            self.start_recording_button
        )

        side_layout.addWidget(
            self.stop_recording_button
        )

        side_layout.addSpacing(30)

        side_layout.addWidget(
            self.settings_button
        )

        side_layout.addStretch()

        layout.addWidget(self.video_widget, 4)
        layout.addWidget(side_panel, 1)

        self.setCentralWidget(main_widget)

        self.apply_recordings_directory()
         
        self.timer = QTimer()

        self.timer.timeout.connect(self.update_frame)

        self.timer.start(30)

        # L'espace disque n'a pas besoin d'être vérifié à
        # chaque image. Un contrôle toutes les dix secondes
        # est suffisant.
        self.disk_timer = QTimer(self)

        self.disk_timer.timeout.connect(
            self.check_disk_usage
        )

        self.disk_timer.start(
            10000
        )

        # Premier contrôle immédiat sans attendre dix secondes.
        self.check_disk_usage()

        # Ouvre la fenêtre en maximisé
        self.showMaximized()

    def update_frame(self):
        if not self.camera_manager.is_open:
            reconnected = (
                self.camera_manager.try_reconnect()
            )

            if not reconnected:
                self.video_widget.set_camera_message(
                    "Caméra indisponible\n"
                    "Tentative de reconnexion en cours..."
                )
                return

            # La caméra vient de revenir.
            self.motion_detector.reset()
            self.frame_buffer.clear()

            self.event_active = False
            self.motion_frame_count = 0
            self.last_motion_time = None
            self.event_started_this_frame = False

        ok, frame = self.camera_manager.read()

        if not ok:
            if self.video_recorder.is_recording:
                saved_path = (
                    self.video_recorder.stop()
                )

                if saved_path is not None:
                    print(
                        "Vidéo finalisée après perte caméra : "
                        f"{saved_path}"
                    )

            self.event_active = False
            self.motion_frame_count = 0
            self.last_motion_time = None

            self.video_widget.set_camera_message(
                "Connexion caméra perdue\n"
                "Tentative de reconnexion en cours..."
            )

            return

        self.event_started_this_frame = False

        self.frame_buffer.add_frame(frame)
               
        self.buffer_status_label.setText(
            f"Buffer : "
            f"{self.frame_buffer.get_frame_count()} images, "
            f"{self.frame_buffer.get_duration():.2f} s"
        )

        motion_levels = (
            self.motion_detector.process_frame(
                frame
            )
        )

        self.video_widget.set_motion_levels(
            motion_levels
        )

        event_data = self.update_event_indicator(
            motion_levels
        )

        if (
            self.snapshots_enabled
            and self.event_active
        ):
            current_motion_score = float(
                event_data.get(
                    "max_motion",
                    0.0,
                )
            )

            if (
                self.best_snapshot_frame is None
                or current_motion_score
                > self.best_snapshot_score
            ):
                self.best_snapshot_frame = (
                    frame.copy()
                )

                self.best_snapshot_score = (
                    current_motion_score
                )

        if (
            self.event_active
            and self.video_recorder.is_recording
            and not self.event_started_this_frame
        ):
            self.video_recorder.write_frame(
                frame
            )

        self.video_widget.set_frame(frame)

    def enable_recording(self):
        if self.disk_recording_blocked:
            self.logger.warning(
                "Activation des enregistrements refusée : "
                "le disque a atteint le seuil critique."
            )

            self.update_recording_controls()

            return

        self.recording_enabled = True

        self.update_recording_controls()

        self.logger.info(
            "Enregistrement automatique activé."
        )

    def disable_recording(self):
        self.recording_enabled = False

        self.update_recording_controls()

        # Si un fichier est actuellement ouvert,
        # on le termine proprement.
        if self.video_recorder.is_recording:
            snapshot_path = (
                self.save_event_snapshot()
            )

            saved_path = (
                self.video_recorder.stop()
            )

            if saved_path is not None:
                self.logger.info(
                    "Enregistrement interrompu et "
                    "sauvegardé : %s",
                    saved_path,
                )

            if snapshot_path is not None:
                self.logger.info(
                    "Snapshot sauvegardé : %s",
                    snapshot_path,
                )

        self.logger.info(
            "Enregistrement automatique arrêté."
        )

    def closeEvent(self, event):
        self.logger.info(
            "Fermeture de l'application."
        )

        # Empêche tout nouveau contrôle vidéo ou disque.
        self.timer.stop()
        self.disk_timer.stop()

        try:
            self.timer.timeout.disconnect(
                self.update_frame
            )

        except RuntimeError:
            pass

        try:
            self.disk_timer.timeout.disconnect(
                self.check_disk_usage
            )

        except RuntimeError:
            pass

        if self.video_recorder.is_recording:
            self.logger.info(
                "Finalisation de l'enregistrement "
                "avant fermeture."
            )

            self.video_recorder.stop()

        # Libère les images conservées par l'application.
        self.best_snapshot_frame = None

        self.frame_buffer.clear()
        self.motion_detector.reset()

        # Arrête le flux puis libère explicitement IC4.
        self.camera_manager.shutdown()

        # Détruit les derniers objets associés pendant que
        # les extensions Python sont encore initialisées.
        gc.collect()

        self.logger.info(
            "Fermeture de la caméra terminée."
        )

        super().closeEvent(event)

    def on_cell_selected(self, cell_id):
        self.current_cell = cell_id

        self.cell_label.setText(
            f"Cellule : {cell_id}"
        )

        cell = self.video_widget.cells[cell_id]

        self.enabled_checkbox.blockSignals(True)
        self.enabled_checkbox.setChecked(
            cell["enabled"]
        )
        self.enabled_checkbox.blockSignals(False)

        # Évite que setValue() déclenche on_threshold_changed()
        self.threshold_spinbox.blockSignals(True)
        self.threshold_spinbox.setValue(
            cell["threshold"]
        )
        self.threshold_spinbox.blockSignals(False)

    def on_event_started(self):
        self.event_started_this_frame = True

        self.reset_snapshot_state()

        pre_event_frames = self.frame_buffer.get_frames()

        video_start_time = (
            self.frame_buffer.get_first_capture_time()
        )

        buffered_frame_count = len(
            pre_event_frames
        )

        buffered_duration = (
            self.frame_buffer.get_duration()
        )

        estimated_fps = (
            self.frame_buffer.get_estimated_fps()
        )

        if estimated_fps <= 0:
            estimated_fps = 25.0

        print("=== DÉBUT DE L'ÉVÉNEMENT ===")

        print(
            f"Pré-buffer récupéré : "
            f"{buffered_frame_count} images, "
            f"{buffered_duration:.2f} seconde(s)"
        )

        if video_start_time is not None:
            formatted_start_time = (
                video_start_time.isoformat(
                    timespec="milliseconds"
                )
            )

            print(
                f"Première image du clip : "
                f"{formatted_start_time}"
            )

        print(
            f"FPS estimés sur le pré-buffer : "
            f"{estimated_fps:.2f}"
        )

        if self.disk_recording_blocked:
            self.logger.warning(
                "Événement détecté, mais aucun fichier "
                "n'est créé car le disque a atteint "
                "le seuil critique."
            )

            return

        if not self.recording_enabled:
            print(
                "Événement détecté, mais "
                "l'enregistrement est désactivé."
            )

            return

        self.video_recorder.start(
            pre_event_frames=pre_event_frames,
            video_start_time=video_start_time,
            fps=estimated_fps,
            station_name=self.station_name,
        )

    def on_event_ended(self):
        self.logger.info("Fin d'événement")

        if not self.video_recorder.is_recording:
            self.reset_snapshot_state()
            return

        snapshot_path = self.save_event_snapshot()

        saved_path = self.video_recorder.stop()

        if saved_path is not None:
            self.logger.info(
                "Vidéo sauvegardée : %s",
                saved_path,
            )

        if snapshot_path is not None:
            self.logger.info(
                "Snapshot sauvegardé : %s",
                snapshot_path,
            )

        self.reset_snapshot_state()

    def save_grid_config(self):
        config = {
            "station": {
                "name": self.station_name,
            },
            "camera": {
                "backend": self.camera_backend,
                "serial": self.camera_serial,
                "index": self.camera_index,
                "width": self.camera_width,
                "height": self.camera_height,
                "fps": self.camera_fps,
                "exposure_auto": (
                    self.camera_exposure_auto
                ),
                "exposure_time": (
                    self.camera_exposure_time
                ),
                "gain_auto": (
                    self.camera_gain_auto
                ),
                "gain": self.camera_gain,
            },
            "detection": {
                "pixel_threshold": (
                    self.motion_detector.pixel_threshold
                ),
                "required_motion_frames": (
                    self.required_motion_frames
                ),
                "no_motion_delay": (
                    self.no_motion_delay
                ),
            },
            "recording": {
                "pre_event_seconds": (
                    self.pre_event_seconds
                ),
                "output_directory": str(
                    self.recordings_directory
                ),
                "snapshots_enabled": (
                    self.snapshots_enabled
                ),
                "disk_warning_percent": (
                    self.disk_warning_percent
                ),
                "disk_stop_percent": (
                    self.disk_stop_percent
                ),
                "max_video_duration_minutes": (
                    self.max_video_duration_minutes
                ),
            },
            "grid": {
                "rows": (
                    self.video_widget.grid_rows
                ),
                "cols": (
                    self.video_widget.grid_cols
                ),
            },
            "cells": self.video_widget.cells,
        }

        self.config_manager.save(config)
        
    def on_threshold_changed(self, value):
        if self.current_cell is None:
            return

        self.video_widget.cells[self.current_cell]["threshold"] = value

        print(
            f"Cellule {self.current_cell} "
            f"nouveau seuil : {value}"
        )

        self.save_grid_config()

    def on_enabled_changed(self, state):
        if self.current_cell is None:
            return

        enabled = self.enabled_checkbox.isChecked()

        self.video_widget.cells[self.current_cell]["enabled"] = enabled

        print(
            f"Cellule {self.current_cell} "
            f"activée : {enabled}"
        )

        self.save_grid_config()

    def update_event_indicator(self, motion_levels):
        triggered_cells = []
        max_motion = 0.0

        for cell_id, motion_percentage in motion_levels.items():
            cell = self.video_widget.cells[cell_id]

            if not cell["enabled"]:
                continue

            max_motion = max(
                max_motion,
                motion_percentage,
            )

            if motion_percentage >= cell["threshold"]:
                triggered_cells.append(cell_id)

        triggered_count = len(triggered_cells)
        current_time = time.monotonic()

        # Mouvement brut détecté sur cette image
        if triggered_count > 0:
            self.motion_frame_count += 1
            self.last_motion_time = current_time

            # Déclenchement après plusieurs images consécutives
            if (
                not self.event_active
                and self.motion_frame_count
                >= self.required_motion_frames
            ):
                self.event_active = True
                self.on_event_started()

        else:
            # Sans mouvement, la série d'images consécutives est interrompue
            self.motion_frame_count = 0

            # Fin de l'événement après le délai sans mouvement
            if (
                self.event_active
                and self.last_motion_time is not None
                and current_time - self.last_motion_time
                >= self.no_motion_delay
            ):
                self.event_active = False
                self.on_event_ended()

        # Mise à jour de l'interface selon l'état stabilisé
        if self.event_active:
            self.event_status_label.setText(
                "État : MOUVEMENT DÉTECTÉ"
            )

            self.event_status_label.setStyleSheet(
                "font-weight: bold; color: red;"
            )

        elif triggered_count > 0:
            self.event_status_label.setText(
                "État : confirmation en cours…"
            )

            self.event_status_label.setStyleSheet(
                "font-weight: bold; color: orange;"
            )

        else:
            self.event_status_label.setText(
                "État : aucun mouvement"
            )

            self.event_status_label.setStyleSheet(
                "font-weight: bold; color: green;"
            )

        self.triggered_cells_label.setText(
            f"Cellules déclenchées : {triggered_count}"
        )

        self.max_motion_label.setText(
            f"Mouvement maximal : {max_motion:.1f} %"
        )

        return {
            "triggered_count": triggered_count,
            "max_motion": max_motion,
        }

    def on_display_mode_changed(self):
        display_mode = (
            self.display_mode_combo.currentData()
        )

        self.video_widget.set_display_mode(
            display_mode
        )

    def open_settings_dialog(self):
        timer_was_active = self.timer.isActive()

        ic4_devices = (
            self.camera_manager
            .get_available_ic4_devices()
        )

        if timer_was_active:
            self.logger.debug(
                "Suspension de l'acquisition pendant "
                "l'ouverture des paramètres."
            )

            self.timer.stop()

        try:
            dialog = SettingsDialog(
                station_name=self.station_name,
                pixel_threshold=(
                    self.motion_detector.pixel_threshold
                ),
                required_motion_frames=(
                    self.required_motion_frames
                ),
                no_motion_delay=(
                    self.no_motion_delay
                ),
                pre_event_seconds=(
                    self.pre_event_seconds
                ),
                recordings_directory=str(
                    self.recordings_directory
                ),
                snapshots_enabled=(
                    self.snapshots_enabled
                ),
                disk_warning_percent=(
                    self.disk_warning_percent
                ),
                disk_stop_percent=(
                    self.disk_stop_percent
                ),
                max_video_duration_minutes=(
                    self.max_video_duration_minutes
                ),
                camera_backend=self.camera_backend,
                camera_serial=self.camera_serial,
                ic4_devices=ic4_devices,
                camera_index=self.camera_index,
                camera_width=self.camera_width,
                camera_height=self.camera_height,
                camera_fps=self.camera_fps,
                camera_exposure_auto=(
                    self.camera_exposure_auto
                ),
                camera_exposure_time=(
                    self.camera_exposure_time
                ),
                camera_gain_auto=(
                    self.camera_gain_auto
                ),
                camera_gain=self.camera_gain,
                parent=self,
            )

            result = dialog.exec()

            if (
                result
                != QDialog.DialogCode.Accepted
            ):
                return

            settings = dialog.get_settings()

            self.apply_general_settings(
                settings
            )

        finally:
            if timer_was_active:
                self.timer.start()

                self.logger.debug(
                    "Reprise de l'acquisition après "
                    "fermeture des paramètres."
                )

    def apply_general_settings(self, settings):
        self.motion_detector.pixel_threshold = int(
            settings["pixel_threshold"]
        )

        self.required_motion_frames = int(
            settings["required_motion_frames"]
        )

        self.no_motion_delay = float(
            settings["no_motion_delay"]
        )

        self.pre_event_seconds = float(
            settings["pre_event_seconds"]
        )

        self.frame_buffer.set_duration(
            self.pre_event_seconds
        )

        self.snapshots_enabled = bool(
            settings.get(
                "snapshots_enabled",
                False,
            )
        )

        new_disk_warning_percent = int(
            settings.get(
                "disk_warning_percent",
                90,
            )
        )

        new_disk_stop_percent = int(
            settings.get(
                "disk_stop_percent",
                95,
            )
        )

        new_disk_warning_percent = max(
            1,
            min(
                99,
                new_disk_warning_percent,
            ),
        )

        new_disk_stop_percent = max(
            new_disk_warning_percent + 1,
            min(
                100,
                new_disk_stop_percent,
            ),
        )

        self.disk_warning_percent = (
            new_disk_warning_percent
        )

        self.disk_stop_percent = (
            new_disk_stop_percent
        )

        new_max_video_duration_minutes = int(
            settings.get(
                "max_video_duration_minutes",
                10,
            )
        )

        new_max_video_duration_minutes = max(
            1,
            min(
                1440,
                new_max_video_duration_minutes,
            ),
        )

        self.max_video_duration_minutes = (
            new_max_video_duration_minutes
        )

        self.max_video_duration_seconds = (
            self.max_video_duration_minutes
            * 60.0
        )

        self.video_recorder.set_max_video_duration_seconds(
            self.max_video_duration_seconds
        )

        new_station_name = str(
            settings["station_name"]
        ).strip()

        if not new_station_name:
            new_station_name = "Station"

        self.station_name = new_station_name

        new_camera_backend = str(
            settings.get(
                "camera_backend",
                "opencv",
            )
        ).strip().lower()

        if new_camera_backend not in (
            "opencv",
            "ic4",
        ):
            new_camera_backend = "opencv"

        new_camera_serial = settings.get(
            "camera_serial"
        )

        if new_camera_serial is not None:
            new_camera_serial = str(
                new_camera_serial
            ).strip()

            if not new_camera_serial:
                new_camera_serial = None

        if new_camera_backend == "opencv":
            new_camera_serial = None
        
        new_camera_index = int(
            settings["camera_index"]
        )

        new_camera_width = int(
            settings["camera_width"]
        )

        new_camera_height = int(
            settings["camera_height"]
        )

        new_camera_fps = float(
            settings["camera_fps"]
        )

        new_camera_exposure_auto = bool(
            settings.get(
                "camera_exposure_auto",
                True,
            )
        )

        new_camera_exposure_time = max(
            1.0,
            float(
                settings.get(
                    "camera_exposure_time",
                    5000.0,
                )
            ),
        )

        new_camera_gain_auto = bool(
            settings.get(
                "camera_gain_auto",
                True,
            )
        )

        new_camera_gain = max(
            0.0,
            float(
                settings.get(
                    "camera_gain",
                    0.0,
                )
            ),
        )

        camera_changed = (
            new_camera_backend
            != self.camera_backend
            or new_camera_serial
            != self.camera_serial
            or new_camera_index
            != self.camera_index
            or new_camera_width
            != self.camera_width
            or new_camera_height
            != self.camera_height
            or new_camera_fps
            != self.camera_fps
            or new_camera_exposure_auto
            != self.camera_exposure_auto
            or new_camera_exposure_time
            != self.camera_exposure_time
            or new_camera_gain_auto
            != self.camera_gain_auto
            or new_camera_gain
            != self.camera_gain
        )



        self.camera_backend = (
            new_camera_backend
        )

        self.camera_serial = (
            new_camera_serial
        )

        self.camera_index = (
            new_camera_index
        )

        self.camera_width = (
            new_camera_width
        )

        self.camera_height = (
            new_camera_height
        )

        self.camera_fps = (
            new_camera_fps
        )

        self.camera_exposure_auto = (
            new_camera_exposure_auto
        )

        self.camera_exposure_time = (
            new_camera_exposure_time
        )

        self.camera_gain_auto = (
            new_camera_gain_auto
        )

        self.camera_gain = (
            new_camera_gain
        )

 
        requested_recordings_directory = str(
            settings.get(
                "recordings_directory",
                "",
            )
        ).strip()

        if not requested_recordings_directory:
            requested_recordings_directory = str(
                self.recordings_directory
            )

        try:
            (
                new_recordings_directory,
                directory_was_replaced,
            ) = prepare_recordings_directory(
                requested_recordings_directory,
                logger=self.logger,
            )

        except OSError as error:
            self.logger.error(
                "Impossible d'utiliser le dossier "
                "d'enregistrement demandé : %s",
                error,
            )

            QMessageBox.critical(
                self,
                "Dossier d'enregistrement inaccessible",
                "Le dossier sélectionné ne peut pas être "
                "utilisé.\n\n"
                f"{error}\n\n"
                "L'ancien dossier d'enregistrement est "
                "conservé.",
            )

            new_recordings_directory = (
                self.recordings_directory
            )

            directory_was_replaced = False

        recordings_directory_changed = (
            new_recordings_directory
            != self.recordings_directory
        )

        if directory_was_replaced:
            QMessageBox.warning(
                self,
                "Dossier d'enregistrement remplacé",
                "Le dossier demandé n'était pas utilisable "
                "sur ce système.\n\n"
                "Open Fish Counter utilisera le dossier "
                "suivant :\n"
                f"{new_recordings_directory}",
            )

        if recordings_directory_changed:
            previous_recordings_directory = (
                self.recordings_directory
            )

            self.recordings_directory = (
                new_recordings_directory
            )

            directory_applied = (
                self.apply_recordings_directory()
            )

            if not directory_applied:
                self.recordings_directory = (
                    previous_recordings_directory
                )

                self.apply_recordings_directory()

                QMessageBox.critical(
                    self,
                    "Changement de dossier impossible",
                    "Le nouveau dossier n'a pas pu être "
                    "appliqué.\n\n"
                    "L'ancien dossier reste utilisé :\n"
                    f"{self.recordings_directory}",
                )

        self.save_grid_config()

        self.last_disk_status = None
        self.check_disk_usage()

        if camera_changed:
            self.restart_camera()

        print("Paramètres généraux appliqués :")

        print(
            f"- Station : {self.station_name}"
        )

        print(
            f"- Seuil pixel : "
            f"{self.motion_detector.pixel_threshold}"
        )

        print(
            f"- Images de confirmation : "
            f"{self.required_motion_frames}"
        )

        print(
            f"- Délai de fin : "
            f"{self.no_motion_delay:.1f} s"
        )

        print(
            f"- Pré-buffer : "
            f"{self.pre_event_seconds:.1f} s"
        )

        print(
            "- Banque d'images : "
            f"{'activée' if self.snapshots_enabled else 'désactivée'}"
        )
        
    def restart_camera(self):
        self.timer.stop()

        if self.video_recorder.is_recording:
            saved_path = (
                self.video_recorder.stop()
            )

            if saved_path is not None:
                print(
                    "Vidéo finalisée avant le "
                    "redémarrage caméra : "
                    f"{saved_path}"
                )

        self.event_active = False
        self.motion_frame_count = 0
        self.last_motion_time = None
        self.event_started_this_frame = False

        self.motion_detector.reset()
        self.frame_buffer.clear()

        camera_opened = (
            self.camera_manager.restart(
                camera_index=self.camera_index,
                requested_width=self.camera_width,
                requested_height=self.camera_height,
                requested_fps=self.camera_fps,
                camera_backend=self.camera_backend,
                camera_serial=self.camera_serial,
                exposure_auto=(
                    self.camera_exposure_auto
                ),
                exposure_time=(
                    self.camera_exposure_time
                ),
                gain_auto=(
                    self.camera_gain_auto
                ),
                gain=self.camera_gain,
                    )
        )

        if camera_opened:
            actual_settings = (
                self.camera_manager
                .get_actual_settings()
            )

            print(
                "Caméra redémarrée : "
                f"{actual_settings['width']} x "
                f"{actual_settings['height']} à "
                f"{actual_settings['fps']:.1f} FPS"
            )

        else:
            self.video_widget.setText(
                "Caméra indisponible\n"
                f"{self.camera_manager.last_error}"
            )

            self.logger.warning(
                "Impossible de redémarrer la caméra : %s",
                self.camera_manager.last_error,
            )

        self.timer.start(30)

    def apply_recordings_directory(self):
        try:
            self.recordings_directory.mkdir(
                parents=True,
                exist_ok=True,
            )

        except OSError as error:
            self.logger.error(
                "Impossible de créer le dossier "
                "d'enregistrement : %s",
                error,
            )

            self.recording_enabled = False

            self.recording_status_label.setText(
                "Enregistrement automatique : "
                "DOSSIER INDISPONIBLE"
            )

            self.recording_status_label.setStyleSheet(
                "font-weight: bold; color: red;"
            )

            self.start_recording_button.setEnabled(
                True
            )

            self.stop_recording_button.setEnabled(
                False
            )

            return False

        # L'enregistreur ne change de destination
        # que lorsqu'aucune vidéo n'est en cours.
        if self.video_recorder.is_recording:
            saved_path = self.video_recorder.stop()

            if saved_path is not None:
                print(
                    "Vidéo finalisée avant le changement "
                    "de dossier : "
                    f"{saved_path}"
                )

            self.event_active = False
            self.motion_frame_count = 0
            self.last_motion_time = None

        self.video_recorder.recordings_directory = (
            self.recordings_directory
        )

        print(
            "Nouveau dossier d'enregistrement : "
            f"{self.recordings_directory}"
        )

        self.logs_directory = (
            self.recordings_directory
            / "logs"
        )

        self.logger = setup_logging(
            self.logs_directory
        )

        self.logger.info(
            "Dossier d'enregistrement modifié : %s",
            self.recordings_directory,
        )

        if hasattr(
            self,
            "disk_status_label",
        ):
            self.last_disk_status = None
            self.check_disk_usage()

        return True    

    def reset_snapshot_state(self):
        self.best_snapshot_frame = None
        self.best_snapshot_score = 0.0

    def save_event_snapshot(self):
        if not self.snapshots_enabled:
            return None

        if self.best_snapshot_frame is None:
            print(
                "Aucune image disponible pour "
                "la banque d'images."
            )

            return None

        video_path = self.video_recorder.output_path

        if video_path is None:
            print(
                "Impossible de créer le snapshot : "
                "aucun fichier vidéo actif."
            )

            return None

        # La vidéo est dans :
        # station/date/videos/video.mp4
        #
        # Le snapshot sera dans :
        # station/date/snapshots/image.jpg
        day_directory = (
            video_path.parent.parent
        )

        snapshots_directory = (
            day_directory / "snapshots"
        )

        try:
            snapshots_directory.mkdir(
                parents=True,
                exist_ok=True,
            )

        except OSError as error:
            print(
                "Impossible de créer le dossier "
                f"des snapshots : {error}"
            )

            return None

        snapshot_filename = (
            f"{video_path.stem}"
            "_max_motion.jpg"
        )

        snapshot_path = (
            snapshots_directory
            / snapshot_filename
        )

        saved = cv2.imwrite(
            str(snapshot_path),
            self.best_snapshot_frame,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                95,
            ],
        )

        if not saved:
            print(
                "Impossible d'enregistrer l'image : "
                f"{snapshot_path}"
            )

            return None

        print(
            "Image ajoutée à la banque : "
            f"{snapshot_path}"
        )

        print(
            "Score de mouvement de l'image : "
            f"{self.best_snapshot_score:.1f} %"
        )

        return snapshot_path

    @staticmethod
    def format_disk_size(size_bytes):
        """
        Convertit une taille en octets en une valeur lisible.
        """
        size_value = float(
            max(
                0,
                size_bytes,
            )
        )

        units = (
            "o",
            "Ko",
            "Mo",
            "Go",
            "To",
        )

        for unit in units:
            if size_value < 1024.0 or unit == units[-1]:
                if unit == "o":
                    return f"{size_value:.0f} {unit}"

                return f"{size_value:.1f} {unit}"

            size_value /= 1024.0

        return f"{size_value:.1f} To"

    def get_disk_usage(self):
        """
        Retourne l'occupation du disque contenant le dossier
        d'enregistrement.

        Le résultat contient :
        - la taille totale ;
        - l'espace utilisé ;
        - l'espace disponible ;
        - le pourcentage utilisé.
        """
        recordings_directory = Path(
            self.recordings_directory
        )

        # Le dossier doit normalement déjà exister grâce à
        # apply_recordings_directory(). Cette sécurité permet
        # néanmoins de remonter jusqu'à un parent existant.
        existing_directory = recordings_directory

        while not existing_directory.exists():
            parent_directory = (
                existing_directory.parent
            )

            if parent_directory == existing_directory:
                raise OSError(
                    "Aucun dossier existant trouvé pour "
                    f"{recordings_directory}"
                )

            existing_directory = (
                parent_directory
            )

        disk_usage = shutil.disk_usage(
            existing_directory
        )

        if disk_usage.total <= 0:
            raise OSError(
                "La taille totale du disque est invalide."
            )

        used_percent = (
            disk_usage.used
            / disk_usage.total
            * 100.0
        )

        return {
            "total": disk_usage.total,
            "used": disk_usage.used,
            "free": disk_usage.free,
            "used_percent": used_percent,
            "checked_path": existing_directory,
        }

    def check_disk_usage(self):
        """
        Met à jour l'indicateur d'occupation du disque et
        bloque les enregistrements au seuil critique.
        """
        try:
            disk_usage = self.get_disk_usage()

        except OSError as error:
            self.disk_status_label.setText(
                "Disque : état indisponible"
            )

            self.disk_status_label.setStyleSheet(
                "font-weight: bold; color: red;"
            )

            if self.last_disk_status != "error":
                self.logger.error(
                    "Impossible de contrôler l'espace disque : %s",
                    error,
                )

            self.last_disk_status = "error"

            self.set_disk_recording_blocked(
                True,
                reason=(
                    "Impossible de vérifier l'espace disque."
                ),
            )

            return

        used_percent = float(
            disk_usage["used_percent"]
        )

        free_text = self.format_disk_size(
            disk_usage["free"]
        )

        total_text = self.format_disk_size(
            disk_usage["total"]
        )

        self.disk_status_label.setText(
            f"Disque : {used_percent:.1f} % utilisé\n"
            f"Disponible : {free_text} sur {total_text}"
        )

        if used_percent >= self.disk_stop_percent:
            disk_status = "critical"

            self.disk_status_label.setStyleSheet(
                "font-weight: bold; color: red;"
            )

            if self.last_disk_status != disk_status:
                self.logger.error(
                    "Seuil critique du disque atteint | "
                    "occupation=%.1f %% | seuil=%d %% | "
                    "disponible=%s",
                    used_percent,
                    self.disk_stop_percent,
                    free_text,
                )

            self.set_disk_recording_blocked(
                True,
                reason=(
                    "Espace disque insuffisant "
                    f"({used_percent:.1f} % utilisé)."
                ),
            )

        elif used_percent >= self.disk_warning_percent:
            disk_status = "warning"

            self.disk_status_label.setStyleSheet(
                "font-weight: bold; color: orange;"
            )

            if self.last_disk_status != disk_status:
                self.logger.warning(
                    "Seuil d'avertissement du disque atteint | "
                    "occupation=%.1f %% | seuil=%d %% | "
                    "disponible=%s",
                    used_percent,
                    self.disk_warning_percent,
                    free_text,
                )

            # Le seuil critique n'est plus atteint.
            self.set_disk_recording_blocked(
                False
            )

        else:
            disk_status = "normal"

            self.disk_status_label.setStyleSheet(
                "font-weight: bold; color: green;"
            )

            if self.last_disk_status in (
                "warning",
                "critical",
                "error",
            ):
                self.logger.info(
                    "Espace disque revenu à un niveau normal | "
                    "occupation=%.1f %% | disponible=%s",
                    used_percent,
                    free_text,
                )

            self.set_disk_recording_blocked(
                False
            )

        self.last_disk_status = disk_status

    def set_disk_recording_blocked(
        self,
        blocked,
        reason=None,
    ):
        """
        Active ou désactive le blocage des enregistrements
        provoqué par l'état du disque.

        Le choix manuel de l'utilisateur est conservé dans
        self.recording_enabled.
        """
        blocked = bool(
            blocked
        )

        state_changed = (
            blocked
            != self.disk_recording_blocked
        )

        self.disk_recording_blocked = (
            blocked
        )

        if blocked:
            if self.video_recorder.is_recording:
                self.logger.warning(
                    "Finalisation de la vidéo en cours "
                    "en raison de l'état du disque."
                )

                snapshot_path = (
                    self.save_event_snapshot()
                )

                saved_path = (
                    self.video_recorder.stop()
                )

                if saved_path is not None:
                    self.logger.info(
                        "Vidéo finalisée avant saturation : %s",
                        saved_path,
                    )

                if snapshot_path is not None:
                    self.logger.info(
                        "Snapshot sauvegardé avant "
                        "saturation : %s",
                        snapshot_path,
                    )

            self.recording_status_label.setText(
                "Enregistrement automatique : "
                "BLOQUÉ PAR LE DISQUE"
            )

            self.recording_status_label.setStyleSheet(
                "font-weight: bold; color: red;"
            )

            self.start_recording_button.setEnabled(
                False
            )

            self.stop_recording_button.setEnabled(
                False
            )

            if state_changed:
                self.logger.error(
                    "Enregistrements bloqués : %s",
                    reason
                    or "espace disque insuffisant",
                )

            return

        # Le disque est de nouveau utilisable.
        if state_changed:
            self.logger.info(
                "Blocage des enregistrements par le disque levé."
            )

        self.update_recording_controls()

    def update_recording_controls(self):
        """
        Met à jour l'état visuel des contrôles en fonction
        du choix de l'utilisateur et de l'état du disque.
        """
        if self.disk_recording_blocked:
            self.recording_status_label.setText(
                "Enregistrement automatique : "
                "BLOQUÉ PAR LE DISQUE"
            )

            self.recording_status_label.setStyleSheet(
                "font-weight: bold; color: red;"
            )

            self.start_recording_button.setEnabled(
                False
            )

            self.stop_recording_button.setEnabled(
                False
            )

        elif self.recording_enabled:
            self.recording_status_label.setText(
                "Enregistrement automatique : ACTIVÉ"
            )

            self.recording_status_label.setStyleSheet(
                "font-weight: bold; color: green;"
            )

            self.start_recording_button.setEnabled(
                False
            )

            self.stop_recording_button.setEnabled(
                True
            )

        else:
            self.recording_status_label.setText(
                "Enregistrement automatique : ARRÊTÉ"
            )

            self.recording_status_label.setStyleSheet(
                "font-weight: bold; color: red;"
            )

            self.start_recording_button.setEnabled(
                True
            )

            self.stop_recording_button.setEnabled(
                False
            )