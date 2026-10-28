from __future__ import annotations

import json
import os
import platform
import shutil
import smtplib
import ssl
import subprocess
import sys

from datetime import date, datetime, time, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any


APP_NAME = "Open Fish Counter"
APP_VERSION = "1.0.0-alpha"

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

SERVICE_NAME = "open-fish-counter.service"

VIDEO_EXTENSIONS = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
}

JSON_EXTENSIONS = {
    ".json",
}


# ============================================================
# Chemins compatibles Debian et Windows
# ============================================================

def get_config_directory() -> Path:
    """
    Retourne le dossier utilisateur de configuration.

    Debian :
        ~/.config/open-fish-counter

    Windows :
        %LOCALAPPDATA%\\OpenFishCounter
    """

    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")

        if local_app_data:
            return Path(local_app_data) / "OpenFishCounter"

        return (
            Path.home()
            / "AppData"
            / "Local"
            / "OpenFishCounter"
        )

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")

    if xdg_config_home:
        return (
            Path(xdg_config_home)
            / "open-fish-counter"
        )

    return (
        Path.home()
        / ".config"
        / "open-fish-counter"
    )


CONFIG_DIRECTORY = get_config_directory()

CONFIG_FILE = (
    CONFIG_DIRECTORY
    / "grid_config.json"
)

MAIL_ENV_FILE = (
    CONFIG_DIRECTORY
    / "mail.env"
)


# ============================================================
# Chargement des fichiers de configuration
# ============================================================

def load_json_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Fichier de configuration introuvable : {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"Format de configuration incorrect : {path}"
        )

    return data


def load_env_file(path: Path) -> dict[str, str]:
    """
    Charge un fichier de type :

        MAIL_FROM=adresse@gmail.com
        MAIL_TO=adresse1@gmail.com,adresse2@gmail.com
        MAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx

    Aucune dépendance python-dotenv n'est nécessaire.
    """

    if not path.is_file():
        raise FileNotFoundError(
            f"Fichier de configuration mail introuvable : {path}"
        )

    values: dict[str, str] = {}

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        for raw_line in file:
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split(
                "=",
                1,
            )

            key = key.strip()
            value = value.strip()

            # Autorise éventuellement :
            # VARIABLE="valeur"
            # VARIABLE='valeur'
            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in {'"', "'"}
            ):
                value = value[1:-1]

            values[key] = value

    return values


# ============================================================
# Lecture des paramètres Open Fish Counter
# ============================================================

def get_station_name(
    app_config: dict[str, Any],
) -> str:
    station_config = app_config.get(
        "station",
        {},
    )

    if not isinstance(station_config, dict):
        station_config = {}

    station_name = str(
        station_config.get(
            "name",
            "Station",
        )
    ).strip()

    if not station_name:
        station_name = "Station"

    return station_name


def find_recording_directory_in_config(
    app_config: dict[str, Any],
) -> Path | None:
    """
    Cherche le dossier d'enregistrement dans la section recording.

    Plusieurs noms sont pris en charge pour rester compatible avec
    une éventuelle évolution du fichier de configuration.
    """

    recording_config = app_config.get(
        "recording",
        {},
    )

    if not isinstance(recording_config, dict):
        return None

    possible_keys = (
        "output_directory",
        "recording_directory",
        "recordings_directory",
        "recording_folder",
        "recordings_folder",
        "output_folder",
        "output_dir",
        "recording_path",
        "save_directory",
        "save_folder",
        "base_directory",
        "directory",
        "folder",
        "path",
    )

    for key in possible_keys:
        value = recording_config.get(key)

        if value is None:
            continue

        value = str(value).strip()

        if value:
            return Path(value).expanduser()

    return None


def get_fallback_recording_directory() -> Path:
    """
    Repli uniquement si aucun chemin n'est présent dans la config.

    Le script privilégie un dossier existant avant d'utiliser
    le chemin standard de la plateforme.
    """

    candidates: list[Path] = []

    if os.name == "nt":
        candidates.extend(
            [
                Path.home()
                / "Videos"
                / "OpenFishCounter",

                Path("D:/OpenFishCounter"),

                Path("D:/"),
            ]
        )

    else:
        candidates.extend(
            [
                Path.home()
                / "Vidéos"
                / "OpenFishCounter",

                Path.home()
                / "Videos"
                / "OpenFishCounter",
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    if os.name == "nt":
        return (
            Path.home()
            / "Videos"
            / "OpenFishCounter"
        )

    return (
        Path.home()
        / "Vidéos"
        / "OpenFishCounter"
    )


def get_recording_directory(
    app_config: dict[str, Any],
) -> Path:
    configured_directory = (
        find_recording_directory_in_config(
            app_config
        )
    )

    if configured_directory is not None:
        return configured_directory

    return get_fallback_recording_directory()


# ============================================================
# Recherche du dossier de la journée
# ============================================================

def find_day_video_directory(
    recording_directory: Path,
    station_name: str,
    report_day: date,
) -> Path:
    """
    Structure attendue :

        OpenFishCounter/
            Nom station/
                2026-10-28/
                    videos/

    On commence par la station exacte. Si le nom du dossier a été
    sécurisé par l'application, on cherche ensuite le dossier du jour
    dans les sous-dossiers immédiats.
    """

    date_directory_name = report_day.strftime(
        "%Y-%m-%d"
    )

    exact_directory = (
        recording_directory
        / station_name
        / date_directory_name
        / "videos"
    )

    if exact_directory.is_dir():
        return exact_directory

    if recording_directory.is_dir():
        matching_directories = list(
            recording_directory.glob(
                f"*/{date_directory_name}/videos"
            )
        )

        matching_directories = [
            directory
            for directory in matching_directories
            if directory.is_dir()
        ]

        if len(matching_directories) == 1:
            return matching_directories[0]

    # Même inexistant, ce chemin permet d'afficher clairement
    # où le script a cherché.
    return exact_directory


# ============================================================
# Comptage des fichiers de la veille
# ============================================================

def count_daily_files(
    day_video_directory: Path,
) -> tuple[int, int, Path | None]:
    if not day_video_directory.is_dir():
        return 0, 0, None

    video_files: list[Path] = []
    json_files: list[Path] = []

    for file_path in day_video_directory.rglob("*"):
        if not file_path.is_file():
            continue

        suffix = file_path.suffix.lower()

        if suffix in VIDEO_EXTENSIONS:
            video_files.append(file_path)

        elif suffix in JSON_EXTENSIONS:
            json_files.append(file_path)

    last_video: Path | None = None

    if video_files:
        last_video = max(
            video_files,
            key=lambda path: path.stat().st_mtime,
        )

    return (
        len(video_files),
        len(json_files),
        last_video,
    )


# ============================================================
# État Open Fish Counter
# ============================================================

def run_command(
    command: list[str],
) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )

        output = (
            result.stdout.strip()
            or result.stderr.strip()
        )

        return result.returncode, output

    except Exception as error:
        return 1, str(error)


def get_application_status() -> str:
    if os.name == "nt":
        return get_windows_application_status()

    return get_linux_application_status()


def get_linux_application_status() -> str:
    return_code, output = run_command(
        [
            "systemctl",
            "--user",
            "is-active",
            SERVICE_NAME,
        ]
    )

    if return_code == 0 and output == "active":
        return "OK - service actif"

    if output:
        return f"ERREUR - {output}"

    return "ERREUR - service inactif"


def get_windows_application_status() -> str:
    """
    Contrôle indicatif sous Windows.

    Il cherche d'abord l'exécutable construit, puis un lancement
    éventuel depuis src/main.py.
    """

    return_code, output = run_command(
        [
            "tasklist",
            "/FI",
            "IMAGENAME eq OpenFishCounter.exe",
        ]
    )

    if (
        return_code == 0
        and "OpenFishCounter.exe".lower()
        in output.lower()
    ):
        return "OK - application active"

    return_code, output = run_command(
        [
            "wmic",
            "process",
            "where",
            (
                "name='python.exe' or "
                "name='pythonw.exe'"
            ),
            "get",
            "CommandLine",
        ]
    )

    if (
        return_code == 0
        and "src\\main.py".lower()
        in output.lower()
    ):
        return "OK - application active depuis Python"

    return "ERREUR - application non détectée"


# ============================================================
# Redémarrages systemd de la veille
# ============================================================

def get_linux_restart_count(
    report_day: date,
) -> int | None:
    if os.name == "nt":
        return None

    day_start = datetime.combine(
        report_day,
        time.min,
    )

    next_day_start = day_start + timedelta(
        days=1
    )

    return_code, output = run_command(
        [
            "journalctl",
            "--user",
            "-u",
            SERVICE_NAME,
            "--since",
            day_start.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "--until",
            next_day_start.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "--no-pager",
            "-o",
            "cat",
        ]
    )

    if return_code != 0:
        return None

    start_messages = (
        "Started Open Fish Counter",
        "Démarré Open Fish Counter",
    )

    start_count = sum(
        1
        for line in output.splitlines()
        if any(
            message in line
            for message in start_messages
        )
    )

    # Un démarrage normal n'est pas un redémarrage après incident.
    return max(
        0,
        start_count - 1,
    )


# ============================================================
# Informations système
# ============================================================

def get_disk_information(
    recording_directory: Path,
) -> tuple[float, float, float]:
    """
    Si le dossier n'existe pas encore, utilise son premier parent
    existant pour déterminer le disque concerné.
    """

    disk_path = recording_directory

    while not disk_path.exists():
        parent = disk_path.parent

        if parent == disk_path:
            break

        disk_path = parent

    disk_usage = shutil.disk_usage(
        disk_path
    )

    total_gb = (
        disk_usage.total
        / 1024**3
    )

    free_gb = (
        disk_usage.free
        / 1024**3
    )

    used_percent = (
        disk_usage.used
        / disk_usage.total
        * 100
    )

    return (
        total_gb,
        free_gb,
        used_percent,
    )


def get_uptime() -> str:
    if os.name == "nt":
        return get_windows_uptime()

    return_code, output = run_command(
        [
            "uptime",
            "-p",
        ]
    )

    if return_code == 0 and output:
        return output

    return "inconnu"


def get_windows_uptime() -> str:
    """
    Utilise PowerShell, présent par défaut sous Windows.
    """

    powershell_command = (
        "$boot = "
        "(Get-CimInstance Win32_OperatingSystem)"
        ".LastBootUpTime; "
        "$up = (Get-Date) - $boot; "
        "'up {0} jour(s) {1} h {2} min' "
        "-f $up.Days, $up.Hours, $up.Minutes"
    )

    return_code, output = run_command(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            powershell_command,
        ]
    )

    if return_code == 0 and output:
        return output

    return "inconnu"


# ============================================================
# Préparation du rapport
# ============================================================

def build_report() -> tuple[str, str]:
    app_config = load_json_file(
        CONFIG_FILE
    )

    station_name = get_station_name(
        app_config
    )

    recording_directory = (
        get_recording_directory(
            app_config
        )
    )

    report_day = (
        datetime.now().date()
        - timedelta(days=1)
    )

    day_video_directory = (
        find_day_video_directory(
            recording_directory,
            station_name,
            report_day,
        )
    )

    (
        video_count,
        json_count,
        last_video,
    ) = count_daily_files(
        day_video_directory
    )

    (
        total_gb,
        free_gb,
        used_percent,
    ) = get_disk_information(
        recording_directory
    )

    application_status = (
        get_application_status()
    )

    restart_count = (
        get_linux_restart_count(
            report_day
        )
    )

    uptime = get_uptime()

    if last_video is None:
        last_video_text = "Aucune"
    else:
        last_video_text = last_video.name

    if restart_count is None:
        restart_text = (
            "Non disponible sur cette plateforme"
        )
    else:
        restart_text = str(restart_count)

    subject = (
        f"[Open Fish Counter] "
        f"{station_name} - "
        f"Rapport du "
        f"{report_day:%d/%m/%Y}"
    )

    body = f"""Bonjour,

Voici le rapport quotidien Open Fish Counter.

Station :
{station_name}

Journée analysée :
{report_day:%d/%m/%Y}
de 00:00:00 à 23:59:59

Enregistrements :
- Vidéos créées : {video_count}
- Fichiers JSON créés : {json_count}
- Dernière vidéo : {last_video_text}

Stockage :
- Dossier analysé : {day_video_directory}
- Espace libre : {free_gb:.1f} Go
- Capacité totale : {total_gb:.1f} Go
- Occupation du disque : {used_percent:.1f} %

État du logiciel :
- Statut actuel : {application_status}
- Redémarrages détectés : {restart_text}

Machine :
- Système : {platform.system()} {platform.release()}
- Nom de la machine : {platform.node()}
- Temps de fonctionnement : {uptime}

Configuration :
- Fichier : {CONFIG_FILE}
- Dossier d'enregistrement : {recording_directory}

--
{APP_NAME} {APP_VERSION}
"""

    return subject, body


# ============================================================
# Envoi Gmail
# ============================================================

def send_email(
    subject: str,
    body: str,
) -> None:
    mail_config = load_env_file(
        MAIL_ENV_FILE
    )

    mail_from = mail_config.get(
        "MAIL_FROM",
        "",
    ).strip()

    mail_to_value = mail_config.get(
        "MAIL_TO",
        "",
    ).strip()

    app_password = mail_config.get(
        "MAIL_APP_PASSWORD",
        "",
    ).replace(
        " ",
        "",
    )

    recipients = [
        address.strip()
        for address in mail_to_value.split(",")
        if address.strip()
    ]

    if not mail_from:
        raise ValueError(
            "MAIL_FROM est absent de mail.env"
        )

    if not recipients:
        raise ValueError(
            "MAIL_TO est absent de mail.env"
        )

    if not app_password:
        raise ValueError(
            "MAIL_APP_PASSWORD est absent de mail.env"
        )

    message = EmailMessage()

    message["Subject"] = subject
    message["From"] = mail_from
    message["To"] = ", ".join(
        recipients
    )

    message.set_content(
        body,
        charset="utf-8",
    )

    tls_context = (
        ssl.create_default_context()
    )

    with smtplib.SMTP(
        SMTP_HOST,
        SMTP_PORT,
        timeout=30,
    ) as smtp:
        smtp.ehlo()
        smtp.starttls(
            context=tls_context
        )
        smtp.ehlo()

        smtp.login(
            mail_from,
            app_password,
        )

        smtp.send_message(
            message,
            from_addr=mail_from,
            to_addrs=recipients,
        )


# ============================================================
# Point d'entrée
# ============================================================

def main() -> int:
    try:
        subject, body = build_report()

        # Permet de contrôler le rapport sans envoyer de mail :
        #
        # Debian :
        #   python scripts/daily_report.py --preview
        #
        # Windows :
        #   python scripts\\daily_report.py --preview

        preview_only = (
            "--preview"
            in sys.argv
        )

        print()
        print(subject)
        print()
        print(body)

        if preview_only:
            print(
                "Mode aperçu : aucun mail envoyé."
            )

            return 0

        send_email(
            subject,
            body,
        )

        print(
            "Rapport envoyé avec succès."
        )

        return 0

    except Exception as error:
        print(
            f"Échec du rapport quotidien : {error}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )