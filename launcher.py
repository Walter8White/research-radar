import os
import sys
import socket
import shutil
import threading
import time
import webbrowser
from pathlib import Path


def find_free_port(start: int = 8501, end: int = 8599) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free port found between 8501 and 8599.")


def get_paths():
    if getattr(sys, "frozen", False):
        app_dir = Path(sys.executable).resolve().parent
        bundled_dir = Path(getattr(sys, "_MEIPASS", app_dir)).resolve()
    else:
        app_dir = Path(__file__).resolve().parent
        bundled_dir = app_dir

    return app_dir, bundled_dir


def ensure_runtime_files(app_dir: Path, bundled_dir: Path) -> None:
    """
    The packaged app keeps bundled files in _internal/.
    Runtime files must live next to the executable so users can edit them.
    """
    for folder in ["data", "reports"]:
        (app_dir / folder).mkdir(parents=True, exist_ok=True)

    user_config = app_dir / "config"
    bundled_config = bundled_dir / "config"

    if not user_config.exists() and bundled_config.exists():
        shutil.copytree(bundled_config, user_config)


def open_browser_later(port: int):
    time.sleep(2)
    webbrowser.open(f"http://127.0.0.1:{port}")


def main() -> None:
    port = find_free_port()

    app_dir, bundled_dir = get_paths()
    ensure_runtime_files(app_dir, bundled_dir)

    os.chdir(app_dir)

    app_path = bundled_dir / "app.py"
    sys.path.insert(0, str(bundled_dir))
    sys.path.insert(0, str(app_dir))

    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_SERVER_ADDRESS"] = "127.0.0.1"
    os.environ["STREAMLIT_SERVER_PORT"] = str(port)

    threading.Thread(target=open_browser_later, args=(port,), daemon=True).start()

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
    ]

    from streamlit.web.cli import main as streamlit_main
    streamlit_main()


if __name__ == "__main__":
    main()
