import os
import sys
import time
import socket
import subprocess
import webbrowser
from pathlib import Path


PORT = 8501


def port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def main() -> None:
    project_dir = Path(__file__).resolve().parent
    app_path = project_dir / "app.py"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_dir)

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(PORT),
        "--server.address",
        "127.0.0.1",
        "--browser.gatherUsageStats",
        "false",
    ]

    subprocess.Popen(
        cmd,
        cwd=str(project_dir),
        env=env,
    )

    for _ in range(40):
        if port_is_open(PORT):
            break
        time.sleep(0.5)

    webbrowser.open(f"http://127.0.0.1:{PORT}")


if __name__ == "__main__":
    main()
