from pathlib import Path
from datetime import date
import os
import yaml
import streamlit as st

from main import collect_all
from core.report import generate_report
from core.automation import (
    AutomationConfig,
    build_command,
    build_cron_entry,
    crontab_available,
    disable_automation,
    save_automation,
)
from collectors.social_collector import load_social_sources, save_social_sources
from core.freshness import DEFAULT_RECENCY_DAYS, RECENCY_OPTIONS
from core.llm.providers import (
    DEFAULT_LLM_PROVIDER,
    LLM_PROVIDERS,
    normalize_provider,
)
from core.report_length import DEFAULT_REPORT_LENGTH, REPORT_LENGTH_PROFILES, normalize_report_length


st.set_page_config(
    page_title="Research Radar",
    page_icon="📡",
    layout="wide",
)

REPORTS_DIR = Path("reports")
TOPICS_PATH = Path("config/topics.yaml")
ENV_PATH = Path(".env")
DEPRECATED_ENV_KEYS = {"OLLAMA_MODEL", "OLLAMA_BASE_URL", "OLLAMA_API_KEY"}

FOCUS_PRIORITIES = ["Critical", "High", "Medium", "Low"]
FOCUS_PRIORITY_TO_WEIGHT = {
    "Critical": "critical",
    "High": "high",
    "Medium": "medium",
    "Low": "low",
}
FOCUS_WEIGHT_TO_PRIORITY = {value: key for key, value in FOCUS_PRIORITY_TO_WEIGHT.items()}


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


def focus_topics_to_text(items: list) -> str:
    return "\n".join(
        item.get("topic", "").strip()
        for item in items or []
        if item.get("topic", "").strip()
    )


def merge_topic_text_with_priorities(text: str, existing_topics: list) -> list:
    existing_priorities = {
        item.get("topic", "").strip().lower(): item.get("priority", "high")
        for item in existing_topics or []
        if item.get("topic", "").strip()
    }

    focus_topics = []

    for topic in text_to_list(text):
        focus_topics.append(
            {
                "topic": topic,
                "priority": existing_priorities.get(topic.lower(), "high"),
            }
        )

    return focus_topics


def load_focus_topics(config: dict) -> list:
    focus_topics = config.get("focus_topics")

    if focus_topics:
        return focus_topics

    return [
        {
            "topic": topic,
            "priority": "high",
        }
        for topic in config.get("priority_topics", [])
    ]


def focus_topics_to_priority_topics(focus_topics: list) -> list:
    return [
        item["topic"].strip()
        for item in focus_topics
        if item.get("topic", "").strip()
    ]


def social_accounts_to_text(accounts: list) -> str:
    return "\n".join(
        " | ".join(
            [
                account.get("handle", "").strip(),
                account.get("name", "").strip(),
                account.get("category", "").strip(),
            ]
        ).strip(" |")
        for account in accounts or []
        if account.get("handle", "").strip() or account.get("name", "").strip()
    )


def text_to_social_accounts(text: str) -> list:
    accounts = []

    for line in text_to_list(text):
        parts = [part.strip() for part in line.split("|")]
        handle = parts[0] if len(parts) > 0 else ""
        name = parts[1] if len(parts) > 1 else ""
        category = parts[2] if len(parts) > 2 else "Technical debate"

        accounts.append(
            {
                "handle": handle.lstrip("@"),
                "name": name,
                "category": category or "Technical debate",
            }
        )

    return accounts


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
    for key in DEPRECATED_ENV_KEYS:
        existing.pop(key, None)

    existing.update(values)

    lines = []
    for key, value in existing.items():
        if value is None:
            value = ""
        os.environ[key] = str(value)
        lines.append(f'{key}="{value}"')

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def selected_recency_label(value: str) -> str:
    try:
        days = int(value)
    except (TypeError, ValueError):
        days = DEFAULT_RECENCY_DAYS

    for label, option_days in RECENCY_OPTIONS.items():
        if option_days == days:
            return label

    return "Last 7 days"


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

    env_values = load_env_file()

    recency_label = st.selectbox(
        "Freshness window",
        options=list(RECENCY_OPTIONS.keys()),
        index=list(RECENCY_OPTIONS.keys()).index(
            selected_recency_label(env_values.get("RECENCY_WINDOW_DAYS", str(DEFAULT_RECENCY_DAYS)))
        ),
        help="Older dated items are filtered out. Undated items are kept but penalized.",
    )
    recency_days = RECENCY_OPTIONS[recency_label]

    report_length = st.selectbox(
        "Report length",
        options=list(REPORT_LENGTH_PROFILES.keys()),
        index=list(REPORT_LENGTH_PROFILES.keys()).index(
            normalize_report_length(env_values.get("REPORT_LENGTH", DEFAULT_REPORT_LENGTH))
        ),
        help="Controls brief density, LLM budget, and how many raw items are shown.",
    )

    generate = st.button("Generate Summary", type="primary", use_container_width=True)

    st.divider()

    st.header("LLM Settings")

    provider_name = st.selectbox(
        "Provider",
        options=LLM_PROVIDERS,
        index=LLM_PROVIDERS.index(
            normalize_provider(env_values.get("LLM_PROVIDER", DEFAULT_LLM_PROVIDER))
        ),
        help="Choose the model provider used for the Morning Brief analysis.",
    )

    api_key_input = env_values.get("OPENAI_API_KEY", "")
    model_input = env_values.get("OPENAI_MODEL", "gpt-5.4")
    anthropic_api_key_input = env_values.get("ANTHROPIC_API_KEY", "")
    claude_model_input = env_values.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    if provider_name == "OpenAI":
        api_key_input = st.text_input(
            "API key",
            value=api_key_input,
            type="password",
            help="Stored locally in .env. Never committed to Git.",
        )

        model_input = st.text_input(
            "Model",
            value=model_input,
            help="Example: gpt-5.4",
        )
    elif provider_name == "Claude":
        anthropic_api_key_input = st.text_input(
            "API key",
            value=anthropic_api_key_input,
            type="password",
            help="Stored locally in .env. Never committed to Git.",
        )

        claude_model_input = st.text_input(
            "Model",
            value=claude_model_input,
            help="Example: claude-sonnet-4-20250514",
        )
    else:
        st.info("No LLM selected. Reports will use the deterministic fallback.")

    if st.button("Save LLM", use_container_width=True):
        save_env_values(
            {
                "LLM_PROVIDER": provider_name,
                "OPENAI_API_KEY": api_key_input,
                "OPENAI_MODEL": model_input or "gpt-5.4",
                "ANTHROPIC_API_KEY": anthropic_api_key_input,
                "CLAUDE_MODEL": claude_model_input or "claude-sonnet-4-20250514",
                "RECENCY_WINDOW_DAYS": str(recency_days),
                "REPORT_LENGTH": report_length,
            }
        )
        st.success(f"LLM settings saved: {provider_name}.")

    st.divider()

    st.header("Radar Focus")

    config = st.session_state.topics_config
    focus_topics = load_focus_topics(config)

    st.caption(
        "First save the topic list. Then set priorities for the saved topics below."
    )

    focus_topics_text = st.text_area(
        "Topics",
        value=focus_topics_to_text(focus_topics),
        height=280,
        placeholder="embodied AI\nexport controls\nopen-source agents",
        help=(
            "One topic per line. Add as many as you want. New topics default to High priority."
        ),
    )

    if st.button("Save topics", use_container_width=True):
        edited_focus_topics = merge_topic_text_with_priorities(focus_topics_text, focus_topics)
        config["focus_topics"] = edited_focus_topics
        config["priority_topics"] = focus_topics_to_priority_topics(edited_focus_topics)

        save_topics_config(config)
        st.session_state.topics_config = config
        st.success("Topics saved. You can now set their priorities.")
        st.rerun()

    if focus_topics:
        st.markdown("### Topic priorities")

    edited_focus_topics = []

    for index, item in enumerate(focus_topics):
        topic = item.get("topic", "").strip()
        if not topic:
            continue

        priority_value = FOCUS_WEIGHT_TO_PRIORITY.get(item.get("priority", "high"), "High")
        priority = st.selectbox(
            topic,
            options=FOCUS_PRIORITIES,
            index=FOCUS_PRIORITIES.index(priority_value),
            key=f"focus_priority_{index}_{topic}",
        )
        edited_focus_topics.append(
            {
                "topic": topic,
                "priority": FOCUS_PRIORITY_TO_WEIGHT[priority],
            }
        )

    if focus_topics and st.button("Save priorities", use_container_width=True):
        config["focus_topics"] = edited_focus_topics
        config["priority_topics"] = focus_topics_to_priority_topics(edited_focus_topics)

        save_topics_config(config)
        st.session_state.topics_config = config
        st.success("Topic priorities saved.")
        st.rerun()

    negative_text = st.text_area(
        "What to avoid",
        value=list_to_text(config.get("negative_topics", [])),
        height=260,
        help=(
            "One noise pattern per line. Matching items are penalized, "
            "but not automatically deleted."
        ),
    )

    companies_focus_text = st.text_area(
        "Companies focus",
        value=list_to_text(config.get("companies_focus", [])),
        height=180,
        placeholder="OpenAI\nAnthropic\nNVIDIA\nFigure AI",
        help="Placeholder for future company-aware scoring and reporting.",
    )

    people_focus_text = st.text_area(
        "People focus",
        value=list_to_text(config.get("people_focus", [])),
        height=180,
        placeholder="Demis Hassabis\nJensen Huang\nYann LeCun",
        help="Placeholder for future people/public-signal tracking.",
    )

    if st.button("Save focus lists", use_container_width=True):
        config["negative_topics"] = text_to_list(negative_text)
        config["companies_focus"] = text_to_list(companies_focus_text)
        config["people_focus"] = text_to_list(people_focus_text)

        save_topics_config(config)
        st.session_state.topics_config = config
        st.success("Focus lists saved.")

    st.divider()

    st.header("Public Signals")
    social_config = load_social_sources()

    st.caption(
        "Automatic X recent search from your Topics, Companies focus, People focus, and optional account watchlist. Requires your own X API bearer token."
    )

    x_bearer_token_input = st.text_input(
        "X API bearer token",
        value=env_values.get("X_BEARER_TOKEN", ""),
        type="password",
        help="Stored locally in .env. Used only for official X API recent search.",
    )

    social_accounts_text = st.text_area(
        "Accounts watchlist",
        value=social_accounts_to_text(social_config.get("accounts", [])),
        height=150,
        placeholder="sama | Sam Altman\ndemishassabis | Demis Hassabis",
        help="Optional. One per line: handle | name. These are added to the automatic X search.",
    )

    social_max_results = st.number_input(
        "Max X posts per run",
        min_value=10,
        max_value=100,
        value=int(social_config.get("max_results") or 25),
        step=5,
    )

    social_enabled = st.checkbox(
        "Enable X collection",
        value=bool(social_config.get("enabled", True)),
    )

    if st.button("Save Public Signals", use_container_width=True):
        social_config["enabled"] = social_enabled
        social_config["max_results"] = int(social_max_results)
        social_config["language"] = social_config.get("language", "en")
        social_config["include_reposts"] = bool(social_config.get("include_reposts", False))
        social_config["include_replies"] = bool(social_config.get("include_replies", False))
        social_config["accounts"] = text_to_social_accounts(social_accounts_text)
        save_social_sources(social_config)
        save_env_values({"X_BEARER_TOKEN": x_bearer_token_input})
        st.success("Public signals saved locally.")

    st.divider()

    st.header("Automation")

    automation_schedule = st.selectbox(
        "Schedule",
        options=["Daily", "Weekdays"],
        index=0,
        help="Linux cron scheduling. Nothing is installed until you click Save Automation.",
    )
    automation_time = st.text_input(
        "Run time",
        value=env_values.get("AUTOMATION_TIME", "08:00"),
        help="24h local time, for example 08:00.",
    )
    automation_output_dir = st.text_input(
        "Output folder",
        value=env_values.get("AUTOMATION_OUTPUT_DIR", "reports"),
        help="Reports generated by automation will be saved here.",
    )
    automation_collect = st.checkbox(
        "Collect fresh sources",
        value=env_values.get("AUTOMATION_COLLECT_FRESH", "true").lower() == "true",
    )
    automation_open = st.checkbox(
        "Open report automatically",
        value=env_values.get("AUTOMATION_OPEN_REPORT", "false").lower() == "true",
    )
    automation_notify = st.checkbox(
        "Desktop notification",
        value=env_values.get("AUTOMATION_NOTIFY", "false").lower() == "true",
    )

    automation_config = AutomationConfig(
        schedule=automation_schedule,
        time=automation_time,
        output_dir=automation_output_dir,
        collect_fresh=automation_collect,
        open_report=automation_open,
        notify=automation_notify,
        recency_days=recency_days,
        report_length=report_length,
    )

    try:
        preview_command = build_command(automation_config)
        preview_cron = build_cron_entry(automation_config)
        st.caption("Scheduled command preview")
        st.code(preview_cron, language="bash")
    except Exception as exc:
        preview_command = ""
        preview_cron = ""
        st.error(f"Invalid automation settings: {exc}")

    col_auto_1, col_auto_2 = st.columns(2)

    with col_auto_1:
        if st.button("Save Automation", use_container_width=True, disabled=not bool(preview_cron)):
            if not crontab_available():
                st.error("crontab command not found on this system.")
            else:
                try:
                    save_automation(automation_config)
                    save_env_values(
                        {
                            "AUTOMATION_TIME": automation_time,
                            "AUTOMATION_OUTPUT_DIR": automation_output_dir,
                            "AUTOMATION_COLLECT_FRESH": str(automation_collect).lower(),
                            "AUTOMATION_OPEN_REPORT": str(automation_open).lower(),
                            "AUTOMATION_NOTIFY": str(automation_notify).lower(),
                            "RECENCY_WINDOW_DAYS": str(recency_days),
                            "REPORT_LENGTH": report_length,
                        }
                    )
                    st.success("Automation saved to user crontab.")
                except Exception as exc:
                    st.error(f"Could not save automation: {exc}")

    with col_auto_2:
        if st.button("Disable Automation", use_container_width=True):
            if not crontab_available():
                st.error("crontab command not found on this system.")
            else:
                try:
                    removed = disable_automation()
                    if removed:
                        st.warning("Automation disabled.")
                    else:
                        st.info("No Research Radar automation was installed.")
                except Exception as exc:
                    st.error(f"Could not disable automation: {exc}")

    if st.button("Run Now", use_container_width=True, disabled=not bool(preview_command)):
        with st.spinner("Running automation once..."):
            if automation_collect:
                collect_all(recency_days=recency_days)

            report_path = generate_report(
                limit=50,
                recency_days=recency_days,
                report_length=report_length,
                output_dir=automation_output_dir,
            )
        st.success(f"Automation run generated: {report_path}")

    st.divider()

    st.markdown("### Report")
    today_path = get_today_report_path()
    st.code(str(today_path), language="text")


if generate:
    with st.spinner("Generating brief..."):
        save_env_values(
            {
                "LLM_PROVIDER": provider_name,
                "OPENAI_API_KEY": api_key_input,
                "OPENAI_MODEL": model_input,
                "ANTHROPIC_API_KEY": anthropic_api_key_input,
                "CLAUDE_MODEL": claude_model_input,
                "RECENCY_WINDOW_DAYS": str(recency_days),
                "REPORT_LENGTH": report_length,
            }
        )

        if run_collect:
            collect_all(recency_days=recency_days)

        report_path = generate_report(
            limit=50,
            recency_days=recency_days,
            report_length=report_length,
        )

    st.success(f"Report generated: {report_path}")


report_path = get_today_report_path()
report_content = read_report(report_path)

if report_content:
    st.markdown(report_content, unsafe_allow_html=True)
else:
    st.info("No report generated yet. Click **Generate Summary**.")
