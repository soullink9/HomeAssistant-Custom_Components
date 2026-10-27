"""A minimal stand-in for Home Assistant, so the integration's own code can run without it.

Not a substitute for real Home Assistant: it checks our code paths (the coordinator, entities, websocket handling,
the electricity meter, the config flow) against small fakes of the Home Assistant APIs we use, written to match
Home Assistant 2026.9. If Home Assistant changes one of those APIs, update the fake here to match.

It also replaces the network layer under carrier_api (aiohttp, gql), so nothing can reach Carrier's cloud.
Needs carrier-api installed (pip install -r tests/carrier_infinity/requirements.txt).
"""

from datetime import UTC, datetime
import enum
import json
from pathlib import Path
import sys
import types
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[3]
FIXTURES = REPO / "tests" / "carrier_infinity" / "fixtures"
sys.path.insert(0, str(REPO / "custom_components"))  # so `import carrier_infinity` finds the integration

TZ = ZoneInfo("America/New_York")
NOW = [datetime(2026, 10, 18, 12, 0, tzinfo=TZ)]  # the clock the integration sees; tests move it
SAVED = {}  # restore-state data by unique_id: what Home Assistant would have saved before a restart


def mod(name, **attrs):
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    sys.modules[name] = m
    return m


# --- carrier_api's network layer (never used: the tests give the coordinator a fake API) -------------------------
class ClientError(Exception): ...


mod(
    "aiohttp",
    ClientError=ClientError,
    ClientResponseError=type("ClientResponseError", (ClientError,), {}),
    ClientSession=MagicMock,
    ClientWebSocketResponse=object,
    WSMsgType=MagicMock(),
)
mod("gql", Client=MagicMock, gql=lambda q: q, GraphQLRequest=object)
mod("gql.transport")
mod("gql.transport.aiohttp", AIOHTTPTransport=MagicMock)
mod(
    "gql.transport.exceptions",
    **{
        n: type(n, (Exception,), {})
        for n in (
            "TransportQueryError",
            "TransportServerError",
            "TransportProtocolError",
            "TransportClosed",
            "TransportAlreadyConnected",
            "TransportError",
            "TransportConnectionFailed",
        )
    },
)
mod("graphql", GraphQLError=type("GraphQLError", (Exception,), {}), get_introspection_query=lambda: "")


# --- homeassistant -----------------------------------------------------------------------------------------------
class Generic:
    def __class_getitem__(cls, _):
        return cls


class StrEnum(str, enum.Enum):
    def __str__(self):
        return self.value


class HVACMode(StrEnum):
    OFF = "off"
    HEAT = "heat"
    COOL = "cool"
    HEAT_COOL = "heat_cool"
    AUTO = "auto"
    DRY = "dry"
    FAN_ONLY = "fan_only"


class HVACAction(StrEnum):
    OFF = "off"
    HEATING = "heating"
    COOLING = "cooling"
    IDLE = "idle"
    FAN = "fan"


class ClimateEntityFeature(enum.IntFlag):
    TARGET_TEMPERATURE = 1
    TARGET_TEMPERATURE_RANGE = 2
    TARGET_HUMIDITY = 4
    FAN_MODE = 8
    PRESET_MODE = 16
    TURN_OFF = 128
    TURN_ON = 256


class UnitOfTemperature(StrEnum):
    CELSIUS = "°C"
    FAHRENHEIT = "°F"


class UnitOfEnergy(StrEnum):
    KILO_WATT_HOUR = "kWh"


class Platform(StrEnum):
    CLIMATE = "climate"
    SENSOR = "sensor"


class SensorDeviceClass(StrEnum):
    TEMPERATURE = "temperature"
    ENERGY = "energy"


class SensorStateClass(StrEnum):
    MEASUREMENT = "measurement"
    TOTAL_INCREASING = "total_increasing"


class HomeAssistantError(Exception): ...


class ConfigEntryAuthFailed(HomeAssistantError): ...


class UpdateFailed(HomeAssistantError): ...


class AbortFlow(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class ConfigEntry(Generic):
    def __init__(self, data, unique_id=None):
        self.data, self.unique_id = dict(data), unique_id
        self.reloaded = 0


class DataUpdateCoordinator(Generic):
    def __init__(self, hass, logger, *, config_entry=None, name, update_interval=None):
        self.hass, self.config_entry, self.name, self.update_interval = hass, config_entry, name, update_interval
        self.data = None
        self.last_update_success, self.last_exception = True, None
        self.listener_updates = 0

    def async_update_listeners(self):
        self.listener_updates += 1


class CoordinatorEntity(Generic):
    def __init__(self, coordinator, context=None):
        self.coordinator = coordinator
        self.writes = 0

    @property
    def available(self):
        return self.coordinator.last_update_success

    async def async_added_to_hass(self):
        pass

    def _handle_coordinator_update(self):
        self.async_write_ha_state()

    def async_write_ha_state(self):
        self.writes += 1


class Entity:
    pass


class ClimateEntity(Entity): ...


class SensorEntity(Entity): ...


class RestoredExtraData:
    def __init__(self, json_dict):
        self.json_dict = json_dict

    def as_dict(self):
        return self.json_dict


class RestoreEntity(Entity):
    async def async_get_last_extra_data(self):
        saved = SAVED.get(self._attr_unique_id)
        return RestoredExtraData(json.loads(json.dumps(saved))) if saved is not None else None  # via JSON, like HA


class ConfigFlow:
    """Just enough of Home Assistant's ConfigFlow for our two forms."""

    existing_unique_ids: set = set()  # unique ids of entries already set up

    def __init_subclass__(cls, domain=None, **kw):
        super().__init_subclass__(**kw)
        cls.domain = domain

    def __init__(self):
        self.unique_id = None
        self.reauth_entry = None

    async def async_set_unique_id(self, unique_id):
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self):
        if self.unique_id in self.existing_unique_ids:
            raise AbortFlow("already_configured")

    def async_show_form(self, *, step_id, data_schema=None, errors=None, description_placeholders=None):
        return {"type": "form", "step_id": step_id, "errors": errors or {}, "placeholders": description_placeholders}

    def async_create_entry(self, *, title, data):
        return {"type": "create_entry", "title": title, "data": data}

    def _get_reauth_entry(self):
        return self.reauth_entry

    def async_update_reload_and_abort(self, entry, *, data_updates):
        entry.data.update(data_updates)
        entry.reloaded += 1
        return {"type": "abort", "reason": "reauth_successful"}


class TextSelectorType(StrEnum):
    PASSWORD = "password"


def _dt_now():
    return NOW[0]


mod("homeassistant")
mod(
    "homeassistant.const",
    CONF_USERNAME="username",
    CONF_PASSWORD="password",
    ATTR_TEMPERATURE="temperature",
    Platform=Platform,
    UnitOfTemperature=UnitOfTemperature,
    UnitOfEnergy=UnitOfEnergy,
)
mod("homeassistant.core", HomeAssistant=object)
mod("homeassistant.config_entries", ConfigEntry=ConfigEntry, ConfigFlow=ConfigFlow, ConfigFlowResult=dict)
mod("homeassistant.exceptions", HomeAssistantError=HomeAssistantError, ConfigEntryAuthFailed=ConfigEntryAuthFailed)
mod("homeassistant.helpers")
mod("homeassistant.helpers.device_registry", DeviceInfo=dict)
mod("homeassistant.helpers.entity_platform", AddConfigEntryEntitiesCallback=object)
mod(
    "homeassistant.helpers.update_coordinator",
    DataUpdateCoordinator=DataUpdateCoordinator,
    CoordinatorEntity=CoordinatorEntity,
    UpdateFailed=UpdateFailed,
)
mod("homeassistant.helpers.restore_state", RestoreEntity=RestoreEntity, RestoredExtraData=RestoredExtraData)
mod(
    "homeassistant.helpers.selector",
    TextSelector=lambda config: ("text_selector", config),
    TextSelectorConfig=lambda **kw: kw,
    TextSelectorType=TextSelectorType,
)
mod("homeassistant.components")
mod(
    "homeassistant.components.climate",
    ATTR_TARGET_TEMP_HIGH="target_temp_high",
    ATTR_TARGET_TEMP_LOW="target_temp_low",
    ClimateEntity=ClimateEntity,
    ClimateEntityFeature=ClimateEntityFeature,
    HVACAction=HVACAction,
    HVACMode=HVACMode,
)
mod(
    "homeassistant.components.sensor",
    SensorEntity=SensorEntity,
    SensorDeviceClass=SensorDeviceClass,
    SensorStateClass=SensorStateClass,
)
mod("homeassistant.util")
mod(
    "homeassistant.util.dt",
    now=_dt_now,
    utc_from_timestamp=lambda ts: datetime.fromtimestamp(ts, tz=UTC),
    as_local=lambda d: d.astimezone(TZ),
)
sys.modules["homeassistant.util"].dt = sys.modules["homeassistant.util.dt"]
mod("voluptuous", Schema=lambda s: s, Required=lambda k: k)


# --- Carrier data from the fixtures -------------------------------------------------------------------------------
def load_systems():
    """carrier_api System objects built from the recorded cloud responses in tests/carrier_infinity/fixtures."""
    from carrier_api import Config, Energy, Profile, Status, System

    raw = json.loads((FIXTURES / "systems.json").read_text())["infinitySystems"]
    energy = json.loads((FIXTURES / "energy.json").read_text())["infinityEnergy"]
    return [System(Profile(s["profile"]), Status(s["status"]), Config(s["config"]), Energy(energy)) for s in raw]


def message(name, serial):
    """A recorded websocket message, addressed to the system with this serial."""
    return (FIXTURES / "messages" / f"{name}.json").read_text().replace("SERIALXXX", serial)
