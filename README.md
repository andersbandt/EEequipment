This repo will be for controlling various EE equipment

I will try to keep things standard, but due to instrument differences code implementations may be different between equipment


Below is a list of currently supported standard test equipment.

- **Power Supplies**: Siglent SPD3303X, HP E3640A
- **Digital Multimeters**: OWON XDM1041, Fluke 8842A, HP 3478A
- **Function Generators**: Agilent 33120A

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

There is also some capability for control of non-standard test equipment

- **Debug Probes**: TI XDS110 JTAG/SWD
- **USB Devices**: Serial ports, relay controllers

The USB relay controller is a specific cheap model readily available on Aliexpress.





### Want to add your equipment?
Check the equipment submodule README or submit an issue!



## Communication backends

These are the communication backends currently used by the pieces of equipment

- `usb` (USB relay)
- `pyvisa` (SPD3303X)
- `serial` (XDM1041)
- `os` executing scripts (XDS110)