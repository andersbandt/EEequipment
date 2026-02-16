# EEequipment

A Python library for controlling electronic test equipment over Serial, PyVISA (USB/LAN), and USB HID. Commands are defined in config files rather than hardcoded, making it easy to add support for new instruments.

## Architecture

```
TestEquipment.py          # Base classes and connection handlers
equipment_manager.py      # Driver discovery and instantiation
<ModelName>/
    __init__.py
    <ModelName>.py        # Driver implementation
    config.ini            # SCPI/command definitions + connection params
```

### Core Components

**CommandRegistry** loads all `config.ini` files at startup and provides command lookup:

```python
from EEequipment.TestEquipment import get_registry

registry = get_registry()
cmd = registry.format_command("SPD3303X", "command", "set_voltage", channel=1, value=3.3)
# Returns: "CH1:VOLTage 3.3"
```

**ConnectionHandlers** abstract the communication protocol:

| Handler | Protocol | Used By |
|---------|----------|---------|
| `PyVISAHandler` | USB-TMC / LAN via PyVISA | SPD3303X, DSOX4104A, DSO1014A, Agilent33120A, E3640A, Fluke8842A, HP3478A |
| `SerialHandler` | RS-232 serial | XDM1041 |
| Raw USB HID | pyusb | USB Relay |
| Subprocess | OS commands | XDS110 |

**Base Classes** define the common interface for each equipment type:

| Base Class | Interface Methods |
|------------|-------------------|
| `TestEquipment` | `test_conn()`, `write()`, `read()`, `query()`, `disconnect()`, `benchmark()` |
| `PowerSupply` | `set_voltage()`, `get_voltage()`, `set_current()`, `get_current()`, `output_on()`, `output_off()`, `check_status()` |
| `DMM` | `read_value()`, `set_mode()`, `get_mode()`, `set_range()`, `set_range_auto()`, `set_sample_speed()` |
| `FunctionGenerator` | `set_frequency()`, `set_duty()`, `set_amplitude()`, `set_offset()` |
| `Oscilloscope` | `run()`, `stop()`, `single()`, `measure_frequency()`, `measure_vpp()`, `set_scale()`, `set_trigger_level()`, `get_waveform_data()` |

### How Connection Works

When a driver is instantiated, the base class:

1. Determines the connection type from the handler class name (e.g., `PyVISAHandler` -> looks up `[pyvisa]` section)
2. Reads connection parameters from `config.ini` (timeout, baud rate, termination characters)
3. Calls `handler.connect(config)` to establish the connection
4. The `status` property reflects whether the connection is live

```python
from EEequipment.SPD3303X import SPD3303X

ps = SPD3303X("USB0::0xF4EC::0x1430::SPD3XIDQ5R1262::INSTR")
print(ps.status)       # True if connected
print(ps.test_conn())  # Returns *IDN? response
```

## Supported Equipment

### Power Supplies

| Model | Connection | Channels | Status |
|-------|-----------|----------|--------|
| **Siglent SPD3303X** | PyVISA | 2 | Full (calibration, timers, networking) |
| **HP E3640A** | PyVISA | 1 | Functional |

### Digital Multimeters

| Model | Connection | Status |
|-------|-----------|--------|
| **OWON XDM1041** | Serial (115200) | Full (dual channels, ranges, calc functions) |
| **Fluke 8842A** | PyVISA | Stub (needs implementation) |
| **HP 3478A** | PyVISA | Stub (needs implementation) |

### Oscilloscopes

| Model | Connection | Channels | Status |
|-------|-----------|----------|--------|
| **Keysight DSOX4104A** | PyVISA | 4 | Full (measurements, waveform capture, triggers, cursors, math) |
| **Agilent DSO1014A** | PyVISA | 4 | Full (same feature set as DSOX4104A) |

### Function Generators

| Model | Connection | Channels | Status |
|-------|-----------|----------|--------|
| **Agilent 33120A** | PyVISA | 1 | Minimal (uses base class methods) |

### Other

| Device | Connection | Notes |
|--------|-----------|-------|
| **USB Relay Module** | USB HID (pyusb) | Standalone controller; supports NO/NC wiring, state tracking, relay aliasing |
| **TI XDS110** | Subprocess | JTAG/SWD debug probe; wraps CCS command-line tools |
| **Arduino** | Serial | Simple serial character send/receive |

## Linux USB Permissions (udev rules)

USBTMC instruments (oscilloscopes, power supplies, etc.) connected over USB require udev rules for non-root access:

```bash
# /etc/udev/rules.d/99-usbtmc.rules
# Agilent/Keysight instruments
SUBSYSTEM=="usb", ATTR{idVendor}=="0957", MODE="0666"
# Siglent instruments
SUBSYSTEM=="usb", ATTR{idVendor}=="f4ec", MODE="0666"
```

Reload and trigger:
```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Find your device's `idVendor` with `lsusb` or `dmesg` after plugging it in.

**Important**: If using `pyvisa-py` (pure Python backend), the kernel `usbtmc` module must be unloaded:
```bash
sudo rmmod usbtmc
echo "blacklist usbtmc" | sudo tee /etc/modprobe.d/blacklist-usbtmc.conf
```

Verify PyVISA can see the instrument:
```python
import pyvisa
rm = pyvisa.ResourceManager('@py')
print(rm.list_resources())
```

## Dependencies

- `pyvisa` + `pyvisa-py` — VISA communication backend
- `pyserial` — Serial port communication
- `pyusb` — USB HID relay control
- `libusb` — Required by pyusb (system package)

## Want to add your equipment?

See [CONTRIBUTING.md](CONTRIBUTING.md) for a step-by-step guide.
