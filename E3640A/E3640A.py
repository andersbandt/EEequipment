

# import needed modules
from pyvisa import ResourceManager
import pyvisa.errors
import usb
import configparser

# import Equipment parent class
from EEequipment.TestEquipment import PowerSupply


class E3640A(PowerSupply):
    def __init__(self, address):
        '''
        Init the VISA (pyvisa) connection and get the basic product info
        '''
        super().__init__(address)

        # set up the ResourceManager
        try:
            self.rm = ResourceManager('@py')  # use 'pyvisa-py' backend
        except ValueError:
            self.rm = ResourceManager()

        # attempt to open instance
        try:
            self.inst = self.rm.open_resource(self.address)
            self.inst.write_termination = '\n'
            self.inst.read_termination = '\n'
            self.inst.timeout = 1 * 1000  # NOTE: used to be 2 seconds

            # set default voltages on connect to 0V because I'm dumb and burn my boards too often
            self.set_voltage(1, 0)
            self.set_voltage(2, 0)
        except (usb.core.USBError, pyvisa.errors.VisaIOError) as e:
            print("Error with opening E3640A")
            print(e)