from pathlib import Path
from datetime import date
import yaml
import streamlit as st

from main import collect_all
from core.report import generate_report


st.set_page_config(
    page_title="Research Radar",
    page_icon="📡",
    layout="wide",
)

REPORTS_DIR = Path("reports")
TOPICS_PATH = Path("config/topics.yaml")
ENV_PATH = Path(".env")


def get_today_report_path() -> Path:
    return REPORTS_DIR / f"{date.today().isoformat()}.md"


def read_report(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_topics_config() -> dict:
    if not TOPICS_PATH.exists():
        return {
            "priority_topics": [],
            "negative_topics": [],
            "domains": {},
        }

    with open(TOPICS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_topics_config(config: dict) -> None:
    with open(TOPICS_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            config,
            f,
            sort_keys=False,
            allow_unicode=True,
            width=100,
        )


def list_to_text(items: list) -> str:
    return "\n".join(items or [])


def text_to_list(text: str) -> list:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


def load_env_file() -> dict:
    values = {}

    if not ENV_PATH.exists():
        return values

    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    return values


def save_env_values(values: dict) -> None:
    existing = load_env_file()
    existing.update(values)

    lines = []
    for key, value in existing.items():
        if value is None:
            value = ""
        lines.append(f'{key}="{value}"')

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if "topics_config" not in st.session_state:
    st.session_state.topics_config = load_topics_config()


st.title("📡 Research Radar")
st.caption(
    "Morning Tech Intelligence Brief — AI, robotics, infrastructure, startups, open source, and geopolitics."
)

with st.sidebar:
    st.header("Controls")

    run_collect = st.checkbox(
        "Collect fresh signals before generating",
        value=True,
        help="If disabled, the app only regenerates the report from the current database.",
    )

    generate = st.button("Generate Summary", type="primary", use_container_width=True)

    st.divider()

    st.header("LLM Settings")

    env_values = load_env_file()

    api_key_input = st.text_input(
        "OpenAI API key",
        value=env_values.get("OPENAI_API_KEY", ""),
        type="password",
        help="Stored locally in .env. Never committed to Git.",
    )

    model_input = st.text_input(
        "OpenAI model",
        value=env_values.get("OPENAI_MODEL", "gpt-5.4"),
        help="Example: gpt-5.4",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Save LLM", use_container_width=True):
            save_env_values(
                {
                    "OPENAI_API_KEY": api_key_input,
                    "OPENAI_MODEL": model_input,
                }
            )
            st.success("Saved locally.")

    with col2:
        if st.button("Disable LLM", use_container_width=True):
            save_env_values(
                {
                    "OPENAI_API_KEY": "",
                    "OPENAI_MODEL": model_input or "gpt-5.4",
                }
            )
            st.warning("LLM disabled.")

    if api_key_input:
        st.success("API key configured locally.")
    else:
        st.info("No API key set. The app will generate a non-LLM report.")

    st.divider()

    st.header("Topics")

    if st.button("Reload topics from file", use_container_width=True):
        st.session_state.topics_config = load_topics_config()
        st.success("Topics reloaded.")

    config = st.session_state.topics_config

    priority_text = st.text_area(
        "Priority topics",
        value=list_to_text(config.get("priority_topics", [])),
        height=160,
        help="One topic per line. These receive a scoring boost.",
    )

    negative_text = st.text_area(
        "Negative topics",
        value=list_to_text(config.get("negative_topics", [])),
        height=140,
        help="One topic per line. These reduce score.",
    )

    st.markdown("### Domain keywords")

    domains = config.get("domains", {})
    edited_domains = {}

    for domain_name, domain in domains.items():
        with st.expander(domain_name, expanded=False):
            description = st.text_input(
                f"{domain_name} description",
                value=domain.get("description", ""),
                key=f"{domain_name}_description",
            )

            priority = st.selectbox(
                f"{domain_name} priority",
                options=["high", "medium", "low"],
                index=["high", "medium", "low"].index(domain.get("priority", "medium"))
                if domain.get("priority", "medium") in ["high", "medium", "low"]
                else 1,
                key=f"{domain_name}_priority",
            )

            keywords_text = st.text_area(
                f"{domain_name} keywords",
                value=list_to_text(domain.get("keywords", [])),
                height=160,
                key=f"{domain_name}_keywords",
            )

            edited_domains[domain_name] = {
                "description": description,
                "priority": priority,
                "keywords": text_to_list(keywords_text),
            }

    if st.button("Save topics", use_container_width=True):
        config["priority_topics"] = text_to_list(priority_text)
        config["negative_topics"] = text_to_list(negative_text)
        config["domains"] = edited_domains

        save_topics_config(config)
        st.session_state.topics_config = config
        st.success("Topics saved.")

    st.divider()

    st.markdown("### Report")
    today_path = get_today_report_path()
    st.code(str(today_path), language="text")


if generate:
    with st.spinner("Generating brief..."):
        if run_collect:
            collect_all()

        report_path = generate_report(limit=50)

    st.success(f"Report generated: {report_path}")


report_path = get_today_report_path()
report_content = read_report(report_path)

if report_content:
    st.markdown(report_content)
else:
    st.info("No report generated yet. Click **Generate Summary**.")
