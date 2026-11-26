# Touch of the Velxio simulator (STM32H7_CORE VELXIO variant, Renode): no GT911 is
# modelled, the simulator writes the mouse on the simulated panel into a mailbox in the
# D3 SRAM (SRAM4), which the firmware does not use otherwise. Same interface as gt911.GT911
# for display_driver: lv_register(), interrupted.
#
# Mailbox, 32-bit words, written by the Velxio backend (renode_manager.py, TOUCH_MAILBOX):
#   +0x00 pressed (0 or 1)   +0x04 x   +0x08 y   (display pixels)   +0x0C sequence number

import machine

MAILBOX = 0x3800FF00


class VelxioTouch:
    def __init__(self, addr=MAILBOX):
        self.addr = addr
        self.interrupted = False
        for off in (0, 4, 8, 12):
            machine.mem32[addr + off] = 0

    def read(self):
        """(pressed, x, y)"""
        a = self.addr
        return machine.mem32[a] != 0, machine.mem32[a + 4], machine.mem32[a + 8]

    def lv_read_cb(self, indev, data):
        import lvgl as lv

        try:
            pressed, x, y = self.read()
        except KeyboardInterrupt:
            self.interrupted = True
            pressed, x, y = False, 0, 0
        data.point.x = x
        data.point.y = y
        data.state = lv.INDEV_STATE.PRESSED if pressed else lv.INDEV_STATE.RELEASED

    def lv_register(self):
        import lvgl as lv

        indev = lv.indev_create()
        indev.set_type(lv.INDEV_TYPE.POINTER)
        indev.set_read_cb(self.lv_read_cb)
        return indev
