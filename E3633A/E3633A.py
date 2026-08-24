from EEequipment.TestEquipment import PowerSupply, SerialHandler


class E3633A(PowerSupply):
    """
    HP/Agilent E3633A single-output dual-range power supply over RS-232.

    Ranges (selected on front panel or via VOLT:RANGe):
        Low  range: 0–8 V  / 0–10 A
        High range: 0–20 V / 0–5 A
    """

    def __init__(self, address):
        super().__init__("E3633A", SerialHandler(address))
        self.channel_count = 1

    def check_error(self):
        """E3633A does not have a SCPI error queue — not implemented."""
        return False

    def check_status(self):
        """
        Return status for the single output.

        STATus:QUEStionable? bit 0: set when output is in CC mode (clear = CV).
        """
        cmd = self.registry.get_command(self.model, "command", "status")

        try:
            status = int(self.conn.query(cmd))
            error = None
        except (ValueError, Exception) as e:
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
                "ch2_display": None,
            }

        ch1_mode = "CV" if not (status & 0x01) else "CC"

        try:
            out_cmd = self.registry.get_command(self.model, "command", "output_state")
            raw = self.conn.query(out_cmd).strip()
            ch1_state = "ON" if raw == "1" else "OFF"
        except Exception:
            ch1_state = None

        return {
            "status": status,
            "error": error,
            "ch1_state": ch1_state,
            "ch1_mode": ch1_mode,
            "ch2_state": None,
            "ch2_mode": None,
            "channel_mode": "Independent",
            "timer1": None,
            "timer2": None,
            "ch1_display": None,
            "ch2_display": None,
        }
