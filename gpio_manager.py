import logging
from typing import Dict, Any, List, Optional
try:
    from gpiozero import Device, DigitalOutputDevice, DigitalInputDevice, PWMOutputDevice
    from gpiozero.pins.lgpio import LGROFactory
    # Try to set the pin factory explicitly if needed, but gpiozero is usually good at auto-detecting on Pi 5
    # Device.pin_factory = LGROFactory() 
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.warning("gpiozero not found. GPIO features will be disabled or mocked.")

logger = logging.getLogger("gpio_manager")

class GPIOManager:
    """
    Manages GPIO pins on the Raspberry Pi 5.
    
    Structure of the 40-pin header (BCM numbering for GPIOs):
    
    3.3V  (1) (2)  5V
    GPIO2 (3) (4)  5V
    GPIO3 (5) (6)  GND
    GPIO4 (7) (8)  GPIO14
    GND   (9) (10) GPIO15
    GPIO17(11) (12) GPIO18
    ... and so on.
    """
    
    # Safe User GPIOs (BCM numbers)
    # We exclude ID_SD and ID_SC (GPIO 0 and 1) as they are reserved for HAT EEPROMs usually.
    # We also exclude pins that might be critical system functions unless we are sure.
    # Standard user GPIOs:
    SAFE_GPIOS = [
        2, 3, 4, 17, 27, 22, 10, 9, 11, 
        5, 6, 13, 19, 26, 14, 15, 18, 23, 24, 25, 8, 7, 12, 16, 20, 21
    ]

    # Full Header Definition for Visualization
    # Pin: (Physical Pin Number, Name/Type, BCM Number or None)
    HEADER_LAYOUT = [
        # Left Column (Odd)
        {"pin": 1, "name": "3.3V", "type": "power", "bcm": None},
        {"pin": 3, "name": "GPIO 2", "type": "gpio", "bcm": 2},
        {"pin": 5, "name": "GPIO 3", "type": "gpio", "bcm": 3},
        {"pin": 7, "name": "GPIO 4", "type": "gpio", "bcm": 4},
        {"pin": 9, "name": "GND", "type": "ground", "bcm": None},
        {"pin": 11, "name": "GPIO 17", "type": "gpio", "bcm": 17},
        {"pin": 13, "name": "GPIO 27", "type": "gpio", "bcm": 27},
        {"pin": 15, "name": "GPIO 22", "type": "gpio", "bcm": 22},
        {"pin": 17, "name": "3.3V", "type": "power", "bcm": None},
        {"pin": 19, "name": "GPIO 10", "type": "gpio", "bcm": 10},
        {"pin": 21, "name": "GPIO 9", "type": "gpio", "bcm": 9},
        {"pin": 23, "name": "GPIO 11", "type": "gpio", "bcm": 11},
        {"pin": 25, "name": "GND", "type": "ground", "bcm": None},
        {"pin": 27, "name": "GPIO 0", "type": "gpio", "bcm": 0, "restricted": True}, # ID_SD
        {"pin": 29, "name": "GPIO 5", "type": "gpio", "bcm": 5},
        {"pin": 31, "name": "GPIO 6", "type": "gpio", "bcm": 6},
        {"pin": 33, "name": "GPIO 13", "type": "gpio", "bcm": 13},
        {"pin": 35, "name": "GPIO 19", "type": "gpio", "bcm": 19},
        {"pin": 37, "name": "GPIO 26", "type": "gpio", "bcm": 26},
        {"pin": 39, "name": "GND", "type": "ground", "bcm": None},

        # Right Column (Even) - we will map these in the frontend to the right side
        {"pin": 2, "name": "5V", "type": "power", "bcm": None},
        {"pin": 4, "name": "5V", "type": "power", "bcm": None},
        {"pin": 6, "name": "GND", "type": "ground", "bcm": None},
        {"pin": 8, "name": "GPIO 14", "type": "gpio", "bcm": 14},
        {"pin": 10, "name": "GPIO 15", "type": "gpio", "bcm": 15},
        {"pin": 12, "name": "GPIO 18", "type": "gpio", "bcm": 18},
        {"pin": 14, "name": "GND", "type": "ground", "bcm": None},
        {"pin": 16, "name": "GPIO 23", "type": "gpio", "bcm": 23},
        {"pin": 18, "name": "GPIO 24", "type": "gpio", "bcm": 24},
        {"pin": 20, "name": "GND", "type": "ground", "bcm": None},
        {"pin": 22, "name": "GPIO 25", "type": "gpio", "bcm": 25},
        {"pin": 24, "name": "GPIO 8", "type": "gpio", "bcm": 8},
        {"pin": 26, "name": "GPIO 7", "type": "gpio", "bcm": 7},
        {"pin": 28, "name": "GPIO 1", "type": "gpio", "bcm": 1, "restricted": True}, # ID_SC
        {"pin": 30, "name": "GND", "type": "ground", "bcm": None},
        {"pin": 32, "name": "GPIO 12", "type": "gpio", "bcm": 12},
        {"pin": 34, "name": "GND", "type": "ground", "bcm": None},
        {"pin": 36, "name": "GPIO 16", "type": "gpio", "bcm": 16},
        {"pin": 38, "name": "GPIO 20", "type": "gpio", "bcm": 20},
        {"pin": 40, "name": "GPIO 21", "type": "gpio", "bcm": 21},
    ]

    def __init__(self):
        self.active_pins: Dict[int, Any] = {} # Map BCM -> gpiozero object
        self.pin_modes: Dict[int, str] = {}   # Map BCM -> 'input' | 'output'

    def get_header_state(self) -> List[Dict[str, Any]]:
        """
        Returns the full state of the 40-pin header for the UI.
        Includes current values for active GPIOs.
        """
        header_state = []
        for pin_def in self.HEADER_LAYOUT:
            pin_info = pin_def.copy()
            bcm = pin_info.get("bcm")
            
            if bcm is not None and not pin_info.get("restricted"):
                # Determine current state
                if bcm in self.active_pins:
                    device = self.active_pins[bcm]
                    pin_info["mode"] = self.pin_modes.get(bcm, "unknown")
                    try:
                        pin_info["value"] = int(device.value) if device.value is not None else 0
                        pin_info["is_active"] = device.is_active
                    except Exception:
                        pin_info["value"] = 0
                else:
                    # Default state if not active (assume input/floating or check safely if possible?)
                    # For safety, we just say it's inactive/closed interaction
                    pin_info["mode"] = "none" # Not configured by us
                    pin_info["value"] = 0
            
            header_state.append(pin_info)
        
        # Sort by physical pin number just in case
        header_state.sort(key=lambda x: x["pin"])
        return header_state

    def setup_pin(self, bcm: int, mode: str) -> bool:
        """
        Configures a pin as Input or Output.
        """
        if not GPIO_AVAILABLE:
            return False
            
        if bcm not in self.SAFE_GPIOS:
            logger.warning(f"Attempt to configure unsafe/restricted GPIO {bcm}")
            return False

        # Close existing device if exists
        self.close_pin(bcm)

        try:
            if mode == "output":
                # Initial value low for safety
                self.active_pins[bcm] = DigitalOutputDevice(bcm, initial_value=False)
                self.pin_modes[bcm] = "output"
            elif mode == "input":
                # Pull down by default? Or floating? gpiozero defaults to no pull or pull up depending on impl.
                # DigitalInputDevice(pin, pull_up=False) -> Pull Down
                self.active_pins[bcm] = DigitalInputDevice(bcm) 
                self.pin_modes[bcm] = "input"
            else:
                return False
            return True
        except Exception as e:
            logger.error(f"Error setting up GPIO {bcm}: {e}")
            return False

    def set_pin_value(self, bcm: int, value: int) -> bool:
        """
        Sets the value (0 or 1) for an Output pin.
        """
        if bcm not in self.active_pins:
            return False
        
        if self.pin_modes.get(bcm) != "output":
            return False

        try:
            device = self.active_pins[bcm]
            if value:
                device.on()
            else:
                device.off()
            return True
        except Exception as e:
            logger.error(f"Error setting value for GPIO {bcm}: {e}")
            return False

    def close_pin(self, bcm: int):
        """Releases a pin resource."""
        if bcm in self.active_pins:
            try:
                self.active_pins[bcm].close()
            except Exception:
                pass
            del self.active_pins[bcm]
            if bcm in self.pin_modes:
                del self.pin_modes[bcm]

    def close_all(self):
        """Releases all pins."""
        for bcm in list(self.active_pins.keys()):
            self.close_pin(bcm)
