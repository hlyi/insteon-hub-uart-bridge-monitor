# Insteon UART Bridge Monitor

Home Assistant custom component that monitors an Insteon UART bridge (PIC32MX695F512H firmware) via its command port.

Provides reachability, online status, firmware version sensors, and optional auto-reload of the Insteon integration when the PLM client disconnects.

## Installation (HACS)

1. Add this repository as a HACS custom repository (type: Integration)
2. Search for "Insteon UART Bridge Monitor" in HACS and install
3. Restart Home Assistant

## Configuration

Add to `configuration.yaml`:

```yaml
insteon_uart_bridge_monitor:
  host: 192.168.1.100
  port: 1984
  scan_interval: 30
  reload_on_reconnect: false
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `host` | — | Bridge IP address (required) |
| `port` | 1984 | Command port |
| `scan_interval` | 30 | Poll interval in seconds |
| `reload_on_reconnect` | false | Auto-reload Insteon integration when PLM client disconnects |

## Entities

| Entity | Description |
|--------|-------------|
| `binary_sensor.*_reachable` | Bridge responds on command port |
| `binary_sensor.*_online` | PLM client connected to port 9761 |
| `sensor.*_firmware_version` | Bridge firmware version |
| `switch.*_reload_on_reconnect` | Toggle auto-reload at runtime |
| `number.*_poll_interval` | Adjust poll interval at runtime (5–300s) |
