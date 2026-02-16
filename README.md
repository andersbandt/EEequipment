This repo will be for controlling various EE equipment

I will try to keep things standard, but due to instrument differences code implementations may be different between equipment

## Supported Equipment
Below is a list of currently supported standard test equipment.

- **Power Supplies**: Siglent SPD3303X, HP E3640A
- **Digital Multimeters**: OWON XDM1041, Fluke 8842A, HP 3478A
- **Function Generators**: Agilent 33120A
- **Oscilloscopes**: Keysight DSOX4104A, Agilent DSO1014A

There is also some capability for control of non-standard test equipment

- **Debug Probes**: TI XDS110 JTAG/SWD
- **USB Devices**: Serial ports, relay controllers

The USB relay controller is a specific cheap model readily available on Aliexpress.


### Linux USB Permissions (udev rules)

USBTMC instruments (oscilloscopes, power supplies, etc.) connected over USB won't appear as `/dev/tty*` serial ports. They use the USB Test & Measurement Class protocol and are accessed via PyVISA.

By default, these devices require root permissions. To allow non-root access, create a udev rule:

```bash
# /etc/udev/rules.d/99-usbtmc.rules
# Agilent/Keysight instruments
SUBSYSTEM=="usb", ATTR{idVendor}=="0957", MODE="0666"
# Siglent instruments
SUBSYSTEM=="usb", ATTR{idVendor}=="f4ec", MODE="0666"
```

Then reload and trigger:
```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

You can find `idVendor` and `idProduct` for your device with `dmesg` or `lsusb` after plugging it in. Add additional lines for other vendors as needed.

**Important**: If using `pyvisa-py` (pure Python backend), make sure the kernel `usbtmc` module is **not** loaded — it will claim the device and block `pyvisa-py`/`libusb` from accessing it:
```bash
# Unload if currently loaded
sudo rmmod usbtmc
# Prevent it from auto-loading on boot
echo "blacklist usbtmc" | sudo tee /etc/modprobe.d/blacklist-usbtmc.conf
```

The `usbtmc` kernel module is only needed if accessing devices directly via `/dev/usbtmc0` (not through PyVISA).

After setup, verify PyVISA can see the instrument:
```python
import pyvisa
rm = pyvisa.ResourceManager()
print(rm.list_resources())
```

### Communication backends

These are the communication backends currently used by the pieces of equipment

- `usb` (USB relay)
- `pyvisa` (SPD3303X, DSOX4104A, DSO1014A, Agilent 33120A, HP E3640A)
- `serial` (XDM1041, Fluke 8842A, HP 3478A)
- `os` executing scripts (XDS110)


## Adding new equipment

Adding new equipment should be very straightforward. Each piece of test equipment will have a `config.ini` file.

For example check out a snippet of the config file for the SPD3303X power supply

```ini
[pyvisa]
timeout = 1000
write_termination = \n
read_termination = \n

[command]
set_voltage = CH{channel}:VOLTage {value}
set_current = CH{channel}:CURRent {value}
get_set_voltage = CH{channel}:VOLTage?
get_set_current = CH{channel}:CURRent?
```
You simply can copy one of the already created templates and replace the actual commands with whatever your programming manual has listed.


### Want to add your equipment?
Check the `CONTRIBUTING.md` file! It has more detail about adding equipment



