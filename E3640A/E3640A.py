

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
        """
        Return the status information for the power supply.
        Returns a standardized dictionary with ch1/ch2 fields (ch2 fields are None for single-channel PS).
        """
        cmd = self.registry.get_command(self.model, "command", "status")

        try:
            status = int(self.conn.query(cmd))
            error = None
        except (ValueError, Exception) as e:
            # Return dict with error field when status query fails
            return {
                "status": None,
                "error": f"Failed to query status: {str(e)}",
                "ch1_state": None,
                "ch1_mode": None,
                "ch2_state": None,
                "ch2_mode": None,
                "channel_mode": None,
                "timer1": None,
                "timer2": None,
                "ch1_display": None,
                "ch2_display": None
            }

        ch1_mode = "CV" if not (status & 0x01) else "CC"

        # get output state
        try:
            cmd = self.registry.get_command(self.model, "command", "output_state")
            ch1_state = self.conn.query(cmd)
            if ch1_state == "1":
                ch1_state = "ON"
            else:
                ch1_state = "OFF"
        except Exception:
            ch1_state = None

        # place everything in a standardized dict
        # E3640A is single-channel, so ch2 fields are None
        status_decode = {
            "status": status,
            "error": error,
            "ch1_state": ch1_state,
            "ch1_mode": ch1_mode,
            "ch2_state": None,  # Single-channel PS
            "ch2_mode": None,   # Single-channel PS
            "channel_mode": "Independent",  # E3640A is always independent (single channel)
            "timer1": None,     # E3640A doesn't have timer feature
            "timer2": None,     # E3640A doesn't have timer feature
            "ch1_display": None,  # E3640A doesn't have display mode feature
            "ch2_display": None   # E3640A doesn't have display mode feature
        }
        return status_decode
