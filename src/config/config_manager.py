import json
from copy import deepcopy
from pathlib import Path


DEFAULT_CONFIG = {
    "camera": {
        "index": 1,
        "width": 720,
        "height": 540,
        "fps": 30.0,
    },
    "detection": {
        "pixel_threshold": 25,
        "required_motion_frames": 3,
        "no_motion_delay": 1.0,
    },
    "recording": {
        "pre_event_seconds": 1.0,
    },
    "grid": {
        "rows": 8,
        "cols": 8,
    },
    "cells": {},
}


class ConfigManager:
    def __init__(self, config_path):
        self.config_path = Path(config_path)
        self.config = deepcopy(DEFAULT_CONFIG)

    def load(self):
        """
        Charge la configuration depuis le fichier JSON.

        Si le fichier n'existe pas ou est invalide,
        les valeurs par défaut sont conservées.
        """
        self.config = deepcopy(DEFAULT_CONFIG)

        if not self.config_path.exists():
            print(
                "Aucune configuration existante, "
                "utilisation des valeurs par défaut."
            )

            return deepcopy(self.config)

        try:
            with self.config_path.open(
                "r",
                encoding="utf-8",
            ) as config_file:
                loaded_config = json.load(config_file)

            self._merge_config(
                self.config,
                loaded_config,
            )

            print(
                "Configuration chargée depuis : "
                f"{self.config_path}"
            )

        except json.JSONDecodeError as error:
            print(
                "Le fichier de configuration contient "
                f"un JSON invalide : {error}"
            )

        except OSError as error:
            print(
                "Impossible de lire la configuration : "
                f"{error}"
            )

        return deepcopy(self.config)

    def save(self, config):
        """
        Sauvegarde atomiquement la configuration.

        Le contenu est d'abord écrit dans un fichier
        temporaire, puis ce fichier remplace le JSON.
        """
        self.config = deepcopy(config)

        self.config_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = self.config_path.with_suffix(
            ".json.tmp"
        )

        try:
            with temporary_path.open(
                "w",
                encoding="utf-8",
            ) as config_file:
                json.dump(
                    self.config,
                    config_file,
                    indent=4,
                    ensure_ascii=False,
                )

            temporary_path.replace(
                self.config_path
            )

            print(
                "Configuration sauvegardée dans : "
                f"{self.config_path}"
            )

            return True

        except OSError as error:
            print(
                "Impossible de sauvegarder "
                f"la configuration : {error}"
            )

            return False

    def get_section(self, section_name):
        """
        Renvoie une copie d'une section complète.
        """
        section = self.config.get(
            section_name,
            {},
        )

        if not isinstance(section, dict):
            return {}

        return deepcopy(section)

    def get_value(
        self,
        section_name,
        key,
        default=None,
    ):
        """
        Renvoie une valeur précise de la configuration.
        """
        section = self.config.get(
            section_name,
            {},
        )

        if not isinstance(section, dict):
            return default

        return section.get(
            key,
            default,
        )

    def _merge_config(
        self,
        default_config,
        loaded_config,
    ):
        """
        Fusionne récursivement le JSON chargé avec les
        valeurs par défaut.

        Cela permet aux anciennes configurations de rester
        compatibles lorsque de nouveaux paramètres sont ajoutés.
        """
        if not isinstance(loaded_config, dict):
            return

        for key, loaded_value in loaded_config.items():
            if (
                key in default_config
                and isinstance(
                    default_config[key],
                    dict,
                )
                and isinstance(
                    loaded_value,
                    dict,
                )
            ):
                self._merge_config(
                    default_config[key],
                    loaded_value,
                )

            else:
                default_config[key] = loaded_value