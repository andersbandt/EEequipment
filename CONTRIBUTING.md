# Contributing a New Equipment Driver

This guide walks through adding support for a new instrument. The process is the same regardless of equipment type.

## Overview

Each driver needs:
1. A directory named after the model (e.g., `MyScope2000/`)
2. A `config.ini` with connection settings and commands
3. A Python file with a class that extends the appropriate base class
4. An `__init__.py` that exports the class

## Step 1: Create the Directory

```
EEequipment/
    MyScope2000/
        __init__.py
        MyScope2000.py
        config.ini
```

## Step 2: Write the config.ini

The config file has two parts: a connection section and a command section.

### For PyVISA instruments (USB-TMC, LAN, GPIB)

```ini
[pyvisa]
timeout = 5000
write_termination = \n
read_termination = \n

[command]
# IEEE 488.2 common commands
query = *IDN?
reset = *RST
clear = *CLS

# Equipment-specific commands
set_voltage = CH{channel}:VOLTage {value}
get_voltage = CH{channel}:VOLTage?
```

### For serial instruments

```ini
[serial]
baudrate = 115200
timeout = 0.5

[command]
query = *IDN?
read = MEAS?
mode_vdc = CONF:VOLT:DC
```

### Command placeholders

Use Python `str.format()` syntax for variable parts:

```ini
# Single placeholder
set_voltage = VOLT {value}

# Multiple placeholders
set_channel_voltage = CH{channel}:VOLT {value}

# No placeholders (static command)
reset = *RST
```

These get filled in at runtime:
```python
cmd = registry.format_command("MyModel", "command", "set_channel_voltage", channel=1, value=3.3)
# Result: "CH1:VOLT 3.3"
```

## Step 3: Choose Your Base Class

Pick the base class that matches your equipment type:

| Equipment Type | Base Class | Import |
|---------------|------------|--------|
| Power Supply | `PowerSupply` | `from EEequipment.TestEquipment import PowerSupply` |
| Digital Multimeter | `DMM` | `from EEequipment.TestEquipment import DMM` |
| Function Generator | `FunctionGenerator` | `from EEequipment.TestEquipment import FunctionGenerator` |
| Oscilloscope | `Oscilloscope` | `from EEequipment.TestEquipment import Oscilloscope` |

Each base class provides common methods so you don't have to reimplement them. For example, `PowerSupply` already has `set_voltage()`, `get_voltage()`, `output_on()`, `output_off()`, etc. These work automatically as long as your `config.ini` has the matching command names.

### Required config.ini command names by base class

**All equipment** (from `TestEquipment`):
- `query` - Identity query (typically `*IDN?`)
- `clear` - Clear status

**PowerSupply** expects:
- `set_voltage`, `get_set_voltage`, `get_voltage`
- `set_current`, `get_set_current`, `get_current`
- `get_power`
- `output_on`, `output_off`
- `check_error`

**DMM** expects:
- `read` - Take a measurement
- `mode_vdc`, `mode_vac`, `mode_idc`, `mode_iac`, `mode_res_2`, `mode_res_4`
- `get_mode`, `range_auto`, `get_range`
- `sample_slow`, `sample_medium`, `sample_fast`

**FunctionGenerator** expects:
- `set_frequency`, `set_duty`, `set_offset`, `set_amplitude`

**Oscilloscope** requires abstract methods to be implemented in your driver (see Step 4).

## Step 4: Write the Driver Class

### Minimal example (Power Supply)

If the base class methods and config commands are sufficient, the driver can be very short:

```python
from EEequipment.TestEquipment import PowerSupply, PyVISAHandler

class MyPS1000(PowerSupply):
    def __init__(self, address):
        super().__init__("MyPS1000", PyVISAHandler(address))
        self.channel_count = 2

    def check_status(self):
        """Required abstract method - return dict with channel modes/states."""
        response = self.query("SYSTem:STATus?")
        return {
            "ch1_mode": "CV",
            "ch1_state": "ON" if "1" in response else "OFF",
            "ch2_mode": "CV",
            "ch2_state": "ON" if "2" in response else "OFF",
        }
```

**Important**: The first argument to `super().__init__()` must match your directory name exactly. This is how the `CommandRegistry` finds your `config.ini`.

### Example with custom methods (Oscilloscope)

Oscilloscopes have abstract methods that must be implemented:

```python
from EEequipment.TestEquipment import Oscilloscope, PyVISAHandler

class MyScope2000(Oscilloscope):
    def __init__(self, address):
        super().__init__("MyScope2000", PyVISAHandler(address))
        self.channel_count = 4

    def _cmd(self, cmd_name, **kwargs):
        """Helper to format a command from the registry."""
        return self.registry.format_command(self.model, "command", cmd_name, **kwargs)

    # --- Required abstract methods ---

    def check_channel(self, channel):
        if channel not in range(1, self.channel_count + 1):
            raise ValueError(f"Channel must be 1-{self.channel_count}")

    def run(self):
        self.conn.write(self._cmd("acq_run"))

    def stop(self):
        self.conn.write(self._cmd("acq_stop"))

    def single(self):
        self.conn.write(self._cmd("acq_single"))

    def measure_frequency(self, channel):
        self.check_channel(channel)
        return float(self.conn.query(self._cmd("measure_freq", channel=channel)))

    def measure_vpp(self, channel):
        self.check_channel(channel)
        return float(self.conn.query(self._cmd("measure_vpp", channel=channel)))

    def set_scale(self, channel, scale):
        self.check_channel(channel)
        self.conn.write(self._cmd("chan_scale", channel=channel, scale=scale))

    def set_offset(self, channel, offset):
        self.check_channel(channel)
        self.conn.write(self._cmd("chan_offset", channel=channel, offset=offset))

    def set_trigger_level(self, channel, level):
        self.check_channel(channel)
        self.conn.write(self._cmd("trig_level", channel=channel, level=level))

    def get_waveform_data(self, channel, points=0, fmt="BYTE"):
        # Implement waveform capture for your scope
        pass
```

### Serial instrument example (DMM)

```python
from EEequipment.TestEquipment import DMM, SerialHandler

class MyDMM500(DMM):
    def __init__(self, address):
        super().__init__("MyDMM500", SerialHandler(address))

    def set_range(self, rng):
        """Required abstract method."""
        cmd = self.registry.get_command(self.model, "command", f"range_{rng}")
        self.write(cmd)
        return True
```

## Step 5: Create __init__.py

```python
from .MyScope2000 import MyScope2000
```

## Step 6: Register in equipment_manager.py (optional)

The `equipment_manager.py` auto-discovers drivers by inspecting subclasses. Your driver will be picked up automatically as long as it's imported somewhere. If you want it to appear in the GUI's equipment dropdown, make sure its `__init__.py` properly exports the class.

## Connection Handlers

| Handler | Constructor | Use When |
|---------|------------|----------|
| `PyVISAHandler(address)` | VISA resource string | USB-TMC, LAN, GPIB instruments |
| `SerialHandler(address)` | COM port / `/dev/ttyXXX` | RS-232 serial instruments |

The handler is selected in the driver's `__init__`. The handler class name (minus "Handler") determines which `config.ini` section is read for connection parameters:
- `PyVISAHandler` -> reads `[pyvisa]` section
- `SerialHandler` -> reads `[serial]` section

## Testing Your Driver

Without hardware:
- Verify `config.ini` loads without errors (the `CommandRegistry` will print errors for malformed entries)
- Check that all command placeholders match your method calls

With hardware:
```python
from EEequipment.MyScope2000 import MyScope2000

scope = MyScope2000("USB0::0x0957::0x1790::MY12345678::INSTR")
print(scope.test_conn())   # Should return *IDN? response
print(scope.status)        # Should be True
scope.disconnect()
```

## Tips

- Copy an existing driver that's similar to your instrument as a starting point
- Check your instrument's programmer's guide for the exact SCPI command syntax
- The `_cmd()` helper pattern (used in DSOX4104A/DSO1014A) keeps methods clean
- Use `self.conn.query()` for commands that return data, `self.conn.write()` for commands that don't
- Set `self.channel_count` in `__init__` so channel validation works correctly
- The SPD3303X driver is the most complete reference for power supplies
- The DSOX4104A driver is the most complete reference for oscilloscopes
