"""Constants shared by every part of the integration."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "carrier_infinity"

# The entity types this integration creates (one climate per zone, plus sensors per system).
PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]

# How often everything is re-read from the Carrier cloud. Changes arrive in between over Carrier's
# websocket, so this full refresh is only a safety net (and how the energy totals are updated).
FULL_REFRESH = timedelta(minutes=5)

# After Home Assistant changes a setting, Carrier's cloud keeps serving (and re-broadcasting) the old
# value for a few minutes. For this long, the value we wrote is shown instead of the cloud's stale copy.
EXPECT_SECONDS = 300

# Websocket reconnect back-off: start here, double on each failure, never wait longer than the cap.
RECONNECT_FIRST = 10
RECONNECT_MAX = 600
