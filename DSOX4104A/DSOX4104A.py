

from EEequipment.TestEquipment import Oscilloscope
from EEequipment.TestEquipment import PyVISAHandler


class DSOX4104A(Oscilloscope):
    """
    Driver for the Keysight DSO-X 4104A InfiniiVision oscilloscope.
    Communicates via PyVISA (USB or LAN).
    """

    def __init__(self, address):
        super().__init__("DSOX4104A", PyVISAHandler(address))
        self.channel_count = 4

    def read_value(self):
        return self.test_conn()
