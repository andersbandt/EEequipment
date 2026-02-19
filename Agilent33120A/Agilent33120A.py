

# import needed modules
from pyvisa import ResourceManager
import pyvisa.errors
import usb
import configparser

# import Equipment parent class
from EEequipment.TestEquipment import FunctionGenerator
from EEequipment.TestEquipment import PyVISAHandler


class Agilent33120A(FunctionGenerator):
    """
    Class for interacting with the SPD3303 Siglent Power Supply
    """

    def __init__(self, address):
        '''
        Init the VISA (pyvisa) connection and get the basic product info
        '''
        super().__init__("Agilent33120A", PyVISAHandler(address))
        self._channel_count = 1

    def read_value(self):
        return self.test_conn()






