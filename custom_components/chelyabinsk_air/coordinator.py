"""Получение и разбор данных с emc.gov74.ru."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_URL,
    DOMAIN,
    FAST_FAIL_SECONDS,
    INVALID_VALUE_THRESHOLD,
    LOCAL_TZ,
    METEO_DT_KEY,
    METEO_MAX_AGE,
    RECENT_SECONDS,
    MIN_PAUSE,
    PRESSURE_RANGE_MMHG,
    REQUEST_TIMEOUT,
    RETRY_DELAY,
    SENSOR_MAP,
    STORAGE_KEY,
    STORAGE_VERSION,
    TARGET_CYCLE,
    UPDATED_KEY,
)

_LOGGER = logging.getLogger(__name__)

StationsData = dict[str, dict[str, Any]]

HPA_TO_MMHG = 0.750062


def _normalize_name(name: Any) -> str:
    """Убирает лишние кавычки/пробелы из названия параметра."""
    if not isinstance(name, str):
        return ""
    return " ".join(name.strip().strip('"').strip().split())


def _to_number(value: Any) -> float | None:
    """Приводит значение API к числу; служебные/битые значения -> None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
        if not value:
            return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number <= INVALID_VALUE_THRESHOLD:  # NaN или -32768
        return None
    return number


def _normalize_pressure(value: float | None) -> float | None:
    """Часть станций (ГНС, Магнитогорск) отдаёт гПа вместо мм рт. ст."""
    if value is None:
        return None
    if value > 900:
        value = round(value * HPA_TO_MMHG, 1)
    low, high = PRESSURE_RANGE_MMHG
    return value if low <= value <= high else None  # битый датчик


def _parse_dt(value: Any) -> datetime | None:
    """'2026-10-27_13:00' (местное время) -> aware datetime."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d_%H:%M").replace(tzinfo=LOCAL_TZ)
    except ValueError:
        return None


def parse_response(raw: Any, now: datetime | None = None) -> StationsData:
    """Разбирает ответ API в {ind: {sensor_key: value}}."""
    now = now or dt_util.utcnow()
    result: StationsData = {}
    if not isinstance(raw, dict):
        raise ValueError(f"Неожиданный формат ответа: {type(raw).__name__}")

    blocks = raw.get("data") or []
    if not isinstance(blocks, list):
        raise ValueError("Поле 'data' не является списком")

    for block in blocks:
        if not isinstance(block, dict):
            continue
        for st in block.get("stations") or []:
            if not isinstance(st, dict):
                continue
            ind = st.get("ind")
            if ind in (None, ""):
                continue
            station = result.setdefault(str(ind), {})

            # --- загрязнения (стандартный индекс) ---
            for item in st.get("si") or []:
                if not isinstance(item, dict):
                    continue
                key = SENSOR_MAP.get(_normalize_name(item.get("name")))
                if not key:
                    continue
                value = _to_number(item.get("val"))
                if value is not None or key not in station:
                    station[key] = value

            max_si = _to_number(st.get("maxSi"))
            if max_si is not None or "max_si" not in station:
                station["max_si"] = max_si

            # --- метео: строки раз в 6 часов, от старых к новым ---
            names = st.get("meteoParamsNames") or []
            rows = st.get("meteoParamsValues") or []
            keys = [SENSOR_MAP.get(_normalize_name(n)) for n in names]
            for key in keys:
                if key:
                    station.setdefault(key, None)

            newest_dt: datetime | None = None
            for pos, row in enumerate(reversed(rows)):
                if not isinstance(row, dict) or not isinstance(row.get("vals"), list):
                    continue
                row_dt = _parse_dt(row.get("dt"))
                if row_dt is None and pos > 0:
                    continue
                if row_dt is not None and now - row_dt > METEO_MAX_AGE:
                    break  # дальше только ещё более старые строки
                vals = row["vals"]
                used = False
                for i, key in enumerate(keys):
                    if not key or i >= len(vals) or station.get(key) is not None:
                        continue
                    value = _to_number(vals[i])
                    if key == "pressure":
                        value = _normalize_pressure(value)
                    if value is not None:
                        station[key] = value
                        used = True
                if used and newest_dt is None and row_dt is not None:
                    newest_dt = row_dt
                if all(not k or station.get(k) is not None for k in keys):
                    break
            if newest_dt is not None:
                station[METEO_DT_KEY] = newest_dt.isoformat()

    return result


def _extract_json(body: bytes) -> Any:
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = body.decode("cp1251", errors="replace")
    text = text.strip()
    if not text:
        raise ValueError("пустой ответ")
    if text.startswith("<"):
        # JSON, обёрнутый в HTML (так бывает у прокси/браузеров) — достаём его
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("сервер вернул HTML вместо JSON")
        text = text[start : end + 1]
    return json.loads(text)


class AirCoordinator(DataUpdateCoordinator[StationsData]):
    """Опрашивает медленный API примерно раз в TARGET_CYCLE."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=TARGET_CYCLE,
        )
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._session = async_get_clientsession(hass)
        self._inflight: asyncio.Future[StationsData] | None = None
        self._finished_at: float | None = None
        self._failing = False
        self.last_api_success: datetime | None = None
        self.last_duration: float | None = None
        self.durations: deque[float] = deque(maxlen=30)

    @property
    def average_duration(self) -> float | None:
        return sum(self.durations) / len(self.durations) if self.durations else None

    async def async_load_cache(self) -> StationsData | None:
        """Загружает кэш с диска (поддерживает и старый формат 1.0.0)."""
        try:
            stored = await self._store.async_load()
        except Exception as err:  # noqa: BLE001 — битый кэш не должен ронять интеграцию
            _LOGGER.warning("Не удалось прочитать кэш: %s", err)
            return None
        if not stored or not isinstance(stored, dict):
            return None
        if isinstance(stored.get("stations"), dict):
            stations = stored["stations"]
            self.last_api_success = dt_util.parse_datetime(stored.get("updated") or "")
            self.durations.extend(stored.get("durations") or [])
            self.last_duration = self.durations[-1] if self.durations else None
        else:  # старый формат: словарь станций целиком
            stations = stored
        _LOGGER.debug("Из кэша загружено станций: %d", len(stations))
        return stations or None

    async def _async_save_cache(self, data: StationsData) -> None:
        await self._store.async_save(
            {
                "updated": self.last_api_success.isoformat() if self.last_api_success else None,
                "durations": list(self.durations),
                "stations": data,
            }
        )

    async def _async_fetch_once(self) -> Any:
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT, sock_connect=30)
        async with self._session.get(API_URL, timeout=timeout) as resp:
            resp.raise_for_status()
            body = await resp.read()
        return _extract_json(body)

    async def _async_fetch(self) -> Any:
        for attempt in (1, 2):
            started = time.monotonic()
            try:
                raw = await self._async_fetch_once()
            except asyncio.TimeoutError as err:
                raise UpdateFailed(f"API не ответил за {REQUEST_TIMEOUT} с") from err
            except (aiohttp.ClientError, ValueError) as err:
                elapsed = time.monotonic() - started
                if attempt == 1 and elapsed < FAST_FAIL_SECONDS:
                    _LOGGER.debug("Запрос упал за %.0f с (%r), повтор через %d с",
                                  elapsed, err, RETRY_DELAY)
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                raise UpdateFailed(f"API недоступен: {err!r}") from err

            duration = time.monotonic() - started
            self.last_duration = round(duration, 1)
            self.durations.append(self.last_duration)
            _LOGGER.debug(
                "API ответил за %.0f с (среднее по %d запросам: %.0f с)",
                duration, len(self.durations), self.average_duration,
            )
            return raw
        raise UpdateFailed("API недоступен")  # недостижимо

    def _schedule_from_start(self, started: float) -> None:
        """Следующий запрос — через TARGET_CYCLE от начала текущего."""
        elapsed = time.monotonic() - started
        pause = max(MIN_PAUSE.total_seconds(), TARGET_CYCLE.total_seconds() - elapsed)
        self.update_interval = timedelta(seconds=pause)

    async def _async_update_data(self) -> StationsData:
        # Запрос идёт ~5 минут. Если обновление попросили, пока он уже идёт
        # (плановое + ручное, перезагрузка и т.п.), ждём тот же запрос,
        # а не запускаем второй параллельно.
        if (
            self.data
            and self._finished_at is not None
            and time.monotonic() - self._finished_at < RECENT_SECONDS
            and (self._inflight is None or self._inflight.done())
        ):
            # Запрос только что завершился (обновление стояло в очереди) —
            # свежее данных всё равно не будет, не грузим сервер повторно.
            return self.data
        if self._inflight is None or self._inflight.done():
            self._inflight = self.config_entry.async_create_background_task(
                self.hass, self._async_update_cycle(), f"{DOMAIN}_fetch"
            )
        return await asyncio.shield(self._inflight)

    async def _async_update_cycle(self) -> StationsData:
        started = time.monotonic()
        try:
            return await self._async_update_locked()
        finally:
            self._finished_at = time.monotonic()
            self._schedule_from_start(started)

    async def _async_update_locked(self) -> StationsData:
        try:
            raw = await self._async_fetch()
            parsed = parse_response(raw)
            if not parsed:
                raise UpdateFailed("API вернул пустой список станций")
        except (UpdateFailed, ValueError) as err:
            if self.data:
                # Отдаём последние данные; устаревание отслеживают сами сенсоры.
                if not self._failing:
                    _LOGGER.warning("%s — используются последние полученные данные", err)
                self._failing = True
                return self.data
            raise UpdateFailed(str(err)) from err

        if self._failing:
            _LOGGER.info("Связь с API восстановлена")
        self._failing = False

        now = dt_util.utcnow()
        self.last_api_success = now
        stamp = now.isoformat()

        merged: StationsData = dict(self.data or {})
        for ind, values in parsed.items():
            values[UPDATED_KEY] = stamp
            merged[ind] = values

        await self._async_save_cache(merged)
        return merged
