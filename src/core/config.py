import os
from pathlib import Path

APP_NAME = ".kodibot"
PROJECT_NAME = "KodiBot"
SETTINGS_FILENAME = "settings.txt"


def get_project_root():
    return Path(__file__).resolve().parents[2]


def get_config_dir():
    project_root = get_project_root()
    project_config = project_root / ".kodibot"

    if project_config.exists() or os.access(project_root, os.W_OK):
        return project_config

    return Path.home() / APP_NAME


def get_settings_path():
    return get_config_dir() / SETTINGS_FILENAME


def read_settings():
    settings_path = get_settings_path()
    if not settings_path.exists():
        return {}

    data = {}
    for raw_line in settings_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def get_setting(key, default=None):
    settings = read_settings()
    return settings.get(key, default)


def set_setting(key, value):
    settings_path = get_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings = read_settings() if settings_path.exists() else {}
    settings[key] = value
    lines = [f"{k}={v}" for k, v in settings.items()]
    settings_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return settings_path
