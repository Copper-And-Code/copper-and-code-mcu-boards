# FT6x06 capacitive touch controller (FT6206, FT6236, FT6336), for LVGL (pointer device).
# On the STM32F769I-DISCO: an FT6206 at 0x2A on I2C4, on the MB1166 display.
#
# Polled, no interrupt: read() reads TD_STATUS and the first point (registers 0x02..0x06)
# in one transfer. The interface is the one of gt911.py (read, lv_read_cb, lv_register,
# errors, interrupted), so display_driver treats both the same way.
#
# The controller reports in the panel's own orientation (portrait, 480 x 800 on the MB1166).
# swap_xy, invert_x and invert_y turn that into the display's, applied in that order. For the
# MB1166 in landscape (800 x 480): swap_xy=True, invert_y=True, i.e. x = raw y and
# y = 479 - raw x, measured on the board by touching four corner targets (2026-11-20).
# cal=(ax, bx, ay, by) then corrects the scale and offset: x = ax * x + bx, y = ay * y + by. The
# MB1166's touch reads about 30 px too high at the bottom edge and 15 px to the right: its fit
# over 21 touches (two runs, docs/log/f769-phase5-2026-11-20.txt) is in stm32_board.py.

from machine import I2C

REG_TD_STATUS = 0x02  # number of points (low 4 bits), then P1_XH, P1_XL, P1_YH, P1_YL
REG_CHIP_ID = 0xA8    # FocalTech's chip id: 0x11 on the FT6206, 0xCD on the FT6236, 0x64 FT6336
REG_FIRMWARE = 0xA6
REG_G_MODE = 0xA4     # 0: polling, INT held while touched

ADDR = 0x2A
CHIP_IDS = (0x11, 0xCD, 0x64, 0x36, 0x06)
READY_MS = 600


class FT6x06:
    def __init__(self, i2c=None, addr=ADDR, width=800, height=480, swap_xy=False,
                 invert_x=False, invert_y=False, cal=None):
        self.i2c = i2c if i2c is not None else I2C(4, freq=400_000)
        self.addr = addr
        self.width = width
        self.height = height
        self.swap_xy = swap_xy
        self.invert_x = invert_x
        self.invert_y = invert_y
        self.cal = cal
        self.x = 0
        self.y = 0
        self.pressed = False
        self.errors = 0  # I2C errors swallowed by lv_read_cb
        # A Ctrl-C that landed in lv_read_cb: display_driver hands it on to the program
        # after lv.timer_handler() and clears this (docs/display-driver.md).
        self.interrupted = False
        self._buf = bytearray(5)
        # Right after the panel's reset (which is the touch controller's too, st_ltdc.init() pulses
        # it at a cold start) the controller does not answer for a while: try for READY_MS.
        import time

        start = time.ticks_ms()
        while True:
            try:
                cid = self.chip_id()
                if cid in CHIP_IDS:
                    break
            except OSError:
                cid = None
            if time.ticks_diff(time.ticks_ms(), start) > READY_MS:
                raise OSError("FT6x06 not found (chip id %r)" % cid)
            time.sleep_ms(20)
        self.i2c.writeto_mem(self.addr, REG_G_MODE, b"\x00")

    def chip_id(self):
        return self.i2c.readfrom_mem(self.addr, REG_CHIP_ID, 1)[0]

    def firmware(self):
        return self.i2c.readfrom_mem(self.addr, REG_FIRMWARE, 1)[0]

    def read_raw(self):
        # (points, x, y) as the controller reports them, panel orientation.
        b = self._buf
        self.i2c.readfrom_mem_into(self.addr, REG_TD_STATUS, b)
        n = b[0] & 0x0F
        return n, ((b[1] & 0x0F) << 8) | b[2], ((b[3] & 0x0F) << 8) | b[4]

    def read(self):
        # Returns (pressed, x, y) in display pixels. No touch keeps the last x, y.
        n, x, y = self.read_raw()
        if 1 <= n <= 2:  # 0 is no touch; 0x0F (and other values) after power-up
            if self.swap_xy:
                x, y = y, x
            if self.invert_x:
                x = self.width - 1 - x
            if self.invert_y:
                y = self.height - 1 - y
            if self.cal:
                ax, bx, ay, by = self.cal
                x = int(ax * x + bx + 0.5)
                y = int(ay * y + by + 0.5)
            self.x = min(max(x, 0), self.width - 1)
            self.y = min(max(y, 0), self.height - 1)
            self.pressed = True
        else:
            self.pressed = False
        return self.pressed, self.x, self.y

    def lv_read_cb(self, indev, data):
        # LVGL calls this from lv.timer_handler(), in C: a KeyboardInterrupt raised here
        # would be printed and dropped by LVGL's callback, so it is kept for display_driver.
        # The `if` is a jump inside the try: the VM raises a pending Ctrl-C only at a jump.
        try:
            self._lv_read(data)
            if self.interrupted:
                pass
        except KeyboardInterrupt:
            self.interrupted = True

    def _lv_read(self, data):
        import lvgl as lv

        try:
            pressed, x, y = self.read()
        except OSError:
            # A transient NACK: keep the last state and try again at the next poll.
            self.errors += 1
            pressed, x, y = self.pressed, self.x, self.y
        data.point.x = x
        data.point.y = y
        data.state = lv.INDEV_STATE.PRESSED if pressed else lv.INDEV_STATE.RELEASED

    def lv_register(self):
        import lvgl as lv

        indev = lv.indev_create()
        indev.set_type(lv.INDEV_TYPE.POINTER)
        indev.set_read_cb(self.lv_read_cb)
        return indev
