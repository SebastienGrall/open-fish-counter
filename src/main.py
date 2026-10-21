import sys
import json
import time
from pathlib import Path
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
    QVBoxLayout,
    QPushButton,
    QComboBox,
    QDialog,
)

from ui.video_widget import VideoWidget
from motion.motion_detector import MotionDetector
from recording.frame_buffer import FrameBuffer
from recording.video_recorder import VideoRecorder
from ui.settings_dialog import SettingsDialog

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "data" / "grid_config.json"
RECORDINGS_DIRECTORY = (
    PROJECT_ROOT / "data" / "recordings"
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Open Fish Counter")
        self.resize(1200, 800)

        self.video_widget = VideoWidget()

        # Valeurs générales par défaut.
        # load_grid_config() pourra les remplacer.
        self.loaded_general_settings = {
            "pixel_threshold": 25,
            "required_motion_frames": 3,
            "no_motion_delay": 1.0,
            "pre_event_seconds": 1.0,
            "camera_index": 1,
            "camera_width": 720,
            "camera_height": 540,
            "camera_fps": 30.0,
        }

        # Charge les cellules et les paramètres généraux depuis le JSON.
        self.load_grid_config()

        # Création du moteur de détection avec les paramètres chargés.
        self.motion_detector = MotionDetector(
            grid_rows=self.video_widget.grid_rows,
            grid_cols=self.video_widget.grid_cols,
            pixel_threshold=int(
                self.loaded_general_settings[
                    "pixel_threshold"
                ]
            ),
        )

        # Paramètres généraux chargés.
        self.required_motion_frames = int(
            self.loaded_general_settings[
                "required_motion_frames"
            ]
        )

        self.no_motion_delay = float(
            self.loaded_general_settings[
                "no_motion_delay"
            ]
        )

        self.pre_event_seconds = float(
            self.loaded_general_settings[
                "pre_event_seconds"
            ]
        )

        self.camera_index = int(
            self.loaded_general_settings[
                "camera_index"
            ]
        )

        self.camera_width = int(
            self.loaded_general_settings[
                "camera_width"
            ]
        )

        self.camera_height = int(
            self.loaded_general_settings[
                "camera_height"
            ]
        )

        self.camera_fps = float(
            self.loaded_general_settings[
                "camera_fps"
            ]
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

        # Ouverture de la caméra.
        self.open_camera()

        camera_fps = self.cap.get(
            cv2.CAP_PROP_FPS
        )

        if camera_fps <= 0:
            camera_fps = self.camera_fps

        self.video_recorder = VideoRecorder(
            recordings_directory=RECORDINGS_DIRECTORY,
            fps=camera_fps,
        )

        print(
            f"Fréquence d'enregistrement : "
            f"{camera_fps:.2f} images/s"
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

        #
        # Pour l'instant :
        # webcam OpenCV par défaut
        #
        #self.cap = cv2.VideoCapture(1)

        self.timer = QTimer()

        self.timer.timeout.connect(self.update_frame)

        self.timer.start(30)

    def update_frame(self):
        ok, frame = self.cap.read()

        if not ok:
            return

        self.event_started_this_frame = False
        # Conserve en mémoire la dernière seconde de vidéo.
        self.frame_buffer.add_frame(frame)
    
        motion_levels = self.motion_detector.process_frame(
            frame
        )

        self.video_widget.set_motion_levels(
            motion_levels
        )

        self.update_event_indicator(
        motion_levels
        )

        self.buffer_status_label.setText(
            f"Buffer : "
            f"{self.frame_buffer.get_frame_count()} images, "
            f"{self.frame_buffer.get_duration():.2f} s"
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
        self.recording_enabled = True

        self.recording_status_label.setText(
            "Enregistrement automatique : ACTIVÉ"
        )

        self.recording_status_label.setStyleSheet(
            "font-weight: bold; color: green;"
        )

        self.start_recording_button.setEnabled(False)
        self.stop_recording_button.setEnabled(True)

        print("Enregistrement automatique activé.")

    def disable_recording(self):
        self.recording_enabled = False

        self.recording_status_label.setText(
            "Enregistrement automatique : ARRÊTÉ"
        )

        self.recording_status_label.setStyleSheet(
            "font-weight: bold; color: red;"
        )

        self.start_recording_button.setEnabled(True)
        self.stop_recording_button.setEnabled(False)

        # Si un fichier est actuellement ouvert,
        # on le termine proprement.
        if self.video_recorder.is_recording:
            saved_path = self.video_recorder.stop()

            if saved_path is not None:
                print(
                    "Enregistrement interrompu et sauvegardé : "
                    f"{saved_path}"
                )

        print("Enregistrement automatique arrêté.")

    def load_grid_config(self):
        if not CONFIG_FILE.exists():
            print(
                "Aucune configuration existante, "
                "utilisation des valeurs par défaut."
            )
            return

        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as config_file:
                config = json.load(config_file)

                camera_config = config.get(
                    "camera",
                    {}
                )

                detection_config = config.get(
                    "detection",
                    {}
                )

                recording_config = config.get(
                    "recording",
                    {}
                )

                self.loaded_general_settings = {
                    "camera_index": camera_config.get(
                        "index",
                        1,
                    ),
                    "camera_width": camera_config.get(
                        "width",
                        720,
                    ),
                    "camera_height": camera_config.get(
                        "height",
                        540,
                    ),
                    "camera_fps": camera_config.get(
                        "fps",
                        30.0,
                    ),

                    "pixel_threshold": detection_config.get(
                        "pixel_threshold",
                        25,
                    ),
                    "required_motion_frames": (
                        detection_config.get(
                            "required_motion_frames",
                            3,
                        )
                    ),
                    "no_motion_delay": detection_config.get(
                        "no_motion_delay",
                        1.0,
                    ),
                    "pre_event_seconds": (
                        recording_config.get(
                            "pre_event_seconds",
                            1.0,
                        )
                    ),
                }

            saved_cells = config.get("cells", {})

            for cell_id_text, saved_cell in saved_cells.items():
                cell_id = int(cell_id_text)

                if cell_id not in self.video_widget.cells:
                    continue

                self.video_widget.cells[cell_id]["enabled"] = saved_cell.get(
                    "enabled",
                    True,
                )

                self.video_widget.cells[cell_id]["threshold"] = saved_cell.get(
                    "threshold",
                    10,
                )

            print(f"Configuration chargée depuis : {CONFIG_FILE}")

        except (OSError, json.JSONDecodeError, ValueError) as error:
            print(f"Impossible de charger la configuration : {error}")

    def closeEvent(self, event):
        self.timer.stop()

        if self.video_recorder.is_recording:
            self.video_recorder.stop()

        self.cap.release()

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
        )

    def on_event_ended(self):
        print("=== FIN DE L'ÉVÉNEMENT ===")

        if not self.video_recorder.is_recording:
            return

        saved_path = self.video_recorder.stop()

        if saved_path is not None:
            print(
                f"Vidéo sauvegardée : "
                f"{saved_path}"
            )

    def save_grid_config(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

        config = {
            "camera": {
                "index": self.camera_index,
                "width": self.camera_width,
                "height": self.camera_height,
                "fps": self.camera_fps,
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
            },
            "grid": {
                "rows": self.video_widget.grid_rows,
                "cols": self.video_widget.grid_cols,
            },
            "cells": self.video_widget.cells,
        }

        temporary_file = CONFIG_FILE.with_suffix(".tmp")

        try:
            with temporary_file.open("w", encoding="utf-8") as config_file:
                json.dump(
                    config,
                    config_file,
                    indent=4,
                    ensure_ascii=False,
                )

            temporary_file.replace(CONFIG_FILE)

            print(f"Configuration sauvegardée dans : {CONFIG_FILE}")

        except OSError as error:
            print(f"Impossible de sauvegarder la configuration : {error}")
        
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

    def on_display_mode_changed(self):
        display_mode = (
            self.display_mode_combo.currentData()
        )

        self.video_widget.set_display_mode(
            display_mode
        )

    def open_settings_dialog(self):
        dialog = SettingsDialog(
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
            camera_index=self.camera_index,
            camera_width=self.camera_width,
            camera_height=self.camera_height,
            camera_fps=self.camera_fps,
            parent=self,
        )

        result = dialog.exec()

        if result != QDialog.DialogCode.Accepted:
            return

        settings = dialog.get_settings()

        self.apply_general_settings(
            settings
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

        camera_changed = (
            new_camera_index != self.camera_index
            or new_camera_width != self.camera_width
            or new_camera_height != self.camera_height
            or new_camera_fps != self.camera_fps
        )

        self.camera_index = new_camera_index
        self.camera_width = new_camera_width
        self.camera_height = new_camera_height
        self.camera_fps = new_camera_fps

        self.save_grid_config()

        print("Paramètres généraux appliqués :")

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

        if camera_changed:
            self.restart_camera()

    def open_camera(self):
        self.cap = cv2.VideoCapture(
            self.camera_index
        )

        if not self.cap.isOpened():
            raise RuntimeError(
                "Impossible d'ouvrir la caméra "
                f"à l'index {self.camera_index}."
            )

        self.cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            self.camera_width,
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            self.camera_height,
        )

        self.cap.set(
            cv2.CAP_PROP_FPS,
            self.camera_fps,
        )

        actual_width = int(
            self.cap.get(
                cv2.CAP_PROP_FRAME_WIDTH
            )
        )

        actual_height = int(
            self.cap.get(
                cv2.CAP_PROP_FRAME_HEIGHT
            )
        )

        announced_fps = self.cap.get(
            cv2.CAP_PROP_FPS
        )

        print(
            "Paramètres caméra demandés : "
            f"{self.camera_width} × "
            f"{self.camera_height} à "
            f"{self.camera_fps:.1f} FPS"
        )

        print(
            "Paramètres caméra obtenus : "
            f"{actual_width} × "
            f"{actual_height} à "
            f"{announced_fps:.1f} FPS"
        )

    def restart_camera(self):
        self.timer.stop()

        if self.video_recorder.is_recording:
            self.video_recorder.stop()

        self.cap.release()

        self.motion_detector.reset()
        self.frame_buffer.clear()

        self.open_camera()

        self.timer.start(30)

        print(
            "Caméra redémarrée avec "
            "les nouveaux paramètres."
        )

app = QApplication(sys.argv)

window = MainWindow()
window.show()

sys.exit(app.exec())