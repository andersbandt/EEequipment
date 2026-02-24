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
            super().__init__("hp3478A", PyVISAHandler(address))
            self.set_range_auto()
            self.read_value() # NOTE: this is here to prevent weird glitch where first voltage read is always "1"


    def set_range(self):
        pass
        # TODO: need to use this as an example for a custom range setting method

    def get_mode(self):
        status_raw = super().get_mode()
        first_byte = ord(status_raw[0])
        bits_765 = (first_byte & 0b11100000) >> 5

        if bits_765 == 1:
            rang="DC Volts"
        elif bits_765 ==2 :
            rang="AC Volts"
        elif bits_765 == 3:
            rang = "2-wire R"
        elif bits_765 == 4:
            rang = "4-wire R"
        elif bits_765 == 5:
            rang = "I_DC"
        elif bits_765 == 6:
            rang = "I_AC"
        elif bits_765 == 7:
            rang = "extended R"
        else:
            rang = "Unknown"

        return rang

    def get_range(self):
        try:
            status_raw = super().get_mode() # first byte only
        except UnicodeDecodeError:
            return "UnicodeDecodeError"

        first_byte = ord(status_raw[0])
        bits_432 = (first_byte & 0b00011100) >> 2

        if bits_432 == 1:
            rang = "30mV DC, 300mV AC, 30 ohm, 300mA AC or DC, extended R"
        elif bits_432 == 2:
            rang = "300mV DC, 3V AV, 300 ohm 3A AC or DC"
        elif bits_432 == 3:
            rang = "300mV DC, 3VAC, 300 ohm, 3A AC or DC"
        elif bits_432 == 4:
            rang = "3VDC, 30VAC, 3k ohm"
        elif bits_432 == 5:
            rang = "300VDC, 300k ohm"
        elif bits_432 == 6:
            rang = "3M ohm"
        elif bits_432 == 7:
            rang = "30M ohm"
        else:
            rang = "Unknown"

        return rang

    def get_sample_speed(self):
        pass
        # TODO: finish this for bits 1,0 of status register
        #   1=5.5 digit
        #   2=4.5 digit
        #   3=3.5 digit