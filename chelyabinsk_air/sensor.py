import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from slugify import slugify

from .const import DOMAIN, STATIONS, SENSORS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]

    coordinator = data["coordinator"]
    manager = data["manager"]

    stations = entry.options.get("stations", entry.data.get("stations", []))

    entities = []

    for station_ind in stations:
        for key in SENSORS:
            entities.append(AirSensor(coordinator, manager, station_ind, key))

    async_add_entities(entities)


class AirSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, manager, station_ind, sensor_key):
        super().__init__(coordinator)

        name, unit, device_class = SENSORS[sensor_key]

        self._manager = manager
        self._station_ind = station_ind
        self._sensor_key = sensor_key

        station_name = STATIONS.get(station_ind, station_ind)

        self._attr_name = f"{station_name} {name}"
        self._attr_unique_id = f"{DOMAIN}_{station_ind}_{sensor_key}"

        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, station_ind)},
            name=station_name,
            manufacturer="Chelyabinsk Air",
        )

    @property
    def native_value(self):
        data = self._manager.data

        station_data = data.get(self._station_ind)

        if not station_data:
            _LOGGER.debug("NO DATA for station %s", self._station_ind)
            return None

        value = station_data.get(self._sensor_key)

        _LOGGER.debug(
            "Station %s, sensor %s = %s",
            self._station_ind,
            self._sensor_key,
            value
        )

        if value in (-32768, "-32768", None, ""):
            return None

        return value