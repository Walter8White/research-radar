import argparse

from core.database import init_db, insert_item, get_item_count
from core.report import generate_report

from collectors.arxiv_collector import collect_arxiv
from collectors.github_collector import collect_github
from collectors.rss_collector import collect_rss


def collect_all() -> None:
    init_db()

    collectors = [
        ("arXiv", collect_arxiv),
        ("GitHub", collect_github),
        ("RSS", collect_rss),
    ]

    total_inserted = 0

    for name, collector in collectors:
        print(f"[Collect] Running {name} collector...")

        try:
            items = collector()
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


def report() -> None:
    init_db()
    report_path = generate_report(limit=50)
    print(f"[Report] Generated: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Research Radar Lite")
    parser.add_argument(
        "command",
        choices=["collect", "report", "run"],
        help="Command to execute",
    )

    args = parser.parse_args()

    if args.command == "collect":
        collect_all()
    elif args.command == "report":
        report()
    elif args.command == "run":
        collect_all()
        report()


if __name__ == "__main__":
    main()
