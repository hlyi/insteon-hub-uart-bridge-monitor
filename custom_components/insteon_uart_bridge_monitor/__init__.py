import asyncio
import logging
import time
from datetime import timedelta

import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import device_registry
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CMD_PORT,
    CMD_BRIDGE_STATUS,
    CMD_VERSION,
    DEFAULT_SCAN_INTERVAL,
    CONF_RELOAD_ON_RECONNECT,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT, default=CMD_PORT): cv.port,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.positive_int,
                vol.Optional(CONF_RELOAD_ON_RECONNECT, default=False): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType):
    conf = config.get(DOMAIN)
    if conf is None:
        return True

    hass.data.setdefault(DOMAIN, {})
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "import"}, data=conf
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    conf = {**entry.data}

    host = conf[CONF_HOST]
    port = conf.get(CONF_PORT, CMD_PORT)
    interval = conf.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    reload_on_reconnect = conf.get(CONF_RELOAD_ON_RECONNECT, False)

    dr = device_registry.async_get(hass)
    device = dr.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, host)},
        name=f"Insteon UART Bridge ({host})",
        manufacturer="YiLabs",
        model="Insteon UART Bridge",
        sw_version="1.0",
    )
    dr.async_update_device(device.id, configuration_url=None)

    async def _poll_once(fetch_version: bool) -> dict:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=5
            )
        except (asyncio.TimeoutError, OSError, ConnectionError) as exc:
            _LOGGER.debug("connect failed: %s", exc)
            return {"reachable": False, "online": False, "version": None}
        version_raw = None
        status_raw = None
        try:
            if fetch_version:
                writer.write(CMD_VERSION.encode() + b"\n")
                await writer.drain()
                version_raw = await asyncio.wait_for(reader.readline(), timeout=5)
                _LOGGER.debug("version raw: %s", version_raw)
                await asyncio.sleep(0.2)
            writer.write(CMD_BRIDGE_STATUS.encode() + b"\n")
            await writer.drain()
            status_raw = await asyncio.wait_for(reader.readline(), timeout=5)
            _LOGGER.debug("bridge_status raw: %s", status_raw)
        except (asyncio.TimeoutError, OSError, ConnectionError) as exc:
            _LOGGER.debug("cmd failed: %s", exc)
        finally:
            writer.close()
            await writer.wait_closed()
        if version_raw is None and fetch_version:
            return {"reachable": False, "online": False, "version": None}
        return {
            "reachable": True,
            "online": status_raw is not None and status_raw.decode(errors="replace").strip() == "online",
            "version": version_raw.decode(errors="replace").strip() if version_raw else None,
        }

    def _reset_entry_state_to_not_loaded(entry):
        if entry.state is ConfigEntryState.NOT_LOADED:
            return
        try:
            entry.state = ConfigEntryState.NOT_LOADED
            _LOGGER.debug("state: direct assignment succeeded")
            return
        except AttributeError:
            pass
        _LOGGER.debug("state: trying object.__setattr__ bypass")
        object.__setattr__(entry, 'state', ConfigEntryState.NOT_LOADED)
        if entry.state is ConfigEntryState.NOT_LOADED:
            _LOGGER.debug("state: object.__setattr__ on 'state' worked")
            return
        for field in ('_state', '_ConfigEntry__state', '__state'):
            if not hasattr(entry, field):
                continue
            _LOGGER.debug("state: trying backing field '%s'", field)
            object.__setattr__(entry, field, ConfigEntryState.NOT_LOADED)
            if entry.state is ConfigEntryState.NOT_LOADED:
                _LOGGER.debug("state: backing field '%s' worked", field)
                return

    async def _reload_insteon():
        domains = ("insteon", "insteon_hub", "insteon_plm")
        entry = None
        for domain in domains:
            for e in hass.config_entries.async_entries(domain):
                if e.data.get("host") == host:
                    entry = e
                    break
            if entry:
                break
        if entry is None:
            _LOGGER.warning("reload_on_reconnect: no insteon config entry found for host %s", host)
            return
        _LOGGER.info(
            "reloading insteon config entry '%s' (state=%s)",
            entry.entry_id, entry.state,
        )
        try:
            if entry.state is ConfigEntryState.LOADED:
                result = await hass.config_entries.async_reload(entry.entry_id)
                if result:
                    return
            _reset_entry_state_to_not_loaded(entry)
            await hass.config_entries.async_setup(entry.entry_id)
            _LOGGER.info("insteon re-setup succeeded")
            coordinator.last_reload_time = time.monotonic()
            coordinator.async_request_refresh()
        except Exception as exc:
            _LOGGER.warning("insteon re-setup: %s", exc)

    async def async_update_data():
        prev = coordinator.data if coordinator.data else {}
        was_reachable = prev.get("reachable", False)
        has_version = prev.get("version") is not None
        fetch_version = not has_version or not was_reachable
        result = await _poll_once(fetch_version)
        if not fetch_version and result.get("version") is None:
            result["version"] = prev.get("version")
        reachable = result.get("reachable", False)
        online = result.get("online", False)
        coordinator.poll_count = coordinator.poll_count + 1
        since_reload = time.monotonic() - getattr(coordinator, 'last_reload_time', -120)
        should_reload = (
            coordinator.reload_on_reconnect
            and coordinator.poll_count >= 2
            and reachable
            and not online
            and since_reload > 120
        )
        _LOGGER.debug(
            "poll: reachable=%s online=%s reload=%s polls=%s trigger=%s",
            reachable, online,
            coordinator.reload_on_reconnect, coordinator.poll_count, should_reload,
        )
        if should_reload:
            _LOGGER.info("bridge reachable + no plm client, triggering insteon reload")
            hass.async_create_task(_reload_insteon())
        return result

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=interval),
    )
    coordinator.reload_on_reconnect = reload_on_reconnect
    coordinator.host = host
    coordinator.device_id = device.id
    coordinator.poll_count = 0

    hass.data[DOMAIN]["coordinator"] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["binary_sensor", "sensor", "switch", "number"])
    await coordinator.async_refresh()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_unload_platforms(entry, ["binary_sensor", "sensor", "switch"])
    hass.data[DOMAIN].pop("coordinator", None)
    return True
