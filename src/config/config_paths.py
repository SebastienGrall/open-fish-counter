import os
import platform
import shutil
import sys
from pathlib import Path


APPLICATION_DIRECTORY_NAME = "OpenFishCounter"
LINUX_APPLICATION_DIRECTORY_NAME = "open-fish-counter"
CONFIG_FILENAME = "grid_config.json"


def get_user_config_directory():
    """
    Retourne le dossier de configuration propre
    à l'utilisateur courant.

    Windows :
        %LOCALAPPDATA%\\OpenFishCounter

    Linux :
        $XDG_CONFIG_HOME/open-fish-counter
        ou ~/.config/open-fish-counter
    """
    system_name = platform.system()

    if system_name == "Windows":
        local_app_data = os.environ.get(
            "LOCALAPPDATA"
        )

        if local_app_data:
            return (
                Path(local_app_data)
                / APPLICATION_DIRECTORY_NAME
            )

        return (
            Path.home()
            / "AppData"
            / "Local"
            / APPLICATION_DIRECTORY_NAME
        )

    xdg_config_home = os.environ.get(
        "XDG_CONFIG_HOME"
    )

    if xdg_config_home:
        return (
            Path(xdg_config_home).expanduser()
            / LINUX_APPLICATION_DIRECTORY_NAME
        )

    return (
        Path.home()
        / ".config"
        / LINUX_APPLICATION_DIRECTORY_NAME
    )


def get_user_config_file():
    """
    Retourne le chemin du fichier de configuration
    propre à l'utilisateur.
    """
    return (
        get_user_config_directory()
        / CONFIG_FILENAME
    )


def get_source_project_root():
    """
    Retourne la racine du projet en mode développement.

    Ce chemin est utilisé uniquement pour rechercher
    l'ancienne configuration du dépôt.
    """
    return (
        Path(__file__).resolve()
        .parent
        .parent
        .parent
    )


def get_packaged_application_directory():
    """
    Retourne le dossier de l'exécutable lorsque
    l'application est construite avec PyInstaller.
    """
    return (
        Path(sys.executable)
        .resolve()
        .parent
    )


def get_legacy_config_candidates():
    """
    Retourne les emplacements où une ancienne
    configuration peut être présente.

    Le premier fichier existant sera utilisé pour
    initialiser la configuration utilisateur.
    """
    candidates = []

    if getattr(
        sys,
        "frozen",
        False,
    ):
        application_directory = (
            get_packaged_application_directory()
        )

        candidates.extend(
            [
                (
                    application_directory
                    / "data"
                    / CONFIG_FILENAME
                ),
                (
                    application_directory
                    / CONFIG_FILENAME
                ),
            ]
        )

    source_project_root = (
        get_source_project_root()
    )

    candidates.append(
        source_project_root
        / "data"
        / CONFIG_FILENAME
    )

    return candidates


def prepare_user_config_file():
    """
    Prépare le fichier de configuration utilisateur.

    Comportement :
    - crée le dossier utilisateur s'il n'existe pas ;
    - conserve une configuration utilisateur existante ;
    - copie l'ancienne configuration au premier lancement ;
    - renvoie le chemin et une description de l'action.

    Renvoie :
        tuple(Path, str)
    """
    user_config_file = (
        get_user_config_file()
    )

    user_config_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if user_config_file.is_file():
        return (
            user_config_file,
            "existing",
        )

    for legacy_config_file in (
        get_legacy_config_candidates()
    ):
        if not legacy_config_file.is_file():
            continue

        shutil.copy2(
            legacy_config_file,
            user_config_file,
        )

        return (
            user_config_file,
            "migrated",
        )

    return (
        user_config_file,
        "new",
    )