This repo will be for controlling various EE equipment

I will try to keep things standard, but due to instrument differences code implementations may be different between equipment


## Supported instruments

- Siglent SPD3303X precision lab power supply
- OWON XDM1041 digital multimeter
- Texas Instruments XDS110 debug probe
- USB controlled relay module (cheap from Aliexpress)




## Communication backends

These are the communication backends currently used by the pieces of equipment

- `usb` (USB relay)
- `pyvisa` (SPD3303X)
- `serial` (XDM1041)
- `os` executing scripts (XDS110)