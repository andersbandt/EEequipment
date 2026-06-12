from EEequipment.TestEquipment import FunctionGenerator, SerialHandler


class Agilent33210A(FunctionGenerator):
    """Agilent 33210A 10 MHz function/arbitrary waveform generator over RS-232."""

    def __init__(self, address):
        super().__init__("Agilent33210A", SerialHandler(address))
        self._channel_count = 1

    def read_value(self):
        return self.test_conn()

    def set_function(self, function):
        if isinstance(function, self.Function):
            value = function.value
        else:
            value = str(function).upper()
        cmd = self.registry.get_command(self.model, "command", "set_function")
        self.conn.write(cmd.format(value=value))

    def output_on(self):
        cmd = self.registry.get_command(self.model, "command", "output_on")
        self.conn.write(cmd)

    def output_off(self):
        cmd = self.registry.get_command(self.model, "command", "output_off")
        self.conn.write(cmd)
