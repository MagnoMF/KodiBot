import sys
import os
import requests
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox,
    QSpinBox, QHeaderView, QComboBox, QStyledItemDelegate, QAbstractItemView,
    QInputDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from pathlib import Path

from src.core.tmdb_client import TMDBClient
from src.core.kodi_namer import KodiNamer
from src.core.config import get_config_dir, get_env_path


class SearchThread(QThread):
    """Thread para buscar filmes sem bloquear a UI"""
    search_completed = pyqtSignal(list)
    search_error = pyqtSignal(str)
    
    def __init__(self, query, year, tmdb_client, media_type):
        super().__init__()
        self.query = query
        self.year = year
        self.tmdb_client = tmdb_client
        self.media_type = media_type
    
    def run(self):
        try:
            if self.media_type == "tv":
                results = self.tmdb_client.search_tv(self.query, self.year if self.year > 0 else None)
            else:
                results = self.tmdb_client.search_movie(self.query, self.year if self.year > 0 else None)
            self.search_completed.emit(results)
        except Exception as e:
            self.search_error.emit(str(e))


RESULTS_ROLE = int(Qt.ItemDataRole.UserRole) + 1
SELECTED_ROLE = int(Qt.ItemDataRole.UserRole) + 2
TYPE_ROLE = int(Qt.ItemDataRole.UserRole) + 3


class ResultComboDelegate(QStyledItemDelegate):
    """Delegate para selecionar resultados do TMDB"""

    selection_changed = pyqtSignal(int, int)

    def createEditor(self, parent, option, index):
        results = index.data(RESULTS_ROLE) or []
        media_type = index.data(TYPE_ROLE) or "movie"
        combo = QComboBox(parent)
        for result in results[:10]:
            if media_type == "tv":
                title = result.get('name', 'N/A')
                release_date = result.get('first_air_date', '')
            else:
                title = result.get('title', 'N/A')
                release_date = result.get('release_date', '')
            year = release_date.split('-')[0] if release_date else ''
            label = f"{title} ({year})" if year else title
            combo.addItem(label)
        combo.activated.connect(lambda i: self._commit_and_close(combo, index.row(), i))
        return combo

    def setEditorData(self, editor, index):
        selected_index = index.data(SELECTED_ROLE)
        if isinstance(selected_index, int) and 0 <= selected_index < editor.count():
            editor.setCurrentIndex(selected_index)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.ItemDataRole.DisplayRole)
        model.setData(index, editor.currentIndex(), SELECTED_ROLE)

    def _commit_and_close(self, editor, row, index):
        self.selection_changed.emit(row, index)
        self.commitData.emit(editor)
        self.closeEditor.emit(editor, QStyledItemDelegate.EndEditHint.NoHint)


class RenomeadorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tmdb_client = None
        self.selected_folder = None
        self.video_files = []
        self.search_thread = None
        self.current_search_index = 0
        self.search_results = []
        self.search_types = []
        self.active_search_type = "movie"
        self.poster_cache = {}
        self.series_results = []
        self.selected_series_id = None
        self.selected_series_title = ""
        self.selected_season_number = None
        self.season_episodes = []
        
        self.init_ui()
        self.init_tmdb()
        self.load_folder_preference()
    
    def init_ui(self):
        """Inicializa a interface gráfica"""
        self.setWindowTitle("Kodi Bot - TMDB")
        self.setGeometry(100, 100, 1000, 700)

        icon_path = self.get_asset_path("tmdb-256.png")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Seção de Configuração
        config_layout = QHBoxLayout()
        logo_path = self.get_asset_path("tmdb-64.png")
        if logo_path.exists():
            logo_label = QLabel()
            pixmap = QPixmap(str(logo_path))
            logo_label.setPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            config_layout.addWidget(logo_label)
        config_layout.addWidget(QLabel("Pasta de Filmes:"))
        config_layout.addStretch()
        browse_btn = QPushButton("Procurar Pasta")
        browse_btn.clicked.connect(self.browse_folder)
        config_layout.addWidget(browse_btn)
        refresh_btn = QPushButton("Atualizar Lista")
        refresh_btn.clicked.connect(self.load_video_files)
        config_layout.addWidget(refresh_btn)
        config_layout.addWidget(QLabel("Tipo:"))
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItem("Filmes", "movie")
        self.search_type_combo.addItem("Series", "tv")
        config_layout.addWidget(self.search_type_combo)
        self.search_type_combo.currentIndexChanged.connect(self.on_search_type_changed)
        config_layout.addWidget(QLabel("Idioma:"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("Selecione...", "")
        self.language_combo.addItem("Portuguese (BR)", "pt-BR")
        self.language_combo.addItem("English (US)", "en-US")
        self.language_combo.addItem("Spanish (ES)", "es-ES")
        current_lang = self.get_env_value("APP_LANGUAGE")
        if current_lang:
            lang_index = self.language_combo.findData(current_lang)
            if lang_index >= 0:
                self.language_combo.setCurrentIndex(lang_index)
            else:
                self.language_combo.addItem(current_lang, current_lang)
                self.language_combo.setCurrentIndex(self.language_combo.count() - 1)
        else:
            self.language_combo.setCurrentIndex(0)
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        config_layout.addWidget(self.language_combo)
        layout.addLayout(config_layout)
        
        self.folder_label = QLabel("Nenhuma pasta selecionada")
        layout.addWidget(self.folder_label)

        self.series_layout = QHBoxLayout()
        self.series_layout.addWidget(QLabel("Serie:"))
        self.series_search_input = QLineEdit()
        self.series_search_input.setPlaceholderText("Digite o nome da serie")
        self.series_layout.addWidget(self.series_search_input)
        self.series_search_btn = QPushButton("Buscar Serie")
        self.series_search_btn.clicked.connect(self.search_series)
        self.series_layout.addWidget(self.series_search_btn)
        self.series_layout.addWidget(QLabel("Resultados:"))
        self.series_results_combo = QComboBox()
        self.series_results_combo.currentIndexChanged.connect(self.on_series_selected)
        self.series_layout.addWidget(self.series_results_combo)
        self.series_layout.addWidget(QLabel("Temporada:"))
        self.season_combo = QComboBox()
        self.season_combo.currentIndexChanged.connect(self.on_season_selected)
        self.series_layout.addWidget(self.season_combo)
        layout.addLayout(self.series_layout)
        
        # Seção de Arquivos
        layout.addWidget(QLabel("Arquivos na pasta:"))
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(4)
        self.files_table.setHorizontalHeaderLabels(
            ["Arquivo Original", "Ano Detectado", "Nome Sugerido", "Selecao"]
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self.files_table.setEditTriggers(
            QAbstractItemView.EditTrigger.CurrentChanged
        )
        self.files_table.currentCellChanged.connect(self.on_table_selection_changed)
        files_layout = QHBoxLayout()
        files_layout.addWidget(self.files_table, 1)

        poster_layout = QVBoxLayout()
        self.poster_label = QLabel("Sem imagem")
        self.poster_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.poster_label.setFixedSize(220, 330)
        self.poster_label.setStyleSheet("border: 1px solid #444;")
        poster_layout.addWidget(self.poster_label)

        self.poster_title = QLabel("")
        self.poster_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.poster_title.setWordWrap(True)
        poster_layout.addWidget(self.poster_title)

        self.poster_meta = QLabel("")
        self.poster_meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.poster_meta.setWordWrap(True)
        poster_layout.addWidget(self.poster_meta)

        self.poster_overview = QLabel("")
        self.poster_overview.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.poster_overview.setWordWrap(True)
        self.poster_overview.setFixedWidth(220)
        poster_layout.addWidget(self.poster_overview)
        poster_layout.addStretch()

        files_layout.addLayout(poster_layout)

        layout.addLayout(files_layout)

        self.result_delegate = ResultComboDelegate(self.files_table)
        self.result_delegate.selection_changed.connect(self.on_result_choice_changed)
        self.files_table.setItemDelegateForColumn(3, self.result_delegate)
        
        # Botões de Ação
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        search_btn = QPushButton("Buscar Filmes")
        search_btn.clicked.connect(self.search_movie)
        action_layout.addWidget(search_btn)
        
        rename_btn = QPushButton("Renomear Arquivos")
        rename_btn.clicked.connect(self.rename_files)
        action_layout.addWidget(rename_btn)
        
        layout.addLayout(action_layout)
        
        central_widget.setLayout(layout)
        self.on_search_type_changed()

    def get_asset_path(self, filename):
        return Path(__file__).parent.parent / "img" / filename

    def get_env_path(self):
        return get_env_path()
    
    def init_tmdb(self):
        """Inicializa o cliente TMDB"""
        try:
            self.tmdb_client = TMDBClient()
        except ValueError as e:
            api_key = self.prompt_api_key()
            if api_key:
                self.save_api_key(api_key)
                os.environ["TMDB_API_KEY"] = api_key
                try:
                    self.tmdb_client = TMDBClient()
                except ValueError as e2:
                    QMessageBox.critical(
                        self, "Erro de Configuração",
                        f"Erro ao inicializar TMDB: {str(e2)}\n\n"
                        "Verifique a chave informada e tente novamente."
                    )
            else:
                QMessageBox.critical(
                    self, "Erro de Configuração",
                    f"Erro ao inicializar TMDB: {str(e)}\n\n"
                    "Certifique-se de que o arquivo .env contém TMDB_API_KEY"
                )

    def prompt_api_key(self):
        """Solicita a API Key do TMDB ao usuario"""
        key, ok = QInputDialog.getText(
            self,
            "Chave TMDB",
            "Informe sua TMDB API Key:",
            QLineEdit.EchoMode.Password
        )
        key = key.strip()
        return key if ok and key else None

    def save_api_key(self, api_key):
        """Salva a API Key no .env na raiz do projeto"""
        from dotenv import load_dotenv
        env_path = self.get_env_path()
        try:
            env_path.parent.mkdir(parents=True, exist_ok=True)
            lines = []
            if env_path.exists():
                lines = env_path.read_text(encoding='utf-8').splitlines()
        except OSError as exc:
            self.show_file_error("Erro ao criar .env", env_path.parent, exc)
            return

        replaced = False
        for idx, line in enumerate(lines):
            if line.startswith("TMDB_API_KEY="):
                lines[idx] = f"TMDB_API_KEY={api_key}"
                replaced = True
                break

        if not replaced:
            lines.append(f"TMDB_API_KEY={api_key}")

        try:
            env_path.write_text("\n".join(lines) + "\n", encoding='utf-8')
            # Força o reload do .env após salvar
            load_dotenv(dotenv_path=env_path, override=True)
        except OSError as exc:
            self.show_file_error("Erro ao salvar .env", env_path, exc)

    def on_search_type_changed(self):
        is_tv = self.search_type_combo.currentData() == "tv"
        for i in range(self.series_layout.count()):
            item = self.series_layout.itemAt(i)
            if item and item.widget():
                item.widget().setVisible(is_tv)

    def save_app_language(self, language):
        """Salva o idioma no .env na raiz do projeto"""
        from dotenv import load_dotenv
        env_path = self.get_env_path()
        try:
            env_path.parent.mkdir(parents=True, exist_ok=True)
            lines = []
            if env_path.exists():
                lines = env_path.read_text(encoding='utf-8').splitlines()
        except OSError as exc:
            self.show_file_error("Erro ao criar .env", env_path.parent, exc)
            return

        replaced = False
        for idx, line in enumerate(lines):
            if line.startswith("APP_LANGUAGE="):
                lines[idx] = f"APP_LANGUAGE={language}"
                replaced = True
                break

        if not replaced:
            lines.append(f"APP_LANGUAGE={language}")

        try:
            env_path.write_text("\n".join(lines) + "\n", encoding='utf-8')
            # Força o reload do .env após salvar
            load_dotenv(dotenv_path=env_path, override=True)
        except OSError as exc:
            self.show_file_error("Erro ao salvar .env", env_path, exc)

    def get_env_value(self, key):
        value = os.getenv(key)
        if value:
            return value
        env_path = self.get_env_path()
        if not env_path.exists():
            return None
        for line in env_path.read_text(encoding='utf-8').splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
        return None

    def on_language_changed(self):
        language = self.language_combo.currentData()
        if language:
            os.environ["APP_LANGUAGE"] = language
            self.save_app_language(language)
    
    def browse_folder(self):
        """Abre diálogo para selecionar pasta"""
        folder = QFileDialog.getExistingDirectory(
            self, "Selecione a pasta com os filmes"
        )
        if folder:
            self.selected_folder = folder
            self.folder_label.setText(f"Pasta: {folder}")
            self.save_folder_preference(folder)
            self.load_video_files()
    
    def save_folder_preference(self, folder_path):
        """Salva a pasta selecionada nas preferências"""
        config_dir = get_config_dir()
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.show_file_error("Erro ao criar pasta de configuracao", config_dir, exc)
            return

        config_file = config_dir / "last_folder.txt"
        try:
            config_file.write_text(folder_path)
        except OSError as exc:
            self.show_file_error("Erro ao salvar ultima pasta", config_file, exc)
    
    def load_folder_preference(self):
        """Carrega a última pasta selecionada"""
        config_file = get_config_dir() / "last_folder.txt"
        
        if config_file.exists():
            try:
                folder = config_file.read_text().strip()
            except OSError as exc:
                self.show_file_error("Erro ao ler ultima pasta", config_file, exc)
                return
            if Path(folder).exists():
                self.selected_folder = folder
                self.folder_label.setText(f"Pasta: {folder}")
                self.load_video_files()

    def show_file_error(self, title, path, exc):
        message = f"{title}:\n{path}\n\nDetalhes: {exc}"
        QMessageBox.critical(self, "Erro de Arquivo", message)
    
    def load_video_files(self):
        """Carrega lista de arquivos de vídeo da pasta selecionada"""
        if not self.selected_folder:
            return
        
        self.video_files = []
        self.search_results = []
        self.search_types = []
        self.poster_label.setText("Sem imagem")
        self.poster_label.setPixmap(QPixmap())
        self.poster_title.setText("")
        self.poster_meta.setText("")
        self.poster_overview.setText("")
        self.files_table.setRowCount(0)
        
        folder_path = Path(self.selected_folder)
        for file in folder_path.iterdir():
            if KodiNamer.is_video_file(file.name):
                self.video_files.append(file)
                self.search_results.append([])
                self.search_types.append(None)
                row = self.files_table.rowCount()
                self.files_table.insertRow(row)
                original_item = QTableWidgetItem(file.name)
                original_item.setFlags(original_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.files_table.setItem(row, 0, original_item)

                year_item = QTableWidgetItem("")
                year_item.setFlags(year_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.files_table.setItem(row, 1, year_item)

                suggested_item = QTableWidgetItem("")
                suggested_item.setFlags(suggested_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.files_table.setItem(row, 2, suggested_item)
                select_item = QTableWidgetItem("Aguardando busca")
                select_item.setFlags(select_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                select_item.setData(RESULTS_ROLE, [])
                select_item.setData(SELECTED_ROLE, -1)
                self.files_table.setItem(row, 3, select_item)
    
    def search_movie(self):
        """Busca filmes no TMDB baseado nos arquivos da pasta"""
        if not self.tmdb_client:
            QMessageBox.warning(self, "Erro", "TMDB não foi inicializado corretamente")
            return
        
        if not self.video_files:
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo de vídeo encontrado na pasta")
            return

        if self.search_type_combo.currentData() == "tv":
            if not self.selected_series_id or not self.season_episodes:
                QMessageBox.warning(self, "Aviso", "Selecione uma serie e temporada primeiro")
                return
            self.apply_season_to_files()
            return
        
        # Inicia a busca sequencial
        self.active_search_type = self.search_type_combo.currentData() or "movie"
        self.current_search_index = 0
        self.search_next_file()

    def search_series(self):
        if not self.tmdb_client:
            QMessageBox.warning(self, "Erro", "TMDB nao foi inicializado corretamente")
            return
        query = self.series_search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Aviso", "Digite o nome da serie")
            return

        try:
            results = self.tmdb_client.search_tv(query)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao buscar serie: {e}")
            return

        # Ordena series por data de lancamento (mais recente primeiro)
        if results:
            results = sorted(
                results,
                key=lambda x: x.get('first_air_date', ''),
                reverse=True
            )
        
        self.series_results = results or []
        self.series_results_combo.blockSignals(True)
        self.series_results_combo.clear()
        if self.series_results:
            for result in self.series_results:
                title = result.get('name', 'N/A')
                release_date = result.get('first_air_date', '')
                year = release_date.split('-')[0] if release_date else ''
                label = f"{title} ({year})" if year else title
                self.series_results_combo.addItem(label)
        self.series_results_combo.blockSignals(False)
        self.on_series_selected()

    def on_series_selected(self):
        if not self.series_results:
            self.selected_series_id = None
            self.selected_series_title = ""
            self.season_combo.clear()
            return

        index = self.series_results_combo.currentIndex()
        if index < 0 or index >= len(self.series_results):
            return
        selected = self.series_results[index]
        self.selected_series_id = selected.get('id')
        self.selected_series_title = selected.get('name', '')

        try:
            details = self.tmdb_client.get_tv_details(self.selected_series_id)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao buscar temporadas: {e}")
            return

        seasons = details.get('seasons', [])
        self.season_combo.blockSignals(True)
        self.season_combo.clear()
        for season in seasons:
            season_number = season.get('season_number')
            if season_number is None:
                continue
            name = season.get('name') or f"Temporada {season_number}"
            self.season_combo.addItem(name, season_number)
        self.season_combo.blockSignals(False)
        self.on_season_selected()

    def on_season_selected(self):
        season_number = self.season_combo.currentData()
        if self.selected_series_id is None or season_number is None:
            return
        self.selected_season_number = int(season_number)

        try:
            season_details = self.tmdb_client.get_tv_season_details(
                self.selected_series_id, self.selected_season_number
            )
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao buscar episodios: {e}")
            return

        self.season_episodes = season_details.get('episodes', [])
        self.apply_season_to_files()

    def apply_season_to_files(self):
        if not self.season_episodes:
            return

        for row, video_file in enumerate(self.video_files):
            self.search_results[row] = self.season_episodes
            self.search_types[row] = "tv"
            select_item = self.files_table.item(row, 3)
            if select_item is None:
                select_item = QTableWidgetItem()
                self.files_table.setItem(row, 3, select_item)
            select_item.setData(RESULTS_ROLE, self.season_episodes)
            select_item.setData(TYPE_ROLE, "tv")

            season, episode = KodiNamer.extract_episode_info(video_file.name)
            if season is None:
                season = self.selected_season_number
            if season != self.selected_season_number:
                select_item.setText("Selecione episodio")
                select_item.setData(SELECTED_ROLE, -1)
                select_item.setFlags(select_item.flags() | Qt.ItemFlag.ItemIsEditable)
                continue

            episode_index = -1
            for idx, ep in enumerate(self.season_episodes):
                if ep.get('episode_number') == episode:
                    episode_index = idx
                    break

            if episode_index >= 0:
                ep = self.season_episodes[episode_index]
                ep_title = ep.get('name', '')
                label = f"E{int(ep.get('episode_number', 0)):02d} - {ep_title}" if ep_title else f"E{int(ep.get('episode_number', 0)):02d}"
                select_item.setText(label)
                select_item.setData(SELECTED_ROLE, episode_index)
                select_item.setFlags(select_item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.update_suggested_name(row, episode_index)
            else:
                select_item.setText("Selecione episodio")
                select_item.setData(SELECTED_ROLE, -1)
                select_item.setFlags(select_item.flags() | Qt.ItemFlag.ItemIsEditable)
    
    def search_next_file(self):
        """Busca o próximo arquivo da lista"""
        if self.current_search_index >= len(self.video_files):
            # Terminou de buscar todos
            QMessageBox.information(self, "Conclusão", "Busca concluída para todos os arquivos!")
            return
        
        video_file = self.video_files[self.current_search_index]
        # Limpa o nome do arquivo antes de buscar e tenta capturar o ano
        query, year = KodiNamer.clean_filename(video_file.name)
        row = self.current_search_index
        if row < len(self.search_types):
            self.search_types[row] = self.active_search_type
        if row < self.files_table.rowCount():
            self.files_table.setItem(row, 1, QTableWidgetItem(str(year or "")))
        
        if not query:
            self.current_search_index += 1
            self.search_next_file()
            return
        
        # Executa a busca em thread separada
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.wait()
        
        self.search_thread = SearchThread(query, year or 0, self.tmdb_client, self.active_search_type)
        self.search_thread.search_completed.connect(self.on_search_completed)
        self.search_thread.search_error.connect(self.on_search_error)
        self.search_thread.start()
    
    def on_search_completed(self, results):
        """Callback quando a busca é concluída"""
        row = self.current_search_index
        if row < self.files_table.rowCount():
            # Ordena os resultados por ano (mais recente primeiro)
            media_type = self.search_types[row] or "movie"
            if results:
                sorted_results = sorted(
                    results,
                    key=lambda x: (
                        x.get('first_air_date', '') if media_type == "tv" else x.get('release_date', '')
                    ),
                    reverse=True
                )
            else:
                sorted_results = results
            
            self.search_results[row] = sorted_results
            select_item = self.files_table.item(row, 3)
            if select_item is None:
                select_item = QTableWidgetItem()
                self.files_table.setItem(row, 3, select_item)
            select_item.setData(RESULTS_ROLE, sorted_results)
            select_item.setData(TYPE_ROLE, media_type)
            if sorted_results:
                best_result = sorted_results[0]
                if media_type == "tv":
                    title = best_result.get('name', 'N/A')
                    release_date = best_result.get('first_air_date', '')
                else:
                    title = best_result.get('title', 'N/A')
                    release_date = best_result.get('release_date', '')
                year = release_date.split('-')[0] if release_date else ''
                label = f"{title} ({year})" if year else title
                select_item.setText(label)
                select_item.setData(SELECTED_ROLE, 0)
                select_item.setFlags(select_item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.update_suggested_name(row, 0)
            else:
                select_item.setText("Sem resultados")
                select_item.setData(SELECTED_ROLE, -1)
                select_item.setFlags(select_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.files_table.setItem(row, 2, QTableWidgetItem(""))
                if row == self.current_search_index:
                    self.poster_label.setText("Sem imagem")
                    self.poster_label.setPixmap(QPixmap())
                    self.poster_title.setText("")
                    self.poster_meta.setText("")
                    self.poster_overview.setText("")
        
        # Busca o próximo arquivo
        self.current_search_index += 1
        self.search_next_file()
    
    def on_search_error(self, error):
        """Callback para erro na busca"""
        print(f"Erro na busca: {error}")
        # Continua para o próximo arquivo mesmo com erro
        self.current_search_index += 1
        self.search_next_file()

    def on_result_choice_changed(self, row, index):
        """Atualiza o nome sugerido conforme selecao do usuario"""
        self.update_suggested_name(row, index)

    def on_table_selection_changed(self, current_row, current_column, previous_row, previous_column):
        if current_row < 0 or current_row >= len(self.search_results):
            return
        select_item = self.files_table.item(current_row, 3)
        if not select_item:
            return
        selected_index = select_item.data(SELECTED_ROLE)
        if selected_index is None:
            return
        self.update_poster(current_row, int(selected_index))

    def update_suggested_name(self, row, index):
        if row >= len(self.search_results):
            return
        results = self.search_results[row]
        if not results or index < 0 or index >= len(results):
            return
        selected = results[index]
        media_type = self.search_types[row] or "movie"
        if media_type == "tv":
            episode_title = selected.get('name', '')
            season_num = selected.get('season_number', self.selected_season_number)
            episode_num = selected.get('episode_number')
            series_title = self.selected_series_title or "Serie"
            video_file = self.video_files[row]
            suggested_name = KodiNamer.suggest_episode_filename(
                video_file.name, series_title, season_num, episode_num, episode_title
            )
            self.files_table.setItem(row, 2, QTableWidgetItem(suggested_name))
            self.update_poster(row, index)
            return
        else:
            title = selected.get('title', 'N/A')
            release_date = selected.get('release_date', '')
        year = release_date.split('-')[0] if release_date else ''
        video_file = self.video_files[row]
        suggested_name = KodiNamer.suggest_kodi_filename(
            video_file.name, title, year
        )
        self.files_table.setItem(row, 2, QTableWidgetItem(suggested_name))
        self.update_poster(row, index)

    def update_poster(self, row, index):
        results = self.search_results[row]
        if not results or index < 0 or index >= len(results):
            self.poster_label.setText("Sem imagem")
            self.poster_label.setPixmap(QPixmap())
            self.poster_title.setText("")
            self.poster_meta.setText("")
            self.poster_overview.setText("")
            return

        media_type = self.search_types[row] or "movie"
        if media_type == "tv":
            poster_path = results[index].get('still_path')
            image_size = "w300"
        else:
            poster_path = results[index].get('poster_path')
            image_size = "w342"
        self.update_poster_info(results[index], media_type)
        if not poster_path:
            self.poster_label.setText("Sem imagem")
            self.poster_label.setPixmap(QPixmap())
            return

        url = f"https://image.tmdb.org/t/p/{image_size}{poster_path}"
        if url in self.poster_cache:
            pixmap = self.poster_cache[url]
            self.poster_label.setPixmap(
                pixmap.scaled(
                    self.poster_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            return

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            pixmap = QPixmap()
            if pixmap.loadFromData(response.content):
                self.poster_cache[url] = pixmap
                self.poster_label.setPixmap(
                    pixmap.scaled(
                        self.poster_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                self.poster_label.setText("")
            else:
                self.poster_label.setText("Sem imagem")
                self.poster_label.setPixmap(QPixmap())
        except requests.RequestException:
            self.poster_label.setText("Sem imagem")
            self.poster_label.setPixmap(QPixmap())

    def update_poster_info(self, result, media_type):
        if media_type == "tv":
            episode_title = result.get('name', 'N/A')
            season_num = result.get('season_number', self.selected_season_number)
            episode_num = result.get('episode_number')
            series_title = self.selected_series_title or "Serie"
            title = f"{series_title} - S{int(season_num):02d}E{int(episode_num):02d}"
            release_date = ''
        else:
            title = result.get('title', 'N/A')
            release_date = result.get('release_date', '')

        year = release_date.split('-')[0] if release_date else ''
        rating = result.get('vote_average')
        votes = result.get('vote_count')
        overview = result.get('overview', '')
        if media_type == "tv" and episode_title:
            overview = f"{episode_title}\n{overview}" if overview else episode_title

        self.poster_title.setText(title if title else '')
        meta_parts = []
        if year:
            meta_parts.append(year)
        if rating is not None:
            meta_parts.append(f"Avaliacao: {rating:.1f}")
        if votes is not None:
            meta_parts.append(f"Votos: {votes}")
        self.poster_meta.setText(" | ".join(meta_parts))
        self.poster_overview.setText(overview if overview else "")
    
    def rename_files(self):
        """Renomeia os arquivos selecionados"""
        if not self.selected_folder:
            QMessageBox.warning(self, "Aviso", "Selecione uma pasta primeiro")
            return
        
        renamed_count = 0
        errors = []
        
        for row in range(self.files_table.rowCount()):
            original_item = self.files_table.item(row, 0)
            suggested_item = self.files_table.item(row, 2)
            
            if not original_item or not suggested_item:
                continue
            
            original_name = original_item.text()
            suggested_name = suggested_item.text()
            
            if not suggested_name:
                continue
            
            original_path = Path(self.selected_folder) / original_name
            new_path = Path(self.selected_folder) / suggested_name
            
            try:
                original_path.rename(new_path)
                renamed_count += 1
            except Exception as e:
                errors.append(f"{original_name}: {str(e)}")
        
        if errors:
            error_msg = "Erros ao renomear:\n" + "\n".join(errors)
            QMessageBox.warning(self, "Erros", error_msg)
        
        QMessageBox.information(
            self, "Conclusão",
            f"{renamed_count} arquivo(s) renomeado(s) com sucesso"
        )
        
        # Recarrega a lista de arquivos
        self.load_video_files()
