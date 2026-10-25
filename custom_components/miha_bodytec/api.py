"""HTTP client for the miha bodytec LogX member portal."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlencode

import aiohttp

from .const import API_PREFIX, BASE_URL, PAST_LIMIT, UPCOMING_DAYS

_LOGGER = logging.getLogger(__name__)


class MihaAuthError(Exception):
    """Invalid credentials or expired session."""


class MihaApiError(Exception):
    """Unexpected API / transport failure."""


class MihaBodytecApi:
    """Cookie-session client for /api/member-portal/v1."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._studio_id: str | None = None

    def _url(self, path: str, params: dict[str, Any] | None = None) -> str:
        url = f"{BASE_URL}{API_PREFIX}{path}"
        if not params:
            return url
        clean = {
            k: v
            for k, v in params.items()
            if v is not None and v != ""
        }
        if not clean:
            return url
        return f"{url}?{urlencode(clean, doseq=True)}"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._studio_id:
            headers["x-studio-id"] = str(self._studio_id)
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        retry_auth: bool = True,
    ) -> Any:
        url = self._url(path, params)
        try:
            async with self._session.request(
                method,
                url,
                headers=self._headers(),
                json=json_body,
            ) as resp:
                if resp.status == 401 and retry_auth:
                    await self.async_login()
                    return await self._request(
                        method,
                        path,
                        params=params,
                        json_body=json_body,
                        retry_auth=False,
                    )
                if resp.status == 401:
                    raise MihaAuthError("Unauthorized")
                if resp.status == 204:
                    return None
                text = await resp.text()
                if resp.status >= 400:
                    _LOGGER.debug(
                        "miha API %s %s -> %s: %s",
                        method,
                        path,
                        resp.status,
                        text[:500],
                    )
                    if resp.status in (401, 403):
                        raise MihaAuthError(text)
                    raise MihaApiError(f"{method} {path} failed ({resp.status}): {text[:300]}")
                if not text:
                    return None
                return await resp.json(content_type=None)
        except (MihaAuthError, MihaApiError):
            raise
        except aiohttp.ClientError as err:
            raise MihaApiError(str(err)) from err

    async def async_login(self) -> dict[str, Any]:
        """Authenticate and store the portal_token cookie."""
        url = self._url("/auth/login")
        try:
            async with self._session.post(
                url,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json={
                    "username": self._username,
                    "password": self._password,
                    "deviceName": None,
                },
            ) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    raise MihaAuthError(text or f"login failed ({resp.status})")
                data = await resp.json(content_type=None) if text else {}
        except MihaAuthError:
            raise
        except aiohttp.ClientError as err:
            raise MihaApiError(str(err)) from err

        if not isinstance(data, dict) or not data.get("ok"):
            raise MihaAuthError("login rejected")
        return data

    async def async_get_me(self) -> dict[str, Any]:
        data = await self._request("GET", "/me")
        return data if isinstance(data, dict) else {}

    async def async_get_studio(self) -> dict[str, Any]:
        data = await self._request("GET", "/studio")
        if isinstance(data, dict) and data.get("id"):
            self._studio_id = str(data["id"])
        return data if isinstance(data, dict) else {}

    async def async_get_studios(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/studios")
        if isinstance(data, dict):
            studios = data.get("studios") or []
            return [s for s in studios if isinstance(s, dict)]
        return []

    async def async_get_appointments(
        self,
        *,
        start: str | None = None,
        end: str | None = None,
        order: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        data = await self._request(
            "GET",
            "/appointments",
            params={
                "start": start,
                "end": end,
                "order": order,
                "limit": limit,
            },
        )
        return data if isinstance(data, dict) else {"appointments": [], "bookableTypeCount": 0}

    async def async_get_calendar(self, year: int, month: int) -> dict[str, Any]:
        data = await self._request(
            "GET",
            "/calendar",
            params={"year": year, "month": month},
        )
        return data if isinstance(data, dict) else {"weeks": []}

    async def async_get_restrictions(self, day: str) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            "/restrictions",
            params={"date": day},
        )
        return data if isinstance(data, list) else []

    async def async_get_slots(self, day: str, studio_id: str | int) -> dict[str, Any]:
        data = await self._request(
            "GET",
            "/slots",
            params={"date": day, "studioId": studio_id},
        )
        return data if isinstance(data, dict) else {}

    async def async_book_appointment(
        self,
        *,
        day: str,
        start: str,
        end: str,
        studio_id: int,
        type_id: int,
        online_scheduling_partner_id: int | None = None,
    ) -> dict[str, Any]:
        data = await self._request(
            "POST",
            "/appointments",
            json_body={
                "date": day,
                "start": start,
                "end": end,
                "studioId": studio_id,
                "typeId": type_id,
                "onlineSchedulingPartnerId": online_scheduling_partner_id,
            },
        )
        return data if isinstance(data, dict) else {}

    async def async_reschedule_appointment(
        self,
        appointment_id: str,
        *,
        start: str,
        end: str,
        studio_id: int,
        type_id: int,
        online_scheduling_partner_id: int | None = None,
    ) -> dict[str, Any]:
        data = await self._request(
            "PUT",
            f"/appointments/{appointment_id}",
            json_body={
                "start": start,
                "end": end,
                "studioId": studio_id,
                "typeId": type_id,
                "onlineSchedulingPartnerId": online_scheduling_partner_id,
            },
        )
        return data if isinstance(data, dict) else {}

    async def async_cancel_appointment(
        self,
        appointment_id: str,
        *,
        online_scheduling_partner_id: int | None = None,
    ) -> dict[str, Any]:
        data = await self._request(
            "DELETE",
            f"/appointments/{appointment_id}",
            params={"onlineSchedulingPartnerId": online_scheduling_partner_id},
        )
        return data if isinstance(data, dict) else {}

    async def async_fetch_dashboard(self) -> dict[str, Any]:
        """Login (if needed) and pull everything useful for HA sensors."""
        await self.async_login()
        me = await self.async_get_me()
        studio = await self.async_get_studio()
        studios = await self.async_get_studios()

        today = date.today()
        upcoming = await self.async_get_appointments(
            start=today.isoformat(),
            end=(today + timedelta(days=UPCOMING_DAYS)).isoformat(),
        )
        past = await self.async_get_appointments(
            end=today.isoformat(),
            order="desc",
            limit=PAST_LIMIT,
        )
        calendar = await self.async_get_calendar(today.year, today.month)
        restrictions = await self.async_get_restrictions(today.isoformat())

        appointments = [
            a
            for a in (upcoming.get("appointments") or [])
            if isinstance(a, dict)
        ]
        past_appointments = [
            a for a in (past.get("appointments") or []) if isinstance(a, dict)
        ]
        appointments.sort(key=lambda a: str(a.get("startDate") or ""))

        next_appt = appointments[0] if appointments else None
        settings = (studio.get("settings") or {}) if isinstance(studio, dict) else {}
        contract = None
        if restrictions:
            first = restrictions[0]
            if isinstance(first, dict):
                contract = first.get("Contract") or first

        return {
            "me": me,
            "studio": studio,
            "studios": studios,
            "appointments": appointments,
            "past_appointments": past_appointments,
            "next_appointment": next_appt,
            "bookable_type_count": upcoming.get("bookableTypeCount")
            or past.get("bookableTypeCount")
            or 0,
            "calendar": calendar,
            "restrictions": restrictions,
            "contract": contract,
            "settings": settings if isinstance(settings, dict) else {},
            "fetched_at": today.isoformat(),
        }
