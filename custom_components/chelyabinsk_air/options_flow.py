"""Изменение списка станций."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlowResult, OptionsFlow

from .const import CONF_STATIONS


class ChelyabinskAirOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        from .config_flow import stations_schema, validate_stations

        errors: dict[str, str] = {}
        if user_input is not None:
            stations, errors = validate_stations(user_input)
            if not errors:
                # Перезагрузку делает update listener в __init__.py —
                # уже после того, как новые настройки сохранены.
                return self.async_create_entry(data={CONF_STATIONS: stations})

        current = self.config_entry.options.get(
            CONF_STATIONS, self.config_entry.data.get(CONF_STATIONS, [])
        )
        return self.async_show_form(
            step_id="init", data_schema=stations_schema(list(current)), errors=errors
        )
