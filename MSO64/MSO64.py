"""Driver for the Tektronix MSO64 (6 Series MSO)."""

import logging
import struct

from EEequipment.TestEquipment import Oscilloscope
from EEequipment.TestEquipment import PyVISAHandler

logger = logging.getLogger(__name__)


class MSO64(Oscilloscope):
    """
    Driver for the Tektronix MSO64 6 Series mixed-signal oscilloscope.
    Four analog channels, PyVISA over USBTMC or LAN.

    Most of the Oscilloscope base class works as-is once config.ini supplies
    the TekScope spelling of each command. The methods overridden below are the
    ones where Tek differs in *meaning*, not just spelling:

        - horizontal position is a percentage of the record, not seconds
        - there is no immediate-measurement query; measurements are objects
        - the waveform preamble is a set of separate queries, not one string
        - a screenshot has to be saved to the scope's disk and read back
        - the GUI's dropdowns speak Keysight, so their values are translated
    """

    # The OSC tab's dropdowns were written against the Keysight command set.
    # Translating here keeps one shared GUI working for both scopes rather
    # than making the tab ask the driver what words it accepts.
    _TRIG_SOURCES = {"CHANnel1": "CH1", "CHANnel2": "CH2",
                     "CHANnel3": "CH3", "CHANnel4": "CH4"}
    _TRIG_SLOPES = {"POSitive": "RISe", "NEGative": "FALL", "EITHer": "EITher"}
    _ACQ_TYPES = {"NORMal": "SAMple", "AVERage": "AVErage",
                  "HRESolution": "HIRes", "PEAK": "PEAKdetect"}

    # Keysight measurement name -> Tektronix measurement type.
    _MEAS_TYPES = {
        "frequency": "FREQUENCY",
        "period": "PERIOD",
        "duty_cycle": "PDUTY",
        "vpp": "PK2PK",
        "vmax": "MAXIMUM",
        "vmin": "MINIMUM",
        "vavg": "MEAN",
        "vrms": "ACRMS",
        "amplitude": "AMPLITUDE",
        "vtop": "TOP",
        "vbase": "BASE",
        "rise_time": "RISETIME",
        "fall_time": "FALLTIME",
        "overshoot": "POVERSHOOT",
        "preshoot": "NOVERSHOOT",
        "pos_width": "PWIDTH",
        "neg_width": "NWIDTH",
        "phase": "PHASE",
        "delay": "DELAY",
    }

    def __init__(self, address):
        super().__init__("MSO64", PyVISAHandler(address))
        self.channel_count = 4
        # Slot index of the scratch measurement object, allocated on first use.
        self._scratch_slot = None

    def read_value(self):
        return self.test_conn()

    def disconnect(self):
        """Drop the scratch measurement before closing so repeated connect /
        disconnect cycles don't leave a pile of measurement badges on screen."""
        self._release_scratch_slot()
        super().disconnect()

    # =========================================================================
    # Timebase -- Tek counts horizontal position in percent of record
    # =========================================================================
    def set_timebase_position(self, position):
        """Set the delay in seconds, as the Keysight-flavoured GUI supplies it.

        Keysight's :TIMebase:POSition is the time at screen centre relative to
        the trigger; Tek's HORizontal:POSition is where the trigger sits as a
        percentage of the record. Ten divisions span the screen, so a delay of
        `position` moves the trigger left by position/(10*scale) of the record.
        """
        percent = 50.0 - (position / (10.0 * self.get_timebase_scale())) * 100.0
        percent = min(100.0, max(0.0, percent))
        self._send_cmd(self._cmd("timebase_position", position=percent))

    def get_timebase_position(self):
        """Return the horizontal position as seconds of delay (see setter)."""
        percent = self._query_float(self._cmd("timebase_get_position"))
        if percent is None:
            return None
        return (50.0 - percent) / 100.0 * (10.0 * self.get_timebase_scale())

    def set_timebase_reference(self, reference):
        raise NotImplementedError(
            "MSO64 has no timebase reference setting; use set_timebase_position()")

    def get_timebase_reference(self):
        raise NotImplementedError(
            "MSO64 has no timebase reference setting; use get_timebase_position()")

    # =========================================================================
    # Trigger / acquisition -- translate the GUI's Keysight vocabulary
    # =========================================================================
    def set_trigger_source(self, source):
        self._send_cmd(self._cmd("trig_source",
                                 source=self._TRIG_SOURCES.get(source, source)))

    def set_trigger_slope(self, slope):
        self._send_cmd(self._cmd("trig_slope",
                                 slope=self._TRIG_SLOPES.get(slope, slope)))

    def set_acq_type(self, acq_type):
        self._send_cmd(self._cmd("acq_type",
                                 acq_type=self._ACQ_TYPES.get(acq_type, acq_type)))

    def run(self):
        """Start continuous acquisition.

        single() leaves ACQuire:STOPAfter on SEQuence, so Run has to put it
        back or the scope stops again after one acquisition.
        """
        with self.conn.transaction():
            self.conn.write(self._cmd("acq_run_continuous"))
            self.conn.write(self._cmd("acq_run"))

    # =========================================================================
    # Measurements -- add / configure / read / remove a scratch measurement
    # =========================================================================
    def _allocate_scratch_slot(self):
        """Reserve a measurement slot that isn't already in use on the scope."""
        if self._scratch_slot is not None:
            return self._scratch_slot

        used = []
        existing = self.conn.query(self._cmd("meas_list")).strip()
        if existing and existing.upper() != "NONE":
            for name in existing.split(","):
                digits = "".join(c for c in name if c.isdigit())
                if digits:
                    used.append(int(digits))

        slot = max(used) + 1 if used else 1
        self.conn.write(self._cmd("meas_add", slot=slot))
        self._scratch_slot = slot
        logger.debug(f"MSO64: allocated scratch measurement MEAS{slot}")
        return slot

    def _release_scratch_slot(self):
        """Best-effort removal of the scratch measurement."""
        if self._scratch_slot is None:
            return
        try:
            self.conn.write(self._cmd("meas_delete", slot=self._scratch_slot))
        except Exception as e:
            logger.debug(f"MSO64: could not delete scratch measurement: {e}")
        finally:
            self._scratch_slot = None

    def _measure_immediate(self, meas_name, channel, channel2=None):
        """Point the scratch measurement at a channel and read one result.

        Returns None when the scope has no valid result (a measurement it
        cannot make on the current waveform reports NAN or 9.9E37), matching
        the base class's convention.
        """
        self.check_channel(channel)
        if channel2 is not None:
            self.check_channel(channel2)

        meas_type = self._MEAS_TYPES[meas_name]
        with self.conn.transaction():
            slot = self._allocate_scratch_slot()
            self.conn.write(self._cmd("meas_type", slot=slot, meas_type=meas_type))
            self.conn.write(self._cmd("meas_source", slot=slot, channel=channel))
            if channel2 is not None:
                self.conn.write(self._cmd("meas_source2", slot=slot, channel=channel2))
            self.conn.query(self._cmd("opc"))
            raw = self.conn.query(self._cmd("meas_result", slot=slot))

        try:
            val = float(raw)
        except ValueError:
            return None
        # Tek reports "no result" two ways: NAN (which float() accepts happily)
        # and the 9.9E37 sentinel the base class knows about.
        if val != val or abs(val) > 9.9e36:
            return None
        return val

    def measure_frequency(self, channel):
        return self._measure_immediate("frequency", channel)

    def measure_period(self, channel):
        return self._measure_immediate("period", channel)

    def measure_duty_cycle(self, channel):
        return self._measure_immediate("duty_cycle", channel)

    def measure_vpp(self, channel):
        return self._measure_immediate("vpp", channel)

    def measure_vmax(self, channel):
        return self._measure_immediate("vmax", channel)

    def measure_vmin(self, channel):
        return self._measure_immediate("vmin", channel)

    def measure_vavg(self, channel):
        return self._measure_immediate("vavg", channel)

    def measure_vrms(self, channel):
        return self._measure_immediate("vrms", channel)

    def measure_amplitude(self, channel):
        return self._measure_immediate("amplitude", channel)

    def measure_vtop(self, channel):
        return self._measure_immediate("vtop", channel)

    def measure_vbase(self, channel):
        return self._measure_immediate("vbase", channel)

    def measure_rise_time(self, channel):
        return self._measure_immediate("rise_time", channel)

    def measure_fall_time(self, channel):
        return self._measure_immediate("fall_time", channel)

    def measure_overshoot(self, channel):
        return self._measure_immediate("overshoot", channel)

    def measure_preshoot(self, channel):
        return self._measure_immediate("preshoot", channel)

    def measure_pos_width(self, channel):
        return self._measure_immediate("pos_width", channel)

    def measure_neg_width(self, channel):
        return self._measure_immediate("neg_width", channel)

    def measure_phase(self, source1, source2):
        return self._measure_immediate("phase", source1, source2)

    def measure_delay(self, source1, source2):
        return self._measure_immediate("delay", source1, source2)

    def measure_counter(self, channel):
        """Not available on the 6 Series -- use measure_frequency()."""
        return None

    # =========================================================================
    # Waveform transfer -- preamble comes back as separate queries
    # =========================================================================
    def get_waveform_data(self, channel, points=0, fmt="BYTE"):
        """Download a waveform, returning the same dict shape as the base class.

        `fmt` is accepted in the base class's vocabulary ("BYTE"/"WORD"/"ASCii")
        and translated to Tek's DATa:ENCdg wording.
        """
        self.check_channel(channel)
        self.stop()

        ascii_mode = fmt == "ASCii"
        width = 2 if fmt == "WORD" else 1
        encoding = "ASCii" if ascii_mode else "SRIbinary"

        with self.conn.transaction():
            self.conn.write(self._cmd("wav_source", channel=channel))
            self.conn.write(self._cmd("wav_format", fmt=encoding))
            self.conn.write(self._cmd("wav_bytes", width=width))
            self.conn.write(self._cmd("wav_start"))
            record = points if points > 0 else int(float(
                self.conn.query(self._cmd("acq_get_points"))))
            self.conn.write(self._cmd("wav_stop", points=record))

            x_inc = float(self.conn.query(self._cmd("wav_x_incr")))
            x_zero = float(self.conn.query(self._cmd("wav_x_zero")))
            y_mult = float(self.conn.query(self._cmd("wav_y_mult")))
            y_off = float(self.conn.query(self._cmd("wav_y_off")))
            y_zero = float(self.conn.query(self._cmd("wav_y_zero")))
            n_points = int(float(self.conn.query(self._cmd("wav_points"))))

            if ascii_mode:
                raw = self.conn.query(self._cmd("wav_get_data"))
                y_raw = [float(v) for v in raw.split(",")]
            else:
                block = self._extract_ieee_block(
                    self.conn.query_raw(self._cmd("wav_get_data")))
                # SRIbinary is signed little-endian, unlike the unsigned codes
                # the Keysight sends.
                code = "b" if width == 1 else "h"
                count = len(block) // width
                y_raw = list(struct.unpack(f"<{count}{code}", block[:count * width]))

        x_data = [x_zero + (i * x_inc) for i in range(len(y_raw))]
        y_data = [((val - y_off) * y_mult) + y_zero for val in y_raw]

        preamble = {
            "format": fmt,
            "type": "NORMAL",
            "points": n_points,
            "count": 1,
            "x_increment": x_inc,
            "x_origin": x_zero,
            "x_reference": 0,
            "y_increment": y_mult,
            "y_origin": y_zero,
            "y_reference": y_off,
        }
        return {"x": x_data, "y": y_data, "preamble": preamble}

    # =========================================================================
    # Screenshot -- save to the scope's disk, read it back, then clean up
    # =========================================================================
    def get_screenshot(self):
        """Return the current display as PNG bytes on the host."""
        scope_path = self.registry.get_command(self.model, "command", "screenshot_path")

        with self.conn.transaction():
            self.conn.write(self._cmd("save_image", filename=scope_path))
            # The save is asynchronous; without waiting, READFile can hit a
            # file that is not there yet or is still being written.
            self.conn.query(self._cmd("opc"))
            # FILESystem:READFile returns the file's raw bytes with no IEEE
            # block header, so this is used as-is.
            data = self.conn.query_raw(self._cmd("file_read", filename=scope_path))
            try:
                self.conn.write(self._cmd("file_delete", filename=scope_path))
            except Exception as e:
                logger.debug(f"MSO64: could not delete {scope_path} on scope: {e}")

        return bytes(data)
