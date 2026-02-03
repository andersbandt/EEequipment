

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
        cmd = self.registry.get_command(self.model, "command", "status")

        try:
            status = int(self.conn.query(cmd))
        except ValueError:
            return {}
            # TODO: add some error handling if this thing can't be an int. Thinking of adding some error flag to the status_decode dict?

        ch1_mode = "CV" if not (status & 0x01) else "CC"

        # get output state
        cmd = self.registry.get_command(self.model, "command", "output_state")
        ch1_state = self.conn.query(cmd)
        if ch1_state == "1":
            ch1_state = "ON"
        else:
            ch1_state = "OFF"

        # place everything in a dict
        status_decode = {
            "status": status,
            "ch1_state": ch1_state,
            "ch1_mode": ch1_mode
        }
        import pprint
        pprint.pprint(status_decode)
        return status_decode