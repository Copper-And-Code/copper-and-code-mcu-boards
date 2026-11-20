# SPDX-License-Identifier: MIT
# What this board has, from its description: the connector, the names of its pins, which bus,
# timer or ADC channel each one is, the LEDs. The same module and the same description format as
# on the Linux boards of lvgl-mpy-linux (python/linux/mpy_board.py there), so that an app written
# against it runs on both. Here machine is MicroPython's own and needs no description: apps take
# from it the connector and what each pin is for.
#
# The description is frozen with the firmware (mpy_board_data.py in the board's folder);
# /flash/board.json, if there is one, replaces it (the same JSON as on Linux).
#
#   import mpy_board
#   mpy_board.describe()["board"]          # "STM32F769I-DISCO"
#   mpy_board.pin("A0")                    # "PA6": an alias of the board's, or the name itself
#   mpy_board.connector()                  # ("Arduino", "Arduino Uno V3 ...", {"D0": "PC7", ...})

FILE = "/flash/board.json"

_described = None


def describe():
    """The board's description, a dict; {} without one."""
    global _described
    if _described is None:
        try:
            import json

            with open(FILE) as f:
                _described = json.load(f)
        except (OSError, ValueError):
            try:
                from mpy_board_data import DESCRIPTION

                _described = DESCRIPTION
            except ImportError:
                _described = {}
    return _described


def pin(name):
    """The MCU's name of a pin given by an alias of the board ("A0", "D6") or by its own name."""
    return describe().get("aliases", {}).get(name.upper(), name.upper())


def connector():
    """(name, title, {pin label: signal}) of the board's main connector, or None. Labels are the
    connector's own: names ("D6", "A0") on an Arduino one, numbers ("38") on a 40-pin header."""
    found = describe().get("connector")
    if not found:
        return None
    return found.get("name", ""), found.get("title", ""), found.get("pins", {})
