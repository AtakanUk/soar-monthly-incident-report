"""Command-line entry point."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from .analytics import active_workflows, build_report, period_start, to_ms
from .charts import pie_chart_data_uri
from .config import ConfigError, MailSettings, ReportSettings, SoarSettings
from .html_renderers import render_monthly_report, render_workflow_list

log = logging.getLogger("soar_monthly_report")


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def run_report(args: argparse.Namespace) -> int:
    from .pdf_writer import write_pdf
    from .soar_client import SoarClient

    settings = ReportSettings.from_env()
    mail_settings = MailSettings.from_env() if args.send_mail else None
    client = SoarClient.connect(SoarSettings.from_env())

    now = datetime.now(UTC)
    cutoff = to_ms(period_start(now, settings.lookback_days))

    log.info("Fetching closed incidents from the last %d days", settings.lookback_days)
    closed = client.closed_incidents_since(cutoff)
    action_values = client.field_values(settings.action_field)
    notified = client.incidents_where(settings.notified_field, settings.notified_value)
    log.info("Fetched %d closed and %d notified incidents", len(closed), len(notified))

    report = build_report(
        closed_incidents=closed,
        notified_incidents=notified,
        action_field=settings.action_field,
        action_values=action_values,
        approval_field=settings.approval_field,
        recipient_field=settings.recipient_field,
        lookback_days=settings.lookback_days,
        long_running_days=settings.long_running_days,
        exclude=settings.exclude_patterns,
        now=now,
    )

    html = render_monthly_report(report, pie_chart_data_uri(report.actions, "Incident Analysis"))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"monthly_incident_report_{now:%Y-%m-%d}"
    html_path = output_dir / f"{stem}.html"
    html_path.write_text(html, encoding="utf-8")
    log.info("HTML report written to %s", html_path)

    pdf_path = None
    if not args.no_pdf:
        pdf_path = write_pdf(html, output_dir / f"{stem}.pdf", settings.wkhtmltopdf_path)
        log.info("PDF report written to %s", pdf_path)

    if mail_settings is not None:
        from .emailer import send_report

        send_report(mail_settings, html, pdf_path)
        log.info("Report mailed to %s", ", ".join(mail_settings.recipients + mail_settings.cc))
    return 0


def run_workflows(args: argparse.Namespace) -> int:
    from .soar_client import SoarClient

    client = SoarClient.connect(SoarSettings.from_env())
    text = render_workflow_list(active_workflows(client.workflows()))
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        log.info("Workflow list written to %s", args.output)
    else:
        sys.stdout.write(text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="soar-monthly-report", description="Monthly incident reporting for IBM QRadar SOAR"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    commands = parser.add_subparsers(dest="command", required=True)

    report = commands.add_parser("report", help="build the monthly incident report")
    report.add_argument(
        "--output-dir",
        default="reports",
        help="where to write the HTML/PDF files (default: reports)",
    )
    report.add_argument("--no-pdf", action="store_true", help="skip PDF generation")
    report.add_argument(
        "--send-mail",
        action="store_true",
        help="mail the report using the SMTP_* / MAIL_* settings",
    )
    report.set_defaults(handler=run_report)

    workflows = commands.add_parser(
        "workflows", help="list workflows that have at least one enabled rule"
    )
    workflows.add_argument("--output", help="write the list to a file instead of stdout")
    workflows.set_defaults(handler=run_workflows)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _load_dotenv()
    try:
        return args.handler(args)
    except ConfigError as exc:
        log.error("Configuration error: %s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
