import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CMD_PORT, DEFAULT_SCAN_INTERVAL, CONF_RELOAD_ON_RECONNECT


class InsteonUartBridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(
                f"insteon_uart_bridge_{user_input[CONF_HOST]}"
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_HOST],
                data=user_input,
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): cv.string,
                    vol.Optional(CONF_PORT, default=CMD_PORT): cv.port,
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_RELOAD_ON_RECONNECT, default=False
                    ): cv.boolean,
                }
            ),
            errors=errors,
        )

    async def async_step_import(self, import_info):
        await self.async_set_unique_id(
            f"insteon_uart_bridge_{import_info[CONF_HOST]}"
        )
        for entry in self._async_current_entries():
            if entry.unique_id == self.unique_id:
                data = {**import_info}
                for key in (CONF_RELOAD_ON_RECONNECT, CONF_SCAN_INTERVAL):
                    if key in entry.data:
                        data[key] = entry.data[key]
                self.hass.config_entries.async_update_entry(entry, data=data)
                return self.async_abort(reason="updated")
        return self.async_create_entry(
            title=import_info[CONF_HOST],
            data=import_info,
        )
