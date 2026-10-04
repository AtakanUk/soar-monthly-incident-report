from datetime import UTC, datetime

from soar_monthly_incident_report.analytics import (
    IncidentRef,
    MonthlyReport,
    PendingNotification,
    ResolutionStats,
)
from soar_monthly_incident_report.html_renderers import render_monthly_report, render_workflow_list


def make_report():
    return MonthlyReport(
        period_start=datetime(2024, 10, 1, tzinfo=UTC),
        period_end=datetime(2024, 10, 31, tzinfo=UTC),
        long_running_days=2,
        total_closed=4,
        long_running=[IncidentRef(7, "<script>alert(1)</script>")],
        resolution=ResolutionStats(3600, 60, "fast one", 7200, "slow one"),
        actions={"No Action": 1, "Blocked": 3},
        pending_notifications=[
            PendingNotification(9, "Login", "owner@example.com", "first\nsecond")
        ],
    )


def test_report_contains_all_sections_and_escapes_values():
    html = render_monthly_report(make_report(), chart_uri="data:image/png;base64,AAAA")
    assert "Reporting period: 2024-10-01 to 2024-10-31" in html
    assert "remained open for more than 2 days" in html
    assert "&lt;script&gt;" in html and "<script>" not in html
    assert "01:00:00" in html and "slow one" in html
    assert (
        "<td style='border:1px solid #dddddd; padding:10px; text-align:left; vertical-align:top;'>Blocked</td>"
        in html
    )
    assert "first<br>second" in html
    assert "data:image/png;base64,AAAA" in html


def test_chart_is_optional():
    assert "<img" not in render_monthly_report(make_report(), chart_uri=None)


def test_workflow_list():
    text = render_workflow_list([{"workflow_id": 3, "name": "Enrich IP"}])
    assert text == "Active Workflows:\nWorkflow ID: 3, Name: Enrich IP\n"
