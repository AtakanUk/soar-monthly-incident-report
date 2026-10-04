from datetime import UTC, datetime, timedelta

import pytest

from soar_monthly_incident_report.analytics import (
    NO_ACTION_LABEL,
    active_workflows,
    build_report,
    format_duration,
    to_ms,
)

NOW = datetime(2024, 10, 31, 12, 0, tzinfo=UTC)
HOUR = 3600 * 1000
DAY = 24 * HOUR


def incident(incident_id, name, created_days_ago, open_hours, actions=None, **properties):
    created = to_ms(NOW) - int(created_days_ago * DAY)
    return {
        "id": incident_id,
        "name": name,
        "plan_status": "C",
        "create_date": created,
        "end_date": created + int(open_hours * HOUR),
        "description": properties.pop("description", None),
        "properties": {"action_info": actions or [], **properties},
    }


ACTION_VALUES = [
    {"value": 11, "label": "Blocked"},
    {"value": 12, "label": "False Positive"},
    {"value": 13, "label": "Escalated"},
]


@pytest.fixture
def report():
    closed = [
        incident(1, "Malware on host-a", 3, 1, actions=[11]),
        incident(2, "Phishing mail", 5, 60, actions=[11, 12]),
        incident(3, "Port scan", 10, 0.5),
        incident(4, "Noisy DLP rule", 2, 100, actions=[12]),
        incident(5, "Old incident", 45, 72, actions=[11]),
    ]
    notified = [
        incident(
            10,
            "Suspicious login",
            4,
            2,
            approval="Waiting",
            mail_to_address="owner@example.com",
            description="Line one\nLine two",
        ),
        incident(11, "Answered alert", 4, 2, approval=None),
        incident(12, "Very old alert", 60, 2, approval="Waiting"),
    ]
    return build_report(
        closed_incidents=closed,
        notified_incidents=notified,
        action_field="action_info",
        action_values=ACTION_VALUES,
        approval_field="approval",
        recipient_field="mail_to_address",
        lookback_days=30,
        long_running_days=2,
        exclude=["DLP"],
        now=NOW,
    )


def test_period_and_exclusions_are_applied(report):
    assert report.total_closed == 3


def test_long_running_incidents(report):
    assert [ref.id for ref in report.long_running] == [2]


def test_resolution_stats(report):
    stats = report.resolution
    assert stats.fastest_name == "Port scan"
    assert stats.longest_name == "Phishing mail"
    assert stats.average_seconds == pytest.approx((1 + 60 + 0.5) / 3 * 3600)


def test_action_breakdown_counts_every_label(report):
    assert report.actions == {NO_ACTION_LABEL: 1, "Blocked": 2, "False Positive": 1, "Escalated": 0}


def test_pending_notifications(report):
    assert len(report.pending_notifications) == 1
    pending = report.pending_notifications[0]
    assert (pending.id, pending.recipient) == (10, "owner@example.com")


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (None, "N/A"),
        (0, "00:00:00"),
        (3725, "01:02:05"),
        (86400 + 61, "1 day, 00:01:01"),
        (3 * 86400 + 7200, "3 days, 02:00:00"),
    ],
)
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected


def test_active_workflows_need_an_enabled_action():
    workflows = [
        {"workflow_id": 1, "name": "enabled", "actions": [{"enabled": False}, {"enabled": True}]},
        {"workflow_id": 2, "name": "disabled", "actions": [{"enabled": False}]},
        {"workflow_id": 3, "name": "orphan", "actions": []},
    ]
    assert [wf["workflow_id"] for wf in active_workflows(workflows)] == [1]


def test_empty_input_produces_empty_report():
    empty = build_report([], [], "action_info", [], "approval", "mail_to_address", 30, 2, now=NOW)
    assert empty.total_closed == 0
    assert empty.resolution.average_seconds is None
    assert empty.actions == {NO_ACTION_LABEL: 0}
    assert empty.period_start == NOW - timedelta(days=30)
