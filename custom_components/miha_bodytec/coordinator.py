"""Data update coordinator for miha bodytec."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MihaApiError, MihaAuthError, MihaBodytecApi
from .const import CONF_PASSWORD, CONF_USERNAME, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MihaBodytecCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the LogX member portal."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
            config_entry=entry,
        )
        self.entry = entry
        self._session = async_create_clientsession(
            hass, cookie_jar=aiohttp.CookieJar(unsafe=True)
        )
        self.api = MihaBodytecApi(
            self._session,
            username=str(entry.data[CONF_USERNAME]),
            password=str(entry.data[CONF_PASSWORD]),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.async_fetch_dashboard()
        except MihaAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except MihaApiError as err:
            raise UpdateFailed(str(err)) from err
