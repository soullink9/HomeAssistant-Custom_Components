"""Constants shared by every part of the TrueNAS Apps integration."""

from homeassistant.const import Platform

DOMAIN = "truenas_apps"

# Entity platforms this integration provides (one module each).
PLATFORMS = [Platform.BUTTON, Platform.SENSOR, Platform.SWITCH, Platform.UPDATE]

# All times are in seconds.
POLL_INTERVAL = 60  # how often Home Assistant asks TrueNAS for fresh data
POLL_TIMEOUT = 90  # hard cap for one poll (connect + log in + every query)
CALL_TIMEOUT = 30  # longest we wait for the answer to a single request
JOB_TIMEOUT = 1800  # give up waiting for an app job (upgrade/redeploy) after 30 minutes
JOB_CHECK_INTERVAL = 1  # how often a running job is checked for completion
