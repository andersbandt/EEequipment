

from EEequipment.TestEquipment import Oscilloscope
from EEequipment.TestEquipment import PyVISAHandler


class DSO1014A(Oscilloscope):
    """
    Driver for the Keysight DSO 1014A oscilloscope.
    Communicates via PyVISA (USB or LAN).
    """

    def __init__(self, address):
        super().__init__("DSO1014A", PyVISAHandler(address))
        self.channel_count = 4

    def _send_cmd(self, cmd):
        """Send command then restore local front-panel control."""
        super()._send_cmd(cmd)
        self.conn.write(self._cmd("unlock_local"))

    def read_value(self):
        return self.measure_vavg(self, 1) # tag:HARDCODE
