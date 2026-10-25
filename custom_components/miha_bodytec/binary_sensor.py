"""Binary sensors for miha bodytec."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import MihaBodytecConfigEntry
from .coordinator import MihaBodytecCoordinator
from .helpers import appointment_window, device_info, studio_timezone


@dataclass(frozen=True, kw_only=True)
class MihaBinaryDescription(BinarySensorEntityDescription):
    """Binary sensor with value extractor."""

    value_fn: Callable[[dict[str, Any]], bool]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _has_training_on(data: dict[str, Any], offset_days: int) -> bool:
    tz = studio_timezone(data)
    target = (datetime.now(tz) + timedelta(days=offset_days)).date()
    for appt in data.get("appointments") or []:
        if not isinstance(appt, dict):
            continue
        start, _ = appointment_window(appt, tz)
        if start and start.date() == target:
            return True
    return False


def _membership_active(data: dict[str, Any]) -> bool:
    me = data.get("me") or {}
    return bool(me.get("hasOngoingServices"))


def _online_booking_allowed(data: dict[str, Any]) -> bool:
    settings = data.get("settings") or (data.get("studio") or {}).get("settings") or {}
    return bool(settings.get("workoutAllowed")) and bool(
        settings.get("rightOnlineAppAppointment")
    )


BINARY_DESCRIPTIONS: tuple[MihaBinaryDescription, ...] = (
    MihaBinaryDescription(
        key="membership_active",
        translation_key="membership_active",
        icon="mdi:card-account-details-outline",
        value_fn=_membership_active,
    ),
    MihaBinaryDescription(
        key="training_today",
        translation_key="training_today",
        icon="mdi:calendar-today",
        value_fn=lambda d: _has_training_on(d, 0),
    ),
    MihaBinaryDescription(
        key="training_tomorrow",
        translation_key="training_tomorrow",
        icon="mdi:calendar-arrow-right",
        value_fn=lambda d: _has_training_on(d, 1),
    ),
    MihaBinaryDescription(
        key="online_booking_allowed",
        translation_key="online_booking_allowed",
        icon="mdi:calendar-check",
        value_fn=_online_booking_allowed,
        attrs_fn=lambda d: {"settings": d.get("settings") or {}},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MihaBodytecConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    _ = hass
    coordinator = entry.runtime_data
    async_add_entities(
        MihaBodytecBinarySensor(coordinator, entry.entry_id, description)
        for description in BINARY_DESCRIPTIONS
    )


class MihaBodytecBinarySensor(
    CoordinatorEntity[MihaBodytecCoordinator], BinarySensorEntity
):
    """Binary sensor backed by coordinator data."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MihaBodytecCoordinator,
        entry_id: str,
        description: MihaBinaryDescription,
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
        self._attr_is_on = bool(self._description.value_fn(data))
        if self._description.attrs_fn:
            self._attr_extra_state_attributes = self._description.attrs_fn(data)
        else:
            self._attr_extra_state_attributes = {}
