
import logging

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

logger = logging.getLogger(__name__)



# Module-level PyVISA backend setting.
# None / "" → NI-VISA default; "@py" → pyvisa-py (no NI-VISA installation required).
# Set at startup via set_visa_backend() so equipment drivers never need to import app config.
_visa_backend = None


def set_visa_backend(backend: str):
    global _visa_backend
    _visa_backend = backend if backend else None


def get_visa_backend():
    return _visa_backend


# TODO: ask Claude to review if this is the best / cleanest way to laod in commands from my .ini files
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
            logger.debug(f"Loaded commands for '{model_name}' from {config_file}")

    def get_command(self, model: str, section: str, cmd_name: str) -> str:
        config_path = self.equipment_dir / model / "config.ini"
        if model not in self.commands:
            msg = f"Model '{model}' not found in registry. Expected config at: {config_path}"
            logger.error(msg)
            raise ValueError(msg)
        if section not in self.commands[model]:
            available = list(self.commands[model].keys())
            msg = (f"Section '[{section}]' not found in {config_path}. "
                   f"Available sections: {available}")
            logger.error(msg)
            raise ValueError(msg)
        if cmd_name not in self.commands[model][section]:
            available = list(self.commands[model][section].keys())
            msg = (f"Command '{cmd_name}' not found in [{section}] of {config_path}. "
                   f"Add '{cmd_name} = <SCPI command>' to the [{section}] section. "
                   f"Available commands: {available}")
            logger.error(msg)
            raise ValueError(msg)

        return self.commands[model][section][cmd_name]

    def format_command(self, model: str, section: str, cmd_name: str, **kwargs) -> str:
        cmd_template = self.get_command(model, section, cmd_name)
        try:
            return cmd_template.format(**kwargs)
        except KeyError as e:
            config_path = self.equipment_dir / model / "config.ini"
            msg = (f"Missing placeholder {e} when formatting '{cmd_name}' in {config_path}. "
                   f"Template: '{cmd_template}', provided keys: {list(kwargs.keys())}")
            logger.error(msg)
            raise ValueError(msg)

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
        backend = get_visa_backend()
        self.rm = pyvisa.ResourceManager(backend) if backend else pyvisa.ResourceManager()

        # print out info
        logger.info(f"PyVISA Version: {pyvisa.__version__}")
        logger.info(f"Backend: {self.rm.visalib}")

        # attempt to open instance
        try:
            logger.info("Starting PyVISA ConnectionHandler")
            try:
                self.inst = self.rm.open_resource(self.address)
            except ValueError:
                # Address may have been null-stripped for display; find
                # the actual resource string that matches after stripping.
                resolved = self._resolve_address(self.address)
                self.inst = self.rm.open_resource(resolved)

            if 'timeout' in config:
                self.inst.timeout = int(config['timeout'])
                logger.debug(f"timeout: {self.inst.timeout}")
            if 'read_termination' in config:
                self.inst.read_termination = config['read_termination'].encode().decode('unicode_escape')
                logger.debug(f"read term: {repr(self.inst.read_termination)}")
            if 'write_termination' in config:
                self.inst.write_termination = config['write_termination'].encode().decode('unicode_escape')
                logger.debug(f"write term: {repr(self.inst.write_termination)}")

            # Flush any stale data left in the USBTMC endpoint buffer from a
            # previous session. Without this, instruments like the SPD3303X
            # raise EOVERFLOW on the very first query after open_resource().
            try:
                self.inst.clear()
                logger.debug("VISA interface cleared")
            except Exception as e:
                logger.debug(f"VISA clear skipped (backend may not support it): {e}")

            self.status = True
        except (usb.core.USBError, pyvisa.errors.VisaIOError) as e:
                logger.error(f"Error with opening PyVISA Handler: {e}")
                self.status = False

    def _resolve_address(self, address):
        """Match a null-stripped address against actual listed resources."""
        clean = address.replace('\x00', '')
        for res in self.rm.list_resources():
            if res.replace('\x00', '') == clean:
                return res
        raise ValueError(f"No matching VISA resource found for: {address}")

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
                logger.error(f"Failed to decode line: {val}")

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
        available = list(self.registry.commands.get(model, {}).keys())
        if conn_type not in available:
            raise ValueError(
                f"{model}: handler is {self.conn.__class__.__name__} (needs [{conn_type}] section) "
                f"but config.ini only has sections: {available}"
            )
        self.config = self.registry.get_config_section(model, conn_type)

        # connect
        logger.info("Initiating TestEquipment connection in __init__()")
        self.conn.connect(self.config)
        logger.info("done with connection in __init__()")

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

    # Required by benchmark(); each subclass implements the appropriate read command.
    @abstractmethod
    def read_value(self):
        pass

    def clear(self):
        cmd = self.registry.get_command(self.model, "command", "clear")
        self.conn.write(cmd)

    def write(self, cmd: str):
        self.conn.write(cmd)

    def read(self):
        return self.conn.read()

    def query(self, cmd: str):
        return self.conn.query(cmd)

    def has_capability(self, capability):
        """Check if a capability is declared in the equipment's config.ini [capabilities] section."""
        caps = self.registry.get_config_section(self.model, "capabilities")
        return caps.get(capability, "false").lower() == "true"

    def benchmark(self, samples, method, store_values=False):
        start_time = time.perf_counter()

        values = []
        for _ in range(samples):
            result = method()
            if store_values:
                values.append(result)

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
            "values": values,
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
        """Validate channel number is within range."""
        if not isinstance(channel, int):
            return False
        if self.channel_count == 0:
            return False
        if channel not in range(1, self.channel_count + 1):
            return False
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

    @abstractmethod
    def check_error(self):
        """Check for instrument errors. Implementation is model-specific."""
        pass

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

    def get_secondary_mode(self):
        """Query the secondary function/mode (FUNC2). Requires 'get_func2' in config."""
        cmd = self.registry.get_command(self.model, "command", "get_func2")
        return self.query(cmd)

    def set_secondary_mode(self, mode: str):
        """Set the secondary function (e.g. 'FREQ' or 'NONe'). Requires 'set_func2' in config."""
        cmd = self.registry.format_command(self.model, "command", "set_func2", mode=mode)
        self.write(cmd)

    def read_secondary_value(self):
        """Read the secondary measurement (MEAS2). Requires 'read_secondary' in config.
        Returns None when the instrument reports a non-numeric value (e.g. 'NONe')."""
        cmd = self.registry.get_command(self.model, "command", "read_secondary")
        raw = self.query(cmd)
        try:
            return float(raw)
        except (ValueError, TypeError):
            return None

    # NOTE: this one is abstract because it's so custom/specific per DMM model
    @abstractmethod
    def set_range(self, rng: int) -> bool:
        pass

    def set_range_auto(self):
        cmd = self.registry.get_command(self.model, "command", "range_auto")
        self.write(cmd)

    def get_range(self):
        cmd = self.registry.get_command(self.model, "command", "get_range")
        return self.query(cmd)

    def set_rate(self, speed):
        if speed == "slow":
            cmd = self.registry.get_command(self.model, "command", "rate_slow")
        elif speed == "medium":
            cmd = self.registry.get_command(self.model, "command", "rate_medium")
        elif speed == "fast":
            cmd = self.registry.get_command(self.model, "command", "rate_fast")
        else:
            raise ValueError(f"Unknown rate: {speed}")
        self.write(cmd)

    def get_rate(self):
        """Query the current measurement rate. Returns None if not supported by this model."""
        try:
            cmd = self.registry.get_command(self.model, "command", "get_rate")
            return self.query(cmd)
        except ValueError:
            return None


class FunctionGenerator(TestEquipment):
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


    @abstractmethod
    def set_function(self, function):
        pass

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


class Oscilloscope(TestEquipment):
    """Base class for oscilloscope instruments.

    Provides standard SCPI-based implementations for channel control,
    timebase, trigger, acquisition, measurements, display, save/recall,
    math, and cursors.  Subclasses only need to set ``model`` and
    ``channel_count``; override individual methods if the hardware
    deviates from the standard command set.
    """

    def __init__(self, model: str, connection_handler: ConnectionHandler):
        self.channel_count = 1
        super().__init__(model, connection_handler)

    # --- Helpers ---
    def _cmd(self, cmd_name, **kwargs):
        """Format a command from the registry and return the string."""
        return self.registry.format_command(self.model, "command", cmd_name, **kwargs)

    def _send_cmd(self, cmd):
        """Write a command and check for errors."""
        self.conn.write(cmd)
        self.check_error()

    def _query_float(self, cmd):
        """Query and return a float, or None if the scope returns 9.9E+37 (no measurement)."""
        result = self.conn.query(cmd)
        val = float(result)
        if val > 9.9e+36:
            return None
        return val

    def check_channel(self, channel):
        if not isinstance(channel, int) or channel not in range(1, self.channel_count + 1):
            raise ValueError(f"Channel must be an integer 1-{self.channel_count}, got {channel}")

    # --- System ---
    def check_error(self):
        """Query the error queue. Returns error string or None if no error."""
        cmd = self.registry.get_command(self.model, "command", "error")
        response = self.conn.query(cmd)
        if response.startswith("+0,") or response.startswith("0,"):
            return None
        return response

    def reset(self):
        self.conn.write(self._cmd("reset"))

    def autoscale(self):
        self.conn.write(self._cmd("autoscale"))

    def self_test(self):
        """Run self-test. Returns 0 if passed."""
        return self.conn.query(self._cmd("self_test"))

    def wait_complete(self):
        """Block until all pending operations complete (*OPC?)."""
        return self.conn.query(self._cmd("opc"))

    # --- Channel Control ---
    def channel_on(self, channel):
        self.check_channel(channel)
        self._send_cmd(self._cmd("chan_display_on", channel=channel))

    def channel_off(self, channel):
        self.check_channel(channel)
        self._send_cmd(self._cmd("chan_display_off", channel=channel))

    def get_channel_display(self, channel):
        self.check_channel(channel)
        return self.conn.query(self._cmd("chan_get_display", channel=channel))

    def set_coupling(self, channel, coupling="DC"):
        self.check_channel(channel)
        self._send_cmd(self._cmd("chan_coupling", channel=channel, coupling=coupling))

    def get_coupling(self, channel):
        self.check_channel(channel)
        return self.conn.query(self._cmd("chan_get_coupling", channel=channel)).strip()

    def set_scale(self, channel, scale):
        self.check_channel(channel)
        self._send_cmd(self._cmd("chan_scale", channel=channel, scale=scale))

    def get_scale(self, channel):
        self.check_channel(channel)
        return float(self.conn.query(self._cmd("chan_get_scale", channel=channel)))

    def set_offset(self, channel, offset):
        self.check_channel(channel)
        self._send_cmd(self._cmd("chan_offset", channel=channel, offset=offset))

    def get_offset(self, channel):
        self.check_channel(channel)
        return float(self.conn.query(self._cmd("chan_get_offset", channel=channel)))

    def set_probe(self, channel, ratio):
        self.check_channel(channel)
        self._send_cmd(self._cmd("chan_probe", channel=channel, ratio=ratio))

    def get_probe(self, channel):
        self.check_channel(channel)
        return float(self.conn.query(self._cmd("chan_get_probe", channel=channel)))

    def set_bw_limit(self, channel, enabled):
        self.check_channel(channel)
        cmd_key = "chan_bw_limit_on" if enabled else "chan_bw_limit_off"
        self._send_cmd(self._cmd(cmd_key, channel=channel))

    def get_bw_limit(self, channel):
        self.check_channel(channel)
        return self.conn.query(self._cmd("chan_get_bw_limit", channel=channel)).strip()

    def set_impedance(self, channel, impedance):
        self.check_channel(channel)
        self._send_cmd(self._cmd("chan_impedance", channel=channel, impedance=impedance))

    def get_impedance(self, channel):
        self.check_channel(channel)
        return self.conn.query(self._cmd("chan_get_impedance", channel=channel)).strip()

    def set_label(self, channel, label):
        self.check_channel(channel)
        self._send_cmd(self._cmd("chan_label", channel=channel, label=label))

    def get_label(self, channel):
        self.check_channel(channel)
        return self.conn.query(self._cmd("chan_get_label", channel=channel)).strip().strip('"')

    # --- Timebase ---
    def set_timebase_scale(self, scale):
        self._send_cmd(self._cmd("timebase_scale", scale=scale))

    def get_timebase_scale(self):
        return float(self.conn.query(self._cmd("timebase_get_scale")))

    def set_timebase_position(self, position):
        self._send_cmd(self._cmd("timebase_position", position=position))

    def get_timebase_position(self):
        return float(self.conn.query(self._cmd("timebase_get_position")))

    def set_timebase_mode(self, mode):
        self._send_cmd(self._cmd("timebase_mode", mode=mode))

    def get_timebase_mode(self):
        return self.conn.query(self._cmd("timebase_get_mode")).strip()

    def set_timebase_reference(self, reference):
        self._send_cmd(self._cmd("timebase_ref", reference=reference))

    def get_timebase_reference(self):
        return self.conn.query(self._cmd("timebase_get_ref")).strip()

    # --- Trigger ---
    def set_trigger_mode(self, mode):
        self._send_cmd(self._cmd("trig_mode", mode=mode))

    def get_trigger_mode(self):
        return self.conn.query(self._cmd("trig_get_mode")).strip()

    def set_trigger_source(self, source):
        self._send_cmd(self._cmd("trig_source", source=source))

    def get_trigger_source(self):
        return self.conn.query(self._cmd("trig_get_source")).strip()

    def set_trigger_level(self, channel, level):
        self.check_channel(channel)
        self._send_cmd(self._cmd("trig_level", channel=channel, level=level))

    def get_trigger_level(self, channel):
        self.check_channel(channel)
        return float(self.conn.query(self._cmd("trig_get_level", channel=channel)))

    def set_trigger_slope(self, slope):
        self._send_cmd(self._cmd("trig_slope", slope=slope))

    def get_trigger_slope(self):
        return self.conn.query(self._cmd("trig_get_slope")).strip()

    def set_trigger_coupling(self, coupling):
        self._send_cmd(self._cmd("trig_coupling", coupling=coupling))

    def get_trigger_coupling(self):
        return self.conn.query(self._cmd("trig_get_coupling")).strip()

    def set_trigger_sweep(self, sweep):
        self._send_cmd(self._cmd("trig_sweep", sweep=sweep))

    def get_trigger_sweep(self):
        return self.conn.query(self._cmd("trig_get_sweep")).strip()

    def force_trigger(self):
        self.conn.write(self._cmd("trig_force"))

    # --- Acquisition ---
    def run(self):
        self.conn.write(self._cmd("acq_run"))

    def stop(self):
        self.conn.write(self._cmd("acq_stop"))

    def single(self):
        self.conn.write(self._cmd("acq_single"))

    def set_acq_type(self, acq_type):
        self._send_cmd(self._cmd("acq_type", acq_type=acq_type))

    def get_acq_type(self):
        return self.conn.query(self._cmd("acq_get_type")).strip()

    def set_acq_count(self, count):
        self._send_cmd(self._cmd("acq_count", count=count))

    def get_acq_count(self):
        return int(self.conn.query(self._cmd("acq_get_count")))

    def get_sample_rate(self):
        return float(self.conn.query(self._cmd("acq_srate")))

    def set_acq_points(self, points):
        self._send_cmd(self._cmd("acq_points", points=points))

    def get_acq_points(self):
        return int(self.conn.query(self._cmd("acq_get_points")))

    # --- Measurements ---
    def measure_frequency(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_freq", channel=channel))

    def measure_period(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_period", channel=channel))

    def measure_duty_cycle(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_duty", channel=channel))

    def measure_vpp(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_vpp", channel=channel))

    def measure_vmax(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_vmax", channel=channel))

    def measure_vmin(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_vmin", channel=channel))

    def measure_vavg(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_vavg", channel=channel))

    def measure_vrms(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_vrms", channel=channel))

    def measure_amplitude(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_vamplitude", channel=channel))

    def measure_vtop(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_vtop", channel=channel))

    def measure_vbase(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_vbase", channel=channel))

    def measure_rise_time(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_rise_time", channel=channel))

    def measure_fall_time(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_fall_time", channel=channel))

    def measure_overshoot(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_overshoot", channel=channel))

    def measure_preshoot(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_preshoot", channel=channel))

    def measure_phase(self, source1, source2):
        self.check_channel(source1)
        self.check_channel(source2)
        return self._query_float(self._cmd("measure_phase", source1=source1, source2=source2))

    def measure_delay(self, source1, source2):
        self.check_channel(source1)
        self.check_channel(source2)
        return self._query_float(self._cmd("measure_delay", source1=source1, source2=source2))

    def measure_counter(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_counter", channel=channel))

    def measure_pos_width(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_pos_width", channel=channel))

    def measure_neg_width(self, channel):
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_neg_width", channel=channel))

    def measure_clear(self):
        self.conn.write(self._cmd("measure_clear"))

    def measure_all(self, channel):
        """Grab a snapshot of common measurements for a channel. Returns a dict."""
        self.check_channel(channel)
        return {
            "frequency": self.measure_frequency(channel),
            "period": self.measure_period(channel),
            "duty_cycle": self.measure_duty_cycle(channel),
            "vpp": self.measure_vpp(channel),
            "vmax": self.measure_vmax(channel),
            "vmin": self.measure_vmin(channel),
            "vavg": self.measure_vavg(channel),
            "vrms": self.measure_vrms(channel),
            "amplitude": self.measure_amplitude(channel),
            "rise_time": self.measure_rise_time(channel),
            "fall_time": self.measure_fall_time(channel),
        }

    # --- Waveform Data Transfer ---
    def get_waveform_data(self, channel, points=0, fmt="BYTE"):
        """Download waveform data from a channel.

        Returns dict with 'x' (time), 'y' (voltage), and 'preamble' keys.
        """
        import struct
        self.check_channel(channel)
        self.stop()

        self.conn.write(self._cmd("wav_source", channel=channel))
        self.conn.write(self._cmd("wav_format", fmt=fmt))
        self.conn.write(self._cmd("wav_points_mode", mode="NORMal"))
        if points > 0:
            self.conn.write(self._cmd("wav_points", points=points))

        preamble_raw = self.conn.query(self._cmd("wav_get_preamble"))
        preamble = self._parse_preamble(preamble_raw)

        if fmt == "ASCii":
            raw = self.conn.query(self._cmd("wav_get_data"))
            y_raw = [float(v) for v in raw.split(",")]
        else:
            self.conn.write(self._cmd("wav_get_data"))
            raw_bytes = self.conn.inst.read_raw()
            y_raw = self._parse_binary_block(raw_bytes, fmt)

        x_inc = preamble["x_increment"]
        x_orig = preamble["x_origin"]
        y_inc = preamble["y_increment"]
        y_orig = preamble["y_origin"]
        y_ref = preamble["y_reference"]

        x_data = [(i * x_inc) + x_orig for i in range(len(y_raw))]
        y_data = [((val - y_ref) * y_inc) + y_orig for val in y_raw]

        return {"x": x_data, "y": y_data, "preamble": preamble}

    @staticmethod
    def _parse_preamble(preamble_str):
        """Parse the 10-field waveform preamble string."""
        vals = preamble_str.split(",")
        return {
            "format": int(vals[0]),
            "type": int(vals[1]),
            "points": int(vals[2]),
            "count": int(vals[3]),
            "x_increment": float(vals[4]),
            "x_origin": float(vals[5]),
            "x_reference": int(vals[6]),
            "y_increment": float(vals[7]),
            "y_origin": float(vals[8]),
            "y_reference": int(vals[9]),
        }

    @staticmethod
    def _parse_binary_block(raw_bytes, fmt):
        """Parse IEEE 488.2 definite-length block data."""
        import struct
        header_idx = raw_bytes.index(ord('#'))
        num_digits = int(chr(raw_bytes[header_idx + 1]))
        data_length = int(raw_bytes[header_idx + 2: header_idx + 2 + num_digits])
        data_start = header_idx + 2 + num_digits
        data_bytes = raw_bytes[data_start: data_start + data_length]

        if fmt == "BYTE":
            return list(struct.unpack(f"{len(data_bytes)}B", data_bytes))
        elif fmt == "WORD":
            count = len(data_bytes) // 2
            return list(struct.unpack(f"<{count}H", data_bytes))
        else:
            raise ValueError(f"Unsupported binary format: {fmt}")

    # --- Display ---
    def clear_display(self):
        self.conn.write(self._cmd("display_clear"))

    def set_persistence(self, enabled):
        cmd_key = "display_persist_on" if enabled else "display_persist_off"
        self.conn.write(self._cmd(cmd_key))

    def get_persistence(self):
        return self.conn.query(self._cmd("display_get_persist")).strip()

    def set_graticule(self, style):
        self._send_cmd(self._cmd("display_graticule", style=style))

    def get_graticule(self):
        return self.conn.query(self._cmd("display_get_graticule")).strip()

    # --- Save / Recall ---
    def save_image(self, filename):
        self._send_cmd(self._cmd("save_image", filename=filename))

    def save_setup(self, filename):
        self._send_cmd(self._cmd("save_setup", filename=filename))

    def recall_setup(self, filename):
        self._send_cmd(self._cmd("recall_setup", filename=filename))

    # --- Math ---
    def math_on(self):
        self.conn.write(self._cmd("math_display_on"))

    def math_off(self):
        self.conn.write(self._cmd("math_display_off"))

    def set_math_function(self, function):
        self._send_cmd(self._cmd("math_function", function=function))

    def get_math_function(self):
        return self.conn.query(self._cmd("math_get_function")).strip()

    # --- Cursors ---
    def set_cursor_mode(self, mode):
        self._send_cmd(self._cmd("cursor_mode", mode=mode))

    def get_cursor_mode(self):
        return self.conn.query(self._cmd("cursor_get_mode")).strip()

    def set_cursor_x(self, x1=None, x2=None):
        if x1 is not None:
            self.conn.write(self._cmd("cursor_x1", position=x1))
        if x2 is not None:
            self.conn.write(self._cmd("cursor_x2", position=x2))

    def get_cursor_x(self):
        x1 = float(self.conn.query(self._cmd("cursor_get_x1")))
        x2 = float(self.conn.query(self._cmd("cursor_get_x2")))
        return x1, x2

    def set_cursor_y(self, y1=None, y2=None):
        if y1 is not None:
            self.conn.write(self._cmd("cursor_y1", position=y1))
        if y2 is not None:
            self.conn.write(self._cmd("cursor_y2", position=y2))

    def get_cursor_y(self):
        y1 = float(self.conn.query(self._cmd("cursor_get_y1")))
        y2 = float(self.conn.query(self._cmd("cursor_get_y2")))
        return y1, y2


# Channel subclass approach for future v2.0 implementation
# TODO: add some details in `todo.md` about what this entails, if it's worth it, etc.
class Channel:
    def __init__(self, parent, index):
        self.parent = parent
        self.index = index

    def cmd(self, key, **kwargs):
        return self.parent.cmd(key, channel=self.index, **kwargs)

    def write(self, key, **kwargs):
        return self.parent.conn.write(key, channel=self.index, **kwargs)