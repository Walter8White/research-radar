import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def user_data_dir() -> Path:
    home = Path.home()
    path = home / ".research-radar"
    path.mkdir(parents=True, exist_ok=True)

    (path / "data").mkdir(exist_ok=True)
    (path / "reports").mkdir(exist_ok=True)
    (path / "config").mkdir(exist_ok=True)

    return path


def bundled_path(*parts: str) -> Path:
    return app_root().joinpath(*parts)


def user_path(*parts: str) -> Path:
    return user_data_dir().joinpath(*parts)
