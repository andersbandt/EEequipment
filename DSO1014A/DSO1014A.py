

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
