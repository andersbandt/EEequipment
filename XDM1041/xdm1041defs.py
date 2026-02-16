from enum import Enum


class XDM1041Mode(Enum):
    """
    Enum class to set the states of the meter and to associate __str__ with the command codes
    """

    MODE_VOLTAGE_DC = 2
    MODE_VOLTAGE_AC = 3
    MODE_CURRENT_DC = 4
    MODE_CURRENT_AC = 5
    MODE_RES = 6
    MODE_CONT = 7
    MODE_DIODE = 8
    MODE_CAPACITANCE = 9
    MODE_FREQUENCY = 10
    MODE_PERIOD = 11
    MODE_TEMP = 12

    def __str__(self):

        if self.value == XDM1041Mode.MODE_VOLTAGE_DC.value:
            return "CONF:VOLT:DC"

        elif self.value == XDM1041Mode.MODE_VOLTAGE_AC.value:
            return "CONF:VOLT:AC"

        elif self.value == XDM1041Mode.MODE_CURRENT_DC.value:
            return "CONF:CURR:DC"

        elif self.value == XDM1041Mode.MODE_CURRENT_AC.value:
            return "CONF:CURR:AC"

        elif self.value == XDM1041Mode.MODE_RES.value:
            return "CONF:RES"

        elif self.value == XDM1041Mode.MODE_CONT.value:
            return "CONF:CONT"

        elif self.value == XDM1041Mode.MODE_DIODE.value:
            return "CONF:DIOD"

        elif self.value == XDM1041Mode.MODE_CAPACITANCE.value:
            return "CONF:CAP"

        elif self.value == XDM1041Mode.MODE_FREQUENCY.value:
            return "CONF:FREQ"

        elif self.value == XDM1041Mode.MODE_PERIOD.value:
            return "CONF:PER"

        elif self.value == XDM1041Mode.MODE_TEMP.value:
            return "CONF:TEMP"


class XDM1041Cmd(Enum):
    IDN = 1

    RATE_S = 13
    RATE_M = 14
    RATE_F = 15

    MEASURE_1 = 16
    MEASURE_2 = 17

    MEASURE_1_RAW = 18
    MEASURE_2_RAW = 19

    SET_RANGE = 20

    SET_BEEP_ON = 21
    SET_BEEP_OFF = 22
    GET_BEEP_STATUS = 23

    GET_SYSTEM_TIME = 30
    GET_SYSTEM_DATE = 31

    GET_AUTO_MODE = 40
    SET_AUTO_MODE = 41

    SET_CALC_STAT_OFF = 50
    SET_CALC_FUNC_AVG = 51
    GET_CALC_AVG = 52
    GET_CALC_MIN = 53
    GET_CALC_MAX = 54

    FUNC1 = 55
    FUNC2 = 56
    GET_RANGE = 57

    def __str__(self):
        if self.value == XDM1041Cmd.IDN.value:
            return "*IDN?"

        elif self.value == XDM1041Cmd.RATE_S.value:
            return "RATE S"

        elif self.value == XDM1041Cmd.RATE_M.value:
            return "RATE M"

        elif self.value == XDM1041Cmd.RATE_F.value:
            return "RATE F"

        elif self.value == XDM1041Cmd.MEASURE_1.value:
            return "MEAS1:SHOW?"

        elif self.value == XDM1041Cmd.MEASURE_2.value:
            return "MEAS2:SHOW?"

        elif self.value == XDM1041Cmd.MEASURE_1_RAW.value:
            return "MEAS1?"

        elif self.value == XDM1041Cmd.MEASURE_2_RAW.value:
            return "MEAS2?"

        elif self.value == XDM1041Cmd.SET_RANGE.value:
            return "RANGE {}"

        elif self.value == XDM1041Cmd.SET_BEEP_ON.value:
            return "SYST:BEEP:STAT ON"

        elif self.value == XDM1041Cmd.SET_BEEP_OFF.value:
            return "SYST:BEEP:STAT OFF"

        elif self.value == XDM1041Cmd.GET_BEEP_STATUS.value:
            return "SYST:BEEP:STAT?"

        elif self.value == XDM1041Cmd.GET_SYSTEM_DATE.value:
            return "SYST:DATE?"

        elif self.value == XDM1041Cmd.GET_SYSTEM_TIME.value:
            return "SYST:TIME?"

        elif self.value == XDM1041Cmd.SET_AUTO_MODE.value:
            return "AUTO"

        elif self.value == XDM1041Cmd.GET_AUTO_MODE.value:
            return "AUTO?"

        elif self.value == XDM1041Cmd.SET_CALC_STAT_OFF.value:
            return "CALC:STAT OFF"

        elif self.value == XDM1041Cmd.SET_CALC_FUNC_AVG.value:
            return "CALC:FUNC AVER"

        elif self.value == XDM1041Cmd.GET_CALC_AVG.value:
            return "CALC:AVER:AVER?"

        elif self.value == XDM1041Cmd.GET_CALC_MIN.value:
            return "CALC:AVER:MIN?"

        elif self.value == XDM1041Cmd.GET_CALC_MAX.value:
            return "CALC:AVER:MAX?"

        elif self.value == XDM1041Cmd.FUNC1.value:
            return "FUNC1?"

        elif self.value == XDM1041Cmd.FUNC2.value:
            return "FUNC2?"

        elif self.value == XDM1041Cmd.GET_RANGE.value:
            return "RANGE?"
