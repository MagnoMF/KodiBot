from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

class HeaderSettings(QWidget):
    movie_folder_selected = pyqtSignal(str)
    kodi_folder_selected = pyqtSignal(str)
    refresh_requested = pyqtSignal()
    search_type_changed = pyqtSignal(str)
    more_settings_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderSettings")
        self.selected_movie_folder = ""
        self.selected_kodi_folder = ""

        layout = QVBoxLayout(self)

        config_layout = QHBoxLayout()

        browse_btn = QPushButton("Pasta de Filmes")
        browse_btn.clicked.connect(self.browse_movies_folder)
        config_layout.addWidget(browse_btn)

        kodi_btn = QPushButton("Pasta Kodi")
        kodi_btn.clicked.connect(self.browse_kodi_folder)
        config_layout.addWidget(kodi_btn)

        refresh_btn = QPushButton("Atualizar Lista")
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        config_layout.addWidget(refresh_btn)

        more_settings_btn = QPushButton("⚙")
        more_settings_btn.setToolTip("Mais configuracoes")
        more_settings_btn.clicked.connect(self.more_settings_requested.emit)
        config_layout.addWidget(more_settings_btn)

        config_layout.addWidget(QLabel("Tipo:"))
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItem("Filmes", "movie")
        self.search_type_combo.addItem("Series", "tv")
        self.search_type_combo.currentIndexChanged.connect(self._emit_search_type_changed)
        config_layout.addWidget(self.search_type_combo)

        layout.addLayout(config_layout)

        self.folder_label = QLabel("Pasta Filmes: Nenhuma pasta selecionada")
        layout.addWidget(self.folder_label)

        self.kodi_folder_label = QLabel("Pasta Kodi: Nenhuma pasta selecionada")
        layout.addWidget(self.kodi_folder_label)

    def set_movie_selected_folder(self, folder):
        self.selected_movie_folder = folder or ""
        if self.selected_movie_folder:
            self.folder_label.setText(f"Pasta Filmes: {self.selected_movie_folder}")
        else:
            self.folder_label.setText("Pasta Filmes: Nenhuma pasta selecionada")

    def set_kodi_selected_folder(self, folder):
        self.selected_kodi_folder = folder or ""
        if self.selected_kodi_folder:
            self.kodi_folder_label.setText(f"Pasta Kodi: {self.selected_kodi_folder}")
        else:
            self.kodi_folder_label.setText("Pasta Kodi: Nenhuma pasta selecionada")

    def get_movie_selected_folder(self):
        return self.selected_movie_folder
    
    def get_kodi_selected_folder(self):
        return self.selected_kodi_folder

    def _emit_search_type_changed(self):
        self.search_type_changed.emit(self.search_type_combo.currentData() or "movie")
    
    def browse_movies_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Selecione a pasta com os filmes"
        )
        if folder:
            self.set_movie_selected_folder(folder)
            self.movie_folder_selected.emit(folder)
    
    def browse_kodi_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Selecione a pasta do Kodi"
        )
        if folder:
            self.set_kodi_selected_folder(folder)
            self.kodi_folder_selected.emit(folder)
            self.refresh_requested.emit()