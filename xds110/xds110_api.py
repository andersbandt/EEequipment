"""
@file     xds110_api.py
@author   Anders Bandt
@date     March 2024
@brief    control the XDS110
"""

# import needed modules
import os
import platform
import configparser

# import user defined modules
from common import subprocessor as subp


# get operating system information
os_name = platform.system()
print(f"Initializing XDS config paths with OS: {os_name}")
if os_name != "Windows" and os_name != "Linux":
    print("Undefined operating system to set for XDS110-API paths!!!")
    raise BaseException


# initialize the config parser
config_file_path = "./EEequipment/xds110/config.ini"
if os.path.exists(config_file_path):
    config = configparser.ConfigParser()
    config.read(config_file_path)
else:
    print(f"Configuration file {config_file_path} does not exist.")
    raise BaseException


# read in parameters from the config file
base_ccs = config[os_name]["base_ccs"]
base_project_path = config[os_name]["base_project_path"]
base_tools_path = config[os_name]["base_tools_path"]
base_script_path = config[os_name]["base_script_path"]
xds110_reset_cmd = config[os_name]["xds110_reset_cmd"]
xds110_jtag_cmd = config[os_name]["xds110_jtag_cmd"]
xds110_xds_cmd = config[os_name]["xds110_xds_cmd"]
gmake_cmd = base_ccs + config[os_name]["gmake_cmd"]
load_cmd = base_script_path + config[os_name]["load_cmd"]


class XDS110Exception(Exception):
    pass

#########################
#### XDS110 API  ########
#########################


def toggle_target(action):
    if action not in ["toggle", "assert", "deassert"]:
        return False
    executable_path = os.path.join(base_tools_path, xds110_reset_cmd)
    packet = subp.execute_command(executable_path, ["-a", action])
    return packet


# @command ./dbgjtag -f @xds110 -S integrity
def get_jtag_integrity():
    executable_path = os.path.join(base_tools_path, xds110_jtag_cmd)
    packet = subp.execute_command(executable_path, ["-f", "@xds110", "-S", "integrity"])
    return packet


def xds110_jtag_reset():
    executable_path = os.path.join(base_tools_path, xds110_jtag_cmd)
    packet = subp.execute_command(executable_path, ["-f", "@xds110", "-r"])
    return packet


def xds110_reset():
    pass


def get_xds110_status():
    executable_path = os.path.join(base_tools_path, xds110_xds_cmd)

    packet = subp.execute_command(executable_path, ["-e"])
    if packet is False:
        return [False, False]

    # check if result contains search string
    search_string = "Found 0 devices"
    if search_string in packet.stdout:
        xds110_status = False
    else:
        xds110_status = True

    return [xds110_status, packet]


#########################
#### CCS BIN ############
#########################


def flash_firmware(config_type, serial_number):
    if config_type == "Any":
        config_file = f"/targetConfigs/CC2642R1F2.ccxml"
    elif config_type == "target_power":
        config_file = f"/targetConfigs/CC2642R1F2_{serial_number}.ccxml"
    elif config_type == "probe_power":
        config_file = "/targetConfigs/CC2642R1F_probe_PWR.ccxml"
    elif config_type == "supply_power":
        config_file = f"/targetConfigs/CC2642R1F2_{serial_number}.ccxml"
    else:
        print(f"Trying config {config_type}")
        raise XDS110Exception("Bad target config type!")

    packet = subp.execute_command(
        load_cmd,
        [
            "-a",
            "-c",
            base_project_path + config_file,
            base_project_path + "/Debug/WWD_prog.out"
        ])
    error_words = [
        "Error code",
        "Error",
        "An attempt to connect to the XDS110 failed"
    ]

    # hack manual parse based on returned message content
    if "Target running" in packet.stdout:
        return [True, packet]

    # return error status based on errors in stdout OR stderr
    for error_key in error_words:
        if error_key in packet.stdout:
            return [False, packet]
        elif error_key in packet.stderr:
            return [False, packet]

    return [True, packet]


