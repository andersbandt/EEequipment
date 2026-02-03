

# import needed modules
from pyvisa import ResourceManager
import pyvisa.errors
import usb
import configparser

# import Equipment parent class
from EEequipment.TestEquipment import PowerSupply
from EEequipment.TestEquipment import PyVISAHandler


class SPD3303X(PowerSupply):
    """
    Class for interacting with the SPD3303 Siglent Power Supply
    """

    ch1_v_m = None
    ch1_v_b = None
    ch1_i_b = None
    ch2_v_m = None
    ch2_v_b = None
    ch2_i_b = None
    channel_count = 2
    save_file_count = 5
    INDEPENDENT_MODE = 0
    SERIES_MODE = 1
    PARALLEL_MODE = 2
    manufacturer = ""
    product_type = ""
    series_number = ""
    software_version = ""
    hardware_version = ""

    def __init__(self, address):
        '''
        Init the VISA (pyvisa) connection and get the basic product info
        '''
        super().__init__("SPD3303X", PyVISAHandler(address))
        self.channel_count = 2
        # load calibration constants
        self._load_cal()

    def _load_cal(self):
        # read in parameters from the config file
        self.ch1_v_m = float(self.config["CH1"]["v_slope"])
        self.ch1_v_b = float(self.config["CH1"]["v_offset"])
        self.ch1_i_b = float(self.config["CH1"]["i_offset"])

        self.ch2_v_m = float(self.config["CH2"]["v_slope"])
        self.ch2_v_b = float(self.config["CH2"]["v_offset"])
        self.ch2_i_b = float(self.config["CH2"]["i_offset"])

    def __get_product_info(self):
        '''
        Query the manufacturer, product type, series, series no., software version, hardware version
        '''
        idn = self.conn.query('*IDN?')

        # NOTE: can't uncomment below code because my equipment simply returns 'Siglent Techno' from query
        # resp_arr = idn.split(",")
        # self.manufacturer = resp_arr[0]
        # self.product_type = resp_arr[1]
        # self.series_number = resp_arr[2]
        # self.software_version = resp_arr[3]
        # self.hardware_version = resp_arr[4]
        return idn

    def _send_cmd(self, cmd):
        '''
        Generic call to send command with error checking
        '''
        self.conn.write(cmd)
        self.check_error()

    def save(self, file_num):
        '''
        Save the current state into non-volatile memory
        '''
        if file_num not in range(1, self.save_file_count + 1):
            raise self.SPD3303Exception('20', f'Save file must be an integer 1 - {self.save_file_count}')
        else:
            self.conn.write(f"*SAV {file_num}")

    def recall(self, file_num):
        '''
        Recall state that had been saved from nonvolatile memory
        '''
        if file_num not in range(1, self.save_file_count + 1):
            raise self.SPD3303Exception('20', f'Save file must be an integer 1 - {self.save_file_count}')
        else:
            self.conn.write(f"*RCL {file_num}")

    def select_channel(self, channel):
        '''
        Select the channel to be operated on
        '''
        if channel not in range(1, self.channel_count + 1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.conn.write(f"INSTrument CH{channel}")

    ##################################
    #### get/set functions  ##########
    ##################################
    def set_raw_voltage(self, channel, value):
        self._send_cmd(f"CH{channel}:VOLTage {value}")

    def set_voltage(self, value, channel=1):
        '''
        Set the voltage value for the selected channel
        '''
        if type(value) != float:
            return False

        self.check_channel(channel)

        def get_ch_v_cal(ch):
            if ch == 1:
                return self.ch1_v_m, self.ch1_v_b
            elif ch == 2:
                return self.ch2_v_m, self.ch2_v_b

        # do some calibration correction (because Siglent makes a shitty product that is a pain to calibrate)
        slope, offset = get_ch_v_cal(channel)
        cal_value = round(value + value * slope + offset, 3)
        self._send_cmd(f"CH{channel}:VOLTage {cal_value}")
        return True

    def get_active_channel(self):
        '''
        Query for the active channel
        '''
        self.conn.write("INSTrument?")
        return self.conn.read()

    def get_voltage(self, channel=1):
        '''
        Get the voltage value for a given channel
        '''
        self.check_channel(channel)

        self.conn.write(f"MEASure:VOLTage? CH{channel}")
        return float(self.conn.read())

    def get_raw_current(self, channel):
        raw_current = float(self.conn.query(f"MEASure:CURRent? CH{channel}"))
        return raw_current

    def get_current(self, channel):
        '''
        Get the current value for a given channel
        '''
        self.check_channel(channel)

        raw_current = self.get_raw_current(channel)
        if channel == 1:
            return raw_current - self.ch1_i_b
        elif channel == 2:
            return raw_current - self.ch2_i_b

    def get_power(self, channel):
        '''
        Get the power value for a given channel
        '''
        self.check_channel(channel)

        self.conn.write(f"MEASure:POWEr? CH{channel}")
        return float(self.conn.read())

    ##################################
    #### control functions  ##########
    ##################################

    def set_operation_mode(self, mode):
        if mode == 0 or mode == 1 or mode == 2:
            self.conn.write(f"OUTPut:TRACK {mode}")
        else:
            raise self.SPD3303Exception('22', f'Invalid Operation Mode')

    def turn_on_waveform_display(self, channel):
        '''
        Turn on the Waveform Display function of specified channel
        '''
        if channel not in range(1, self.channel_count + 1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self._send_cmd(f"OUTPut:WAVE CH{channel},ON")

    def turn_off_waveform_display(self, channel):
        '''
        Turn on the Waveform Display function of specified channel
        '''
        if channel not in range(1, self.channel_count + 1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.conn.write(f"OUTPut:WAVE CH{channel},OFF")

    def set_timing_parameters(self, channel, group, voltage, current, time):
        '''
        Set the timing parameters of specified channel, group setting the voltage current and execution time
        '''
        if channel not in range(1, self.channel_count + 1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.conn.write(f"TIMEr:SET CH{channel},{group},{voltage},{current},{time}")

    def query_timing_parameters(self, channel, group):
        '''
        Query for the voltage/current/time parameters of specified group of specific channels
        '''
        if channel not in range(1, self.channel_count + 1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.conn.write(f"TIMEr:SET? CH{channel},{group}")
            response = self.conn.read()
            resp_arr = response.split(",")
            return (resp_arr[0], (resp_arr[1], resp_arr[2]))

    def turn_on_timer(self, channel):
        '''
        Turn on timer function of specific channel
        '''
        if channel not in range(1, self.channel_count + 1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.conn.write(f"TIMEr CH{channel},ON")

    def turn_off_timer(self, channel):
        '''
        Turn off timer fuction of specific channel
        '''
        if channel not in range(1, self.channel_count + 1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.conn.write(f"TIMEr CH{channel},OFF")

    ##################################
    #### etc functions  ##############
    ##################################
    def check_status(self):
        '''
        Return the top level info about the power supply functional status
        '''
        cmd = self.registry.get_command(self.model, "command", "status")
        hex_num = self.conn.query(cmd)
        return self._decode_hex(hex_num)

    def check_version(self):
        '''
        Query the software version of the equipment
        '''
        self.conn.write("SYSTem:VERSion?")
        return self.conn.read()

    def _decode_hex(self, hex_value):
        # Convert hex value to an integer
        value = int(hex_value, 16)

        # Dictionary to store decoded states
        decoded_info = {"ch1_mode": "CV" if not (value & 0x01) else "CC",
                        "ch2_mode": "CV" if not (value & 0x02) else "CC"}

        # Decode each bit according to the given states

        mode_bits = (value >> 2) & 0x03
        if mode_bits == 0x01:
            decoded_info["channel_mode"] = "Independent"
        elif mode_bits == 0x02:
            decoded_info["channel_mode"] = "Parallel"
        else:
            decoded_info["channel_mode"] = "Unknown"

        decoded_info["ch1_state"] = "OFF" if not (value & 0x10) else "ON"
        decoded_info["ch2_state"] = "OFF" if not (value & 0x20) else "ON"

        decoded_info["timer1"] = "OFF" if not (value & 0x40) else "ON"
        decoded_info["timer2"] = "OFF" if not (value & 0x80) else "ON"

        decoded_info["ch1_display"] = "Digital" if not (value & 0x100) else "Waveform"
        decoded_info["ch2_display"] = "Digital" if not (value & 0x200) else "Waveform"

        return decoded_info

    ##################################
    #### networking functions  #######
    ##################################
    def assign_ip_addr(self, ip):
        '''
        Assign a static Internet Protocol (IP) address for the instrument
        WARNING: This command is invalid when DHCP is on
        '''
        self._send_cmd(f"IPaddr {ip}")

    def query_ip_addr(self):
        '''
        Query the static Internet Protocol (IP) address for the instrument
        '''
        self.conn.write(f"IPaddr?")
        return self.conn.read()

    def assign_subnet_mask(self, subnet_mask):
        '''
        Assign a subnet mask for the instrument
        WARING: This command is invalid when DHCP is on
        '''
        self._send_cmd(f"MASKaddr {subnet_mask}")

    def query_subnet_mask(self):
        '''
        Query the subnet mask for the instrument
        '''
        self.conn.write(f"MASKaddr?")
        return self.conn.read()

    def assign_gate_address(self, gate_addr):
        '''
        Assign a gate address for the instrument
        WARING: This command is invalid when DHCP is on
        '''
        self._send_cmd(f"GATEaddr {gate_addr}")

    def query_gate_address(self):
        '''
        Query the gate address for the instrument
        WARING: This command is invalid when DHCP is on
        '''
        self.conn.write(f"GATEaddr?")
        return self.conn.read()

    def dhcp(self, state):
        '''
        Turn on or off DHCP
        '''
        if state:
            self.conn.write(f"DHCP ON")
        else:
            self.conn.write(f"DHCP OFF")

    def query_dhcp(self):
        '''
        Query to see the status of DHCP
        '''
        self.conn.write(f"DHCP?")
        return self.conn.read()

    ##################################
    #### calibration functions  ######
    ##################################
    def cal_voltage(self, channel, point, actual_v):
        #cmd = f"CAL:VOLT ch{channel},{point},{actual_v}"
        cmd = f"CALibration:VOLTage CH{channel},{point},{actual_v}"
        print(cmd)
        self.conn.write(cmd)

    def cal_current(self, channel, point, actual_i):
        cmd = f"CAL:CURR CH{channel},{point},{actual_i}"
        print(cmd)
        self.conn.write(cmd)

    def cal_recall(self):
        cmd = "*CALRCL"
        print(f"SPD3303X: querying {cmd}")
        print(self.conn.query("CALRCL"))

    def cal_clear(self, channel, cal_type):
        NR1 = -1  # for "setting" calibration coefficients
        NR2 = -1  # for "display" calibration coefficients
        if channel == 1:
            if cal_type == "VOLTAGE":
                NR1 = 0
                NR2 = 1
            elif cal_type == "CURRENT":
                NR1 = 2
                NR2 = 3
        elif channel == 2:
            if cal_type == "VOLTAGE":
                NR1 = 4
                NR2 = 5
            elif cal_type == "CURRENT":
                NR1 = 6
                NR2 = 7

        self.conn.write(f"*CALCLS {NR1}")
        self.conn.write(f"*CALCLS {NR2}")
        print(f"Cleared calibration with NR values of {NR1},{NR2}")

    def cal_clear_all(self):
        self.conn.write("*CALCLS 8")

    def cal_save(self):
        self.conn.write("*CALST")

