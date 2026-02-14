#!/usr/bin/env python3
"""
Renomeador de Filmes - TMDB
Aplicativo desktop para renomear filmes com base na API do TheMovieDB
compatível com Kodi
"""

import sys
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import RenomeadorUI


def main():
    app = QApplication(sys.argv)
    window = RenomeadorUI()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
