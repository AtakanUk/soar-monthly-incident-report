"""HTML rendering. Styles are inline because most mail clients drop <style> blocks."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from html import escape

from .analytics import MonthlyReport, format_duration

TABLE = (
    "width:100%; border-collapse:collapse; margin-bottom:20px; border-radius:8px; "
    "overflow:hidden; box-shadow:0 0 10px rgba(0,0,0,0.1);"
)
CAPTION = (
    "font-weight:bold; background-color:#2f5d8a; color:#ffffff; padding:10px; "
    "border-top-left-radius:8px; border-top-right-radius:8px;"
)
HEADER_ROW = "background-color:#d9e7f2; color:#1b2a38;"
ROW = "background-color:#f4f6f8;"
CELL = "border:1px solid #dddddd; padding:10px; text-align:left; vertical-align:top;"


def _text(value: object) -> str:
    return escape("" if value is None else str(value))


def _multiline(value: str | None) -> str:
    return _text(value).replace("\n", "<br>") if value else "N/A"


def _table(caption: str, headers: Sequence[str], rows: Iterable[Sequence[str]]) -> str:
    """Build a table; cells in ``rows`` must already be HTML-safe."""
    head = "".join(f"<th style='{CELL}'>{_text(h)}</th>" for h in headers)
    head_row = f"<tr style='{HEADER_ROW}'>{head}</tr>" if headers else ""
    body = "".join(
        f"<tr style='{ROW}'>" + "".join(f"<td style='{CELL}'>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table style='{TABLE}'><caption style='{CAPTION}'>{_text(caption)}</caption>{head_row}{body}</table>"


def _days_label(days: float) -> str:
    return f"{days:g} day" if days == 1 else f"{days:g} days"


def long_running_table(report: MonthlyReport) -> str:
    rows = [[str(len(report.long_running)), ""]]
    rows += [["", f"{_text(ref.id)} - {_text(ref.name)}"] for ref in report.long_running]
    return _table(
        f"How many incidents remained open for more than {_days_label(report.long_running_days)}?",
        ["Total", "Incident ID and Name"],
        rows,
    )


def resolution_table(report: MonthlyReport) -> str:
    stats = report.resolution
    return _table(
        "How long does it take to close an incident on average? What are the fastest and longest closing times?",
        ["Metric", "Time", "Incident"],
        [
            ["Fastest", format_duration(stats.fastest_seconds), _text(stats.fastest_name)],
            ["Longest", format_duration(stats.longest_seconds), _text(stats.longest_name)],
            ["Average", format_duration(stats.average_seconds), ""],
        ],
    )


def actions_section(report: MonthlyReport, chart_uri: str | None) -> str:
    total = _table(
        "Closed Incidents in the Period", ["Total Incidents"], [[str(report.total_closed)]]
    )
    actions = _table(
        "How many of the incidents were concluded with which actions?",
        ["Action", "Total"],
        [[_text(label), str(count)] for label, count in report.actions.items()],
    )
    left = f"<div style='width:48%; display:inline-block; vertical-align:top; margin-right:2%;'>{total}{actions}</div>"
    if not chart_uri:
        return left
    chart = _table(
        "Action Distribution",
        [],
        [[f"<img src='{chart_uri}' alt='Action distribution chart' style='width:100%;'>"]],
    )
    return left + f"<div style='width:48%; display:inline-block; vertical-align:top;'>{chart}</div>"


def pending_table(report: MonthlyReport) -> str:
    rows = [[str(len(report.pending_notifications)), "", "", ""]]
    rows += [
        [
            "",
            f"{_text(item.id)} - {_text(item.name)}",
            _text(item.recipient),
            _multiline(item.description),
        ]
        for item in report.pending_notifications
    ]
    return _table(
        "How many offenses were reported but not responded to, and what are they?",
        ["Total", "Offense ID and Name", "Mail To", "Details"],
        rows,
    )


def render_monthly_report(report: MonthlyReport, chart_uri: str | None) -> str:
    period = f"{report.period_start:%Y-%m-%d} to {report.period_end:%Y-%m-%d}"
    sections = [
        long_running_table(report),
        resolution_table(report),
        actions_section(report, chart_uri),
        pending_table(report),
    ]
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Monthly Incident Report</title></head>"
        "<body style='font-family:Arial, Helvetica, sans-serif; color:#1b2a38; margin:24px;'>"
        "<h2 style='margin-bottom:4px;'>Monthly Incident Report</h2>"
        f"<p style='margin-top:0; color:#5b6b79;'>Reporting period: {period} (UTC)</p>"
        + "".join(sections)
        + "</body></html>"
    )


def render_workflow_list(workflows: Iterable[dict]) -> str:
    lines = ["Active Workflows:"]
    lines += [f"Workflow ID: {wf.get('workflow_id')}, Name: {wf.get('name')}" for wf in workflows]
    return "\n".join(lines) + "\n"
