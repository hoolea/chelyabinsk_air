import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
from .options_flow import ChelyabinskAirOptionsFlow
from .const import DOMAIN, STATIONS


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    @staticmethod
    def async_get_options_flow(config_entry):
        return ChelyabinskAirOptionsFlow()
        
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Chelyabinsk Air", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("stations"): cv.multi_select(STATIONS)
            })
        )
