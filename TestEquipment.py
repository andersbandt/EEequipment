

# import needed connection modules
import pyvisa
import usb
import serial

# import other modules
import configparser
import abc
from abc import ABC, abstractmethod
from pathlib import Path
import time
from enum import Enum

# import user created modules
# from units import ureg as u
# from util_fns import assume_units, ProxyList


class CommandRegistry:
    """Loads and manages equipment commands from INI files"""

    def __init__(self, equipment_dir: str = "EEequipment"):
        self.equipment_dir = Path(equipment_dir)
        self.commands = {}
        self._load_all_commands()

    def _load_all_commands(self):
        """Load config.ini from each model subdirectory"""
        if not self.equipment_dir.exists():
            raise FileNotFoundError(f"Equipment directory not found: {self.equipment_dir}")

        # Look for subdirectories containing config.ini
        for model_dir in self.equipment_dir.iterdir():
            if not model_dir.is_dir():
                continue

            config_file = model_dir / "config.ini"
            if not config_file.exists():
                continue

            model_name = model_dir.name  # Use directory name as model identifier
            config = configparser.ConfigParser()
            config.read(config_file)

            self.commands[model_name] = {
                section: dict(config[section])
                for section in config.sections()
            }
            print(f"Loaded commands for '{model_name}' from {config_file}")

    def get_command(self, model: str, section: str, cmd_name: str) -> str:
        if model not in self.commands:
            raise ValueError(f"Model not found: {model}")
        if section not in self.commands[model]:
            raise ValueError(f"Section '{section}' not found for {model}")
        if cmd_name not in self.commands[model][section]:
            raise ValueError(f"Command '{cmd_name}' not found in {model}:{section}")

        return self.commands[model][section][cmd_name]

    def format_command(self, model: str, section: str, cmd_name: str, **kwargs) -> str:
        cmd_template = self.get_command(model, section, cmd_name)
        return cmd_template.format(**kwargs)

    def get_config_section(self, model: str, section: str) -> dict:
        """Get entire config section (for connection params, etc)"""
        if model not in self.commands:
            raise ValueError(f"Model not found: {model}")
        return self.commands[model].get(section, {})


_registry = None

def get_registry(equipment_dir: str = "EEequipment") -> CommandRegistry:
    global _registry
    if _registry is None:
        _registry = CommandRegistry(equipment_dir)
    return _registry


# ============================================================================
# CONNECTION HANDLERS (Protocol layer - composition)
# ============================================================================

class ConnectionHandler(ABC):
    """Abstract connection handler - defines the protocol"""
    status = False

    @abstractmethod
    def connect(self, config: dict):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def write(self, cmd: str):
        pass

    @abstractmethod
    def read(self) -> str:
        pass

    @abstractmethod
    def query(self, cmd: str) -> str:
        pass


class PyVISAHandler(ConnectionHandler):
    """Handles PyVISA protocol"""

    def __init__(self, address):
        self.address = address
        self.rm = None
        self.inst = None
        self.status = False

    def connect(self, config: dict):
        # set up the ResourceManager
        try:
            self.rm = pyvisa.ResourceManager('@py')  # use 'pyvisa-py' backend
        except ValueError:
            self.rm = pyvisa.ResourceManager()

        # print out info
        print("PyVISA Version:", pyvisa.__version__)
        print("Backend:", self.rm.visalib)

        # attempt to open instance
        try:
            print("Starting PyVISA ConnectionHandler")
            try:
                self.inst = self.rm.open_resource(self.address)
            except ValueError:
                self.rm = pyvisa.ResourceManager()
                self.inst = self.rm.open_resource(self.address)

            if 'timeout' in config:
                self.inst.timeout = int(config['timeout'])
                print(f"\ttimeout: {self.inst.timeout}")
            if 'read_termination' in config:
                self.inst.read_termination = config['read_termination'].encode().decode('unicode_escape')
                print("\tread term:", repr(self.inst.read_termination))
            if 'write_termination' in config:
                self.inst.write_termination = config['write_termination'].encode().decode('unicode_escape')
                print("\twrite term:", repr(self.inst.write_termination))

            self.status = True
        except (usb.core.USBError, pyvisa.errors.VisaIOError) as e:
                print("Error with opening PyVISA Handler")
                self.status = False
                print(e)

    def disconnect(self):
        if self.inst:
            self.inst.close()
        if self.rm:
            self.rm.close()
        self.status = False

    def write(self, cmd: str):
        self.inst.write(cmd)

    def read(self) -> str:
        if not self.status:
            raise RuntimeError("Not connected")
        return self.inst.read()

    def query(self, cmd: str):
        if not self.status:
            raise RuntimeError("Not connected, can't query")

        return self.inst.query(cmd)


class SerialHandler(ConnectionHandler):
    """Handles serial protocol"""

    def __init__(self, address):
        self.address = address
        self.inst = None
        self.status = False

    def connect(self, config: dict):
        baudrate = int(config['baudrate'])
        timeout = float(config['timeout'])
        try:
            self.inst = serial.Serial(
                port=self.address,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout,
                xonxoff=False,
                write_timeout=timeout
            )
            self.inst.reset_input_buffer()
            self.status = True
        except serial.serialutil.SerialException:
            self.inst = None
            self.status = False

        except Exception as e:
            raise ValueError(f"Failed to connect via serial: {e}")

    def disconnect(self):
        if self.status:
            self.inst.close()
            self.status = False

    def set_timeout(self, timeout):
        self.inst.timeout = timeout

    def write(self, cmd: str):
        if not self.status:
            raise RuntimeError("Not connected")

        self.inst.write((cmd + "\n").encode())

    def read(self, decode=True) -> str:
        if not self.status:
            raise RuntimeError("Not connected")

        val = self.inst.readline()
        if decode:
            try:
                val = val.decode('utf-8').strip()
            except UnicodeDecodeError:
                print("Failed to decode below line")
                print(val)

        return val

    def query(self, cmd: str):
        if not self.status:
            raise RuntimeError("Not connected")

        self.write(cmd)
        return self.read()


# ============================================================================
# TEST EQUIPMENT BASE CLASSES
# ============================================================================

class TestEquipment(ABC):
    """Base class for all test equipment. Hides protocol details."""

    def __init__(self, model: str, connection_handler: ConnectionHandler):
        self.model = model
        self.registry = get_registry()
        self.conn = connection_handler

        # get connection config
        conn_type = self.conn.__class__.__name__.replace('Handler', '').lower()
        self.config = self.registry.get_config_section(model, conn_type)

        # connect
        print("Initiating TestEquipment connection in __init__()")
        self.conn.connect(self.config)
        print("done with connection in __init()")

    @property
    def status(self) -> bool:
        return self.conn.status

    def connect(self, address, config):
        """Establish connection (serial, PyVISA, ethernet, whatever)"""
        self.conn.connect(self.config)

    def disconnect(self):
        """Close connection"""
        self.conn.disconnect()

    def test_conn(self) -> str:
        cmd = self.registry.get_command(self.model, "command", "query")
        try:
            res = self.conn.query(cmd)
        except RuntimeError:
            return ""
        return res

    def clear(self):
        cmd = self.registry.get_command(self.model, "command", "clear")
        self.conn.write(cmd)

    def write(self, cmd: str):
        self.conn.write(cmd)

    def read(self):
        return self.conn.read()

    def query(self, cmd: str):
        return self.conn.query(cmd)

    def benchmark(self, samples, method):
        start_time = time.perf_counter()

        for _ in range(samples):
            _ = method()

        end_time = time.perf_counter()

        # Calculate elapsed time and sample rate
        elapsed = end_time - start_time
        sample_rate = samples / elapsed

        result_str = f"Queried {samples} samples in {elapsed:.4f} seconds"
        result_str += f"\nApproximate sample rate: {sample_rate:.2f} Hz"

        result = {
            "samples": samples,
            "elapsed_sec": round(elapsed, 4),
            "sample_rate_hz": round(sample_rate, 2),
            "string": result_str,
        }

        return result


class PowerSupply(TestEquipment):
    """Abstract power supply - defines PS-specific interface"""

    class PowerSupplyException(Exception):
        """Exception raised when a call returns an error message"""

        def __init__(self, code, message):
            self.code = code
            self.message = message
            super().__init__(self.message)

        def __str__(self):
            return f'Error Code: {self.code} -> {self.message}'

    def __init__(self, model: str, connection_handler: ConnectionHandler):
        self.channel_count = 0
        super().__init__(model, connection_handler)

    def check_channel(self, channel) -> bool:
        if not isinstance(channel, int):
            return False
            raise self.PowerSupplyException(self.channel_count, "Channel count must be an integer")

        if self.channel_count == 0:
            return False

        """Validate channel number is within range"""
        if channel not in range(1, self.channel_count + 1):
            return False
            raise self.PowerSupplyException('21', f'Channel # must be an integer 1 - {self.channel_count}')

        return True

    def read_value(self) -> float:
        return self.get_voltage(1)

    def set_voltage(self, value, channel=1):
        """Set the voltage value for the selected channel with calibration"""
        cmd = self.registry.get_command(self.model, "command", "set_voltage")
        cmd = cmd.format(channel=channel, value=value)
        self.conn.write(cmd)
        return value

    def set_current(self, value, channel=1):
        """Set the current value for the selected channel"""
        self.check_channel(channel)

        cmd = self.registry.get_command(self.model, "command", "set_current")
        cmd = cmd.format(channel=channel, value=value)
        self.conn.write(cmd)

    def get_set_voltage(self, channel=1):
        """Get the set voltage value of the channel"""
        self.check_channel(channel)

        cmd = self.registry.get_command(self.model, "command", "get_set_voltage")
        cmd = cmd.format(channel=channel)
        self.conn.write(cmd)
        response = self.conn.read()
        return float(response)

    def get_set_current(self, channel=1):
        """Get the set current value of the channel"""
        self.check_channel(channel)

        cmd = self.registry.get_command(self.model, "command", "get_set_current")
        cmd = cmd.format(channel=channel)
        self.conn.write(cmd)
        response = self.conn.read()
        return float(response)

    def get_voltage(self, channel=1):
        """Get the measured voltage value for a given channel"""
        if not self.check_channel(channel):
            return None

        cmd = self.registry.get_command(self.model, "command", "get_voltage")
        cmd = cmd.format(channel=channel)
        response = self.conn.query(cmd)
        return float(response)

    def get_current(self, channel=1):
        """Get the current value for a given channel with calibration"""
        if not self.check_channel(channel):
            return None

        cmd = self.registry.get_command(self.model, "command", "get_current")
        cmd = cmd.format(channel=channel)
        return float(self.conn.query(cmd))

    def get_power(self, channel=1):
        """Get the power value for a given channel"""
        self.check_channel(channel)

        cmd = self.registry.get_command(self.model, "command", "get_power")
        cmd = cmd.format(channel=channel)
        response = self.conn.query(cmd)
        return float(response)

    def output_on(self, channel=1):
        """Turn on the channel output"""
        self.check_channel(channel)

        cmd = self.registry.get_command(self.model, "command", "output_on")
        cmd = cmd.format(channel=channel)
        self.conn.write(cmd)

    def output_off(self, channel=1):
        """Turn off the channel output"""
        self.check_channel(channel)

        cmd = self.registry.get_command(self.model, "command", "output_off")
        cmd = cmd.format(channel=channel)
        self.conn.write(cmd)

    def check_error(self):
        """Check for an error on the system"""
        cmd = self.registry.get_command(self.model, "command", "check_error")
        self.conn.write(cmd)
        response = self.conn.read()
        resp_list = response.split('  ')

        if resp_list[0] == '0':
            return False

        resp_list[1] = resp_list[1].rstrip('\n')
        raise self.PowerSupplyException(resp_list[0], resp_list[1])

    @abstractmethod
    def check_status(self):
        """Return the top level info about the power supply functional status. This method is abstract because the implementation
            will vary by a lot between models

        The return is a dict with the following main keys:

        chX_mode: either "CV" or "CC" (constant-voltage or constant-current)
        chX_state: either "ON" or "OFF"

        Some models may include more elaborate features in which case the following keys will be there
        channel_mode: "Independent", "Parallel", or "Unknown"
        timerX: "ON" or "OFF
        chX_display: "Digital" or "Waveform"
        """


class DMM(TestEquipment):
    """Abstract digital multimeter - defines DMM-specific interface"""
    def __init__(self, model: str, connection_handler: ConnectionHandler):
        super().__init__(model, connection_handler)
        self.mode = None

    def read_value(self) -> float:
        cmd = self.registry.get_command(self.model, "command", "read")
        return float(self.conn.query(cmd))

    def set_mode(self, mode: str):
        if mode == "VDC":
            cmd = self.registry.get_command(self.model, "command", "mode_vdc")
        elif mode == "VAC":
            cmd = self.registry.get_command(self.model, "command", "mode_vac")
        elif mode == "IDC":
            cmd = self.registry.get_command(self.model, "command", "mode_idc")
        elif mode == "IAC":
            cmd = self.registry.get_command(self.model, "command", "mode_iac")
        elif mode == "RES_2WIRE":
            cmd = self.registry.get_command(self.model, "command", "mode_res_2")
        elif mode == "RES_4WIRE":
            cmd = self.registry.get_command(self.model, "command", "mode_res_4")
        else:
            raise BaseException("Unknown mode")
        self.mode = mode
        self.write(cmd)

    def get_mode(self):
        cmd = self.registry.get_command(self.model, "command", "get_mode")
        return self.query(cmd)

    @abstractmethod
    def set_range(self, rng: int) -> bool:
        pass

    def set_range_auto(self):
        cmd = self.registry.get_command(self.model, "command", "range_auto")
        self.write(cmd)

    def get_range(self):
        cmd = self.registry.get_command(self.model, "command", "get_range")
        return self.query(cmd)

    def set_sample_speed(self, speed):
        if speed == "slow":
            cmd = self.registry.get_command(self.model, "command", "sample_slow")
        elif speed == "medium":
            cmd = self.registry.get_command(self.model, "command", "sample_medium")
        elif speed == "fast":
            cmd = self.registry.get_command(self.model, "command", "sample_fast")
        else:
            raise BaseException("Unknown speed")
        self.write(cmd)


class FunctionGenerator(TestEquipment, metaclass=abc.ABCMeta):
    """
    Abstract base class for function generator instruments.

    All applicable concrete instruments should inherit from this ABC to
    provide a consistent interface to the user.
    """

    def __init__(self, model: str, connection_handler: ConnectionHandler):
        super().__init__(model, connection_handler)
        self._channel_count = 1


    # ENUMS #
    class VoltageMode(Enum):
        """
        Enum containing valid voltage modes for many function generators
        """
        peak_to_peak = "VPP"
        rms = "VRMS"
        dBm = "DBM"

    class Function(Enum):
        """
        Enum containg valid output function modes for many function generators
        """

        sinusoid = "SIN"
        square = "SQU"
        triangle = "TRI"
        ramp = "RAMP"
        noise = "NOIS"
        arbitrary = "ARB"


    def set_function(self, function):
        raise NotImplementedError

    def set_frequency(self, value, channel=1):
        """Set the voltage value for the selected channel with calibration"""
        cmd = self.registry.get_command(self.model, "command", "set_frequency")
        cmd = cmd.format(value=value, channel=channel)
        self.write(cmd)

    def set_duty(self, value, channel=1):
        """Set the duty cycle for the selected channel"""
        cmd = self.registry.get_command(self.model, "command", "set_duty")
        cmd = cmd.format(value=value, channel=channel)
        self.write(cmd)

    def set_offset(self, value, channel=1):
        """Set the DC offset for the selected channel"""
        cmd = self.registry.get_command(self.model, "command", "set_offset")
        cmd = cmd.format(value=value, channel=channel)
        self.write(cmd)

    def set_amplitude(self, value, channel=1):
        """Set the amplitude for the selected channel"""
        cmd = self.registry.get_command(self.model, "command", "set_amplitude")
        cmd = cmd.format(value=value, channel=channel)
        self.write(cmd)



# Channel subclass approach for future v2.0 implementation
class Channel:
    def __init__(self, parent, index):
        self.parent = parent
        self.index = index

    def cmd(self, key, **kwargs):
        return self.parent.cmd(key, channel=self.index, **kwargs)

    def write(self, key, **kwargs):
        return self.parent.conn.write(key, channel=self.index, **kwargs)