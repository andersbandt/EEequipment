from EEequipment.TestEquipment import PowerSupply, SerialHandler


class E3631A(PowerSupply):
    """
    HP/Agilent E3631A triple-output power supply over RS-232.

    Outputs:
        1 = P6V  (0–6 V, 0–5 A)
        2 = P25V (0–25 V, 0–1 A)
        3 = N25V (0 to −25 V, 0–1 A)

    The OUTP command controls all three outputs simultaneously.
    Channel selection (INST:NSEL) must precede any per-channel command.
    """

    def __init__(self, address):
        super().__init__("E3631A", SerialHandler(address))
        self.channel_count = 3

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _select_channel(self, channel):
        cmd = self.registry.format_command(self.model, "command", "select_channel", channel=channel)
        self.conn.write(cmd)

    # ------------------------------------------------------------------
    # PowerSupply overrides — channel selection required before each cmd
    # ------------------------------------------------------------------

    def set_voltage(self, value, channel=1):
        self._select_channel(channel)
        cmd = self.registry.get_command(self.model, "command", "set_voltage")
        self.conn.write(cmd.format(value=value))
        return value

    def set_current(self, value, channel=1):
        self._select_channel(channel)
        cmd = self.registry.get_command(self.model, "command", "set_current")
        self.conn.write(cmd.format(value=value))

    def get_set_voltage(self, channel=1):
        self._select_channel(channel)
        cmd = self.registry.get_command(self.model, "command", "get_set_voltage")
        self.conn.write(cmd)
        return float(self.conn.read())

    def get_set_current(self, channel=1):
        self._select_channel(channel)
        cmd = self.registry.get_command(self.model, "command", "get_set_current")
        self.conn.write(cmd)
        return float(self.conn.read())

    def get_voltage(self, channel=1):
        if not self.check_channel(channel):
            return None
        self._select_channel(channel)
        cmd = self.registry.get_command(self.model, "command", "get_voltage")
        return float(self.conn.query(cmd))

    def get_current(self, channel=1):
        if not self.check_channel(channel):
            return None
        self._select_channel(channel)
        cmd = self.registry.get_command(self.model, "command", "get_current")
        return float(self.conn.query(cmd))

    def output_on(self, channel=1):
        # E3631A OUTP applies to all channels simultaneously
        cmd = self.registry.get_command(self.model, "command", "output_on")
        self.conn.write(cmd)

    def output_off(self, channel=1):
        cmd = self.registry.get_command(self.model, "command", "output_off")
        self.conn.write(cmd)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def check_status(self):
        """
        Return status for all three outputs.

        STATus:QUEStionable? bits (E3631A programming guide):
            bit 0 = P6V  in CV mode
            bit 1 = P25V in CV mode
            bit 2 = N25V in CV mode
        CV bit clear → CC mode.
        """
        cmd = self.registry.get_command(self.model, "command", "status")

        try:
            status = int(self.conn.query(cmd))
            error = None
        except (ValueError, Exception) as e:
            return {
                "status": None,
                "error": f"Failed to query status: {str(e)}",
                "ch1_state": None, "ch1_mode": None,
                "ch2_state": None, "ch2_mode": None,
                "ch3_state": None, "ch3_mode": None,
                "channel_mode": None,
                "timer1": None, "timer2": None,
                "ch1_display": None, "ch2_display": None,
            }

        ch1_mode = "CV" if (status & 0x01) else "CC"
        ch2_mode = "CV" if (status & 0x02) else "CC"
        ch3_mode = "CV" if (status & 0x04) else "CC"

        try:
            out_cmd = self.registry.get_command(self.model, "command", "output_state")
            raw = self.conn.query(out_cmd).strip()
            out_state = "ON" if raw == "1" else "OFF"
        except Exception:
            out_state = None

        return {
            "status": status,
            "error": error,
            "ch1_state": out_state,
            "ch1_mode": ch1_mode,
            "ch2_state": out_state,
            "ch2_mode": ch2_mode,
            "ch3_state": out_state,
            "ch3_mode": ch3_mode,
            "channel_mode": "Independent",
            "timer1": None,
            "timer2": None,
            "ch1_display": None,
            "ch2_display": None,
        }
