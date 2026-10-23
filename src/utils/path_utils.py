import os
import platform
import re
from pathlib import Path, PureWindowsPath


def get_default_recordings_directory():
    """
    Retourne le dossier d'enregistrement par défaut
    adapté au système d'exploitation.
    """
    home_directory = Path.home()

    if platform.system() == "Windows":
        videos_directory = home_directory / "Videos"

    else:
        # Sous Linux, le dossier peut s'appeler Videos,
        # Vidéos ou ne pas encore exister.
        possible_directories = (
            home_directory / "Videos",
            home_directory / "Vidéos",
        )

        videos_directory = next(
            (
                directory
                for directory in possible_directories
                if directory.is_dir()
            ),
            home_directory / "Videos",
        )

    return (
        videos_directory
        / "OpenFishCounter"
    )


def is_windows_path(path_value):
    """
    Indique si une chaîne ressemble à un chemin Windows.

    Exemples :
        C:\\Users\\user\\Videos
        D:/OpenFishCounter
    """
    path_text = str(
        path_value or ""
    ).strip()

    if not path_text:
        return False

    windows_path = PureWindowsPath(
        path_text
    )

    return bool(
        windows_path.drive
    )


def is_unix_absolute_path(path_value):
    """
    Indique si une chaîne ressemble à un chemin
    absolu Linux ou macOS.
    """
    path_text = str(
        path_value or ""
    ).strip()

    return path_text.startswith("/")


def is_path_from_another_os(path_value):
    """
    Détecte un chemin manifestement issu d'un autre
    système d'exploitation.
    """
    system_name = platform.system()

    if system_name != "Windows":
        return is_windows_path(
            path_value
        )

    return is_unix_absolute_path(
        path_value
    )


def normalize_path(path_value):
    """
    Nettoie et développe un chemin local.

    Cette fonction ne convertit pas un chemin Windows
    en chemin Linux, car les deux arborescences ne sont
    pas équivalentes.
    """
    path_text = str(
        path_value or ""
    ).strip()

    if not path_text:
        return None

    path_text = os.path.expandvars(
        path_text
    )

    path_text = os.path.expanduser(
        path_text
    )

    return Path(path_text)


def directory_is_writable(directory):
    """
    Vérifie que le dossier existe et qu'il est possible
    d'y créer puis supprimer un petit fichier de test.
    """
    directory = Path(directory)

    if not directory.is_dir():
        return False

    test_file = (
        directory
        / ".open_fish_counter_write_test"
    )

    try:
        test_file.write_text(
            "write test",
            encoding="utf-8",
        )

        test_file.unlink()

        return True

    except OSError:
        try:
            if test_file.exists():
                test_file.unlink()

        except OSError:
            pass

        return False


def prepare_recordings_directory(
    configured_directory,
    logger=None,
):
    """
    Valide et prépare le dossier d'enregistrement.

    Comportement :
    - remplace un chemin provenant d'un autre OS ;
    - crée le dossier s'il n'existe pas ;
    - vérifie qu'il est accessible en écriture ;
    - utilise un dossier local de secours si nécessaire.

    Renvoie :
        tuple(Path, bool)

    Le booléen vaut True si le chemin configuré a dû
    être remplacé.
    """
    default_directory = (
        get_default_recordings_directory()
    )

    path_was_replaced = False

    if not configured_directory:
        recordings_directory = (
            default_directory
        )

        path_was_replaced = True

        if logger is not None:
            logger.warning(
                "Aucun dossier d'enregistrement "
                "configuré. Utilisation de : %s",
                recordings_directory,
            )

    elif is_path_from_another_os(
        configured_directory
    ):
        recordings_directory = (
            default_directory
        )

        path_was_replaced = True

        if logger is not None:
            logger.warning(
                "Le dossier configuré appartient à un "
                "autre système d'exploitation : %s. "
                "Utilisation de : %s",
                configured_directory,
                recordings_directory,
            )

    else:
        recordings_directory = normalize_path(
            configured_directory
        )

    try:
        recordings_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    except OSError as error:
        if logger is not None:
            logger.error(
                "Impossible de créer le dossier "
                "d'enregistrement %s : %s",
                recordings_directory,
                error,
            )

        recordings_directory = (
            default_directory
        )

        path_was_replaced = True

        recordings_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    if not directory_is_writable(
        recordings_directory
    ):
        if logger is not None:
            logger.error(
                "Le dossier d'enregistrement n'est "
                "pas accessible en écriture : %s",
                recordings_directory,
            )

        fallback_directory = (
            default_directory
        )

        fallback_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not directory_is_writable(
            fallback_directory
        ):
            raise OSError(
                "Aucun dossier d'enregistrement "
                "accessible en écriture. "
                f"Dossier testé : {fallback_directory}"
            )

        recordings_directory = (
            fallback_directory
        )

        path_was_replaced = True

        if logger is not None:
            logger.warning(
                "Utilisation du dossier de secours : %s",
                recordings_directory,
            )

    return (
        recordings_directory.resolve(),
        path_was_replaced,
    )