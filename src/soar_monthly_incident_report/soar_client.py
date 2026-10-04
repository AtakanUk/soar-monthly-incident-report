"""Thin wrapper around the IBM SOAR REST client for the queries the report needs."""

from __future__ import annotations

import logging
from typing import Any, Protocol

from .config import SoarSettings

log = logging.getLogger(__name__)

QUERY_PAGED_URI = (
    "/incidents/query_paged?return_level=full&field_handle=-1&include_records_total=true"
)
QUERY_URI = "/incidents/query?return_level=full"


class RestClient(Protocol):
    def get(self, uri: str) -> Any: ...

    def post(self, uri: str, payload: Any) -> Any: ...


class SoarClient:
    def __init__(self, rest_client: RestClient, page_size: int = 500) -> None:
        self._client = rest_client
        self._page_size = page_size

    @classmethod
    def connect(cls, settings: SoarSettings) -> SoarClient:
        import resilient

        return cls(resilient.get_client(settings.client_options()))

    def closed_incidents_since(self, cutoff_ms: int) -> list[dict[str, Any]]:
        """Return closed incidents created at or after ``cutoff_ms``.

        Results are requested newest first, so paging stops at the first
        incident older than the cutoff instead of walking the full history.
        """
        incidents: list[dict[str, Any]] = []
        start = 0
        while True:
            query = {
                "filters": [
                    {
                        "conditions": [
                            {"field_name": "plan_status", "method": "equals", "value": "C"}
                        ]
                    }
                ],
                "sorts": [{"field_name": "create_date", "type": "desc"}],
                "start": start,
                "length": self._page_size,
            }
            page = (self._client.post(QUERY_PAGED_URI, query) or {}).get("data") or []
            for incident in page:
                created = incident.get("create_date")
                if created is None or created < cutoff_ms:
                    log.debug(
                        "Reached incidents older than the cutoff after %d results", len(incidents)
                    )
                    return incidents
                incidents.append(incident)
            if len(page) < self._page_size:
                return incidents
            start += self._page_size

    def field_values(self, field_name: str) -> list[dict[str, Any]]:
        """Return the selectable values (``value``/``label`` pairs) of an incident field."""
        definition = self._client.get(f"/types/incident/fields/{field_name}") or {}
        return definition.get("values") or []

    def incidents_where(self, field_name: str, value: Any) -> list[dict[str, Any]]:
        query = {
            "filters": [
                {
                    "conditions": [
                        {
                            "field_name": f"properties.{field_name}",
                            "method": "equals",
                            "value": value,
                        }
                    ]
                }
            ]
        }
        return self._client.post(QUERY_URI, query) or []

    def workflows(self) -> list[dict[str, Any]]:
        response = self._client.get("/workflows") or {}
        entities = response.get("entities")
        return entities if isinstance(entities, list) else []
