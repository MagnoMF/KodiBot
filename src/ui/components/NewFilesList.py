from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


RESULTS_ROLE = int(Qt.ItemDataRole.UserRole) + 1
SELECTED_ROLE = int(Qt.ItemDataRole.UserRole) + 2
TYPE_ROLE = int(Qt.ItemDataRole.UserRole) + 3
SUGGESTED_NAME_ROLE = int(Qt.ItemDataRole.UserRole) + 4


class ResultComboDelegate(QStyledItemDelegate):
    selection_changed = pyqtSignal(int, int)

    def createEditor(self, parent, option, index):
        results = index.data(RESULTS_ROLE) or []
        media_type = index.data(TYPE_ROLE) or "movie"
        combo = QComboBox(parent)
        for result in results[:10]:
            if media_type == "tv":
                title = result.get("name", "N/A")
                release_date = result.get("first_air_date", "")
            else:
                title = result.get("title", "N/A")
                release_date = result.get("release_date", "")
            year = release_date.split("-")[0] if release_date else ""
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


class NewFilesList(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NewFilesList")

        self.original_column = 0
        self.year_column = 1
        self.suggested_column = 2
        self.select_column = 2
        self.send_to_kodi_column = 3

        layout = QVBoxLayout(self)
        main_content_layout = QHBoxLayout()
        layout.addWidget(QLabel("Arquivos na pasta:"))
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(4)
        self.files_table.setHorizontalHeaderLabels(
            ["Arquivo Original", "Ano Detectado", "Nome Sugerido", "Enviar"]
        )
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.files_table.setEditTriggers(QAbstractItemView.EditTrigger.CurrentChanged)

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
        main_content_layout.addLayout(files_layout, 3)

        self.result_delegate = ResultComboDelegate(self.files_table)
        self.files_table.setItemDelegateForColumn(self.select_column, self.result_delegate)

        kodi_layout = QVBoxLayout()
        kodi_layout.addWidget(QLabel("Filmes existentes na pasta Kodi:"))
        self.kodi_files_table = QTableWidget()
        self.kodi_files_table.setColumnCount(1)
        self.kodi_files_table.setHorizontalHeaderLabels(["Arquivo no Kodi"])
        self.kodi_files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.kodi_files_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.kodi_files_table.setMinimumWidth(340)
        kodi_layout.addWidget(self.kodi_files_table)

        main_content_layout.addLayout(kodi_layout, 2)
        layout.addLayout(main_content_layout)

    def clear_kodi_files(self):
        self.kodi_files_table.setRowCount(0)

    def set_kodi_files(self, filenames):
        self.kodi_files_table.setRowCount(0)
        for filename in filenames:
            row = self.kodi_files_table.rowCount()
            self.kodi_files_table.insertRow(row)
            item = QTableWidgetItem(filename)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.kodi_files_table.setItem(row, 0, item)