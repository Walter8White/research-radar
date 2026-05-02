from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
import os
from dataclasses import dataclass
from pathlib import Path


CRON_BEGIN = "# BEGIN Research Radar"
CRON_END = "# END Research Radar"


@dataclass
class AutomationConfig:
    schedule: str
    time: str
    output_dir: str
    collect_fresh: bool
    open_report: bool
    notify: bool
    recency_days: int
    report_length: str


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def python_executable() -> str:
    venv_python = project_root() / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)

    return sys.executable


def cron_time_fields(schedule: str, time_value: str) -> str:
    hour_text, minute_text = time_value.split(":", 1)
    hour = int(hour_text)
    minute = int(minute_text)

    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("Automation time must be in HH:MM format.")

    if schedule == "Weekdays":
        return f"{minute} {hour} * * 1-5"

    return f"{minute} {hour} * * *"


def build_command(config: AutomationConfig) -> str:
    command = "run" if config.collect_fresh else "report"
    args = [
        python_executable(),
        "main.py",
        command,
        "--recency-days",
        str(config.recency_days),
        "--report-length",
        config.report_length,
        "--output-dir",
        str(Path(config.output_dir).expanduser()),
    ]

    if config.open_report:
        args.append("--open-report")
    if config.notify:
        args.append("--notify")

    return " ".join(shlex.quote(part) for part in args)


def build_cron_entry(config: AutomationConfig) -> str:
    cron_fields = cron_time_fields(config.schedule, config.time)
    root = shlex.quote(str(project_root()))
    command = build_command(config)
    log_path = shlex.quote(str(project_root() / "data" / "automation.log"))
    env_prefix = build_desktop_env_prefix()

    return f"{cron_fields} cd {root} && {env_prefix}{command} >> {log_path} 2>&1"


def build_desktop_env_prefix() -> str:
    env_parts = []

    for key in ["DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR", "WAYLAND_DISPLAY"]:
        value = os.environ.get(key)
        if value:
            env_parts.append(f"{key}={shlex.quote(value)}")

    if not env_parts:
        return ""

    return "env " + " ".join(env_parts) + " "


def build_cron_block(config: AutomationConfig) -> str:
    return "\n".join(
        [
            CRON_BEGIN,
            build_cron_entry(config),
            CRON_END,
        ]
    )


def crontab_available() -> bool:
    return shutil.which("crontab") is not None


def read_crontab() -> str:
    if not crontab_available():
        raise RuntimeError("crontab command not found.")

    result = subprocess.run(
        ["crontab", "-l"],
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        return ""

    return result.stdout


def remove_existing_block(crontab_text: str) -> str:
    lines = crontab_text.splitlines()
    output = []
    in_block = False

    for line in lines:
        if line.strip() == CRON_BEGIN:
            in_block = True
            continue
        if line.strip() == CRON_END:
            in_block = False
            continue
        if not in_block:
            output.append(line)

    return "\n".join(output).strip()


def write_crontab(crontab_text: str) -> None:
    if not crontab_available():
        raise RuntimeError("crontab command not found.")

    subprocess.run(
        ["crontab", "-"],
        input=crontab_text.strip() + "\n",
        text=True,
        check=True,
    )


def save_automation(config: AutomationConfig) -> str:
    current = read_crontab()
    cleaned = remove_existing_block(current)
    block = build_cron_block(config)
    next_crontab = f"{cleaned}\n\n{block}" if cleaned else block

    write_crontab(next_crontab)
    return block


def disable_automation() -> bool:
    current = read_crontab()
    cleaned = remove_existing_block(current)

    if cleaned.strip() == current.strip():
        return False

    write_crontab(cleaned)
    return True
