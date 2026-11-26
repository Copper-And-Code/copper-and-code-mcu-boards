# Per-board settings of the STM32 boards that are not in the C board files: the
# touch wiring (from docs/stm32-inventory.md, the old boards.py) and the default panel.
#
#   import stm32_board
#   stm32_board.NAME          # "STM32H7_CORE V1.3", "STM32F769I-DISCO", ...
#   t = stm32_board.touch()   # the board's touch controller (gt911.GT911, ft6x06.FT6x06,
#                             # velxio_touch.VelxioTouch in the Velxio simulator)
#
# The panel is chosen in /flash/display_config.py (PANEL = "RGB043M2"); without it,
# the board's own ("MB1166" on the STM32F769I-DISCO) or IPS1024x600; see panels.py.

import os

# touch: (rst, int, bus) of a GT911; bus is an int for hardware I2C, else (scl, sda) for
# SoftI2C. ("ft6x06", bus, options): an FT6x06 on hardware I2C, without reset or
# interrupt lines (the STM32F769I-DISCO's shares the panel's reset, which st_ltdc pulses).
# panel: the default when /flash/display_config.py names none.
BOARDS = {
    "DEV190806042": {"touch": ("I8", "H7", ("H6", "G7"))},
    "FK743M5-XIH6": {"touch": ("I10", "I11", ("G3", "G7"))},
    "STM32H7_CORE V1.0": {"touch": ("H7", "E3", 4)},
    "STM32H7_CORE V1.3": {"touch": ("B14", "H7", ("B12", "B13"))},
    # The V1.3 in the Velxio simulator: touch from a mailbox (velxio_touch.py).
    "STM32H7_CORE Velxio": {"touch": ("velxio",)},
    # MB1166 in landscape: x = raw y, y = 479 - raw x (docs/log/f769-phase3-2026-11-20.txt),
    # then scale and offset fitted to 21 touches (docs/log/f769-phase5-2026-11-20.txt).
    # audio: the WM8994 codec through audio.py (buzzer.py uses it).
    "STM32F769I-DISCO": {"panel": "MB1166", "audio": True,
                         "touch": ("ft6x06", 4, {"swap_xy": True, "invert_y": True,
                                                 "cal": (1.008, -19.2, 1.0925, -7.3)})},
}

# The GT911 is rated for 400 kHz. The port's hardware I2C timings are for a 54 MHz
# kernel clock; these boards clock I2C from PCLK at 120 MHz, so freq=400_000 ran the
# bus at 1.07 MHz. TOUCH_TIMINGR is 400 kHz Fast mode at 120 MHz (PRESC 5, SCLDEL 7,
# SDADEL 2, SCLH 18, SCLL 26). SoftI2C rounds its half period to whole microseconds:
# freq=400_000 gives 500 kHz, 250_000 is the fastest setting within the rating.
# Measured on the V1.0 (docs/stm32h743.md): address NACKs, 1 in about 30 000 to
# 150 000 reads, only seen above 400 kHz.
TOUCH_FREQ = 400_000
TOUCH_TIMINGR = 0x5072121A  # for a 120 MHz I2C kernel clock
TOUCH_SOFT_FREQ = 250_000

NAME = None
for _n in BOARDS:
    if os.uname().machine.startswith(_n + " with"):
        NAME = _n
CONFIG = BOARDS.get(NAME, {})


def panel():
    try:
        from display_config import PANEL

        return PANEL
    except ImportError:
        return CONFIG.get("panel", "IPS1024x600")


def touch_i2c():
    from machine import I2C, Pin, SoftI2C

    bus = CONFIG["touch"][2]
    if isinstance(bus, int):
        import machine

        if machine.freq()[2] == 120_000_000:  # PCLK, the I2C kernel clock here
            return I2C(bus, freq=TOUCH_FREQ, timingr=TOUCH_TIMINGR)
        return I2C(bus, freq=TOUCH_FREQ)
    return SoftI2C(scl=Pin(bus[0]), sda=Pin(bus[1]), freq=TOUCH_SOFT_FREQ)


def touch(**kw):
    """The board's touch controller: a GT911 (reset, address 0x5D) or an FT6x06;
    OSError if it does not answer."""
    if "touch" not in CONFIG:
        raise OSError("no touch wiring known for %r" % os.uname().machine)
    if CONFIG["touch"][0] == "velxio":
        import velxio_touch

        return velxio_touch.VelxioTouch(**kw)
    if CONFIG["touch"][0] == "ft6x06":
        import ft6x06
        from machine import I2C

        _, bus, options = CONFIG["touch"]
        options = dict(options)
        options.update(kw)
        return ft6x06.FT6x06(i2c=I2C(bus, freq=400_000), **options)
    import gt911

    rst, irq, _ = CONFIG["touch"]
    return gt911.GT911(i2c=touch_i2c(), rst=rst, irq=irq, **kw)
