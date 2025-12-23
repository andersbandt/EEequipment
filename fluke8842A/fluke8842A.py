"""
@file     hp3478A.py
@author   Anders Bandt
@brief    class for talking to a Fluke fluke8842A
"""

# import modules
import logging
import serial

# import user created modules
from EEequipment.TestEquipment import DMM
from EEequipment.TestEquipment import PyVISAHandler

class Fluke8842A(DMM):
    def __init__(self, address):
            super().__init__("fluke8842A", PyVISAHandler(address))
            self.set_range_auto()

    def set_mode(self, mode: str):
        pass

    def set_range(self, rng: int) -> bool:
        pass

    def set_range_auto(self):
        pass