from PyQt6.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QInputDialog, QLineEdit, QWidget
from src.core.config import set_setting


class MoreSettings(QWidget):
    LANGUAGE_OPTIONS = [
        ("Portuguese (BR)", "pt-BR"),
        ("English (US)", "en-US"),
        ("Spanish (ES)", "es-ES"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MoreSettings")

    def ask_tmdb_api_key(self):
        key, ok = QInputDialog.getText(
            self,
            "Chave TMDB",
            "Informe sua TMDB API Key:",
            QLineEdit.EchoMode.Password
        )
        key = key.strip()
        if ok and key:
            set_setting("TMDB_API_KEY", key)
        return key if ok and key else None

    def open_settings_dialog(self, current_language=None, remove_original_after_send=False):
        dialog = QDialog(self)
        dialog.setWindowTitle("Mais Configuracoes")

        layout = QFormLayout(dialog)

        api_key_input = QLineEdit(dialog)
        api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_key_input.setPlaceholderText("Informe sua TMDB API Key")
        layout.addRow("TMDB API Key:", api_key_input)

        language_combo = QComboBox(dialog)
        for label, value in self.LANGUAGE_OPTIONS:
            language_combo.addItem(label, value)

        if current_language:
            lang_index = language_combo.findData(current_language)
            if lang_index >= 0:
                language_combo.setCurrentIndex(lang_index)
                
        layout.addRow("Idioma:", language_combo)

        remove_original_checkbox = QCheckBox(dialog)
        remove_original_checkbox.setChecked(bool(remove_original_after_send))
        remove_original_checkbox.setText("Apagar arquivo da pasta de filmes após enviar")
        layout.addRow("Ao enviar:", remove_original_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        api_key = api_key_input.text().strip()
        selected_language = language_combo.currentData()
        remove_original = remove_original_checkbox.isChecked()

        if api_key:
            set_setting("TMDB_API_KEY", api_key)
        if selected_language:
            set_setting("APP_LANGUAGE", selected_language)
        set_setting("REMOVE_ORIGINAL_AFTER_SEND", "true" if remove_original else "false")

        return {
            "api_key": api_key,
            "language": selected_language,
            "remove_original_after_send": remove_original,
        }