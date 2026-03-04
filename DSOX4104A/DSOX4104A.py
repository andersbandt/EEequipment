

import struct

# import user created Equipment modules
from EEequipment.TestEquipment import Oscilloscope
from EEequipment.TestEquipment import PyVISAHandler





class DSOX4104A(Oscilloscope):
    """
    Driver for the Keysight DSO-X 4104A InfiniiVision oscilloscope.
    Communicates via PyVISA (USB or LAN).
    """

    def __init__(self, address):
        '''
        Init the VISA (pyvisa) connection and get the basic product info
        '''
        super().__init__("DSOX4104A", PyVISAHandler(address))
        self.channel_count = 4

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

    # =========================================================================
    # System
    # =========================================================================
    def check_error(self):
        """Query the error queue. Returns error string or None if no error."""
        cmd = self.registry.get_command(self.model, "command", "error")
        response = self.conn.query(cmd)
        # Format: "+0,"No error" or error_code,"error message"
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

    # =========================================================================
    # Channel Control
    # =========================================================================
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
        """Set channel coupling. coupling: 'AC' or 'DC'."""
        self.check_channel(channel)
        self._send_cmd(self._cmd("chan_coupling", channel=channel, coupling=coupling))

    def get_coupling(self, channel):
        self.check_channel(channel)
        return self.conn.query(self._cmd("chan_get_coupling", channel=channel)).strip()

    def set_scale(self, channel, scale):
        """Set vertical scale (V/div) for a channel."""
        self.check_channel(channel)
        self._send_cmd(self._cmd("chan_scale", channel=channel, scale=scale))

    def get_scale(self, channel):
        self.check_channel(channel)
        return float(self.conn.query(self._cmd("chan_get_scale", channel=channel)))

    def set_offset(self, channel, offset):
        """Set vertical offset (V) for a channel."""
        self.check_channel(channel)
        self._send_cmd(self._cmd("chan_offset", channel=channel, offset=offset))

    def get_offset(self, channel):
        self.check_channel(channel)
        return float(self.conn.query(self._cmd("chan_get_offset", channel=channel)))

    def set_probe(self, channel, ratio):
        """Set probe attenuation ratio (e.g. 1, 10, 100)."""
        self.check_channel(channel)
        self._send_cmd(self._cmd("chan_probe", channel=channel, ratio=ratio))

    def get_probe(self, channel):
        self.check_channel(channel)
        return float(self.conn.query(self._cmd("chan_get_probe", channel=channel)))

    def set_bw_limit(self, channel, enabled):
        """Enable or disable bandwidth limit on a channel."""
        self.check_channel(channel)
        cmd_key = "chan_bw_limit_on" if enabled else "chan_bw_limit_off"
        self._send_cmd(self._cmd(cmd_key, channel=channel))

    def get_bw_limit(self, channel):
        self.check_channel(channel)
        return self.conn.query(self._cmd("chan_get_bw_limit", channel=channel)).strip()

    def set_impedance(self, channel, impedance):
        """Set channel input impedance. impedance: 'FIFTy' or 'ONEMeg'."""
        self.check_channel(channel)
        self._send_cmd(self._cmd("chan_impedance", channel=channel, impedance=impedance))

    def get_impedance(self, channel):
        self.check_channel(channel)
        return self.conn.query(self._cmd("chan_get_impedance", channel=channel)).strip()

    def set_label(self, channel, label):
        """Set display label for a channel."""
        self.check_channel(channel)
        self._send_cmd(self._cmd("chan_label", channel=channel, label=label))

    def get_label(self, channel):
        self.check_channel(channel)
        return self.conn.query(self._cmd("chan_get_label", channel=channel)).strip().strip('"')

    # =========================================================================
    # Timebase
    # =========================================================================
    def set_timebase_scale(self, scale):
        """Set horizontal time/div in seconds."""
        self._send_cmd(self._cmd("timebase_scale", scale=scale))

    def get_timebase_scale(self):
        return float(self.conn.query(self._cmd("timebase_get_scale")))

    def set_timebase_position(self, position):
        """Set horizontal position (delay) in seconds."""
        self._send_cmd(self._cmd("timebase_position", position=position))

    def get_timebase_position(self):
        return float(self.conn.query(self._cmd("timebase_get_position")))

    def set_timebase_mode(self, mode):
        """Set timebase mode: 'MAIN', 'WINDow', 'XY', or 'ROLL'."""
        self._send_cmd(self._cmd("timebase_mode", mode=mode))

    def get_timebase_mode(self):
        return self.conn.query(self._cmd("timebase_get_mode")).strip()

    def set_timebase_reference(self, reference):
        """Set time reference position: 'LEFT', 'CENTer', or 'RIGHt'."""
        self._send_cmd(self._cmd("timebase_ref", reference=reference))

    def get_timebase_reference(self):
        return self.conn.query(self._cmd("timebase_get_ref")).strip()

    # =========================================================================
    # Trigger
    # =========================================================================
    def set_trigger_mode(self, mode):
        """Set trigger mode: 'EDGE', 'GLITch', 'PATTern', 'TV', etc."""
        self._send_cmd(self._cmd("trig_mode", mode=mode))

    def get_trigger_mode(self):
        return self.conn.query(self._cmd("trig_get_mode")).strip()

    def set_trigger_source(self, source):
        """Set edge trigger source: 'CHANnel1'-'CHANnel4', 'EXTernal', 'LINE'."""
        self._send_cmd(self._cmd("trig_source", source=source))

    def get_trigger_source(self):
        return self.conn.query(self._cmd("trig_get_source")).strip()

    def set_trigger_level(self, channel, level):
        """Set trigger level in volts for a given channel."""
        self.check_channel(channel)
        self._send_cmd(self._cmd("trig_level", channel=channel, level=level))

    def get_trigger_level(self, channel):
        self.check_channel(channel)
        return float(self.conn.query(self._cmd("trig_get_level", channel=channel)))

    def set_trigger_slope(self, slope):
        """Set edge trigger slope: 'POSitive', 'NEGative', 'EITHer', 'ALTernate'."""
        self._send_cmd(self._cmd("trig_slope", slope=slope))

    def get_trigger_slope(self):
        return self.conn.query(self._cmd("trig_get_slope")).strip()

    def set_trigger_coupling(self, coupling):
        """Set trigger coupling: 'AC', 'DC', 'LFReject'."""
        self._send_cmd(self._cmd("trig_coupling", coupling=coupling))

    def get_trigger_coupling(self):
        return self.conn.query(self._cmd("trig_get_coupling")).strip()

    def set_trigger_sweep(self, sweep):
        """Set trigger sweep mode: 'AUTO' or 'NORMal'."""
        self._send_cmd(self._cmd("trig_sweep", sweep=sweep))

    def get_trigger_sweep(self):
        return self.conn.query(self._cmd("trig_get_sweep")).strip()

    def force_trigger(self):
        self.conn.write(self._cmd("trig_force"))

    # =========================================================================
    # Acquisition Control
    # =========================================================================
    def run(self):
        self.conn.write(self._cmd("acq_run"))

    def stop(self):
        self.conn.write(self._cmd("acq_stop"))

    def single(self):
        self.conn.write(self._cmd("acq_single"))

# TODO: audit the abstract class naming here
    def set_acq_type(self, acq_type):
        """Set acquisition type: 'NORMal', 'AVERage', 'HRESolution', 'PEAK'."""
        self._send_cmd(self._cmd("acq_type", acq_type=acq_type))

# TODO: rename acquire to acq in below functions

    def get_acquire_type(self):
        return self.conn.query(self._cmd("acq_get_type")).strip()

    def set_acq_count(self, count):
        """Set averaging count (used when acquire type is AVERage)."""
        self._send_cmd(self._cmd("acq_count", count=count))

    def get_acq_count(self):
        return int(self.conn.query(self._cmd("acq_get_count")))

    def get_sample_rate(self):
        """Get the current sample rate in Sa/s."""
        return float(self.conn.query(self._cmd("acq_srate")))

    def set_acquire_points(self, points):
        """Set number of acquisition points."""
        self._send_cmd(self._cmd("acq_points", points=points))

    def get_acquire_points(self):
        return int(self.conn.query(self._cmd("acq_get_points")))

    # =========================================================================
    # Measurements
    # =========================================================================
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
        """Measure voltage amplitude (Vtop - Vbase)."""
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
        """Measure phase between two channels in degrees."""
        self.check_channel(source1)
        self.check_channel(source2)
        return self._query_float(self._cmd("measure_phase", source1=source1, source2=source2))

    def measure_delay(self, source1, source2):
        """Measure delay between two channels in seconds."""
        self.check_channel(source1)
        self.check_channel(source2)
        return self._query_float(self._cmd("measure_delay", source1=source1, source2=source2))

    def measure_counter(self, channel):
        """Use hardware frequency counter for high-accuracy frequency measurement."""
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_counter", channel=channel))

    def measure_pos_width(self, channel):
        """Measure positive pulse width."""
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_pos_width", channel=channel))

    def measure_neg_width(self, channel):
        """Measure negative pulse width."""
        self.check_channel(channel)
        return self._query_float(self._cmd("measure_neg_width", channel=channel))

    def measure_clear(self):
        """Clear all measurements from the display."""
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

    # =========================================================================
    # Waveform Data Transfer
    # =========================================================================
    def get_waveform_data(self, channel, points=0, fmt="BYTE"):
        """
        Download waveform data from a channel.

        Args:
            channel: Channel number (1-4)
            points: Number of points (0 = max available)
            fmt: Data format - 'BYTE' (uint8), 'WORD' (uint16), or 'ASCii'

        Returns:
            dict with keys:
                'x': list of time values in seconds
                'y': list of voltage values in volts
                'preamble': raw preamble dict
        """
        self.check_channel(channel)

        # stop acquisition to get stable data
        self.stop()

        # configure waveform source and format
        self.conn.write(self._cmd("wav_source", channel=channel))
        self.conn.write(self._cmd("wav_format", fmt=fmt))
        self.conn.write(self._cmd("wav_points_mode", mode="NORMal"))
        if points > 0:
            self.conn.write(self._cmd("wav_points", points=points))

        # get preamble (10 comma-separated values)
        preamble_raw = self.conn.query(self._cmd("wav_get_preamble"))
        preamble = self._parse_preamble(preamble_raw)

        # get raw data
        if fmt == "ASCii":
            raw = self.conn.query(self._cmd("wav_get_data"))
            y_raw = [float(v) for v in raw.split(",")]
        else:
            # Binary transfer - use read_raw for IEEE 488.2 block data
            self.conn.write(self._cmd("wav_get_data"))
            raw_bytes = self.conn.inst.read_raw()
            y_raw = self._parse_binary_block(raw_bytes, fmt)

        # convert to voltage and time using preamble
        x_inc = preamble["x_increment"]
        x_orig = preamble["x_origin"]
        y_inc = preamble["y_increment"]
        y_orig = preamble["y_origin"]
        y_ref = preamble["y_reference"]

        x_data = [(i * x_inc) + x_orig for i in range(len(y_raw))]
        y_data = [((val - y_ref) * y_inc) + y_orig for val in y_raw]

        return {
            "x": x_data,
            "y": y_data,
            "preamble": preamble,
        }

    def _parse_preamble(self, preamble_str):
        """Parse the 10-field waveform preamble string."""
        vals = preamble_str.split(",")
        return {
            "format": int(vals[0]),        # 0=BYTE, 1=WORD, 4=ASCii
            "type": int(vals[1]),           # 0=NORMal, 1=PEAK, 2=AVERage, 3=HRESolution
            "points": int(vals[2]),
            "count": int(vals[3]),
            "x_increment": float(vals[4]),
            "x_origin": float(vals[5]),
            "x_reference": int(vals[6]),
            "y_increment": float(vals[7]),
            "y_origin": float(vals[8]),
            "y_reference": int(vals[9]),
        }

    def _parse_binary_block(self, raw_bytes, fmt):
        """Parse IEEE 488.2 definite-length block data (#NXXXXXXXXX<data>)."""
        # Find the '#' header
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

    # =========================================================================
    # Display
    # =========================================================================
    def clear_display(self):
        self.conn.write(self._cmd("display_clear"))

    def set_persistence(self, enabled):
        """Enable infinite persistence or turn it off."""
        cmd_key = "display_persist_on" if enabled else "display_persist_off"
        self.conn.write(self._cmd(cmd_key))

    def get_persistence(self):
        return self.conn.query(self._cmd("display_get_persist")).strip()

    def set_graticule(self, style):
        """Set graticule style: 'FULL', 'HALF', 'NONE'."""
        self._send_cmd(self._cmd("display_graticule", style=style))

    def get_graticule(self):
        return self.conn.query(self._cmd("display_get_graticule")).strip()

    # =========================================================================
    # Save / Recall
    # =========================================================================
    def save_image(self, filename):
        """Save a screenshot to the scope's filesystem."""
        self._send_cmd(self._cmd("save_image", filename=filename))

    def save_setup(self, filename):
        """Save current setup to a file on the scope."""
        self._send_cmd(self._cmd("save_setup", filename=filename))

    def recall_setup(self, filename):
        """Recall a saved setup from the scope's filesystem."""
        self._send_cmd(self._cmd("recall_setup", filename=filename))

    # =========================================================================
    # Math
    # =========================================================================
    def math_on(self):
        self.conn.write(self._cmd("math_display_on"))

    def math_off(self):
        self.conn.write(self._cmd("math_display_off"))

    def set_math_function(self, function):
        """Set math function, e.g. 'ADD', 'SUBTract', 'MULTiply', 'FFT', etc."""
        self._send_cmd(self._cmd("math_function", function=function))

    def get_math_function(self):
        return self.conn.query(self._cmd("math_get_function")).strip()

    # =========================================================================
    # Cursors
    # =========================================================================
    def set_cursor_mode(self, mode):
        """Set cursor mode: 'OFF', 'MANual', 'WAVeform', 'MEASurement'."""
        self._send_cmd(self._cmd("cursor_mode", mode=mode))

    def get_cursor_mode(self):
        return self.conn.query(self._cmd("cursor_get_mode")).strip()

    def set_cursor_x(self, x1=None, x2=None):
        """Set X cursor positions in seconds."""
        if x1 is not None:
            self.conn.write(self._cmd("cursor_x1", position=x1))
        if x2 is not None:
            self.conn.write(self._cmd("cursor_x2", position=x2))

    def get_cursor_x(self):
        x1 = float(self.conn.query(self._cmd("cursor_get_x1")))
        x2 = float(self.conn.query(self._cmd("cursor_get_x2")))
        return x1, x2

    def set_cursor_y(self, y1=None, y2=None):
        """Set Y cursor positions in volts."""
        if y1 is not None:
            self.conn.write(self._cmd("cursor_y1", position=y1))
        if y2 is not None:
            self.conn.write(self._cmd("cursor_y2", position=y2))

    def get_cursor_y(self):
        y1 = float(self.conn.query(self._cmd("cursor_get_y1")))
        y2 = float(self.conn.query(self._cmd("cursor_get_y2")))
        return y1, y2
