"""Settings loaded from environment variables (optionally via a .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Raised when a required setting is missing or invalid."""


def _get(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _require(name: str) -> str:
    value = _get(name)
    if value is None:
        raise ConfigError(f"Environment variable {name} is required")
    return value


def _get_int(name: str, default: int) -> int:
    raw = _get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


def _get_float(name: str, default: float) -> float:
    raw = _get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc


def _get_bool(name: str, default: bool) -> bool:
    raw = _get(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _get_list(name: str) -> tuple[str, ...]:
    raw = _get(name, "") or ""
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class SoarSettings:
    host: str
    port: int
    org: str
    api_key_id: str
    api_key_secret: str
    cafile: str | None

    @classmethod
    def from_env(cls) -> SoarSettings:
        return cls(
            host=_require("SOAR_HOST"),
            port=_get_int("SOAR_PORT", 443),
            org=_require("SOAR_ORG"),
            api_key_id=_require("SOAR_API_KEY_ID"),
            api_key_secret=_require("SOAR_API_KEY_SECRET"),
            cafile=_get("SOAR_CAFILE"),
        )

    def client_options(self) -> dict[str, object]:
        """Options in the format expected by ``resilient.get_client``."""
        options: dict[str, object] = {
            "host": self.host,
            "port": self.port,
            "org": self.org,
            "api_key_id": self.api_key_id,
            "api_key_secret": self.api_key_secret,
        }
        if self.cafile:
            options["cafile"] = self.cafile
        return options


@dataclass(frozen=True)
class ReportSettings:
    lookback_days: int = 30
    long_running_days: float = 2.0
    exclude_patterns: tuple[str, ...] = ()
    action_field: str = "action_info"
    notified_field: str = "second_info"
    notified_value: str = "Ok"
    approval_field: str = "approval"
    recipient_field: str = "mail_to_address"
    wkhtmltopdf_path: str | None = None

    @classmethod
    def from_env(cls) -> ReportSettings:
        return cls(
            lookback_days=_get_int("REPORT_LOOKBACK_DAYS", cls.lookback_days),
            long_running_days=_get_float("REPORT_LONG_RUNNING_DAYS", cls.long_running_days),
            exclude_patterns=_get_list("REPORT_EXCLUDE_PATTERNS"),
            action_field=_get("REPORT_ACTION_FIELD", cls.action_field) or cls.action_field,
            notified_field=_get("REPORT_NOTIFIED_FIELD", cls.notified_field) or cls.notified_field,
            notified_value=_get("REPORT_NOTIFIED_VALUE", cls.notified_value) or cls.notified_value,
            approval_field=_get("REPORT_APPROVAL_FIELD", cls.approval_field) or cls.approval_field,
            recipient_field=_get("REPORT_RECIPIENT_FIELD", cls.recipient_field)
            or cls.recipient_field,
            wkhtmltopdf_path=_get("WKHTMLTOPDF_PATH"),
        )


@dataclass(frozen=True)
class MailSettings:
    host: str
    port: int
    use_starttls: bool
    username: str | None
    password: str | None
    sender: str
    recipients: tuple[str, ...]
    cc: tuple[str, ...]
    subject: str

    @classmethod
    def from_env(cls) -> MailSettings:
        recipients = _get_list("MAIL_TO")
        if not recipients:
            raise ConfigError("MAIL_TO must contain at least one address")
        return cls(
            host=_require("SMTP_HOST"),
            port=_get_int("SMTP_PORT", 25),
            use_starttls=_get_bool("SMTP_STARTTLS", False),
            username=_get("SMTP_USERNAME"),
            password=_get("SMTP_PASSWORD"),
            sender=_require("MAIL_FROM"),
            recipients=recipients,
            cc=_get_list("MAIL_CC"),
            subject=_get("MAIL_SUBJECT", "[IBM QRadar SOAR] Monthly Incident Report")
            or "[IBM QRadar SOAR] Monthly Incident Report",
        )
