# Agilent DSO1014A

4-channel, 100 MHz digital storage oscilloscope.

## Connection

Communicates over USB using the USBTMC protocol via PyVISA.

| Field       | Value              |
|-------------|--------------------|
| idVendor    | `0957`             |
| idProduct   | `0588`             |
| VISA String | `USB0::0x0957::0x0588::<serial>::INSTR` |

## Linux Setup

Non-root USB access requires a udev rule:

```bash
# /etc/udev/rules.d/99-usbtmc.rules
SUBSYSTEM=="usb", ATTR{idVendor}=="0957", ATTR{idProduct}=="0588", MODE="0666"
```

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

**Important**: Do NOT load the kernel `usbtmc` module — it conflicts with `pyvisa-py`. If it's loaded, unload it:
```bash
sudo rmmod usbtmc
```

See the main [EEequipment README](../README.md#linux-usb-permissions-udev-rules) for more details on udev rules and the `usbtmc` conflict.
