import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN, CONF_RELOAD_ON_RECONNECT

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN]["coordinator"]
    async_add_entities([InsteonReloadOnReconnectSwitch(hass, entry, coordinator)])


class InsteonReloadOnReconnectSwitch(SwitchEntity):
    _attr_has_entity_name = True

    def __init__(self, hass, entry, coordinator):
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.host}_reload_on_reconnect"
        self._attr_name = "Reload on Reconnect"
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.host)}}

    @property
    def is_on(self):
        return self.coordinator.reload_on_reconnect

    async def _set_state(self, value):
        self.coordinator.reload_on_reconnect = value
        data = {**self.entry.data, CONF_RELOAD_ON_RECONNECT: value}
        self.hass.config_entries.async_update_entry(self.entry, data=data)
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        await self._set_state(True)

    async def async_turn_off(self, **kwargs):
        await self._set_state(False)

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_update)
        )

    @callback
    def _handle_update(self):
        self.async_write_ha_state()
