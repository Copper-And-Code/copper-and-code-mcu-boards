# SPDX-License-Identifier: MIT
# The STM32F769I-DISCO's description for mpy_board (python/mpy_board.py), in the format of the
# Linux boards' board.json. Pins from ST's pin data and Zephyr's Arduino map (see pins.csv);
# timers as machine.PWM picks them (checked on the board, 2026-11-20).

DESCRIPTION = {
    "board": "STM32F769I-DISCO",
    "about": (
        "STM32F769I-DISCO (MB1225B) with MicroPython's own machine. The Arduino connector's "
        "peripherals: UART6 on D1/D0, SPI2 on D13/D12/D11 (D10 chip select), I2C1 on D15/D14, "
        "PWM on D3 D5 D6 D9 D10, ADC on A0-A5 (A0-A2 on ADC1, A3-A5 on ADC3; the numbers are "
        "the channels). LD3 (green, PA12) is D13 too: it lights with SPI2's clock."
    ),
    "connector": {
        "name": "Arduino",
        "title": "Arduino Uno V3 connectors",
        "pins": {
            "D0": "PC7", "D1": "PC6", "D2": "PJ1", "D3": "PF6", "D4": "PJ0", "D5": "PC8",
            "D6": "PF7", "D7": "PJ3", "D8": "PJ4", "D9": "PH6", "D10": "PA11", "D11": "PB15",
            "D12": "PB14", "D13": "PA12", "D14": "PB9", "D15": "PB8",
            "A0": "PA6", "A1": "PA4", "A2": "PC2", "A3": "PF10", "A4": "PF8", "A5": "PF9",
        },
    },
    "i2c": {"1": {"scl": "PB8", "sda": "PB9"}},
    "spi": {"2": {"sck": "PA12", "mosi": "PB15", "miso": "PB14", "cs": "PA11"}},
    "uart": {"6": {"tx": "PC6", "rx": "PC7"}},
    "pwm": {
        "PF6": {"name": "TIM10 CH1"},
        "PC8": {"name": "TIM8 CH3"},
        "PF7": {"name": "TIM11 CH1"},
        "PH6": {"name": "TIM12 CH1"},
        "PA11": {"name": "TIM1 CH4"},
    },
    "adc": {
        "bits": 12,
        "range_uv": 3300000,
        "pins": {"PA6": 6, "PA4": 4, "PC2": 12, "PF10": 8, "PF8": 6, "PF9": 7},
    },
    "aliases": {
        "D0": "PC7", "D1": "PC6", "D2": "PJ1", "D3": "PF6", "D4": "PJ0", "D5": "PC8",
        "D6": "PF7", "D7": "PJ3", "D8": "PJ4", "D9": "PH6", "D10": "PA11", "D11": "PB15",
        "D12": "PB14", "D13": "PA12", "D14": "PB9", "D15": "PB8",
        "A0": "PA6", "A1": "PA4", "A2": "PC2", "A3": "PF10", "A4": "PF8", "A5": "PF9",
    },
    "leds": {
        "red": {"pin": "PJ13", "where": "LD1"},
        "green": {"pin": "PJ5", "where": "LD2"},
    },
    "button": {"pin": "PA0", "where": "B1 (USER)", "active_low": False},
}
