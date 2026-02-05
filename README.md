This repo will be for controlling various EE equipment

I will try to keep things standard, but due to instrument differences code implementations may be different between equipment


## Supported Equipment

### Power Supplies
- ✅ Siglent SPD3303X (PyVISA)
- ✅ HP E3640A (PyVISA)

### Digital Multimeters
- ✅ OWON XDM1041 (Serial)
- ✅ Fluke 8842A (PyVISA)
- ✅ HP 3478A (PyVISA)

### Function Generators
- ✅ Agilent 33120A (PyVISA)

### Debug Probes
- ✅ TI XDS110 JTAG/SWD

### USB Devices
- ✅ Generic serial ports (pyserial)
- ✅ USB relay controllers (pyusb)

### Want to add your equipment?
Check the equipment submodule README or submit an issue!



## Communication backends

These are the communication backends currently used by the pieces of equipment

- `usb` (USB relay)
- `pyvisa` (SPD3303X)
- `serial` (XDM1041)
- `os` executing scripts (XDS110)