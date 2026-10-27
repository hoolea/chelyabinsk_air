"""Интеграция «Качество воздуха Челябинска»."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import API_DEVICE_ID, CONF_STATIONS, DOMAIN
from .coordinator import AirCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


def get_stations(entry: ConfigEntry) -> list[str]:
    return list(entry.options.get(CONF_STATIONS, entry.data.get(CONF_STATIONS, [])))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = AirCoordinator(hass, entry)

    # API отвечает ~5 минут, поэтому настройку не блокируем никогда:
    # показываем кэш (или пустые сенсоры), а данные грузим в фоне.
    cached = await coordinator.async_load_cache()
    coordinator.async_set_updated_data(cached or {})
    entry.async_create_background_task(
        hass, coordinator.async_refresh(), f"{DOMAIN}_initial_refresh"
    )

    entry.runtime_data = coordinator

    _remove_stale_devices(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options))
    return True


async def _async_reload_on_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _remove_stale_devices(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Удаляет устройства (и их сенсоры) станций, которые убрали из настроек."""
    stations = set(get_stations(entry))
    registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        station_ids = {ident for domain, ident in device.identifiers if domain == DOMAIN}
        if station_ids and not station_ids & (stations | {API_DEVICE_ID}):
            _LOGGER.debug("Удаляю устройство станции %s", station_ids)
            registry.async_update_device(device.id, remove_config_entry_id=entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
