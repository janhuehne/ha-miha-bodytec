"""Shared helpers for miha bodytec entities."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo


def studio_timezone(data: dict[str, Any] | None) -> ZoneInfo:
    """Resolve studio timezone from coordinator data."""
    studio = (data or {}).get("studio") or {}
    tz_name = studio.get("timezone") or "Europe/Berlin"
    try:
        return ZoneInfo(str(tz_name))
    except Exception:  # noqa: BLE001
        return ZoneInfo("Europe/Berlin")


def parse_local_datetime(value: str | None, tz: ZoneInfo) -> datetime | None:
    """Parse portal datetimes like '2026-10-26 09:00:00' as studio-local."""
    if not value or not isinstance(value, str):
        return None
    raw = value.strip().replace("T", " ")
    for fmt, length in (
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%d %H:%M", 16),
        ("%Y-%m-%d", 10),
    ):
        try:
            naive = datetime.strptime(raw[:length], fmt)
            return naive.replace(tzinfo=tz)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz)


def parse_iso_date(value: str | None) -> date | None:
    """Parse ISO / portal date strings to a date."""
    if not value or not isinstance(value, str):
        return None
    raw = value.strip()
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def appointment_window(
    appt: dict[str, Any], tz: ZoneInfo
) -> tuple[datetime | None, datetime | None]:
    """Return (start, end) for an appointment dict."""
    start = parse_local_datetime(appt.get("startDate"), tz)
    end = parse_local_datetime(appt.get("endDate"), tz)
    if start and not end:
        end = start + timedelta(minutes=30)
    return start, end


def summarize_appointment(appt: dict[str, Any] | None) -> dict[str, Any] | None:
    """Flatten appointment fields for sensor attributes."""
    if not isinstance(appt, dict):
        return None
    studio = appt.get("studio") or {}
    address = studio.get("address") or {}
    return {
        "id": appt.get("id") or appt.get("appointmentId"),
        "name": appt.get("name"),
        "start": appt.get("startDate"),
        "end": appt.get("endDate"),
        "studio_id": studio.get("id") or studio.get("studioId"),
        "studio_name": studio.get("name"),
        "studio_city": address.get("city") if isinstance(address, dict) else None,
        "allow_change": appt.get("allowChange"),
        "changeable_online": appt.get("changeableOnline"),
        "type_id": appt.get("typeId"),
        "background_color": appt.get("backgroundColor"),
    }


def device_info(entry_id: str, data: dict[str, Any] | None) -> dict[str, Any]:
    """Shared device registry info (stable name → stable entity_ids)."""
    studio = (data or {}).get("studio") or {}
    studio_name = str(studio.get("name") or "").strip()
    return {
        "identifiers": {("miha_bodytec", entry_id)},
        "name": "miha bodytec",
        "manufacturer": "miha bodytec (unofficial)",
        "model": studio_name or "LogX member portal",
        "configuration_url": "https://training.miha-bodytec.com/",
    }
