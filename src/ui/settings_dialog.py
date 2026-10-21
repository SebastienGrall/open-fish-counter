from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QSpinBox,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    def __init__(
        self,
        pixel_threshold,
        required_motion_frames,
        no_motion_delay,
        pre_event_seconds,
        camera_index,
        camera_width,
        camera_height,
        camera_fps,
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle(
            "Paramètres - Open Fish Counter"
        )

        self.setMinimumWidth(400)

        main_layout = QVBoxLayout(self)

        camera_group = QGroupBox(
            "Caméra"
        )

        camera_layout = QFormLayout(
            camera_group
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

        main_layout.addWidget(button_box)

    def get_settings(self):
        return {
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
        }