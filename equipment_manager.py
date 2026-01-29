

# import needed EEequipment modules
import EEequipment
from EEequipment.TestEquipment import TestEquipment, PowerSupply
from EEequipment.TestEquipment import DMM, FunctionGenerator

# import needed modules
import usb
import pyvisa.errors
import inspect, pkgutil, importlib


# setup common connection errors
COMMUNICATION_ERRORS = (AttributeError, pyvisa.errors.VisaIOError, usb.USBError)


ALL_BASES = (TestEquipment,)  # add DMMBase, PowerSupplyBase, etc., if available
DMM_BASES = (DMM,)  # add DMMBase, PowerSupplyBase, etc., if available
PS_BASES = (PowerSupply,)  # add DMMBase, PowerSupplyBase, etc., if available
FG_BASES = (FunctionGenerator,)


def get_instruments(base):
    """Return {display_name: class_obj} by walking subpackages and filtering."""
    if base == "all":
        ALLOWED_BASES = ALL_BASES
    elif base == "ps":
        ALLOWED_BASES = PS_BASES
    elif base == "dmm":
        ALLOWED_BASES = DMM_BASES
    elif base == "fg":
        ALLOWED_BASES = FG_BASES

    reg = {}
    base_pkg = EEequipment.__name__
    for m in pkgutil.walk_packages(EEequipment.__path__, prefix=f"{base_pkg}."):
        modname = m.name
        try:
            module = importlib.import_module(modname)
        except Exception:
            continue
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != modname:
                continue
            if any(obj is base or issubclass(obj, base) for base in ALLOWED_BASES) and obj not in ALLOWED_BASES:
                display = name  # or f"{modname}.{name}" for uniqueness
                reg[display] = obj
    return reg