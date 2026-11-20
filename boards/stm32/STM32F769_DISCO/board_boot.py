# SPDX-License-Identifier: MIT
# Run by MicroPython before boot.py (MICROPY_BOARD_FROZEN_BOOT_FILE). With an SD card in, the
# STM32 port makes /sd the current directory, so boot.py and main.py would be looked for on the
# card: back to /flash, where LVGL MPY Studio's autostart and the launcher put main.py. The card
# stays mounted at /sd (and first in sys.path).
import os

try:
    os.chdir("/flash")
except OSError:
    pass
