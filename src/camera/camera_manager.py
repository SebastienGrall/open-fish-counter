import platform
import time
import cv2


class CameraManager:
    def __init__(
        self,
        camera_index=0,
        requested_width=640,
        requested_height=480,
        requested_fps=30.0,
    ):
        self.camera_index = int(camera_index)

        self.requested_width = int(
            requested_width
        )

        self.requested_height = int(
            requested_height
        )

        self.requested_fps = float(
            requested_fps
        )

        self.capture = None

        self.actual_width = 0
        self.actual_height = 0
        self.actual_fps = 0.0

        self.last_error = None

        self.reconnect_interval = 2.0
        self.last_reconnect_attempt = 0.0

    @property
    def is_open(self):
        return (
            self.capture is not None
            and self.capture.isOpened()
        )

    def open(self):
        """
        Ouvre la caméra et applique les paramètres demandés.

        Renvoie True si la caméra est correctement ouverte,
        sinon False.
        """
        self.close()

        self.last_error = None

        backend = self._get_backend()

        if backend is None:
            self.capture = cv2.VideoCapture(
                self.camera_index
            )
        else:
            self.capture = cv2.VideoCapture(
                self.camera_index,
                backend,
            )

        if not self.capture.isOpened():
            self.last_error = (
                "Impossible d'ouvrir la caméra "
                f"à l'index {self.camera_index}."
            )

            self.close()

            return False

        self._apply_requested_settings()
        self._read_actual_settings()

        print(
            "Paramètres caméra demandés : "
            f"{self.requested_width} x "
            f"{self.requested_height} à "
            f"{self.requested_fps:.1f} FPS"
        )

        print(
            "Paramètres caméra obtenus : "
            f"{self.actual_width} x "
            f"{self.actual_height} à "
            f"{self.actual_fps:.1f} FPS"
        )

        return True

    def read(self):
        """
        Lit une image de la caméra.

        Renvoie :
            (True, frame) si la lecture réussit ;
            (False, None) sinon.
        """
        if not self.is_open:
            self.last_error = (
                "La caméra n'est pas ouverte."
            )

            return False, None

        ok, frame = self.capture.read()

        if not ok or frame is None:
            self.last_error = (
                "Connexion à la caméra perdue."
            )

            self.close()

            return False, None

        return True, frame

    def restart(
        self,
        camera_index=None,
        requested_width=None,
        requested_height=None,
        requested_fps=None,
    ):
        """
        Ferme puis rouvre la caméra avec les nouveaux
        paramètres éventuellement fournis.
        """
        self.update_settings(
            camera_index=camera_index,
            requested_width=requested_width,
            requested_height=requested_height,
            requested_fps=requested_fps,
        )

        return self.open()

    def update_settings(
        self,
        camera_index=None,
        requested_width=None,
        requested_height=None,
        requested_fps=None,
    ):
        """
        Modifie les paramètres mémorisés sans redémarrer
        automatiquement la caméra.
        """
        if camera_index is not None:
            self.camera_index = int(
                camera_index
            )

        if requested_width is not None:
            self.requested_width = max(
                1,
                int(requested_width),
            )

        if requested_height is not None:
            self.requested_height = max(
                1,
                int(requested_height),
            )

        if requested_fps is not None:
            self.requested_fps = max(
                1.0,
                float(requested_fps),
            )

    def close(self):
        """
        Ferme proprement la caméra.
        """
        if self.capture is not None:
            self.capture.release()

        self.capture = None

        self.actual_width = 0
        self.actual_height = 0
        self.actual_fps = 0.0

    def get_recording_fps(self):
        """
        Renvoie un FPS utilisable par défaut pour
        l'enregistreur.

        Le FPS mesuré à partir du pré-buffer restera
        prioritaire au démarrage de chaque événement.
        """
        if self.actual_fps > 0:
            return self.actual_fps

        if self.requested_fps > 0:
            return self.requested_fps

        return 25.0

    def get_actual_settings(self):
        """
        Renvoie les paramètres réellement annoncés par
        la caméra et son pilote.
        """
        return {
            "width": self.actual_width,
            "height": self.actual_height,
            "fps": self.actual_fps,
        }

    def _apply_requested_settings(self):
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

    def _read_actual_settings(self):
        self.actual_width = int(
            self.capture.get(
                cv2.CAP_PROP_FRAME_WIDTH
            )
        )

        self.actual_height = int(
            self.capture.get(
                cv2.CAP_PROP_FRAME_HEIGHT
            )
        )

        self.actual_fps = float(
            self.capture.get(
                cv2.CAP_PROP_FPS
            )
        )

    @staticmethod
    def _get_backend():
        """
        Choisit un backend vidéo adapté au système.

        Windows : DirectShow
        Linux : V4L2
        Autres systèmes : sélection automatique OpenCV
        """
        system_name = platform.system()

        if system_name == "Windows":
            return cv2.CAP_DSHOW

        if system_name == "Linux":
            return cv2.CAP_V4L2

        return None

    def try_reconnect(self):
        """
        Tente de rouvrir la caméra au maximum une fois
        par intervalle de reconnexion.

        Renvoie True si la caméra est disponible.
        """
        if self.is_open:
            return True

        current_time = time.monotonic()

        if (
            current_time - self.last_reconnect_attempt
            < self.reconnect_interval
        ):
            return False

        self.last_reconnect_attempt = current_time

        print(
            "Tentative de reconnexion à la caméra "
            f"d'index {self.camera_index}..."
        )

        opened = self.open()

        if opened:
            print("Caméra reconnectée avec succès.")

        else:
            print(
                "Échec de la reconnexion : "
                f"{self.last_error}"
            )

        return opened