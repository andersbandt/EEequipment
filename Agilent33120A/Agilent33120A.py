from EEequipment.TestEquipment import FunctionGenerator
from EEequipment.TestEquipment import PyVISAHandler


class Agilent33120A(FunctionGenerator):
    """Agilent 33120A 15 MHz function/arbitrary waveform generator over PyVISA."""

    def __init__(self, address):
        super().__init__("Agilent33120A", PyVISAHandler(address))
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






