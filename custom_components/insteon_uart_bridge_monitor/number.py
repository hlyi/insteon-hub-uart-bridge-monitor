import logging
from datetime import timedelta

from homeassistant.const import CONF_SCAN_INTERVAL, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.number import NumberEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN]["coordinator"]
    async_add_entities([InsteonPollIntervalNumber(hass, entry, coordinator)])


class InsteonPollIntervalNumber(NumberEntity):
    _attr_has_entity_name = True
    _attr_native_min_value = 5
    _attr_native_max_value = 300
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_icon = "mdi:timer"

    def __init__(self, hass, entry, coordinator):
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.host}_scan_interval"
        self._attr_name = "Poll Interval"
        self._attr_device_info = {"identifiers": {(DOMAIN, coordinator.host)}}
        self._attr_native_value = coordinator.update_interval.total_seconds()

    async def async_set_native_value(self, value):
        self.coordinator.update_interval = timedelta(seconds=value)
        data = {**self.entry.data, CONF_SCAN_INTERVAL: int(value)}
        self.hass.config_entries.async_update_entry(self.entry, data=data)
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_update)
        )

    @callback
    def _handle_update(self):
        self._attr_native_value = self.coordinator.update_interval.total_seconds()
        self.async_write_ha_state()
