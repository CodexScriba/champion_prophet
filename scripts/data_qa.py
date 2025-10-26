#!/usr/bin/env python3
"""Generate a Phase 0 data QA report for the email database."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from champion_prophet.config import Settings, ensure_directories, load_settings  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate data QA summary for the email database")
    parser.add_argument("--db-path", type=Path, default=None, help="Override path to the SQLite database")
    parser.add_argument("--start-date", type=str, default=None, help="Optional lower bound (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default=None, help="Optional upper bound (YYYY-MM-DD)")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "docs" / "analysis" / "data_qa_report.md",
        help="Destination markdown file",
    )
    return parser.parse_args()


def _interval_clause(start: str | None, end: str | None) -> tuple[str, tuple[str, ...]]:
    clauses = []
    params: list[str] = []
    if start:
        clauses.append("date >= ?")
        params.append(start)
    if end:
        clauses.append("date <= ?")
        params.append(end)
    sql = " AND ".join(clauses)
    return (f"WHERE {sql}" if sql else "", tuple(params))


def fetch_daily_summary(conn: sqlite3.Connection, start: str | None, end: str | None) -> dict[str, object]:
    clause, params = _interval_clause(start, end)
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT MIN(date), MAX(date), COUNT(*)
        FROM days
        {clause}
        """,
        params,
    )
    min_date, max_date, row_count = cursor.fetchone()

    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM days
        {clause} {'AND' if clause else 'WHERE'} has_email_data = 1
        """,
        params,
    )
    email_days = cursor.fetchone()[0]

    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM days
        {clause} {'AND' if clause else 'WHERE'} has_sla_data = 1
        """,
        params,
    )
    sla_days = cursor.fetchone()[0]

    return {
        "min_date": min_date,
        "max_date": max_date,
        "row_count": row_count,
        "email_days": email_days,
        "sla_days": sla_days,
    }


def fetch_null_counts(conn: sqlite3.Connection, table: str) -> dict[str, int]:
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    nulls: dict[str, int] = {}
    for column in columns:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL")
        nulls[column] = cursor.fetchone()[0]
    return nulls


def fetch_duplicate_dates(conn: sqlite3.Connection, start: str | None, end: str | None) -> list[tuple[str, int]]:
    clause, params = _interval_clause(start, end)
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT date, COUNT(*) AS cnt
        FROM days
        {clause}
        GROUP BY date
        HAVING cnt > 1
        ORDER BY date
        """,
        params,
    )
    return cursor.fetchall()


def fetch_hourly_coverage(conn: sqlite3.Connection, start: str | None, end: str | None) -> dict[str, object]:
    clause, params = _interval_clause(start, end)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM hourly_data")
    total_rows = cursor.fetchone()[0]

    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM hourly_data
        WHERE emails_received IS NULL OR emails_worked IS NULL OR unread_count IS NULL
        """
    )
    null_rows = cursor.fetchone()[0]

    cursor.execute(
        f"""
        SELECT date, COUNT(*) AS hours
        FROM hourly_data
        {clause}
        GROUP BY date
        HAVING hours != 24
        ORDER BY date
        """,
        params,
    )
    incomplete = cursor.fetchall()

    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM days
        {clause} {'AND' if clause else 'WHERE'} has_sla_data = 1
        """,
        params,
    )
    sla_days = cursor.fetchone()[0]

    expected_rows = sla_days * 24

    return {
        "total_rows": total_rows,
        "null_rows": null_rows,
        "expected_rows": expected_rows,
        "incomplete_days": incomplete,
    }


def render_report(settings: Settings, output: Path, summary: dict[str, object], daily_nulls: dict[str, int], duplicates: list[tuple[str, int]], hourly: dict[str, object], start: str | None, end: str | None) -> None:
    ensure_directories(settings)
    output.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Data QA Report")
    lines.append("")
    lines.append(f"_Database_: `{settings.database_path}`")
    if start or end:
        bounds = f"{start or 'MIN'} → {end or 'MAX'}"
        lines.append(f"_Window_: {bounds}")
    lines.append("")

    lines.append("## Coverage")
    lines.append("")
    lines.append(f"- Earliest date: **{summary['min_date']}**")
    lines.append(f"- Latest date: **{summary['max_date']}**")
    lines.append(f"- Total days in scope: **{summary['row_count']}**")
    lines.append(f"- Days with email data: **{summary['email_days']}**")
    lines.append(f"- Days with SLA/hourly data: **{summary['sla_days']}**")
    lines.append("")

    lines.append("## Daily Table Null Counts")
    lines.append("")
    lines.append("| Column | Null Rows |\n| --- | --- |")
    for column, nulls in sorted(daily_nulls.items(), key=lambda item: item[0]):
        lines.append(f"| `{column}` | {nulls} |")
    lines.append("")

    lines.append("## Duplicate Date Checks")
    lines.append("")
    if duplicates:
        lines.append("| Date | Rows |\n| --- | --- |")
        for dup_date, count in duplicates:
            lines.append(f"| {dup_date} | {count} |")
    else:
        lines.append("No duplicate dates detected in `days` table.")
    lines.append("")

    lines.append("## Hourly Coverage")
    lines.append("")
    lines.append(f"- Expected hourly rows (24 × SLA days): **{hourly['expected_rows']}**")
    lines.append(f"- Actual hourly rows: **{hourly['total_rows']}**")
    lines.append(f"- Rows with null hourly metrics: **{hourly['null_rows']}**")
    if hourly["incomplete_days"]:
        lines.append("- Days missing full 24 hours:")
        for missing_date, hours in hourly["incomplete_days"]:
            lines.append(f"  - {missing_date}: {hours} hours")
    else:
        lines.append("- All SLA days contain full 24 hourly rows.")

    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    settings = load_settings()
    if args.db_path is not None:
        settings.database_path = args.db_path

    with sqlite3.connect(settings.database_path) as conn:
        summary = fetch_daily_summary(conn, args.start_date, args.end_date)
        daily_nulls = fetch_null_counts(conn, "days")
        duplicates = fetch_duplicate_dates(conn, args.start_date, args.end_date)
        hourly = fetch_hourly_coverage(conn, args.start_date, args.end_date)

    render_report(settings, args.output, summary, daily_nulls, duplicates, hourly, args.start_date, args.end_date)


if __name__ == "__main__":
    main()
