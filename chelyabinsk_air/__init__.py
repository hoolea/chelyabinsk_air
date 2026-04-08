import asyncio
import logging
from datetime import timedelta

import aiohttp
import json

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.storage import Store
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .options_flow import ChelyabinskAirOptionsFlow

from .const import DOMAIN, SENSOR_MAP

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

API_URL = "https://emc.gov74.ru/uisem/portal/ad/services/getData.php?d=now&t=chelyabinsk-1"

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_data"


def build_station_name(st):
    return f"{st['name']}, №{st['nom']}, {st['place']}"


class AirDataManager:
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.data = {}
        self.store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._lock = asyncio.Lock()

    async def async_load(self):
        _LOGGER.debug("Loading data from storage")

        stored = await self.store.async_load()

        if stored:
            self.data = stored
            _LOGGER.info("Loaded data from storage (%d stations)", len(stored))
        else:
            _LOGGER.warning("No stored data found")

    async def async_save(self):
        await self.store.async_save(self.data)

    async def update_from_api(self):
        async with self._lock:
            _LOGGER.debug("Starting API update")

            try:
                session = async_get_clientsession(self.hass)
                timeout = aiohttp.ClientTimeout(total=600)

                _LOGGER.debug("Requesting API: %s", API_URL)

                async with session.get(API_URL, timeout=timeout) as resp:
                    _LOGGER.debug("Response status: %s", resp.status)
                    _LOGGER.debug("Response headers: %s", dict(resp.headers))

                    text = await resp.text()

                    _LOGGER.debug("Response size: %d bytes", len(text))

                    if text.strip().startswith("<"):
                        _LOGGER.error("API returned HTML instead of JSON")
                        _LOGGER.debug("Response preview: %s", text[:500])
                        raise ValueError("HTML instead of JSON")
                        
                    _LOGGER.debug("Raw response: %s", text[:300])
                    
                    try:
                        raw = json.loads(text)
                    except Exception as e:
                        _LOGGER.error("JSON decode failed: %s", e)
                        _LOGGER.debug("Response preview: %s", text[:500])
                        raise

                parsed = self._parse(raw)

                _LOGGER.debug("Parsed stations: %d", len(parsed))

                self.data = parsed

                await self.async_save()

                _LOGGER.info("Data successfully updated from API")

            except asyncio.TimeoutError:
                _LOGGER.error("API request timeout (60s)")
                _LOGGER.warning("Using cached data")

            except Exception as e:
                _LOGGER.error("API update failed: %s", e, exc_info=True)

                if self.data:
                    _LOGGER.warning("Fallback to cached data")

    def _parse(self, raw):
        result = {}

        for block in raw.get("data", []):
            for st in block.get("stations", []):
                ind = st.get("ind")

                if not ind:
                    continue

                if ind not in result:
                    result[ind] = {}

                # --- загрязнения ---
                for s in st.get("si", []):
                    key = SENSOR_MAP.get(s["name"])
                    if key:
                        result[ind][key] = s.get("val")

                # --- метео ---
                names = st.get("meteoParamsNames", [])
                values = st.get("meteoParamsValues", [])

                if values:
                    last = values[-1]["vals"]

                    for i, param in enumerate(names):
                        key = SENSOR_MAP.get(param.strip('"'))
                        if key and i < len(last):
                            result[ind][key] = last[i]
        return result


class AirCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, manager: AirDataManager):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=3),
        )
        self.manager = manager

    async def _async_update_data(self):
        return self.manager.data


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    manager = AirDataManager(hass)
    await manager.async_load()

    coordinator = AirCoordinator(hass, manager)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "manager": manager,
        "coordinator": coordinator,
    }
    stations = entry.options.get("stations", entry.data.get("stations", []))
    _LOGGER.debug("Configured stations: %s", stations)
    
    async def periodic_update():
        _LOGGER.info("Background update task started")

        while True:
            _LOGGER.debug("Background update triggered")

            await manager.update_from_api()

            _LOGGER.debug("Sleeping 10 minutes")

            await asyncio.sleep(600)

    hass.loop.create_task(periodic_update())

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await coordinator.async_refresh()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
