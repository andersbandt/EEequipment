

# import needed modules
import pyvisa
import usb

# import Equipment parent class
from EEequipment.Equipment import Equipment


# TODO: figure out how to get rid of the "having to press connect twice" issue
class SPD3303X(Equipment):
    """
    Class for interacting with the SPD3303 Siglent Power Supply
    """

    class SPD3303Exception(Exception):
        '''
        Exception raised when a call returns an error message
        '''
        def __init__(self, code, message):
            self.code = code
            self.message = message
            super().__init__(self.message)

        def __str__(self):
            return f'Error Code: {self.code} -> {self.message}'
            
    scpi = None
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

    def __init__(self, instadd):
        '''
        Init the VISA (pyvisa) connection and get the basic product info
        '''
        rm = pyvisa.ResourceManager()
        try:
            self.inst = rm.open_resource(instadd)
        except usb.core.USBError:
            return
        self.inst.write_termination = '\n'
        self.inst.read_termination = '\n'
        self.inst.timeout = 2*1000  # NOTE: used to be 4 seconds

    def test_conn(self):
        print("SPD3303X: issuing IDN? command")
        try:
            idn = self.__get_product_info()
        except usb.core.USBError:
            print("USB operation to query instrument did not work!")
            return False
        print(f"IDN: {idn}")
        return idn

    def close(self):
        '''
        Close the socket connection
        '''
        self.inst.close()

    def __get_product_info(self):
        '''
        Query the manufacturer, product type, series, series no., software version, hardware version
        '''
        idn = self.inst.query('*IDN?')

        # NOTE: can't uncomment below code because my equipment simply returns 'Siglent Techno' from query
        # resp_arr = idn.split(",")
        # self.manufacturer = resp_arr[0]
        # self.product_type = resp_arr[1]
        # self.series_number = resp_arr[2]
        # self.software_version = resp_arr[3]
        # self.hardware_version = resp_arr[4]
        return idn

    def __send_cmd(self, cmd):
        '''
        Generic call to send command with error checking
        '''
        self.inst.write(cmd)
        self.check_error()

    def save(self, file_num):
        '''
        Save the current state into non-volatile memory
        '''
        if file_num not in range(1, self.save_file_count+1):
            raise self.SPD3303Exception('20', f'Save file must be an integer 1 - {self.save_file_count}')
        else:
            self.inst.write(f"*SAV {file_num}")

    def recall(self, file_num):
        '''
        Recall state that had been saved from nonvolatile memory
        '''
        if file_num not in range(1, self.save_file_count+1):
            raise self.SPD3303Exception('20', f'Save file must be an integer 1 - {self.save_file_count}')
        else:
            self.inst.write(f"*RCL {file_num}")

    def select_channel(self, channel):
        '''
        Select the channel to be operated on
        '''
        if channel not in range(1, self.channel_count+1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.inst.write(f"INSTrument CH{channel}")

    def get_active_channel(self):
        '''
        Query for the active channel
        '''
        self.inst.write("INSTrument?")
        return self.inst.read()

    def get_current(self, channel):
        '''
        Get the current value for a given channel
        '''
        if channel not in range(1,self.channel_count+1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.inst.write(f"MEASure:CURRent? CH{channel}")
            return float(self.inst.read())

    def get_voltage(self, channel):
        '''
        Get the voltage value for a given channel
        '''
        if channel not in range(1,self.channel_count+1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.inst.write(f"MEASure:VOLTage? CH{channel}")
            return float(self.inst.read())

    def get_power(self, channel):
        '''
        Get the power value for a given channel
        '''
        if channel not in range(1,self.channel_count+1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.inst.write(f"MEASure:POWEr? CH{channel}")
            return float(self.inst.read())

    def set_current(self, channel, value):
        '''
        Set the current value for the selected channel
        '''
        if channel not in range(1,self.channel_count+1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.__send_cmd(f"CH{channel}:CURRent {value}")
    
    def get_set_current(self, channel):
        '''
        Get the set current value of the channel
        '''
        if channel not in range(1,self.channel_count+1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.inst.write(f"CH{channel}:CURRent?")

    def set_voltage(self, channel, value):
        '''
        Set the voltage value for the selected channel
        '''
        if channel not in range(1, self.channel_count+1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            # do some calibration correction (because Siglent makes a shitty product that is a pain to calibrate)
            if channel == 1:
                offset = 0.19637500000000008
                slope = -0.029375000000000016
            elif channel == 2:
                offset = 0.24129166666666663
                slope = -0.032891666666666645
            cal_value = round(value + value*slope + offset, 3)
            self.__send_cmd(f"CH{channel}:VOLTage {cal_value}")
    
    def get_set_voltage(self, channel):
        '''
        Get the set voltage value of the channel
        '''
        if channel not in range(1,self.channel_count+1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.inst.write(f"CH{channel}:VOLTage?")

    def output_on(self, channel):
        '''
        Turn on the channel output
        '''
        if channel not in range(1, self.channel_count+1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.inst.write(f"OUTPut CH{channel},ON")

    def output_off(self, channel):
        '''
        Turn off the channel output
        '''
        if channel not in range(1, self.channel_count+1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.inst.write(f"OUTPut CH{channel},OFF")

    def set_operation_mode(self, mode):
        if mode == 0 or mode == 1 or mode == 2:
            self.inst.write(f"OUTPut:TRACK {mode}")
        else:
            raise self.SPD3303Exception('22', f'Invalid Operation Mode')

    def turn_on_waveform_display(self, channel):
        '''
        Turn on the Waveform Display function of specified channel
        '''
        if channel not in range(1, self.channel_count+1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.__send_cmd(f"OUTPut:WAVE CH{channel},ON")

    def turn_off_waveform_display(self, channel):
        '''
        Turn on the Waveform Display function of specified channel
        '''
        if channel not in range(1,self.channel_count+1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.inst.write(f"OUTPut:WAVE CH{channel},OFF")

    def set_timing_parameters(self, channel, group, voltage, current, time):
        '''
        Set the timing parameters of specified channel, group setting the voltage current and execution time
        '''
        if channel not in range(1, self.channel_count+1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.inst.write(f"TIMEr:SET CH{channel},{group},{voltage},{current},{time}")

    def query_timing_parameters(self, channel, group):
        '''
        Query for the voltage/current/time parameters of specified group of specific channels
        '''
        if channel not in range(1, self.channel_count+1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.inst.write(f"TIMEr:SET? CH{channel},{group}")
            response = self.inst.read()
            resp_arr = response.split(",")
            return (resp_arr[0],(resp_arr[1],resp_arr[2]))

    def turn_on_timer(self, channel):
        '''
        Turn on timer function of specific channel
        '''
        if channel not in range(1,self.channel_count+1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.inst.write(f"TIMEr CH{channel},ON")

    def turn_off_timer(self, channel):
        '''
        Turn off timer fuction of specific channel
        '''
        if channel not in range(1,self.channel_count+1):
            raise self.SPD3303Exception('21', f'Channel # must be an integer 1 - {self.channel_count}')
        else:
            self.inst.write(f"TIMEr CH{channel},OFF")

    def check_error(self):
        '''
        Check for an error on the system
        '''
        self.inst.write("SYSTem:ERRor?")
        response = self.inst.read()
        resp_list = response.split('  ')
        # If error code zero do not raise exception, move along
        if resp_list[0] == '0':
            return False
        # Remove the newline at the end of the message
        resp_list[1] = resp_list[1][:-1]
        # Raise a response with the error code and message
        raise self.SPD3303Exception(resp_list[0], resp_list[1])

    def check_version(self):
        '''
        Query the software version of the equipment
        '''
        self.inst.write("SYSTem:VERSion?")
        return self.inst.read()

    def _decode_hex(self, hex_value):
        # Convert hex value to an integer
        value = int(hex_value, 16)

        # Dictionary to store decoded states
        decoded_info = {}

        # Decode each bit according to the given states
        decoded_info["ch1_mode"] = "CV" if not (value & 0x01) else "CC"
        decoded_info["ch2_mode"] = "CV" if not (value & 0x02) else "CC"

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
        decoded_info["timer22"] = "OFF" if not (value & 0x80) else "ON"

        decoded_info["ch1_display"] = "Digital" if not (value & 0x100) else "Waveform"
        decoded_info["ch2_display"] = "Digital" if not (value & 0x200) else "Waveform"

        return decoded_info

    def check_status(self):
        '''
        Return the top level info about the power supply functional status
        '''
        self.inst.write("SYSTem:STATus?")
        hex_num = self.inst.read()
        return self._decode_hex(hex_num)

    def assign_ip_addr(self, ip):
        '''
        Assign a static Internet Protocol (IP) address for the instrument
        WARNING: This command is invalid when DHCP is on
        '''
        self.__send_cmd(f"IPaddr {ip}")

    def query_ip_addr(self):
        '''
        Query the static Internet Protocol (IP) address for the instrument
        '''
        self.inst.write(f"IPaddr?")
        return self.inst.read()

    def assign_subnet_mask(self, subnet_mask):
        '''
        Assign a subnet mask for the instrument
        WARING: This command is invalid when DHCP is on
        '''
        self.__send_cmd(f"MASKaddr {subnet_mask}")

    def query_subnet_mask(self):
        '''
        Query the subnet mask for the instrument
        '''
        self.inst.write(f"MASKaddr?")
        return self.inst.read()

    def assign_gate_address(self, gate_addr):
        '''
        Assign a gate address for the instrument
        WARING: This command is invalid when DHCP is on
        '''
        self.__send_cmd(f"GATEaddr {gate_addr}")

    def query_subnet_mask(self):
        '''
        Query the gate address for the instrument
        WARING: This command is invalid when DHCP is on
        '''
        self.inst.write(f"GATEaddr?")
        return self.inst.read()
    
    def dhcp(self, state):
        '''
        Turn on or off DHCP
        '''
        if state:
            self.inst.write(f"DHCP ON")
        else:
            self.inst.write(f"DHCP OFF")

    def query_dhcp(self):
        '''
        Query to see the status of DHCP
        '''        
        self.inst.write(f"DHCP?")
        return self.inst.read()

    def cal_voltage(self, channel, point, actual_v):
        #cmd = f"CAL:VOLT ch{channel},{point},{actual_v}"
        cmd = f"CALibration:VOLTage CH{channel},{point},{actual_v}"
        print(cmd)
        self.inst.write(cmd)

    def cal_recall(self):
        cmd = "*CALRCL"
        print(f"SPD3303X: querying {cmd}")
        print(self.inst.query("CALRCL"))
        
    def cal_clear(self, channel, cal_type):
        NR1 = -1 # for "setting" calibration coefficients
        NR2 = -1 # for "display" calibration coefficients
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

        self.inst.write(f"*CALCLS {NR1}")
        self.inst.write(f"*CALCLS {NR2}")
        print(f"Cleared calibration with NR values of {NR1},{NR2}")

    def cal_clear_all(self):
        self.inst.write("*CALCLS 8")
        
    def cal_save(self):
        self.inst.write("*CALST")

        
            
