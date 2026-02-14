#!/usr/bin/env python3
"""
Renomeador de Filmes - TMDB
Aplicativo desktop para renomear filmes com base na API do TheMovieDB
compatível com Kodi
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from src.ui.main_window import RenomeadorUI


def main():
    app = QApplication(sys.argv)
    icon_path = Path(__file__).parent / "src" / "img" / "tmdb-256.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = RenomeadorUI()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
