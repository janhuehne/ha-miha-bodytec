"""Services for miha bodytec appointment writes."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .api import MihaApiError, MihaAuthError
from .const import DOMAIN

SERVICE_REFRESH = "refresh"
SERVICE_CANCEL = "cancel_appointment"
SERVICE_BOOK = "book_appointment"
SERVICE_RESCHEDULE = "reschedule_appointment"

_SCHEMA_CANCEL = vol.Schema(
    {
        vol.Required("appointment_id"): cv.string,
        vol.Optional("online_scheduling_partner_id"): vol.Any(int, None),
    }
)

_SCHEMA_BOOK = vol.Schema(
    {
        vol.Required("date"): cv.string,
        vol.Required("start"): cv.string,
        vol.Required("end"): cv.string,
        vol.Required("type_id"): vol.Coerce(int),
        vol.Optional("studio_id"): vol.Coerce(int),
        vol.Optional("online_scheduling_partner_id"): vol.Any(int, None),
    }
)

_SCHEMA_RESCHEDULE = vol.Schema(
    {
        vol.Required("appointment_id"): cv.string,
        vol.Required("start"): cv.string,
        vol.Required("end"): cv.string,
        vol.Required("type_id"): vol.Coerce(int),
        vol.Optional("studio_id"): vol.Coerce(int),
        vol.Optional("online_scheduling_partner_id"): vol.Any(int, None),
    }
)


def _coordinator(hass: HomeAssistant):
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        raise HomeAssistantError("miha bodytec is not configured")
    return entries[0].runtime_data


async def _async_refresh(call: ServiceCall) -> None:
    await _coordinator(call.hass).async_request_refresh()


async def _async_cancel(call: ServiceCall) -> None:
    coordinator = _coordinator(call.hass)
    try:
        await coordinator.api.async_cancel_appointment(
            call.data["appointment_id"],
            online_scheduling_partner_id=call.data.get(
                "online_scheduling_partner_id"
            ),
        )
    except (MihaAuthError, MihaApiError) as err:
        raise HomeAssistantError(str(err)) from err
    await coordinator.async_request_refresh()


async def _async_book(call: ServiceCall) -> None:
    coordinator = _coordinator(call.hass)
    data = coordinator.data or {}
    studio = data.get("studio") or {}
    studio_id = call.data.get("studio_id") or int(studio.get("id") or 0)
    if not studio_id:
        raise HomeAssistantError("studio_id is required")
    try:
        await coordinator.api.async_book_appointment(
            day=call.data["date"],
            start=call.data["start"],
            end=call.data["end"],
            studio_id=int(studio_id),
            type_id=int(call.data["type_id"]),
            online_scheduling_partner_id=call.data.get(
                "online_scheduling_partner_id"
            ),
        )
    except (MihaAuthError, MihaApiError) as err:
        raise HomeAssistantError(str(err)) from err
    await coordinator.async_request_refresh()


async def _async_reschedule(call: ServiceCall) -> None:
    coordinator = _coordinator(call.hass)
    data = coordinator.data or {}
    studio = data.get("studio") or {}
    studio_id = call.data.get("studio_id") or int(studio.get("id") or 0)
    if not studio_id:
        raise HomeAssistantError("studio_id is required")
    try:
        await coordinator.api.async_reschedule_appointment(
            call.data["appointment_id"],
            start=call.data["start"],
            end=call.data["end"],
            studio_id=int(studio_id),
            type_id=int(call.data["type_id"]),
            online_scheduling_partner_id=call.data.get(
                "online_scheduling_partner_id"
            ),
        )
    except (MihaAuthError, MihaApiError) as err:
        raise HomeAssistantError(str(err)) from err
    await coordinator.async_request_refresh()


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register domain services once."""
    if hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        return

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, _async_refresh)
    hass.services.async_register(
        DOMAIN, SERVICE_CANCEL, _async_cancel, schema=_SCHEMA_CANCEL
    )
    hass.services.async_register(
        DOMAIN, SERVICE_BOOK, _async_book, schema=_SCHEMA_BOOK
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RESCHEDULE, _async_reschedule, schema=_SCHEMA_RESCHEDULE
    )


@callback
def async_unload_services(hass: HomeAssistant) -> None:
    """Remove domain services."""
    for service in (
        SERVICE_REFRESH,
        SERVICE_CANCEL,
        SERVICE_BOOK,
        SERVICE_RESCHEDULE,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
