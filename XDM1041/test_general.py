import logging
from xdm1041defs import XDM1041Mode, XDM1041Cmd
from xdm1041main import XDM1041
import time
import configparser

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")
    logger = logging.getLogger(__name__)

    # show the available ranges for the different modes
    XDM1041.show_available_ranges()

    # read in the global app config
    config = configparser.ConfigParser()
    config.read('config.ini')

    ser_device = config.get("SERIAL", "serial_port")

    logger.info("Setting port to:{}".format(ser_device))

    # initialize the XDM class
    # measure voltage @50V range
    xdm = XDM1041(XDM1041Mode.MODE_VOLTAGE_DC, 1, ser_device)
    xdm.set_sample_speed_slow()

    xdm.test_conn()

    try:
        while True:
            time.sleep(0.5)

            # read the raw float value
            val_raw: float = xdm.read_val1_raw()
            val_str: str = xdm.read_val1_str().replace('\n', '').replace('\r', '')

            logger.info("Timestamp:{} Formatted value:{} Raw value:{}".format(
                int(time.time() * 1000),
                val_str,
                val_raw)
            )

    except (KeyboardInterrupt, SystemExit):
        logger.info("Exiting")


