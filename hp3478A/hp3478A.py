"""
@file     hp3478A.py
@author   Anders Bandt
@brief    class for talking to a HP 3478A multimeter
"""


# import user created modules
from EEequipment.TestEquipment import DMM
from EEequipment.TestEquipment import PyVISAHandler


class HP3478A(DMM):
    def __init__(self, address):
            super().__init__("fluke8842A", PyVISAHandler(address))
            self.set_range_auto()
            self.read_value() # NOTE: this is here to prevent weird glitch where first voltage read is always "1"

    def set_mode(self, mode: str):
        pass

    def set_range(self, rng: int) -> bool:
        pass

    def set_range_auto(self):
        pass