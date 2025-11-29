"""
@file     8842A.py
@author   Anders Bandt
@brief    class for talking to a Fluke 8842A
"""

# import modules
import logging
import serial

# import user created modules
from EEequipment.TestEquipment import DMM


class 8842A(DMM):
    def __init__(self, address):
            super().__init__(address)
            try:
                self.serial = serial.Serial(
                    port=address,
                    baudrate=115200,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=0.5,
                    xonxoff=False,
                    write_timeout=0.5
                )
                self.status = self.serial.is_open
            except serial.serialutil.SerialException:
                self.serial = None
                self.status = False

            self.logger = logging.getLogger(__name__)  # TODO: understand this logger thing
            self.logger.info("Serial port status:{}".format(self.status))
            self.set_range_auto()