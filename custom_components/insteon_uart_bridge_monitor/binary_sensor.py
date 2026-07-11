import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.const import STATE_ON, STATE_OFF

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN]["coordinator"]
    async_add_entities(
        [
            InsteonUartBridgeReachableSensor(coordinator),
            InsteonUartBridgeOnlineSensor(coordinator),
        ]
    )


class InsteonUartBridgeReachableSensor(BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = True

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.host}_reachable"
        self._attr_name = "Reachable"
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.host)}}

    @property
    def is_on(self):
        return self.coordinator.data and self.coordinator.data.get("reachable", False)

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_update)
        )

    @callback
    def _handle_update(self):
        self.async_write_ha_state()


class InsteonUartBridgeOnlineSensor(BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = True

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.host}_online"
        self._attr_name = "Online"
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.host)}}

    @property
    def is_on(self):
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("online", False)

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_update)
        )

    @callback
    def _handle_update(self):
        self.async_write_ha_state()
