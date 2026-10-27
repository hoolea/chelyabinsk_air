"""Настройка интеграции через UI."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import CONF_STATIONS, DOMAIN, STATIONS
from .options_flow import ChelyabinskAirOptionsFlow


def stations_schema(default: list[str] | None = None) -> vol.Schema:
    key = (
        vol.Required(CONF_STATIONS, default=default)
        if default is not None
        else vol.Required(CONF_STATIONS)
    )
    return vol.Schema({key: cv.multi_select(STATIONS)})


def validate_stations(user_input: dict[str, Any]) -> tuple[list[str], dict[str, str]]:
    stations = [s for s in user_input.get(CONF_STATIONS, []) if s in STATIONS]
    return stations, ({} if stations else {"base": "no_stations"})


class ChelyabinskAirConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> ChelyabinskAirOptionsFlow:
        return ChelyabinskAirOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            stations, errors = validate_stations(user_input)
            if not errors:
                return self.async_create_entry(
                    title="Chelyabinsk Air", data={CONF_STATIONS: stations}
                )

        return self.async_show_form(
            step_id="user", data_schema=stations_schema(), errors=errors
        )
