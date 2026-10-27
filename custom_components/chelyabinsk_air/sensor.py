"""Сенсоры станций мониторинга."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import get_stations
from .const import (
    API_DEVICE_ID,
    DOMAIN,
    MAX_DATA_AGE,
    METEO_DT_KEY,
    METEO_KEYS,
    SENSORS,
    STATIONS,
    UPDATED_KEY,
)
from .coordinator import AirCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AirCoordinator = entry.runtime_data
    entities: list[SensorEntity] = [ApiResponseTimeSensor(coordinator)]
    entities.extend(
        AirSensor(coordinator, station_ind, key)
        for station_ind in get_stations(entry)
        for key in SENSORS
    )
    async_add_entities(entities)


class AirSensor(CoordinatorEntity[AirCoordinator], SensorEntity):
    def __init__(self, coordinator: AirCoordinator, station_ind: str, sensor_key: str) -> None:
        super().__init__(coordinator)
        name, unit, device_class, state_class = SENSORS[sensor_key]
        station_name = STATIONS.get(station_ind, station_ind)

        self._station_ind = station_ind
        self._sensor_key = sensor_key

        # Имена и unique_id прежние — entity_id и история не меняются.
        self._attr_name = f"{station_name} {name}"
        self._attr_unique_id = f"{DOMAIN}_{station_ind}_{sensor_key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        if sensor_key not in METEO_KEYS:
            self._attr_icon = "mdi:molecule" if sensor_key != "max_si" else "mdi:alert-circle-outline"
            self._attr_suggested_display_precision = 1
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, station_ind)},
            name=station_name,
            manufacturer="ЕМЦ Челябинской области",
            model="Станция мониторинга",
            configuration_url="https://emc.gov74.ru",
        )

    @property
    def _station(self) -> dict[str, Any] | None:
        return (self.coordinator.data or {}).get(self._station_ind)

    def _station_updated(self):
        station = self._station or {}
        return dt_util.parse_datetime(station.get(UPDATED_KEY) or "")

    @property
    def available(self) -> bool:
        if not super().available or not self._station:
            return False
        updated = self._station_updated()
        if updated is None:
            # Кэш старой версии без метки: доверяем, пока API ни разу не ответил.
            return self.coordinator.last_api_success is None
        return dt_util.utcnow() - updated < MAX_DATA_AGE

    @property
    def native_value(self) -> float | None:
        station = self._station
        if not station:
            return None
        value = station.get(self._sensor_key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if value <= -9999:
                return None
            return value
        # совместимость со строковыми значениями из старого кэша
        try:
            value = float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return None
        return None if value <= -9999 else value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        attrs: dict[str, Any] = {}
        updated = self._station_updated()
        if updated:
            attrs["data_updated"] = updated.isoformat()
        if self._sensor_key in METEO_KEYS and self._station:
            # метеоданные на сервере обновляются раз в 6 часов
            measured = self._station.get(METEO_DT_KEY)
            if measured:
                attrs["measured_at"] = measured
        return attrs or None


class ApiResponseTimeSensor(CoordinatorEntity[AirCoordinator], SensorEntity):
    """Диагностика: сколько отвечает API (среднее видно в статистике HA)."""

    _attr_name = "Chelyabinsk Air Время ответа API"
    _attr_unique_id = f"{DOMAIN}_api_response_time"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:timer-sand"

    def __init__(self, coordinator: AirCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, API_DEVICE_ID)},
            name="Chelyabinsk Air API",
            manufacturer="ЕМЦ Челябинской области",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://emc.gov74.ru",
        )

    @property
    def available(self) -> bool:
        return self.coordinator.last_duration is not None

    @property
    def native_value(self) -> float | None:
        return self.coordinator.last_duration

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        avg = self.coordinator.average_duration
        last = self.coordinator.last_api_success
        return {
            "average_seconds": round(avg, 1) if avg is not None else None,
            "samples": len(self.coordinator.durations),
            "last_success": last.isoformat() if last else None,
            "api_ok": self.coordinator.last_update_success
            and not self.coordinator._failing,
        }
