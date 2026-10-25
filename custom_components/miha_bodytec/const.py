"""Constants for miha bodytec (LogX member portal)."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "miha_bodytec"

CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"

BASE_URL: Final = "https://training.miha-bodytec.com"
API_PREFIX: Final = "/api/member-portal/v1"

DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=15)
UPCOMING_DAYS: Final = 90
PAST_LIMIT: Final = 20

ATTR_APPOINTMENTS: Final = "appointments"
ATTR_NEXT_APPOINTMENT: Final = "next_appointment"
ATTR_STUDIO: Final = "studio"
ATTR_CONTRACT: Final = "contract"
ATTR_RESTRICTIONS: Final = "restrictions"
ATTR_SOURCE: Final = "source"

SOURCE_MIHA: Final = "miha_bodytec"
