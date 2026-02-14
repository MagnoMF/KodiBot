import os
import sys
from pathlib import Path

APP_NAME = "kodibot"
PROJECT_NAME = "KodiBot"


def get_project_root():
    return Path(__file__).resolve().parents[2]


def get_config_dir():
    if sys.platform.startswith("win"):
        base = os.getenv("APPDATA") or os.getenv("LOCALAPPDATA")
        if base:
            return Path(base) / PROJECT_NAME
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / PROJECT_NAME

    return Path.home() / ".config" / APP_NAME


def get_env_path():
    project_root = get_project_root()
    project_env = project_root / ".env"

    if project_env.exists():
        return project_env

    if os.access(project_root, os.W_OK):
        return project_env

    return get_config_dir() / ".env"
