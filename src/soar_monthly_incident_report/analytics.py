"""Pure report calculations over incident dictionaries returned by the SOAR API."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

MS_PER_DAY = 24 * 60 * 60 * 1000
NO_ACTION_LABEL = "No Action"

Incident = dict[str, Any]


@dataclass(frozen=True)
class IncidentRef:
    id: Any
    name: str


@dataclass(frozen=True)
class ResolutionStats:
    average_seconds: float | None = None
    fastest_seconds: float | None = None
    fastest_name: str | None = None
    longest_seconds: float | None = None
    longest_name: str | None = None


@dataclass(frozen=True)
class PendingNotification:
    id: Any
    name: str
    recipient: str | None
    description: str | None


@dataclass
class MonthlyReport:
    period_start: datetime
    period_end: datetime
    long_running_days: float
    total_closed: int
    long_running: list[IncidentRef] = field(default_factory=list)
    resolution: ResolutionStats = field(default_factory=ResolutionStats)
    actions: dict[str, int] = field(default_factory=dict)
    pending_notifications: list[PendingNotification] = field(default_factory=list)


def to_ms(moment: datetime) -> int:
    return int(moment.timestamp() * 1000)


def period_start(now: datetime, lookback_days: int) -> datetime:
    return now - timedelta(days=lookback_days)


def format_duration(seconds: float | None) -> str:
    """Render a duration as ``HH:MM:SS`` or ``N days, HH:MM:SS``."""
    if seconds is None:
        return "N/A"
    delta = timedelta(seconds=round(seconds))
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    clock = f"{hours:02}:{minutes:02}:{secs:02}"
    if delta.days:
        unit = "day" if delta.days == 1 else "days"
        return f"{delta.days} {unit}, {clock}"
    return clock


def is_excluded(incident: Incident, patterns: Iterable[str]) -> bool:
    name = incident.get("name") or ""
    return any(pattern in name for pattern in patterns)


def in_period(incident: Incident, cutoff_ms: int) -> bool:
    created = incident.get("create_date")
    return created is not None and created >= cutoff_ms


def select_incidents(
    incidents: Iterable[Incident], cutoff_ms: int, exclude: Sequence[str]
) -> list[Incident]:
    return [i for i in incidents if in_period(i, cutoff_ms) and not is_excluded(i, exclude)]


def _resolution_seconds(incident: Incident) -> float | None:
    created, closed = incident.get("create_date"), incident.get("end_date")
    if created is None or closed is None:
        return None
    return (closed - created) / 1000


def long_running(incidents: Iterable[Incident], min_days: float) -> list[IncidentRef]:
    """Closed incidents that stayed open for longer than ``min_days``."""
    result = []
    for incident in incidents:
        seconds = _resolution_seconds(incident)
        if (
            incident.get("plan_status") == "C"
            and seconds is not None
            and seconds * 1000 / MS_PER_DAY > min_days
        ):
            result.append(IncidentRef(incident.get("id"), incident.get("name") or ""))
    return result


def resolution_stats(incidents: Iterable[Incident]) -> ResolutionStats:
    timed = [
        (s, i.get("name") or "") for i in incidents if (s := _resolution_seconds(i)) is not None
    ]
    if not timed:
        return ResolutionStats()
    fastest = min(timed, key=lambda item: item[0])
    longest = max(timed, key=lambda item: item[0])
    return ResolutionStats(
        average_seconds=sum(seconds for seconds, _ in timed) / len(timed),
        fastest_seconds=fastest[0],
        fastest_name=fastest[1],
        longest_seconds=longest[0],
        longest_name=longest[1],
    )


def action_breakdown(
    incidents: Iterable[Incident], action_field: str, field_values: Iterable[dict[str, Any]]
) -> dict[str, int]:
    """Count incidents per selected value of a multi-select incident field.

    Incidents with nothing selected are counted under ``No Action``. Every
    defined value is listed, including the ones with a zero count.
    """
    incidents = list(incidents)
    counts = {NO_ACTION_LABEL: 0}
    for incident in incidents:
        if not (incident.get("properties") or {}).get(action_field):
            counts[NO_ACTION_LABEL] += 1
    for option in field_values:
        value, label = option.get("value"), option.get("label") or str(option.get("value"))
        counts[label] = sum(
            1
            for incident in incidents
            if value in ((incident.get("properties") or {}).get(action_field) or [])
        )
    return counts


def pending_notifications(
    incidents: Iterable[Incident], approval_field: str, recipient_field: str
) -> list[PendingNotification]:
    """Notified incidents whose approval field is still populated, i.e. awaiting a reply."""
    pending = []
    for incident in incidents:
        properties = incident.get("properties") or {}
        if properties.get(approval_field) is None:
            continue
        pending.append(
            PendingNotification(
                id=incident.get("id"),
                name=incident.get("name") or "",
                recipient=properties.get(recipient_field),
                description=incident.get("description"),
            )
        )
    return pending


def active_workflows(workflows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Workflows that have at least one enabled rule (action) attached."""
    return [
        wf
        for wf in workflows
        if any(action.get("enabled", False) for action in wf.get("actions") or [])
    ]


def build_report(
    closed_incidents: Iterable[Incident],
    notified_incidents: Iterable[Incident],
    action_field: str,
    action_values: Iterable[dict[str, Any]],
    approval_field: str,
    recipient_field: str,
    lookback_days: int,
    long_running_days: float,
    exclude: Sequence[str] = (),
    now: datetime | None = None,
) -> MonthlyReport:
    now = now or datetime.now(UTC)
    start = period_start(now, lookback_days)
    cutoff = to_ms(start)

    closed = select_incidents(closed_incidents, cutoff, exclude)
    notified = select_incidents(notified_incidents, cutoff, exclude)

    return MonthlyReport(
        period_start=start,
        period_end=now,
        long_running_days=long_running_days,
        total_closed=len(closed),
        long_running=long_running(closed, long_running_days),
        resolution=resolution_stats(closed),
        actions=action_breakdown(closed, action_field, action_values),
        pending_notifications=pending_notifications(notified, approval_field, recipient_field),
    )
