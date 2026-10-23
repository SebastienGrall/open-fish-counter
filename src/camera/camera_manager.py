import platform
import time

import cv2
import numpy as np
import gc

from logging_utils.log_manager import get_logger

try:
    import imagingcontrol4 as ic4

    IC4_AVAILABLE = True
except ImportError:
    ic4 = None
    IC4_AVAILABLE = False


class CameraManager:
    BACKEND_OPENCV = "opencv"
    BACKEND_IC4 = "ic4"

    def __init__(
        self,
        camera_index=0,
        requested_width=640,
        requested_height=480,
        requested_fps=30.0,
        camera_backend="opencv",
        camera_serial=None,
        exposure_auto=True,
        exposure_time=5000.0,
        gain_auto=True,
        gain=0.0,
    ):
        self.logger = get_logger("camera")

        self.camera_index = int(camera_index)
        self.camera_backend = self._normalize_backend(camera_backend)
        self.camera_serial = (
            str(camera_serial).strip()
            if camera_serial
            else None
        )

        self.exposure_auto = bool(
            exposure_auto
        )

        self.exposure_time = max(
            1.0,
            float(exposure_time),
        )

        self.gain_auto = bool(
            gain_auto
        )

        self.gain = max(
            0.0,
            float(gain),
        )

        self.requested_width = max(1, int(requested_width))
        self.requested_height = max(1, int(requested_height))
        self.requested_fps = max(1.0, float(requested_fps))

        # Backend OpenCV.
        self.capture = None

        # Backend IC4.
        self.ic4_grabber = None
        self.ic4_sink = None
        self.ic4_device = None
        self.ic4_stream_started = False
        self.ic4_library_initialized = False

        self.actual_width = 0
        self.actual_height = 0
        self.actual_fps = 0.0

        self.last_error = None
        self.reconnect_interval = 2.0
        self.last_reconnect_attempt = 0.0

    @property
    def is_open(self):
        if self.camera_backend == self.BACKEND_IC4:
            return (
                self.ic4_grabber is not None
                and self.ic4_sink is not None
                and self.ic4_stream_started
            )

        return (
            self.capture is not None
            and self.capture.isOpened()
        )

    def open(self):
        """Ouvre la caméra avec le backend sélectionné."""
        self.close()
        self.last_error = None

        if self.camera_backend == self.BACKEND_IC4:
            return self._open_ic4()

        return self._open_opencv()

    def read(self):
        """Renvoie (True, frame) ou (False, None)."""
        if not self.is_open:
            self.last_error = "La caméra n'est pas ouverte."
            return False, None

        if self.camera_backend == self.BACKEND_IC4:
            return self._read_ic4()

        return self._read_opencv()

    def restart(
        self,
        camera_index=None,
        requested_width=None,
        requested_height=None,
        requested_fps=None,
        camera_backend=None,
        camera_serial=None,
        exposure_auto=None,
        exposure_time=None,
        gain_auto=None,
        gain=None,
    ):
        self.update_settings(
            camera_index=camera_index,
            requested_width=requested_width,
            requested_height=requested_height,
            requested_fps=requested_fps,
            camera_backend=camera_backend,
            camera_serial=camera_serial,
            exposure_auto=exposure_auto,
            exposure_time=exposure_time,
            gain_auto=gain_auto,
            gain=gain,
        )

        return self.open()

    def update_settings(
        self,
        camera_index=None,
        requested_width=None,
        requested_height=None,
        requested_fps=None,
        camera_backend=None,
        camera_serial=None,
        exposure_auto=None,
        exposure_time=None,
        gain_auto=None,
        gain=None,
    ):
        if camera_index is not None:
            self.camera_index = int(camera_index)

        if requested_width is not None:
            self.requested_width = max(1, int(requested_width))

        if requested_height is not None:
            self.requested_height = max(1, int(requested_height))

        if requested_fps is not None:
            self.requested_fps = max(1.0, float(requested_fps))

        if camera_backend is not None:
            self.camera_backend = (
                self._normalize_backend(
                    camera_backend
                )
            )

            if (
                self.camera_backend
                == self.BACKEND_OPENCV
            ):
                self.camera_serial = None

        if camera_serial is not None:
            serial = str(
                camera_serial
            ).strip()

            self.camera_serial = (
                serial or None
            )
        if exposure_auto is not None:
            self.exposure_auto = bool(
                exposure_auto
            )

        if exposure_time is not None:
            self.exposure_time = max(
                1.0,
                float(exposure_time),
            )

        if gain_auto is not None:
            self.gain_auto = bool(
                gain_auto
            )

        if gain is not None:
            self.gain = max(
                0.0,
                float(gain),
            )
        

    def close(self):
        """
        Ferme le flux courant sans arrêter définitivement IC4.
        """
        grabber = self.ic4_grabber

        if (
            grabber is not None
            and self.ic4_stream_started
        ):
            try:
                grabber.stream_stop()

            except Exception as error:
                self.logger.debug(
                    "Erreur pendant l'arrêt du flux IC4 : %s",
                    self._format_error(error),
                )

        self.ic4_stream_started = False

        # Supprime d'abord le sink, puis le périphérique,
        # puis le grabber local.
        self.ic4_sink = None
        self.ic4_device = None
        self.ic4_grabber = None

        if grabber is not None:
            del grabber

        if self.capture is not None:
            self.capture.release()

        self.capture = None

        self.actual_width = 0
        self.actual_height = 0
        self.actual_fps = 0.0

    def shutdown(self):
        """
        Ferme définitivement la caméra et libère IC4.

        Les objets Python liés aux buffers IC4 sont détruits
        avant l'arrêt de la bibliothèque native.
        """
        self.logger.info(
            "Arrêt définitif du gestionnaire de caméra."
        )

        # Arrête le flux et supprime les références vers
        # le Grabber, le Sink et le périphérique IC4.
        self.close()

        # Force la destruction des objets Python pouvant
        # encore référencer des objets natifs IC4.
        gc.collect()

        if (
            IC4_AVAILABLE
            and self.ic4_library_initialized
        ):
            try:
                self.logger.info(
                    "Fermeture de la bibliothèque IC4."
                )

                ic4.Library.exit()

                self.logger.info(
                    "Bibliothèque IC4 fermée."
                )

            except Exception as error:
                self.logger.warning(
                    "Erreur pendant la fermeture d'IC4 : %s",
                    self._format_error(error),
                )

            finally:
                self.ic4_library_initialized = False

        # Force une dernière collecte pendant que Python
        # et les extensions natives sont encore initialisés.
        gc.collect()

    def get_recording_fps(self):
        if self.actual_fps > 0:
            return self.actual_fps

        if self.requested_fps > 0:
            return self.requested_fps

        return 25.0

    def get_actual_settings(self):
        return {
            "backend": self.camera_backend,
            "serial": self.camera_serial,
            "width": self.actual_width,
            "height": self.actual_height,
            "fps": self.actual_fps,
            "exposure_auto": (
                self.exposure_auto
            ),
            "exposure_time": (
                self.exposure_time
            ),
            "gain_auto": (
                self.gain_auto
            ),
            "gain": self.gain,
        }

    def get_available_ic4_devices(self):
        """
        Retourne les caméras IC4 disponibles, dédoublonnées
        par numéro de série.

        Les objets internes IC4 ne sont pas transmis à
        l'interface graphique.
        """
        if not IC4_AVAILABLE:
            return []

        try:
            self._initialize_ic4_library()

            devices = self._list_unique_ic4_devices()

            return [
                {
                    "model": device["model"],
                    "serial": device["serial"],
                }
                for device in devices
            ]

        except Exception as error:
            self.logger.warning(
                "Impossible d'énumérer les caméras IC4 : %s",
                self._format_error(error),
            )

            return []

    def try_reconnect(self):
        if self.is_open:
            return True

        current_time = time.monotonic()

        if (
            current_time - self.last_reconnect_attempt
            < self.reconnect_interval
        ):
            return False

        self.last_reconnect_attempt = current_time

        self.logger.info(
            "Tentative de reconnexion caméra | backend=%s | index=%d | série=%s",
            self.camera_backend,
            self.camera_index,
            self.camera_serial,
        )

        opened = self.open()

        if opened:
            self.logger.info("Caméra reconnectée avec succès.")
        else:
            self.logger.warning(
                "Échec de la reconnexion : %s",
                self.last_error,
            )

        return opened

    def _open_opencv(self):
        system_name = platform.system()

        if system_name == "Windows":
            backends = (
                cv2.CAP_DSHOW,
                cv2.CAP_MSMF,
                cv2.CAP_ANY,
            )

        elif system_name == "Linux":
            backends = (
                cv2.CAP_V4L2,
                cv2.CAP_ANY,
            )

        else:
            backends = (
                cv2.CAP_ANY,
            )

        self.capture = None

        for backend in backends:
            capture = cv2.VideoCapture(
                self.camera_index,
                backend,
            )

            if capture.isOpened():
                self.capture = capture
                break

            capture.release()

        if (
            self.capture is None
            or not self.capture.isOpened()
        ):
            self.last_error = (
                "Impossible d'ouvrir la caméra OpenCV "
                f"d'index {self.camera_index}."
            )

            self.logger.warning(
                "%s",
                self.last_error,
            )

            self.close()

            return False

        self._apply_opencv_settings()
        self._read_opencv_settings()

        self.logger.info(
            "Caméra OpenCV ouverte | index=%d | "
            "résolution=%dx%d | fps=%.1f",
            self.camera_index,
            self.actual_width,
            self.actual_height,
            self.actual_fps,
        )

        return True

    def _read_opencv(self):
        ok, frame = self.capture.read()

        if not ok or frame is None:
            self.last_error = "Connexion à la caméra OpenCV perdue."
            self.logger.warning("%s", self.last_error)
            self.close()
            return False, None

        return True, frame

    def _open_ic4(self):
        if not IC4_AVAILABLE:
            self.last_error = (
                "Le backend IC4 est sélectionné, mais imagingcontrol4 "
                "n'est pas installé."
            )
            self.logger.error("%s", self.last_error)
            return False

        try:
            self._initialize_ic4_library()
            devices = self._list_unique_ic4_devices()

            if not devices:
                self.last_error = "Aucune caméra IC4 détectée."
                self.logger.warning("%s", self.last_error)
                return False

            self.ic4_device = self._select_ic4_device(devices)

            if self.ic4_device is None:
                available = ", ".join(
                    device["serial"] for device in devices
                )
                self.last_error = (
                    f"Caméra IC4 de série {self.camera_serial} introuvable. "
                    f"Séries disponibles : {available}"
                )
                self.logger.warning("%s", self.last_error)
                return False

            self.ic4_grabber = ic4.Grabber()
            self.ic4_grabber.device_open(
                self.ic4_device["device_info"]
            )

            self._apply_ic4_settings()

            self.ic4_sink = ic4.SnapSink()
            self.ic4_grabber.stream_setup(
                self.ic4_sink,
                setup_option=(
                    ic4.StreamSetupOption.ACQUISITION_START
                ),
            )
            self.ic4_stream_started = True

            self.actual_width = self.requested_width
            self.actual_height = self.requested_height
            self.actual_fps = self._read_ic4_fps()

            self.logger.info(
                "Caméra IC4 ouverte | modèle=%s | série=%s | "
                "résolution demandée=%dx%d | fps=%.1f",
                self.ic4_device["model"],
                self.ic4_device["serial"],
                self.requested_width,
                self.requested_height,
                self.actual_fps,
            )
            return True

        except Exception as error:
            self.last_error = self._format_error(error)
            self.logger.exception(
                "Impossible d'ouvrir la caméra IC4 : %s",
                self.last_error,
            )
            self.close()
            return False

    def _read_ic4(self):
        image_buffer = None
        buffer_view = None

        try:
            image_buffer = (
                self.ic4_sink.snap_single(2000)
            )

            # numpy_wrap() renvoie une vue vers la mémoire
            # du buffer IC4. Le buffer doit donc rester vivant
            # jusqu'à la fin de la copie.
            buffer_view = (
                image_buffer.numpy_wrap()
            )

            # Création explicite d'une image indépendante.
            frame = np.array(
                buffer_view,
                copy=True,
                order="C",
            )

            # Destruction dans l'ordre inverse :
            # d'abord la vue NumPy, puis le buffer IC4.
            del buffer_view
            buffer_view = None

            del image_buffer
            image_buffer = None

            if frame.size == 0:
                raise RuntimeError(
                    "IC4 a renvoyé une image vide."
                )

            # Uniformisation vers le format BGR utilisé
            # par le reste de l'application.
            if frame.ndim == 2:
                frame = cv2.cvtColor(
                    frame,
                    cv2.COLOR_GRAY2BGR,
                )

            elif (
                frame.ndim == 3
                and frame.shape[2] == 1
            ):
                frame = cv2.cvtColor(
                    frame,
                    cv2.COLOR_GRAY2BGR,
                )

            elif (
                frame.ndim == 3
                and frame.shape[2] == 4
            ):
                frame = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGRA2BGR,
                )

            self.actual_height = int(
                frame.shape[0]
            )

            self.actual_width = int(
                frame.shape[1]
            )

            return True, frame

        except Exception as error:
            self.last_error = (
                "Connexion à la caméra IC4 perdue : "
                f"{self._format_error(error)}"
            )

            self.logger.warning(
                "%s",
                self.last_error,
            )

            self.close()

            return False, None

        finally:
            # Sécurise également l'ordre de destruction
            # lorsqu'une exception survient avant la copie.
            if buffer_view is not None:
                del buffer_view

            if image_buffer is not None:
                del image_buffer

    def _initialize_ic4_library(self):
        if self.ic4_library_initialized:
            return

        ic4.Library.init(
            api_log_level=ic4.LogLevel.INFO,
            log_targets=ic4.LogTarget.STDERR,
        )
        self.ic4_library_initialized = True

    def _list_unique_ic4_devices(self):
        unique_devices = {}

        for device_info in ic4.DeviceEnum.devices():
            serial = str(device_info.serial).strip()
            unique_name = str(device_info.unique_name).strip()
            key = serial or unique_name

            if key not in unique_devices:
                unique_devices[key] = {
                    "model": str(device_info.model_name),
                    "serial": serial,
                    "unique_name": unique_name,
                    "device_info": device_info,
                }

        return list(unique_devices.values())

    def _select_ic4_device(self, devices):
        if not self.camera_serial:
            return devices[0]

        for device in devices:
            if device["serial"] == self.camera_serial:
                return device

        return None

    def _apply_ic4_settings(self):
        property_map = self.ic4_grabber.device_property_map

        settings = (
            (ic4.PropId.WIDTH, self.requested_width, "largeur"),
            (ic4.PropId.HEIGHT, self.requested_height, "hauteur"),
            (
                ic4.PropId.ACQUISITION_FRAME_RATE,
                self.requested_fps,
                "fréquence d'images",
            ),
        )

        for property_id, value, label in settings:
            try:
                property_map.set_value(property_id, value)
            except Exception as error:
                self.logger.warning(
                    "Réglage IC4 non appliqué | %s=%s | %s",
                    label,
                    value,
                    self._format_error(error),
                )

        self._apply_ic4_exposure_settings(
            property_map
        )
        self._apply_ic4_gain_settings(
            property_map
        )

    def _apply_ic4_exposure_settings(
        self,
        property_map,
    ):
        """
        Applique les réglages d'exposition IC4.

        En mode automatique, le temps manuel mémorisé
        n'est pas appliqué.
        """
        try:
            if self.exposure_auto:
                property_map.set_value(
                    ic4.PropId.EXPOSURE_AUTO,
                    "Continuous",
                )

                self.logger.info(
                    "Exposition IC4 automatique activée."
                )

            else:
                property_map.set_value(
                    ic4.PropId.EXPOSURE_AUTO,
                    "Off",
                )

                property_map.set_value(
                    ic4.PropId.EXPOSURE_TIME,
                    self.exposure_time,
                )

                self.logger.info(
                    "Exposition IC4 manuelle | "
                    "temps=%.1f µs",
                    self.exposure_time,
                )

        except Exception as error:
            self.logger.warning(
                "Impossible d'appliquer l'exposition "
                "IC4 : %s",
                self._format_error(error),
            )

    def _apply_ic4_gain_settings(
        self,
        property_map,
    ):
        """
        Applique les réglages de gain IC4.

        En mode automatique, le gain manuel mémorisé
        n'est pas appliqué.
        """
        try:
            if self.gain_auto:
                property_map.set_value(
                    ic4.PropId.GAIN_AUTO,
                    "Continuous",
                )

                self.logger.info(
                    "Gain IC4 automatique activé."
                )

            else:
                property_map.set_value(
                    ic4.PropId.GAIN_AUTO,
                    "Off",
                )

                property_map.set_value(
                    ic4.PropId.GAIN,
                    self.gain,
                )

                self.logger.info(
                    "Gain IC4 manuel | gain=%.2f",
                    self.gain,
                )

        except Exception as error:
            self.logger.warning(
                "Impossible d'appliquer le gain "
                "IC4 : %s",
                self._format_error(error),
            )

    def _read_ic4_fps(self):
        try:
            value = self.ic4_grabber.device_property_map.get_value(
                ic4.PropId.ACQUISITION_FRAME_RATE
            )
            return float(value)
        except Exception:
            return self.requested_fps

    def _apply_opencv_settings(self):
        self.capture.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            self.requested_width,
        )
        self.capture.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            self.requested_height,
        )
        self.capture.set(
            cv2.CAP_PROP_FPS,
            self.requested_fps,
        )

    def _read_opencv_settings(self):
        self.actual_width = int(
            self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        )
        self.actual_height = int(
            self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        )
        self.actual_fps = float(
            self.capture.get(cv2.CAP_PROP_FPS)
        )

    @staticmethod
    def _normalize_backend(camera_backend):
        backend = str(camera_backend).strip().lower()

        if backend not in (
            CameraManager.BACKEND_OPENCV,
            CameraManager.BACKEND_IC4,
        ):
            return CameraManager.BACKEND_OPENCV

        return backend

    @staticmethod
    def _format_error(error):
        return str(getattr(error, "message", error))

    @staticmethod
    def _get_opencv_backend():
        system_name = platform.system()

        if system_name == "Windows":
            return cv2.CAP_DSHOW

        if system_name == "Linux":
            return cv2.CAP_V4L2

        return None
