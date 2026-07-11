import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN]["coordinator"]
    entity = InsteonUartBridgeVersionSensor(coordinator)
    if coordinator.data:
        entity._attr_native_value = coordinator.data.get("version")
    async_add_entities([entity])


class InsteonUartBridgeVersionSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:chip"

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.host}_version"
        self._attr_name = "Firmware Version"
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.host)}}
        self._attr_native_value = None

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_update)
        )

    @callback
    def _handle_update(self):
        if self.coordinator.data:
            self._attr_native_value = self.coordinator.data.get("version")
        self.async_write_ha_state()
