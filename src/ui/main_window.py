import sys
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox,
    QSpinBox, QHeaderView, QComboBox, QStyledItemDelegate, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from pathlib import Path

from src.core.tmdb_client import TMDBClient
from src.core.kodi_namer import KodiNamer


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
        
        self.init_ui()
        self.init_tmdb()
        self.load_folder_preference()
    
    def init_ui(self):
        """Inicializa a interface gráfica"""
        self.setWindowTitle("Kodi Bot - TMDB")
        self.setGeometry(100, 100, 1000, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Seção de Configuração
        config_layout = QHBoxLayout()
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
        layout.addLayout(config_layout)
        
        self.folder_label = QLabel("Nenhuma pasta selecionada")
        layout.addWidget(self.folder_label)
        
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
        self.files_table.setEditTriggers(
            QAbstractItemView.EditTrigger.CurrentChanged
        )
        layout.addWidget(self.files_table)

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
    
    def init_tmdb(self):
        """Inicializa o cliente TMDB"""
        try:
            self.tmdb_client = TMDBClient()
        except ValueError as e:
            QMessageBox.critical(
                self, "Erro de Configuração",
                f"Erro ao inicializar TMDB: {str(e)}\n\n"
                "Certifique-se de que o arquivo .env contém TMDB_API_KEY"
            )
    
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
        config_dir = Path(__file__).parent.parent.parent / ".kodibot"
        config_dir.mkdir(exist_ok=True)
        
        config_file = config_dir / "last_folder.txt"
        config_file.write_text(folder_path)
    
    def load_folder_preference(self):
        """Carrega a última pasta selecionada"""
        config_file = Path(__file__).parent.parent.parent / ".kodibot" / "last_folder.txt"
        
        if config_file.exists():
            folder = config_file.read_text().strip()
            if Path(folder).exists():
                self.selected_folder = folder
                self.folder_label.setText(f"Pasta: {folder}")
                self.load_video_files()
    
    def load_video_files(self):
        """Carrega lista de arquivos de vídeo da pasta selecionada"""
        if not self.selected_folder:
            return
        
        self.video_files = []
        self.search_results = []
        self.search_types = []
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
        
        # Inicia a busca sequencial
        self.active_search_type = self.search_type_combo.currentData() or "movie"
        self.current_search_index = 0
        self.search_next_file()
    
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
            self.search_results[row] = results
            select_item = self.files_table.item(row, 3)
            if select_item is None:
                select_item = QTableWidgetItem()
                self.files_table.setItem(row, 3, select_item)
            media_type = self.search_types[row] or "movie"
            select_item.setData(RESULTS_ROLE, results)
            select_item.setData(TYPE_ROLE, media_type)
            if results:
                best_result = results[0]
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

    def update_suggested_name(self, row, index):
        if row >= len(self.search_results):
            return
        results = self.search_results[row]
        if not results or index < 0 or index >= len(results):
            return
        selected = results[index]
        media_type = self.search_types[row] or "movie"
        if media_type == "tv":
            title = selected.get('name', 'N/A')
            release_date = selected.get('first_air_date', '')
        else:
            title = selected.get('title', 'N/A')
            release_date = selected.get('release_date', '')
        year = release_date.split('-')[0] if release_date else ''
        video_file = self.video_files[row]
        suggested_name = KodiNamer.suggest_kodi_filename(
            video_file.name, title, year
        )
        self.files_table.setItem(row, 2, QTableWidgetItem(suggested_name))
    
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
