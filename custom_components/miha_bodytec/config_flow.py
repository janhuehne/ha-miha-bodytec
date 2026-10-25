"""Config flow for miha bodytec."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import MihaApiError, MihaAuthError, MihaBodytecApi
from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD, autocomplete="current-password"
            )
        ),
    }
)


def _credentials_schema(
    *, username: str | None = None, require_username: bool = True
) -> vol.Schema:
    user_field: Any
    if require_username:
        user_field = vol.Required(CONF_USERNAME, default=username or "")
    else:
        user_field = vol.Optional(CONF_USERNAME, default=username or "")
    return vol.Schema(
        {
            user_field: TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.EMAIL, autocomplete="username"
                )
            ),
            vol.Required(CONF_PASSWORD): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.PASSWORD, autocomplete="current-password"
                )
            ),
        }
    )


async def _async_validate_login(
    session: aiohttp.ClientSession, username: str, password: str
) -> dict[str, str]:
    api = MihaBodytecApi(session, username, password)
    await api.async_login()
    me = await api.async_get_me()
    user_id = str(me.get("id") or "")
    if not user_id:
        raise MihaAuthError("missing user id")
    display = (
        f"{me.get('firstName') or ''} {me.get('lastName') or ''}".strip()
        or str(me.get("email") or username)
    )
    return {"user_id": user_id, "display": display}


class MihaBodytecConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for miha bodytec."""

    VERSION = 1

    def __init__(self) -> None:
        self._reauth_entry: ConfigEntry | None = None

    async def _async_try_login(
        self, username: str, password: str
    ) -> tuple[dict[str, str] | None, dict[str, str]]:
        session = async_create_clientsession(
            self.hass, cookie_jar=aiohttp.CookieJar(unsafe=True)
        )
        try:
            info = await _async_validate_login(session, username, password)
        except MihaAuthError:
            return None, {"base": "invalid_auth"}
        except (MihaApiError, aiohttp.ClientError):
            return None, {"base": "cannot_connect"}
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected miha bodytec login error")
            return None, {"base": "unknown"}
        return info, {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = str(user_input[CONF_USERNAME]).strip()
            password = str(user_input[CONF_PASSWORD])
            info, errors = await self._async_try_login(username, password)
            if info:
                await self.async_set_unique_id(info["user_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"miha bodytec ({info['display']})",
                    data={CONF_USERNAME: username, CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Re-authenticate when credentials are invalid."""
        _ = entry_data
        self._reauth_entry = self._get_reauth_entry()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect updated credentials and reload the entry."""
        entry = self._reauth_entry or self._get_reauth_entry()
        errors: dict[str, str] = {}
        current_user = str(entry.data.get(CONF_USERNAME) or "")

        if user_input is not None:
            username = str(user_input.get(CONF_USERNAME) or current_user).strip()
            password = str(user_input[CONF_PASSWORD])
            info, errors = await self._async_try_login(username, password)
            if info:
                await self.async_set_unique_id(info["user_id"])
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                    title=f"miha bodytec ({info['display']})",
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_credentials_schema(username=current_user),
            errors=errors,
            description_placeholders={"username": current_user},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow updating stored credentials from the UI."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        current_user = str(entry.data.get(CONF_USERNAME) or "")

        if user_input is not None:
            username = str(user_input.get(CONF_USERNAME) or current_user).strip()
            password = str(user_input[CONF_PASSWORD])
            info, errors = await self._async_try_login(username, password)
            if info:
                await self.async_set_unique_id(info["user_id"])
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                    title=f"miha bodytec ({info['display']})",
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_credentials_schema(username=current_user),
            errors=errors,
        )
