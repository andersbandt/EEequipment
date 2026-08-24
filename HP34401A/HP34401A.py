from EEequipment.TestEquipment import DMM, SerialHandler


class HP34401A(DMM):
    """
    HP/Agilent 34401A 6.5-digit multimeter over RS-232.

    Mode is set with CONF commands (auto-range by default).
    set_range() and set_range_auto() are mode-aware — call set_mode() first.
    """

    # 1-based index → physical range value, keyed by mode string
    _RANGES = {
        "VDC":       [0.1, 1, 10, 100, 1000],
        "VAC":       [0.1, 1, 10, 100, 750],
        "IDC":       [0.01, 0.1, 1, 3],
        "IAC":       [0.01, 0.1, 1, 3],
        "RES_2WIRE": [100, 1e3, 10e3, 100e3, 1e6, 10e6, 100e6],
        "RES_4WIRE": [100, 1e3, 10e3, 100e3, 1e6, 10e6, 100e6],
    }

    # mode string → SCPI range node prefix
    _RANGE_PREFIX = {
        "VDC":       "SENS:VOLT:DC:RANG",
        "VAC":       "SENS:VOLT:AC:RANG",
        "IDC":       "SENS:CURR:DC:RANG",
        "IAC":       "SENS:CURR:AC:RANG",
        "RES_2WIRE": "SENS:RES:RANG",
        "RES_4WIRE": "SENS:FRES:RANG",
    }

    def __init__(self, address):
        super().__init__("HP34401A", SerialHandler(address))
        self.set_range_auto()

    def set_range(self, rng: int) -> bool:
        """Set range by 1-based index for the current measurement mode.

        Returns True on success, False if mode is unknown or index is out of range.
        """
        if self.mode not in self._RANGES:
            return False
        ranges = self._RANGES[self.mode]
        if rng < 1 or rng > len(ranges):
            return False
        prefix = self._RANGE_PREFIX[self.mode]
        self.write(f"{prefix} {ranges[rng - 1]}")
        return True

    def set_range_auto(self):
        """Enable auto-range for the current measurement mode (default: VDC)."""
        prefix = self._RANGE_PREFIX.get(self.mode, "SENS:VOLT:DC:RANG")
        self.write(f"{prefix}:AUTO 1")
