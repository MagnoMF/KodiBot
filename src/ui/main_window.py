import requests
import shutil
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidgetItem, QMessageBox,
    QComboBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from pathlib import Path

from src.core.TmdbClient import TMDBClient
from src.core.KodiNamer import KodiNamer
from src.core.assets_handler import get_asset_path
from src.core.config import get_setting, get_settings_path, set_setting
from src.ui.components.HeaderSettings import HeaderSettings
from src.ui.components.MoreSettings import MoreSettings
from src.ui.components.NewFilesList import NewFilesList, RESULTS_ROLE, SELECTED_ROLE, TYPE_ROLE, SUGGESTED_NAME_ROLE


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

        icon_path = get_asset_path("tmdb-256.png")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()

        self.header_config = HeaderSettings(parent=self)
        self.header_config.movie_folder_selected.connect(self.on_movie_folder_selected)
        self.header_config.kodi_folder_selected.connect(self.on_kodi_folder_selected)
        self.header_config.refresh_requested.connect(self.refresh_files_lists)
        self.header_config.search_type_changed.connect(self.on_search_type_changed)
        self.header_config.more_settings_requested.connect(self.open_more_settings)
        layout.addWidget(self.header_config)

        self.search_type_combo = self.header_config.search_type_combo
        self.folder_label = self.header_config.folder_label

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
        
        self.files_section = NewFilesList(parent=self)
        self.files_table = self.files_section.files_table
        self.kodi_files_table = self.files_section.kodi_files_table
        self.poster_label = self.files_section.poster_label
        self.poster_title = self.files_section.poster_title
        self.poster_meta = self.files_section.poster_meta
        self.poster_overview = self.files_section.poster_overview
        self.result_delegate = self.files_section.result_delegate
        self.original_column = self.files_section.original_column
        self.year_column = self.files_section.year_column
        self.select_column = self.files_section.select_column
        self.send_to_kodi_column = self.files_section.send_to_kodi_column
        self.files_table.currentCellChanged.connect(self.on_table_selection_changed)
        self.result_delegate.selection_changed.connect(self.on_result_choice_changed)
        layout.addWidget(self.files_section)
        
        # Botões de Ação
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        search_btn = QPushButton("Buscar Filmes")
        search_btn.clicked.connect(self.search_movie)
        action_layout.addWidget(search_btn)
        
        rename_btn = QPushButton("Enviar Arquivos")
        rename_btn.clicked.connect(self.rename_files)
        action_layout.addWidget(rename_btn)
        
        layout.addLayout(action_layout)
        
        central_widget.setLayout(layout)
        self.on_search_type_changed()

    def init_tmdb(self):
        """Inicializa o cliente TMDB"""
        try:
            self.tmdb_client = TMDBClient()
        except OSError as e:
            self.show_file_error("Erro ao ler configuracoes", get_settings_path(), e)
        except ValueError as e:
            api_key = self.prompt_api_key()
            if api_key:
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
                    "Certifique-se de que a configuracao contém TMDB_API_KEY"
                )

    def prompt_api_key(self):
        """Solicita a API Key do TMDB ao usuario"""
        more_settings = MoreSettings(parent=self)
        return more_settings.ask_tmdb_api_key()

    def open_more_settings(self):
        more_settings = MoreSettings(parent=self)
        current_language = self.get_env_value("APP_LANGUAGE")
        settings_result = more_settings.open_settings_dialog(
            current_language=current_language,
            remove_original_after_send=self.should_remove_original_after_send(),
        )

        if not settings_result:
            return

        language = settings_result.get("language")
        if language:
            self.save_app_language(language)

        api_key = settings_result.get("api_key")
        if not api_key:
            QMessageBox.information(self, "Configurações", "Idioma atualizado com sucesso.")
            return

        try:
            self.tmdb_client = TMDBClient()
            QMessageBox.information(self, "Configurações", "TMDB API Key atualizada com sucesso.")
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Erro de Configuração",
                f"Nao foi possivel inicializar TMDB com a nova chave:\n\n{exc}"
            )

    def on_search_type_changed(self, *_):
        is_tv = self.search_type_combo.currentData() == "tv"
        for i in range(self.series_layout.count()):
            item = self.series_layout.itemAt(i)
            if item and item.widget():
                item.widget().setVisible(is_tv)

    def save_app_language(self, language):
        """Salva o idioma nas configuracoes do app"""
        try:
            set_setting("APP_LANGUAGE", language)
        except OSError as exc:
            self.show_file_error("Erro ao salvar configuracoes", get_settings_path(), exc)

    def get_env_value(self, key):
        try:
            return get_setting(key)
        except OSError as exc:
            self.show_file_error("Erro ao ler configuracoes", get_settings_path(), exc)
            return None

    def should_remove_original_after_send(self):
        value = (self.get_env_value("REMOVE_ORIGINAL_AFTER_SEND") or "").strip().lower()
        return value in {"1", "true", "yes", "on", "sim"}

    def on_movie_folder_selected(self, folder):
        self.selected_movie_folder = folder
        set_setting("MOVIES_FOLDER", folder)
        
        self.load_video_files()
    
    def on_kodi_folder_selected(self, folder):
        self.selected_kodi_folder = folder
        set_setting("KODI_FOLDER", folder)
        self.load_kodi_files()
    
    def load_folder_preference(self):
        movie_folder = get_setting("MOVIES_FOLDER")
        if movie_folder and Path(movie_folder).exists():
            self.selected_movie_folder = movie_folder
            self.header_config.set_movie_selected_folder(movie_folder)
        
        kodi_folder = get_setting("KODI_FOLDER")
        if kodi_folder and Path(kodi_folder).exists():
            self.selected_kodi_folder = kodi_folder
            self.header_config.set_kodi_selected_folder(kodi_folder)
        
        self.refresh_files_lists()

    def show_file_error(self, title, path, exc):
        message = f"{title}:\n{path}\n\nDetalhes: {exc}"
        QMessageBox.critical(self, "Erro de Arquivo", message)

    def refresh_files_lists(self):
        self.load_video_files()
        self.load_kodi_files()
    
    def load_video_files(self):
        """Carrega lista de arquivos de vídeo da pasta selecionada"""
        self.selected_folder = self.header_config.get_movie_selected_folder()
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
                self.files_table.setItem(row, self.original_column, original_item)

                year_item = QTableWidgetItem("")
                year_item.setFlags(year_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.files_table.setItem(row, self.year_column, year_item)
                select_item = QTableWidgetItem("Aguardando busca")
                select_item.setFlags(select_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                select_item.setData(RESULTS_ROLE, [])
                select_item.setData(SELECTED_ROLE, -1)
                select_item.setData(SUGGESTED_NAME_ROLE, "")
                self.files_table.setItem(row, self.select_column, select_item)

                send_item = QTableWidgetItem("")
                send_item.setFlags(
                    Qt.ItemFlag.ItemIsUserCheckable
                    | Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                )
                send_item.setCheckState(Qt.CheckState.Unchecked)
                self.files_table.setItem(row, self.send_to_kodi_column, send_item)

    def load_kodi_files(self):
        kodi_folder = self.header_config.get_kodi_selected_folder()
        if not kodi_folder:
            self.files_section.clear_kodi_files()
            return

        kodi_path = Path(kodi_folder)
        if not kodi_path.exists():
            self.files_section.clear_kodi_files()
            return

        kodi_files = []
        for file in kodi_path.iterdir():
            if file.is_file() and KodiNamer.is_video_file(file.name):
                kodi_files.append(file.name)

        kodi_files.sort(key=str.lower)
        self.files_section.set_kodi_files(kodi_files)
    
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
            select_item = self.files_table.item(row, self.select_column)
            if select_item is None:
                select_item = QTableWidgetItem()
                self.files_table.setItem(row, self.select_column, select_item)
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
            year_item = self.files_table.item(row, self.year_column)
            if year_item is None:
                year_item = QTableWidgetItem("")
                year_item.setFlags(year_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.files_table.setItem(row, self.year_column, year_item)
            year_item.setText(str(year or ""))
        
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
            select_item = self.files_table.item(row, self.select_column)
            if select_item is None:
                select_item = QTableWidgetItem()
                self.files_table.setItem(row, self.select_column, select_item)
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
                select_item.setData(SUGGESTED_NAME_ROLE, "")
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

    def on_table_selection_changed(self, current_row):
        if current_row < 0 or current_row >= len(self.search_results):
            return
        select_item = self.files_table.item(current_row, self.select_column)
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
            select_item = self.files_table.item(row, self.select_column)
            if select_item is not None:
                select_item.setData(SUGGESTED_NAME_ROLE, suggested_name)
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
        select_item = self.files_table.item(row, self.select_column)
        if select_item is not None:
            select_item.setData(SUGGESTED_NAME_ROLE, suggested_name)
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
        """Copia os arquivos marcados para a pasta do Kodi"""
        if not self.selected_folder:
            QMessageBox.warning(self, "Aviso", "Selecione uma pasta primeiro")
            return

        kodi_folder = self.header_config.get_kodi_selected_folder()
        if not kodi_folder:
            QMessageBox.warning(self, "Aviso", "Selecione a pasta do Kodi primeiro")
            return

        kodi_path = Path(kodi_folder)
        if not kodi_path.exists() or not kodi_path.is_dir():
            QMessageBox.warning(self, "Aviso", "Pasta do Kodi inválida")
            return
        
        copied_count = 0
        selected_count = 0
        errors = []
        remove_original_after_send = self.should_remove_original_after_send()
        
        for row in range(self.files_table.rowCount()):
            original_item = self.files_table.item(row, self.original_column)
            select_item = self.files_table.item(row, self.select_column)
            send_item = self.files_table.item(row, self.send_to_kodi_column)
            
            if not original_item or not select_item or not send_item:
                continue

            if send_item.checkState() != Qt.CheckState.Checked:
                continue

            selected_count += 1
            
            original_name = original_item.text()
            suggested_name = select_item.data(SUGGESTED_NAME_ROLE) or original_name
            
            original_path = Path(self.selected_folder) / original_name
            new_path = kodi_path / suggested_name

            if not original_path.exists():
                errors.append(f"{original_name}: arquivo de origem não encontrado")
                continue

            if new_path.exists():
                errors.append(f"{suggested_name}: já existe na pasta Kodi")
                continue
            
            try:
                if remove_original_after_send:
                    shutil.move(str(original_path), str(new_path))
                else:
                    shutil.copy2(original_path, new_path)
                copied_count += 1
            except Exception as e:
                errors.append(f"{original_name}: {str(e)}")

        if selected_count == 0:
            QMessageBox.information(self, "Aviso", "Nenhum arquivo marcado para envio")
            return
        
        if errors:
            error_msg = "Erros ao enviar:\n" + "\n".join(errors)
            QMessageBox.warning(self, "Erros", error_msg)
        
        QMessageBox.information(
            self, "Conclusão",
            f"{copied_count} arquivo(s) {'movido(s)' if remove_original_after_send else 'copiado(s)'} para a pasta Kodi"
        )
        
        self.refresh_files_lists()
