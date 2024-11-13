"""
@file     arduino.py
@author   Anders Bandt
@date     November 2024
@brief    Python class for managing data with a serial connection
"""


# import user created modules
from EEequipment.Equipment import Equipment
from common.SerialGeneral import SerialGeneral


class Arduino(Equipment):
    # define class variables here

    def __init__(self, port, baud_rate):
        self.port = port
        self.baud_rate = baud_rate
        self.serial = SerialGeneral(
            self.port,
            self.baud_rate)

    def send_char(self, char):
        # TODO: add some error checking on input char
        self.serial.send_data(char)
        return True

    def get_all_data(self):
        data = self.serial.get_data()
        return data


