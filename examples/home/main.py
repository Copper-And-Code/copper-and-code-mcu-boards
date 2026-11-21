# SPDX-License-Identifier: MIT
# The ESP32-4848S040's main.py for the home on the SD card (examples/home): mounts the card, puts
# /sd/lib first in sys.path and starts home.py from there. Without a card, or with no home.py on
# it, the shell in the internal flash starts as before. main.py does not run after a soft reset
# from the raw REPL, so Thonny, mpremote and Copper and Code Studio take the board as usual.
import os
import sys

home = None
try:
    import machine

    import display_driver  # the card's bus works only with the display started

    if "sd" not in os.listdir("/"):
        os.mount(machine.SDCard(slot=2, sck=48, miso=41, mosi=47, cs=42, freq=10_000_000), "/sd")
    os.stat("/sd/lib/home.py")
    sys.path.insert(0, "/sd/lib")
    import home
except OSError as e:  # no card, or no home on it
    print("home: not on the SD card (%r), the shell of the flash starts" % e)
except Exception as e:
    sys.print_exception(e)
try:
    if home:
        home.main()
    else:
        import shell

        shell.main()
except Exception as e:
    sys.print_exception(e)
