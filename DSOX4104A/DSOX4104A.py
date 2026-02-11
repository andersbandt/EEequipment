

# import user created Equipment modules
from EEequipment.TestEquipment import Oscilloscope
from EEequipment.TestEquipment import PyVISAHandler


class DSOX4104A(Oscilloscope):
    def __init__(self, address):
        '''
        Init the VISA (pyvisa) connection and get the basic product info
        '''
        super().__init__("DSOX4104A", PyVISAHandler(address))
        self.channel_count = 4
