import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


LOGGER_NAME = "open_fish_counter"


def setup_logging(
    logs_directory,
    log_level=logging.INFO,
):
    logs_directory = Path(
        logs_directory
    ).expanduser()

    logs_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_file = (
        logs_directory
        / "open-fish-counter.log"
    )

    logger = logging.getLogger(
        LOGGER_NAME
    )

    logger.setLevel(log_level)
    logger.propagate = False

    # Évite de multiplier les handlers si la fonction
    # est appelée plusieurs fois.
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(
        fmt=(
            "%(asctime)s | "
            "%(levelname)-8s | "
            "%(name)s | "
            "%(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Affichage dans le terminal.
    console_handler = logging.StreamHandler()

    console_handler.setLevel(
        log_level
    )

    console_handler.setFormatter(
        formatter
    )

    logger.addHandler(
        console_handler
    )

    # Rotation quotidienne à minuit.
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
        delay=True,
    )

    file_handler.setLevel(
        log_level
    )

    file_handler.setFormatter(
        formatter
    )

    file_handler.suffix = "%Y-%m-%d"

    logger.addHandler(
        file_handler
    )

    logger.info(
        "Journalisation initialisée : %s",
        log_file,
    )

    return logger


def get_logger(module_name=None):
    if module_name:
        logger_name = (
            f"{LOGGER_NAME}.{module_name}"
        )
    else:
        logger_name = LOGGER_NAME

    return logging.getLogger(
        logger_name
    )