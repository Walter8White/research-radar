import argparse
import shutil
import subprocess

from core.database import init_db, insert_item, get_item_count
from core.report import generate_report

from collectors.arxiv_collector import collect_arxiv
from collectors.github_collector import collect_github
from collectors.rss_collector import collect_rss
from collectors.social_collector import collect_social
from core.freshness import DEFAULT_RECENCY_DAYS
from core.report_length import DEFAULT_REPORT_LENGTH, REPORT_LENGTH_PROFILES, normalize_report_length


def collect_all(recency_days: int = DEFAULT_RECENCY_DAYS) -> None:
    init_db()

    collectors = [
        ("arXiv", collect_arxiv),
        ("GitHub", collect_github),
        ("RSS", collect_rss),
        ("Social", collect_social),
    ]

    total_inserted = 0

    for name, collector in collectors:
        print(f"[Collect] Running {name} collector...")

        try:
            items = collector(recency_days=recency_days)
        except Exception as e:
            print(f"[Collect] {name} failed: {e}")
            continue

        inserted = 0

        for item in items:
            if insert_item(item):
                inserted += 1

        total_inserted += inserted
        print(f"[Collect] {name}: {inserted}/{len(items)} new items inserted.")

    print(f"[Collect] Done. Total new items: {total_inserted}")
    print(f"[DB] Total items: {get_item_count()}")


def report(
    recency_days: int = DEFAULT_RECENCY_DAYS,
    report_length: str = DEFAULT_REPORT_LENGTH,
    output_dir: str = "reports",
    open_report: bool = False,
    notify: bool = False,
) -> None:
    init_db()
    report_path = generate_report(
        limit=50,
        recency_days=recency_days,
        report_length=report_length,
        output_dir=output_dir,
    )
    print(f"[Report] Generated: {report_path}")

    if notify:
        send_notification(report_path)

    if open_report:
        open_report_file(report_path)


def send_notification(report_path) -> None:
    notify_send = shutil.which("notify-send")
    if not notify_send:
        print("[Notify] notify-send not found; skipping desktop notification.")
        return

    subprocess.run(
        [
            notify_send,
            "Research Radar",
            f"Report generated: {report_path}",
        ],
        check=False,
    )


def open_report_file(report_path) -> None:
    opener = shutil.which("xdg-open")
    if not opener:
        print("[Open] xdg-open not found; skipping auto-open.")
        return

    subprocess.Popen(
        [opener, str(report_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Research Radar Lite")
    parser.add_argument(
        "command",
        choices=["collect", "report", "run"],
        help="Command to execute",
    )
    parser.add_argument(
        "--recency-days",
        type=int,
        default=DEFAULT_RECENCY_DAYS,
        help="Only prioritize items from the last N days.",
    )
    parser.add_argument(
        "--report-length",
        choices=list(REPORT_LENGTH_PROFILES.keys()),
        default=DEFAULT_REPORT_LENGTH,
        help="Report density to generate.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Folder where generated reports are saved.",
    )
    parser.add_argument(
        "--open-report",
        action="store_true",
        help="Open the generated report with xdg-open.",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Send a local desktop notification when the report is generated.",
    )

    args = parser.parse_args()
    report_length = normalize_report_length(args.report_length)

    if args.command == "collect":
        collect_all(recency_days=args.recency_days)
    elif args.command == "report":
        report(
            recency_days=args.recency_days,
            report_length=report_length,
            output_dir=args.output_dir,
            open_report=args.open_report,
            notify=args.notify,
        )
    elif args.command == "run":
        collect_all(recency_days=args.recency_days)
        report(
            recency_days=args.recency_days,
            report_length=report_length,
            output_dir=args.output_dir,
            open_report=args.open_report,
            notify=args.notify,
        )


if __name__ == "__main__":
    main()
