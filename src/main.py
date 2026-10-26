import sys
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def get_resource_path(relative_path):
    """
    Retourne le chemin d'une ressource en développement
    ou dans une application construite avec PyInstaller.
    """
    if getattr(
        sys,
        "frozen",
        False,
    ):
        base_directory = Path(
            sys._MEIPASS
        )

    else:
        base_directory = (
            Path(__file__).resolve()
            .parent
            .parent
        )

    return (
        base_directory
        / relative_path
    )


def main():
    app = QApplication(sys.argv)

    app_icon_path = get_resource_path(
        Path(
            "assets"
        )
        / "icons"
        / "open-fish-counter-512.png"
    )

    if app_icon_path.is_file():
        app.setWindowIcon(
            QIcon(
                str(app_icon_path)
            )
        )

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()