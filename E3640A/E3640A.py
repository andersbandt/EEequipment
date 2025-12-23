

# import user created Equipment modules
from EEequipment.TestEquipment import PowerSupply
from EEequipment.TestEquipment import PyVISAHandler


class E3640A(PowerSupply):
    def __init__(self, address):
        '''
        Init the VISA (pyvisa) connection and get the basic product info
        '''
        super().__init__("E3640A", PyVISAHandler(address))
        self.channel_count = 1


    def check_status(self):
        status = super().check_status()
        cmd = self.registry.get_command(self.model, "command", "output_state")
        ch1_state = self.conn.query(cmd)
        if ch1_state == "1":
            ch1_state = "ON"
        else:
            ch1_state = "OFF"

        status_decode = {
            "status": status,
            "ch1_state": ch1_state
        }
        import pprint
        pprint.pprint(status_decode)
        return status_decode