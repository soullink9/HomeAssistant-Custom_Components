from enum import StrEnum

CONF_API_KEY = "api_key"
CONF_HOST = "host"
CONF_VERIFY_SSL = "verify_ssl"
PERCENTAGE = "%"


class Platform(StrEnum):
    BUTTON = "button"
    SENSOR = "sensor"
    SWITCH = "switch"
    UPDATE = "update"
