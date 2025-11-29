
from abc import ABC, abstractmethod


class TestEquipment(ABC):
    """Base class for all test equipment. Hides protocol details."""

    def __init__(self, address: str):
        """
        address: Could be '/dev/ttyUSB0' (serial), 'GPIB0::1::INSTR' (PyVISA), etc.
        The subclass figures out which protocol to use.
        """
        self.address = address
        self.connection = None

    @abstractmethod
    def connect(self):
        """Establish connection (serial, PyVISA, ethernet, whatever)"""
        pass

    @abstractmethod
    def disconnect(self):
        """Close connection"""
        pass

    @abstractmethod
    def test_conn(self) -> str:
        """Test connection, return device ID"""
        pass

    @abstractmethod
    def _send_cmd(self, cmd: str) -> str:
        """Send command and get response. Subclass handles protocol."""
        pass

    def check_error(self) -> str:
        """Common error checking - most equipment supports this"""
        response = self._send_cmd("*ERR?")
        return response

    def close(self):
        """Alias for disconnect for backwards compatibility"""
        self.disconnect()


class PowerSupply(TestEquipment):
    """Abstract power supply - defines PS-specific interface"""

    @abstractmethod
    def set_voltage(self, channel: int, value: float):
        pass

    @abstractmethod
    def get_voltage(self, channel: int) -> float:
        pass

    @abstractmethod
    def set_current(self, channel: int, value: float):
        pass

    @abstractmethod
    def get_current(self, channel: int) -> float:
        pass

    @abstractmethod
    def output_on(self, channel: int):
        pass

    @abstractmethod
    def output_off(self, channel: int):
        pass

    @abstractmethod
    def get_power(self, channel: int) -> float:
        pass

    @abstractmethod
    def check_status(self) -> dict:
        """Return status dict with channel info"""
        pass


class DMM(TestEquipment):
    """Abstract digital multimeter - defines DMM-specific interface"""

    @abstractmethod
    def set_mode(self, mode: str):
        pass

    @abstractmethod
    def set_range(self, rng: int) -> bool:
        pass

    @abstractmethod
    def read_voltage(self) -> float:
        pass

    @abstractmethod
    def set_range_auto(self):
        pass
