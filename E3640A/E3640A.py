

# import user created Equipment modules
from EEequipment.TestEquipment import PowerSupply
from EEequipment.TestEquipment import PyVISAHandler


class E3640A(PowerSupply):
    def __init__(self, address):
        '''
        Init the VISA (pyvisa) connection and get the basic product info
        '''
        super().__init__(address, "E3640A", PyVISAHandler())


    def check_status(self):
        res = super().check_status()
        print(f"{self.model} has status of {res}")
        # TODO: add decoding for the status check
        status_decode = {
            "ch1_state": "OFF",
            "ch2_state": "OFF"}
        return status_decode