"""
USB-201 interface — Measurement Computing USB-201 DAQ device.

Install dependencies:
    pip install uldaq

On Linux you also need the UL for Linux shared library:
    https://github.com/mccdaq/uldaq  (follow the README install steps)

USB-201 specs:
    - 8 analog inputs (12-bit, single-ended) or 4 differential pairs
    - Input ranges: ±10V, ±5V, ±2V, ±1V
    - 8 digital I/O lines (AUXPORT, bidirectional per-bit)
    - 1 counter/timer input (32-bit)
"""

from uldaq import (
    get_daq_device_inventory,
    DaqDevice,
    InterfaceType,
    AiInputMode,
    AInFlag,
    Range,
    DigitalDirection,
    DigitalPortIoType,
    DigitalPortType,
    ScanStatus,
    create_float_buffer,
)


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def find_devices():
    """Return a list of all connected MCC USB devices."""
    devices = get_daq_device_inventory(InterfaceType.USB)
    if not devices:
        raise RuntimeError("No MCC USB devices found.")
    return devices


def connect(device_index: int = 0) -> DaqDevice:
    """
    Open a connection to the USB-201.

    Args:
        device_index: Index into the list returned by find_devices().
                      Defaults to the first device found.

    Returns:
        A connected DaqDevice instance. Call disconnect() when finished.
    """
    devices = find_devices()
    if device_index >= len(devices):
        raise IndexError(
            f"Device index {device_index} out of range "
            f"({len(devices)} device(s) found)."
        )
    daq = DaqDevice(devices[device_index])
    daq.connect(connection_code=0)
    print(f"Connected: {devices[device_index].product_name} "
          f"(S/N {devices[device_index].unique_id})")
    return daq


def disconnect(daq: DaqDevice) -> None:
    """Cleanly close the device connection."""
    if daq.is_connected():
        daq.disconnect()
    daq.release()
    print("Disconnected.")


# ---------------------------------------------------------------------------
# Analog input
# ---------------------------------------------------------------------------

# Convenient range presets
RANGE_10V = Range.BIP10VOLTS   # ±10 V
RANGE_5V  = Range.BIP5VOLTS    # ±5 V
RANGE_2V  = Range.BIP2VOLTS    # ±2 V
RANGE_1V  = Range.BIP1VOLTS    # ±1 V


def read_analog(daq: DaqDevice, channel: int,
                input_mode: AiInputMode = AiInputMode.SINGLE_ENDED,
                voltage_range: Range = RANGE_10V) -> float:
    """
    Read a single analog voltage.

    Args:
        daq:           Connected DaqDevice.
        channel:       AI channel number (0–7 single-ended, 0–3 differential).
        input_mode:    AiInputMode.SINGLE_ENDED or DIFFERENTIAL.
        voltage_range: One of the RANGE_* constants above.

    Returns:
        Voltage in volts (float).
    """
    ai = daq.get_ai_device()
    return ai.a_in(channel, input_mode, voltage_range, AInFlag.DEFAULT)


def read_analog_all(daq: DaqDevice,
                    num_channels: int = 8,
                    input_mode: AiInputMode = AiInputMode.SINGLE_ENDED,
                    voltage_range: Range = RANGE_10V) -> list[float]:
    """
    Read all analog input channels in one call (channels 0 to num_channels-1).

    Returns:
        List of voltages in volts, indexed by channel number.
    """
    ai = daq.get_ai_device()
    return [
        ai.a_in(ch, input_mode, voltage_range, AInFlag.DEFAULT)
        for ch in range(num_channels)
    ]


# ---------------------------------------------------------------------------
# Digital I/O
# ---------------------------------------------------------------------------

# The USB-201 exposes one 8-bit port: AUXPORT
PORT = DigitalPortType.AUXPORT


def set_digital_direction(daq: DaqDevice, bit: int,
                          direction: DigitalDirection) -> None:
    """
    Set the direction of a single digital bit.

    Args:
        daq:       Connected DaqDevice.
        bit:       Bit number 0–7.
        direction: DigitalDirection.INPUT or OUTPUT.
    """
    dio = daq.get_dio_device()
    dio.d_config_bit(PORT, bit, direction)


def configure_port(daq: DaqDevice,
                   direction: DigitalDirection = DigitalDirection.INPUT) -> None:
    """
    Set all 8 digital bits to the same direction at once.

    Args:
        direction: DigitalDirection.INPUT or OUTPUT.
    """
    dio = daq.get_dio_device()
    # Check that the port supports per-port configuration
    port_info = dio.get_info().get_port_info(PORT)
    if port_info.port_io_type == DigitalPortIoType.BITIO:
        for bit in range(8):
            dio.d_config_bit(PORT, bit, direction)
    else:
        dio.d_config_port(PORT, direction)


def read_digital_bit(daq: DaqDevice, bit: int) -> bool:
    """
    Read a single digital input bit.

    Args:
        bit: Bit number 0–7.

    Returns:
        True if the bit is high, False if low.
    """
    dio = daq.get_dio_device()
    return bool(dio.d_bit_in(PORT, bit))


def read_digital_port(daq: DaqDevice) -> int:
    """
    Read all 8 digital bits as a single byte.

    Returns:
        Integer 0–255 representing the port state.
    """
    dio = daq.get_dio_device()
    return dio.d_in(PORT)


def write_digital_bit(daq: DaqDevice, bit: int, value: bool) -> None:
    """
    Write a single digital output bit.

    Args:
        bit:   Bit number 0–7.
        value: True for high, False for low.
    """
    dio = daq.get_dio_device()
    dio.d_bit_out(PORT, bit, int(value))


def write_digital_port(daq: DaqDevice, value: int) -> None:
    """
    Write all 8 digital output bits at once.

    Args:
        value: Integer 0–255.
    """
    if not 0 <= value <= 255:
        raise ValueError(f"Port value must be 0–255, got {value}.")
    dio = daq.get_dio_device()
    dio.d_out(PORT, value)


# ---------------------------------------------------------------------------
# Counter input
# ---------------------------------------------------------------------------

def read_counter(daq: DaqDevice, counter_num: int = 0) -> int:
    """
    Read the 32-bit event counter.

    Args:
        counter_num: Counter index (USB-201 has one counter, index 0).

    Returns:
        Current count value.
    """
    ctr = daq.get_ctr_device()
    return ctr.c_in(counter_num)


def reset_counter(daq: DaqDevice, counter_num: int = 0) -> None:
    """Reset the counter to zero."""
    ctr = daq.get_ctr_device()
    ctr.c_load(counter_num, 0)


# ---------------------------------------------------------------------------
# Context manager wrapper for convenient use
# ---------------------------------------------------------------------------

class USB201:
    """
    Context-manager wrapper around a connected USB-201.

    Usage:
        with USB201() as daq:
            v = daq.read_analog(0)
            print(f"CH0 = {v:.4f} V")
    """

    def __init__(self, device_index: int = 0):
        self._index = device_index
        self._daq: DaqDevice | None = None

    def __enter__(self) -> "USB201":
        self._daq = connect(self._index)
        return self

    def __exit__(self, *_):
        if self._daq:
            disconnect(self._daq)

    # Expose module-level functions as methods for convenience
    def read_analog(self, channel: int,
                    input_mode: AiInputMode = AiInputMode.SINGLE_ENDED,
                    voltage_range: Range = RANGE_10V) -> float:
        return read_analog(self._daq, channel, input_mode, voltage_range)

    def read_analog_all(self, num_channels: int = 8,
                        input_mode: AiInputMode = AiInputMode.SINGLE_ENDED,
                        voltage_range: Range = RANGE_10V) -> list[float]:
        return read_analog_all(self._daq, num_channels, input_mode, voltage_range)

    def set_digital_direction(self, bit: int, direction: DigitalDirection) -> None:
        set_digital_direction(self._daq, bit, direction)

    def configure_port(self, direction: DigitalDirection = DigitalDirection.INPUT) -> None:
        configure_port(self._daq, direction)

    def read_digital_bit(self, bit: int) -> bool:
        return read_digital_bit(self._daq, bit)

    def read_digital_port(self) -> int:
        return read_digital_port(self._daq)

    def write_digital_bit(self, bit: int, value: bool) -> None:
        write_digital_bit(self._daq, bit, value)

    def write_digital_port(self, value: int) -> None:
        write_digital_port(self._daq, value)

    def read_counter(self, counter_num: int = 0) -> int:
        return read_counter(self._daq, counter_num)

    def reset_counter(self, counter_num: int = 0) -> None:
        reset_counter(self._daq, counter_num)


# ---------------------------------------------------------------------------
# Quick demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("MCC USB-201 demo")
    print("Available devices:", [d.product_name for d in find_devices()])

    with USB201() as daq:
        # Analog: read all 8 channels
        print("\nAnalog inputs (±10 V, single-ended):")
        voltages = daq.read_analog_all()
        for ch, v in enumerate(voltages):
            print(f"  CH{ch}: {v:+.4f} V")

        # Digital: configure all bits as inputs, then read
        daq.configure_port(DigitalDirection.INPUT)
        port_val = daq.read_digital_port()
        print(f"\nDigital port (AUXPORT): 0x{port_val:02X}  ({port_val:08b}b)")
        for bit in range(8):
            print(f"  Bit {bit}: {'HIGH' if (port_val >> bit) & 1 else 'LOW'}")

        # Counter
        count = daq.read_counter()
        print(f"\nCounter 0: {count}")
