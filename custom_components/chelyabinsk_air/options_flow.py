import voluptuous as vol
import logging

from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv

from .const import STATIONS

_LOGGER = logging.getLogger(__name__)


class ChelyabinskAirOptionsFlow(config_entries.OptionsFlow):

    async def async_step_init(self, user_input=None):
        _LOGGER.debug("Options flow started")

        if user_input is not None:
            _LOGGER.debug("User selected stations: %s", user_input["stations"])

            valid_stations = [
                s for s in user_input["stations"]
                if s in STATIONS
            ]

            entry = self.async_create_entry(
                title="",
                data={"stations": valid_stations}
            )

            self.hass.async_create_task(
                self.hass.config_entries.async_reload(self.config_entry.entry_id)
            )

            return entry

        current_stations = self.config_entry.options.get(
            "stations",
            self.config_entry.data.get("stations", [])
        )

        _LOGGER.debug("Current stations: %s", current_stations)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    "stations",
                    default=current_stations
                ): cv.multi_select(STATIONS)
            }),
        )