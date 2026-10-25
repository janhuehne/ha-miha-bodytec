"""Sensors for miha bodytec training portal."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import MihaBodytecConfigEntry
from .const import (
    ATTR_APPOINTMENTS,
    ATTR_CONTRACT,
    ATTR_NEXT_APPOINTMENT,
    ATTR_RESTRICTIONS,
    ATTR_SOURCE,
    ATTR_STUDIO,
    SOURCE_MIHA,
)
from .coordinator import MihaBodytecCoordinator
from .helpers import (
    appointment_window,
    device_info,
    parse_iso_date,
    studio_timezone,
    summarize_appointment,
)


@dataclass(frozen=True, kw_only=True)
class MihaSensorDescription(SensorEntityDescription):
    """Sensor description with value / attribute extractors."""

    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _me(data: dict[str, Any]) -> dict[str, Any]:
    return data.get("me") or {}


def _studio(data: dict[str, Any]) -> dict[str, Any]:
    return data.get("studio") or {}


def _settings(data: dict[str, Any]) -> dict[str, Any]:
    return data.get("settings") or _studio(data).get("settings") or {}


def _next(data: dict[str, Any]) -> dict[str, Any] | None:
    return data.get("next_appointment")


def _next_start(data: dict[str, Any]) -> datetime | None:
    appt = _next(data)
    if not appt:
        return None
    start, _ = appointment_window(appt, studio_timezone(data))
    return start


def _days_until_next(data: dict[str, Any]) -> int | None:
    start = _next_start(data)
    if not start:
        return None
    local_today = datetime.now(studio_timezone(data)).date()
    return (start.date() - local_today).days


def _membership_until(data: dict[str, Any]) -> date | None:
    return parse_iso_date(_me(data).get("contractsUntil"))


def _contract_name(data: dict[str, Any]) -> str | None:
    restrictions = data.get("restrictions") or []
    if restrictions and isinstance(restrictions[0], dict):
        return restrictions[0].get("Name") or restrictions[0].get("ServiceTypeName")
    contract = data.get("contract") or {}
    if isinstance(contract, dict):
        return contract.get("Name")
    return None


def _iter_known_appointments(data: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key in ("appointments", "past_appointments"):
        for appt in data.get(key) or []:
            if isinstance(appt, dict):
                items.append(appt)
    return items


def _trainings_this_week_list(data: dict[str, Any]) -> list[dict[str, Any] | None]:
    tz = studio_timezone(data)
    now = datetime.now(tz)
    start_week = (now - timedelta(days=now.weekday())).date()
    end_week = start_week + timedelta(days=6)
    out: list[dict[str, Any] | None] = []
    for appt in _iter_known_appointments(data):
        start, _ = appointment_window(appt, tz)
        if start and start_week <= start.date() <= end_week:
            out.append(summarize_appointment(appt))
    return out


def _trainings_this_week(data: dict[str, Any]) -> int:
    return len(_trainings_this_week_list(data))


def _trainings_this_month(data: dict[str, Any]) -> int:
    tz = studio_timezone(data)
    now = datetime.now(tz)
    count = 0
    for appt in _iter_known_appointments(data):
        start, _ = appointment_window(appt, tz)
        if start and start.year == now.year and start.month == now.month:
            count += 1
    return count


SENSOR_DESCRIPTIONS: tuple[MihaSensorDescription, ...] = (
    MihaSensorDescription(
        key="next_appointment",
        translation_key="next_appointment",
        icon="mdi:calendar-clock",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_next_start,
        attrs_fn=lambda d: {
            ATTR_NEXT_APPOINTMENT: summarize_appointment(_next(d)),
            ATTR_SOURCE: SOURCE_MIHA,
        },
    ),
    MihaSensorDescription(
        key="next_appointment_name",
        translation_key="next_appointment_name",
        icon="mdi:dumbbell",
        value_fn=lambda d: (_next(d) or {}).get("name"),
        attrs_fn=lambda d: {
            ATTR_NEXT_APPOINTMENT: summarize_appointment(_next(d)),
        },
    ),
    MihaSensorDescription(
        key="days_until_next_training",
        translation_key="days_until_next_training",
        icon="mdi:timer-sand",
        native_unit_of_measurement="d",
        value_fn=_days_until_next,
    ),
    MihaSensorDescription(
        key="upcoming_count",
        translation_key="upcoming_count",
        icon="mdi:calendar-multiple",
        value_fn=lambda d: len(d.get("appointments") or []),
        attrs_fn=lambda d: {
            ATTR_APPOINTMENTS: [
                summarize_appointment(a) for a in (d.get("appointments") or [])
            ],
            ATTR_SOURCE: SOURCE_MIHA,
        },
    ),
    MihaSensorDescription(
        key="past_count",
        translation_key="past_count",
        icon="mdi:history",
        value_fn=lambda d: len(d.get("past_appointments") or []),
        attrs_fn=lambda d: {
            ATTR_APPOINTMENTS: [
                summarize_appointment(a) for a in (d.get("past_appointments") or [])
            ],
        },
    ),
    MihaSensorDescription(
        key="membership_until",
        translation_key="membership_until",
        icon="mdi:card-account-details",
        device_class=SensorDeviceClass.DATE,
        value_fn=_membership_until,
        attrs_fn=lambda d: {
            "has_ongoing_services": _me(d).get("hasOngoingServices"),
            "email": _me(d).get("email"),
            "first_name": _me(d).get("firstName"),
            "last_name": _me(d).get("lastName"),
            "member_id": _me(d).get("id"),
        },
    ),
    MihaSensorDescription(
        key="contract_name",
        translation_key="contract_name",
        icon="mdi:file-document",
        value_fn=_contract_name,
        attrs_fn=lambda d: {
            ATTR_CONTRACT: d.get("contract"),
            ATTR_RESTRICTIONS: d.get("restrictions") or [],
        },
    ),
    MihaSensorDescription(
        key="studio_name",
        translation_key="studio_name",
        icon="mdi:store-marker",
        value_fn=lambda d: str(_studio(d).get("name") or "").strip() or None,
        attrs_fn=lambda d: {
            ATTR_STUDIO: {
                "id": _studio(d).get("id"),
                "name": _studio(d).get("name"),
                "address": _studio(d).get("address"),
                "contact": _studio(d).get("contact"),
                "timezone": _studio(d).get("timezone"),
            },
            "studios": d.get("studios") or [],
        },
    ),
    MihaSensorDescription(
        key="studio_phone",
        translation_key="studio_phone",
        icon="mdi:phone",
        value_fn=lambda d: ((_studio(d).get("contact") or {}) or {}).get("phone"),
    ),
    MihaSensorDescription(
        key="studio_email",
        translation_key="studio_email",
        icon="mdi:email",
        value_fn=lambda d: ((_studio(d).get("contact") or {}) or {}).get("email"),
    ),
    MihaSensorDescription(
        key="studio_city",
        translation_key="studio_city",
        icon="mdi:city",
        value_fn=lambda d: ((_studio(d).get("address") or {}) or {}).get("city"),
        attrs_fn=lambda d: {"address": _studio(d).get("address")},
    ),
    MihaSensorDescription(
        key="cancellation_deadline_hours",
        translation_key="cancellation_deadline_hours",
        icon="mdi:cancel",
        native_unit_of_measurement="h",
        value_fn=lambda d: _settings(d).get("cancellationDeadline"),
        attrs_fn=lambda d: {"settings": _settings(d)},
    ),
    MihaSensorDescription(
        key="booking_lead_time_minutes",
        translation_key="booking_lead_time_minutes",
        icon="mdi:clock-start",
        native_unit_of_measurement="min",
        value_fn=lambda d: _settings(d).get("bookingAllowedWorkoutFromNowIn"),
    ),
    MihaSensorDescription(
        key="slot_duration_minutes",
        translation_key="slot_duration_minutes",
        icon="mdi:timer-outline",
        native_unit_of_measurement="min",
        value_fn=lambda d: _settings(d).get("slotDurationWorkout"),
    ),
    MihaSensorDescription(
        key="bookable_type_count",
        translation_key="bookable_type_count",
        icon="mdi:format-list-bulleted-type",
        value_fn=lambda d: d.get("bookable_type_count") or 0,
    ),
    MihaSensorDescription(
        key="member_name",
        translation_key="member_name",
        icon="mdi:account",
        value_fn=lambda d: (
            f"{_me(d).get('firstName') or ''} {_me(d).get('lastName') or ''}".strip()
            or None
        ),
        attrs_fn=lambda d: {
            "email": _me(d).get("email"),
            "member_id": _me(d).get("id"),
        },
    ),
    MihaSensorDescription(
        key="trainings_this_week",
        translation_key="trainings_this_week",
        icon="mdi:calendar-week",
        value_fn=_trainings_this_week,
        attrs_fn=lambda d: {
            ATTR_APPOINTMENTS: _trainings_this_week_list(d),
        },
    ),
    MihaSensorDescription(
        key="trainings_this_month",
        translation_key="trainings_this_month",
        icon="mdi:calendar-month",
        value_fn=_trainings_this_month,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MihaBodytecConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    _ = hass
    coordinator = entry.runtime_data
    async_add_entities(
        MihaBodytecSensor(coordinator, entry.entry_id, description)
        for description in SENSOR_DESCRIPTIONS
    )


class MihaBodytecSensor(
    CoordinatorEntity[MihaBodytecCoordinator], SensorEntity
):
    """Generic miha bodytec sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MihaBodytecCoordinator,
        entry_id: str,
        description: MihaSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._description = description
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_suggested_object_id = description.key
        self._attr_device_info = device_info(entry_id, coordinator.data)
        self._update_from_coordinator()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_from_coordinator()
        self.async_write_ha_state()

    def _update_from_coordinator(self) -> None:
        data = self.coordinator.data or {}
        self._attr_device_info = device_info(self._entry_id, data)
        self._attr_native_value = self._description.value_fn(data)
        if self._description.attrs_fn:
            self._attr_extra_state_attributes = self._description.attrs_fn(data)
        else:
            self._attr_extra_state_attributes = {}
