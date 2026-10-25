"""miha bodytec — LogX EMS training appointments for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import MihaBodytecCoordinator
from .services import async_setup_services, async_unload_services

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.CALENDAR,
]

type MihaBodytecConfigEntry = ConfigEntry[MihaBodytecCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: MihaBodytecConfigEntry
) -> bool:
    """Set up miha bodytec from a config entry."""
    coordinator = MihaBodytecCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    async_setup_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: MihaBodytecConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        from .const import DOMAIN

        if not hass.config_entries.async_entries(DOMAIN):
            async_unload_services(hass)
    return unload_ok
