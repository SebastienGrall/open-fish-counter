from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QCheckBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QScrollArea,
)
from PySide6.QtCore import Qt
from pathlib import Path


class SettingsDialog(QDialog):
    def __init__(
        self,
        station_name,
        pixel_threshold,
        required_motion_frames,
        no_motion_delay,
        pre_event_seconds,
        recordings_directory,
        snapshots_enabled,
        disk_warning_percent,
        disk_stop_percent,
        max_video_duration_minutes,
        camera_backend,
        camera_serial,
        ic4_devices,
        camera_index,
        camera_width,
        camera_height,
        camera_fps,
        camera_exposure_auto,
        camera_exposure_time,
        camera_gain_auto,
        camera_gain,
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle(
            "Paramètres - Open Fish Counter"
        )

        self.setMinimumSize(
            420,
            420,
        )

        self.resize(
            620,
            650,
        )

        # Layout principal de la fenêtre.
        # Il contient la zone déroulante et les boutons fixes.
        dialog_layout = QVBoxLayout(self)

        # Zone de défilement contenant les paramètres.
        self.settings_scroll_area = QScrollArea()

        self.settings_scroll_area.setWidgetResizable(
            True
        )

        self.settings_scroll_area.setFrameShape(
            QScrollArea.Shape.NoFrame
        )

        self.settings_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.settings_scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        # Widget réellement placé dans la zone déroulante.
        settings_content_widget = QWidget()

        main_layout = QVBoxLayout(
            settings_content_widget
        )

        main_layout.setContentsMargins(
            6,
            6,
            6,
            6,
        )

        main_layout.setSpacing(
            10
        )

        self.settings_scroll_area.setWidget(
            settings_content_widget
        )

        dialog_layout.addWidget(
            self.settings_scroll_area,
            1,
        )

        station_group = QGroupBox(
            "Station"
        )

        station_layout = QFormLayout(
            station_group
        )

        self.station_name_edit = QLineEdit()

        self.station_name_edit.setText(
            str(station_name)
        )

        self.station_name_edit.setMaxLength(100)

        self.station_name_edit.setPlaceholderText(
            "Exemple : Passe à poissons du Moulin"
        )

        self.station_name_edit.setToolTip(
            "Nom de la station ajouté aux vidéos, "
            "aux métadonnées et aux futurs résultats."
        )

        station_layout.addRow(
            "Nom de la station :",
            self.station_name_edit,
        )

        main_layout.addWidget(
            station_group
        )

        camera_group = QGroupBox(
            "Caméra"
        )

        camera_layout = QFormLayout(
            camera_group
        )

        self.camera_backend_combo = QComboBox()

        self.camera_backend_combo.addItem(
            "Webcam / caméra OpenCV",
            "opencv",
        )

        self.camera_backend_combo.addItem(
            "Caméra The Imaging Source IC4",
            "ic4",
        )

        backend_index = (
            self.camera_backend_combo.findData(
                str(camera_backend).strip().lower()
            )
        )

        if backend_index < 0:
            backend_index = 0

        self.camera_backend_combo.setCurrentIndex(
            backend_index
        )

        camera_layout.addRow(
            "Type de caméra :",
            self.camera_backend_combo,
        )

        self.ic4_camera_combo = QComboBox()

        selected_ic4_index = -1
        configured_serial_found = False

        for device in ic4_devices:
            model = str(
                device.get(
                    "model",
                    "Caméra IC4",
                )
            )

            serial = str(
                device.get(
                    "serial",
                    "",
                )
            ).strip()

            if not serial:
                continue

            self.ic4_camera_combo.addItem(
                f"{model} - Série {serial}",
                serial,
            )

            if serial == camera_serial:
                selected_ic4_index = (
                    self.ic4_camera_combo.count()
                    - 1
                )

                configured_serial_found = True

        configured_serial = str(
            camera_serial or ""
        ).strip()

        if (
            configured_serial
            and not configured_serial_found
        ):
            self.ic4_camera_combo.addItem(
                f"Série {configured_serial} "
                "(actuellement indisponible)",
                configured_serial,
            )

            selected_ic4_index = (
                self.ic4_camera_combo.count()
                - 1
            )

        if selected_ic4_index >= 0:
            self.ic4_camera_combo.setCurrentIndex(
                selected_ic4_index
            )

        camera_layout.addRow(
            "Caméra IC4 :",
            self.ic4_camera_combo,
        )

        self.camera_backend_combo.currentIndexChanged.connect(
            self.update_camera_fields
        )

        self.camera_index_spinbox = QSpinBox()
        self.camera_index_spinbox.setRange(0, 20)
        self.camera_index_spinbox.setValue(
            int(camera_index)
        )

        camera_layout.addRow(
            "Index caméra :",
            self.camera_index_spinbox,
        )

        self.camera_width_spinbox = QSpinBox()
        self.camera_width_spinbox.setRange(160, 7680)
        self.camera_width_spinbox.setValue(
            int(camera_width)
        )
        self.camera_width_spinbox.setSuffix(" px")

        camera_layout.addRow(
            "Largeur demandée :",
            self.camera_width_spinbox,
        )

        self.camera_height_spinbox = QSpinBox()
        self.camera_height_spinbox.setRange(120, 4320)
        self.camera_height_spinbox.setValue(
            int(camera_height)
        )
        self.camera_height_spinbox.setSuffix(" px")

        camera_layout.addRow(
            "Hauteur demandée :",
            self.camera_height_spinbox,
        )

        self.camera_fps_spinbox = QDoubleSpinBox()
        self.camera_fps_spinbox.setRange(1.0, 300.0)
        self.camera_fps_spinbox.setDecimals(1)
        self.camera_fps_spinbox.setValue(
            float(camera_fps)
        )
        self.camera_fps_spinbox.setSuffix(" FPS")

        camera_layout.addRow(
            "Fréquence demandée :",
            self.camera_fps_spinbox,
        )

        main_layout.addWidget(camera_group)

        # Réglages avancés propres aux caméras IC4.
        self.ic4_settings_group = QGroupBox(
            "Réglages avancés IC4"
        )

        ic4_settings_layout = QFormLayout(
            self.ic4_settings_group
        )

        self.exposure_auto_checkbox = QCheckBox(
            "Exposition automatique"
        )

        self.exposure_auto_checkbox.setChecked(
            bool(camera_exposure_auto)
        )

        self.exposure_auto_checkbox.setToolTip(
            "Laisse la caméra adapter automatiquement "
            "le temps d'exposition."
        )

        ic4_settings_layout.addRow(
            "Exposition :",
            self.exposure_auto_checkbox,
        )

        self.exposure_time_spinbox = (
            QDoubleSpinBox()
        )

        self.exposure_time_spinbox.setRange(
            1.0,
            1000000.0,
        )

        self.exposure_time_spinbox.setDecimals(
            1
        )

        self.exposure_time_spinbox.setSingleStep(
            100.0
        )

        self.exposure_time_spinbox.setSuffix(
            " µs"
        )

        self.exposure_time_spinbox.setValue(
            float(camera_exposure_time)
        )

        self.exposure_time_spinbox.setToolTip(
            "Temps pendant lequel le capteur reçoit "
            "la lumière pour chaque image.\n"
            "Une valeur courte limite le flou de mouvement."
        )

        ic4_settings_layout.addRow(
            "Temps d'exposition :",
            self.exposure_time_spinbox,
        )

        self.gain_auto_checkbox = QCheckBox(
            "Gain automatique"
        )

        self.gain_auto_checkbox.setChecked(
            bool(camera_gain_auto)
        )

        self.gain_auto_checkbox.setToolTip(
            "Laisse la caméra adapter automatiquement "
            "l'amplification du signal."
        )

        ic4_settings_layout.addRow(
            "Gain :",
            self.gain_auto_checkbox,
        )

        self.gain_spinbox = QDoubleSpinBox()

        self.gain_spinbox.setRange(
            0.0,
            100.0,
        )

        self.gain_spinbox.setDecimals(
            2
        )

        self.gain_spinbox.setSingleStep(
            0.1
        )

        self.gain_spinbox.setValue(
            float(camera_gain)
        )

        self.gain_spinbox.setToolTip(
            "Amplification du signal du capteur.\n"
            "Une valeur élevée éclaircit l'image, "
            "mais augmente également le bruit."
        )

        ic4_settings_layout.addRow(
            "Gain manuel :",
            self.gain_spinbox,
        )

        self.exposure_auto_checkbox.toggled.connect(
            self.update_ic4_manual_fields
        )

        self.gain_auto_checkbox.toggled.connect(
            self.update_ic4_manual_fields
        )

        main_layout.addWidget(
            self.ic4_settings_group
        )

        # Paramètres de détection
        detection_group = QGroupBox(
            "Détection de mouvement"
        )

        detection_layout = QFormLayout(
            detection_group
        )

        self.pixel_threshold_spinbox = QSpinBox()
        self.pixel_threshold_spinbox.setRange(
            1,
            255,
        )
        self.pixel_threshold_spinbox.setValue(
            int(pixel_threshold)
        )

        self.pixel_threshold_spinbox.setToolTip(
            "Différence minimale de luminosité pour "
            "considérer qu'un pixel a changé."
        )

        detection_layout.addRow(
            "Variation minimale d'un pixel :",
            self.pixel_threshold_spinbox,
        )

        self.required_frames_spinbox = QSpinBox()
        self.required_frames_spinbox.setRange(
            1,
            100,
        )
        self.required_frames_spinbox.setValue(
            int(required_motion_frames)
        )

        self.required_frames_spinbox.setToolTip(
            "Nombre d'images consécutives avec mouvement "
            "nécessaires pour confirmer un événement."
        )

        detection_layout.addRow(
            "Images de confirmation :",
            self.required_frames_spinbox,
        )

        self.no_motion_delay_spinbox = (
            QDoubleSpinBox()
        )

        self.no_motion_delay_spinbox.setRange(
            0.1,
            60.0,
        )
        self.no_motion_delay_spinbox.setDecimals(1)
        self.no_motion_delay_spinbox.setSingleStep(
            0.1
        )
        self.no_motion_delay_spinbox.setSuffix(
            " s"
        )
        self.no_motion_delay_spinbox.setValue(
            float(no_motion_delay)
        )

        self.no_motion_delay_spinbox.setToolTip(
            "Durée sans mouvement avant de terminer "
            "l'événement et fermer la vidéo."
        )

        detection_layout.addRow(
            "Délai de fin d'événement :",
            self.no_motion_delay_spinbox,
        )

        main_layout.addWidget(detection_group)

        # Paramètres d'enregistrement
        recording_group = QGroupBox(
            "Enregistrement"
        )

        recording_layout = QFormLayout(
            recording_group
        )

        self.pre_event_spinbox = QDoubleSpinBox()
        self.pre_event_spinbox.setRange(
            0.0,
            30.0,
        )
        self.pre_event_spinbox.setDecimals(1)
        self.pre_event_spinbox.setSingleStep(0.1)
        self.pre_event_spinbox.setSuffix(" s")
        self.pre_event_spinbox.setValue(
            float(pre_event_seconds)
        )

        self.pre_event_spinbox.setToolTip(
            "Durée vidéo conservée avant la confirmation "
            "du mouvement."
        )

        recording_layout.addRow(
            "Pré-buffer :",
            self.pre_event_spinbox,
        )

        self.disk_warning_spinbox = QSpinBox()

        self.disk_warning_spinbox.setRange(
            1,
            99,
        )

        self.disk_warning_spinbox.setSuffix(
            " %"
        )

        self.disk_warning_spinbox.setValue(
            max(
                1,
                min(
                    99,
                    int(disk_warning_percent),
                ),
            )
        )

        self.disk_warning_spinbox.setToolTip(
            "Pourcentage d'occupation du disque à partir "
            "duquel un avertissement est affiché."
        )

        recording_layout.addRow(
            "Avertissement disque :",
            self.disk_warning_spinbox,
        )

        self.disk_stop_spinbox = QSpinBox()

        self.disk_stop_spinbox.setRange(
            2,
            100,
        )

        self.disk_stop_spinbox.setSuffix(
            " %"
        )

        self.disk_stop_spinbox.setValue(
            max(
                2,
                min(
                    100,
                    int(disk_stop_percent),
                ),
            )
        )

        self.disk_stop_spinbox.setToolTip(
            "Pourcentage d'occupation du disque à partir "
            "duquel les enregistrements sont arrêtés "
            "et les nouveaux enregistrements sont bloqués."
        )

        recording_layout.addRow(
            "Arrêt des enregistrements :",
            self.disk_stop_spinbox,
        )

        self.disk_warning_spinbox.valueChanged.connect(
            self.update_disk_thresholds
        )

        self.disk_stop_spinbox.valueChanged.connect(
            self.update_disk_thresholds
        )

        self.max_video_duration_spinbox = (
            QSpinBox()
        )

        self.max_video_duration_spinbox.setRange(
            1,
            1440,
        )

        self.max_video_duration_spinbox.setSuffix(
            " min"
        )

        self.max_video_duration_spinbox.setValue(
            max(
                1,
                min(
                    1440,
                    int(
                        max_video_duration_minutes
                    ),
                ),
            )
        )

        self.max_video_duration_spinbox.setToolTip(
            "Durée maximale d'un fichier vidéo.\n"
            "Si un événement dure plus longtemps, "
            "il est poursuivi automatiquement dans "
            "un nouveau fichier appartenant au même événement."
        )

        recording_layout.addRow(
            "Durée maximale d'un fichier :",
            self.max_video_duration_spinbox,
        )

        self.recordings_directory_edit = (
            QLineEdit()
        )

        self.recordings_directory_edit.setText(
            str(recordings_directory)
        )

        self.recordings_directory_edit.setReadOnly(
            True
        )

        self.recordings_directory_edit.setToolTip(
            "Dossier racine dans lequel seront "
            "créés les dossiers de station et "
            "les enregistrements."
        )

        self.browse_directory_button = QPushButton(
            "Parcourir..."
        )

        self.browse_directory_button.clicked.connect(
            self.select_recordings_directory
        )

        self.snapshots_enabled_checkbox = QCheckBox(
            "Créer une image par événement"
        )

        self.snapshots_enabled_checkbox.setChecked(
            bool(snapshots_enabled)
        )

        self.snapshots_enabled_checkbox.setToolTip(
            "Enregistre l'image brute présentant le niveau "
            "de mouvement maximal pendant l'événement."
        )

        recording_layout.addRow(
            "Banque d'images :",
            self.snapshots_enabled_checkbox,
        )

        directory_widget = QWidget()

        directory_layout = QHBoxLayout(
            directory_widget
        )

        directory_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        directory_layout.addWidget(
            self.recordings_directory_edit,
            1,
        )

        directory_layout.addWidget(
            self.browse_directory_button,
        )

        recording_layout.addRow(
            "Dossier de destination :",
            directory_widget,
        )

        main_layout.addWidget(recording_group)

        # Boutons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        button_box.accepted.connect(
            self.accept
        )

        button_box.rejected.connect(
            self.reject
        )

        # Les boutons restent visibles même lorsque les
        # paramètres sont parcourus avec la barre de défilement.
        dialog_layout.addWidget(
            button_box
        )

        self.update_camera_fields()

        self.update_disk_thresholds()

    def update_disk_thresholds(self):
        warning_percent = (
            self.disk_warning_spinbox.value()
        )

        stop_percent = (
            self.disk_stop_spinbox.value()
        )

        if stop_percent <= warning_percent:
            self.disk_stop_spinbox.blockSignals(
                True
            )

            self.disk_stop_spinbox.setValue(
                min(
                    100,
                    warning_percent + 1,
                )
            )

            self.disk_stop_spinbox.blockSignals(
                False
            )

        stop_percent = (
            self.disk_stop_spinbox.value()
        )

        if warning_percent >= stop_percent:
            self.disk_warning_spinbox.blockSignals(
                True
            )

            self.disk_warning_spinbox.setValue(
                max(
                    1,
                    stop_percent - 1,
                )
            )

            self.disk_warning_spinbox.blockSignals(
                False
            )

    def get_settings(self):
        return {
            "station_name": (
                self.station_name_edit.text().strip()
            ),
            "pixel_threshold": (
                self.pixel_threshold_spinbox.value()
            ),
            "required_motion_frames": (
                self.required_frames_spinbox.value()
            ),
            "no_motion_delay": (
                self.no_motion_delay_spinbox.value()
            ),
            "pre_event_seconds": (
                self.pre_event_spinbox.value()
            ),
            "recordings_directory": (
                self.recordings_directory_edit.text().strip()
            ),
            "snapshots_enabled": (
                self.snapshots_enabled_checkbox.isChecked()
            ),
            "disk_warning_percent": (
                self.disk_warning_spinbox.value()
            ),
            "disk_stop_percent": (
                self.disk_stop_spinbox.value()
            ),
            "max_video_duration_minutes": (
                self.max_video_duration_spinbox.value()
            ),
            "camera_backend": (
                self.camera_backend_combo.currentData()
            ),
            "camera_serial": (
                self.ic4_camera_combo.currentData()
                if (
                    self.camera_backend_combo.currentData()
                    == "ic4"
                )
                else None
            ),
            "camera_index": (
                self.camera_index_spinbox.value()
            ),
            "camera_width": (
                self.camera_width_spinbox.value()
            ),
            "camera_height": (
                self.camera_height_spinbox.value()
            ),
            "camera_fps": (
                self.camera_fps_spinbox.value()
            ),
            "camera_exposure_auto": (
                self.exposure_auto_checkbox.isChecked()
            ),
            "camera_exposure_time": (
                self.exposure_time_spinbox.value()
            ),
            "camera_gain_auto": (
                self.gain_auto_checkbox.isChecked()
            ),
            "camera_gain": (
                self.gain_spinbox.value()
            ),
        }

    def select_recordings_directory(self):
        current_directory = (
            self.recordings_directory_edit.text()
            .strip()
        )

        if not current_directory:
            current_directory = str(
                Path.home()
            )

        selected_directory = (
            QFileDialog.getExistingDirectory(
                self,
                "Choisir le dossier des enregistrements",
                current_directory,
                QFileDialog.Option.ShowDirsOnly,
            )
        )

        if not selected_directory:
            return

        self.recordings_directory_edit.setText(
            selected_directory
        )

    def update_camera_fields(self):
        camera_backend = (
            self.camera_backend_combo.currentData()
        )

        using_ic4 = (
            camera_backend == "ic4"
        )

        self.camera_index_spinbox.setEnabled(
            not using_ic4
        )

        self.ic4_camera_combo.setEnabled(
            using_ic4
        )

        self.ic4_settings_group.setEnabled(
            using_ic4
        )

        if using_ic4:
            self.camera_index_spinbox.setToolTip(
                "L'index est ignoré avec une caméra IC4."
            )

            self.ic4_camera_combo.setToolTip(
                "Les caméras IC4 sont distinguées par "
                "leur numéro de série."
            )

        else:
            self.camera_index_spinbox.setToolTip(
                "Index OpenCV de la webcam."
            )

            self.ic4_camera_combo.setToolTip(
                "Ce champ est utilisé uniquement avec "
                "le backend IC4."
            )

        self.update_ic4_manual_fields()

    def update_ic4_manual_fields(self):
        using_ic4 = (
            self.camera_backend_combo.currentData()
            == "ic4"
        )

        exposure_is_manual = (
            using_ic4
            and not (
                self.exposure_auto_checkbox
                .isChecked()
            )
        )

        gain_is_manual = (
            using_ic4
            and not (
                self.gain_auto_checkbox
                .isChecked()
            )
        )

        self.exposure_time_spinbox.setEnabled(
            exposure_is_manual
        )

        self.gain_spinbox.setEnabled(
            gain_is_manual
        )