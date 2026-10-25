"""Calendar platform for miha bodytec appointments."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import MihaBodytecConfigEntry
from .coordinator import MihaBodytecCoordinator
from .helpers import appointment_window, device_info, studio_timezone


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MihaBodytecConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the calendar entity."""
    _ = hass
    async_add_entities([MihaBodytecCalendar(entry.runtime_data, entry.entry_id)])


class MihaBodytecCalendar(
    CoordinatorEntity[MihaBodytecCoordinator], CalendarEntity
):
    """Expose upcoming + recent appointments as calendar events."""

    _attr_has_entity_name = True
    _attr_translation_key = "appointments"
    _attr_icon = "mdi:calendar-month"

    def __init__(
        self, coordinator: MihaBodytecCoordinator, entry_id: str
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_appointments"
        self._attr_suggested_object_id = "appointments"
        self._attr_device_info = device_info(entry_id, coordinator.data)
        self._event: CalendarEvent | None = None
        self._update_from_coordinator()

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        return self._event

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events in a time range."""
        _ = hass
        return [
            event
            for event in self._all_events()
            if event.start < end_date and event.end > start_date
        ]

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_from_coordinator()
        self.async_write_ha_state()

    def _update_from_coordinator(self) -> None:
        data = self.coordinator.data or {}
        self._attr_device_info = device_info(self._entry_id, data)
        events = self._all_events()
        now = datetime.now(studio_timezone(data))
        upcoming = [e for e in events if e.end >= now]
        self._event = upcoming[0] if upcoming else None

    def _all_events(self) -> list[CalendarEvent]:
        data = self.coordinator.data or {}
        tz = studio_timezone(data)
        events: list[CalendarEvent] = []
        seen: set[str] = set()
        for key in ("appointments", "past_appointments"):
            for appt in data.get(key) or []:
                if not isinstance(appt, dict):
                    continue
                event = self._to_event(appt, tz)
                if event is None:
                    continue
                eid = str(appt.get("id") or appt.get("appointmentId") or "")
                if eid and eid in seen:
                    continue
                if eid:
                    seen.add(eid)
                events.append(event)
        events.sort(key=lambda e: e.start)
        return events

    @staticmethod
    def _to_event(appt: dict[str, Any], tz) -> CalendarEvent | None:
        start, end = appointment_window(appt, tz)
        if not start or not end:
            return None
        studio = appt.get("studio") or {}
        city = ((studio.get("address") or {}) or {}).get("city")
        location_parts = [str(studio.get("name") or "").strip()]
        if city:
            location_parts.append(str(city))
        description_bits = []
        if appt.get("id") or appt.get("appointmentId"):
            description_bits.append(
                f"ID: {appt.get('id') or appt.get('appointmentId')}"
            )
        if appt.get("allowChange") is False:
            description_bits.append("Änderung nicht mehr möglich")
        return CalendarEvent(
            start=start,
            end=end,
            summary=str(appt.get("name") or "Training"),
            location=", ".join(p for p in location_parts if p) or None,
            description=" · ".join(description_bits) or None,
            uid=str(appt.get("id") or appt.get("appointmentId") or ""),
        )
