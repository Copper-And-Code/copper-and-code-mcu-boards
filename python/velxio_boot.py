# Frozen boot code of the STM32H7_CORE VELXIO variant (Velxio simulator, Renode):
# MICROPY_BOARD_FROZEN_BOOT_FILE in mpconfigboard.h, run at every (soft) reset
# before boot.py.
#
# Renode's QSPI flash model does not answer the W25Q128's status commands, so the
# port cannot mount /flash ("MPY: can't mount flash"). Without a filesystem a
# program cannot be more than one pasted file: Velxio writes a project's modules
# (ui.py, app_events.py, ...) next to its entry point, and apps keep settings in
# files. So when /flash is missing, a littlefs in RAM is mounted there instead: it
# lives in the GC heap (the SDRAM) and is empty again after every reset, which is
# what a simulator that loads the project at each Run expects.

import os
import sys
import vfs

BLOCK_SIZE = 4096
BLOCKS = 1024  # 4 MB


class RAMBlockDev:
    """Block device in a bytearray, with the extended interface littlefs uses."""

    def __init__(self, block_size, blocks):
        self.block_size = block_size
        self.data = bytearray(block_size * blocks)
        self.view = memoryview(self.data)

    def readblocks(self, block_num, buf, offset=0):
        addr = block_num * self.block_size + offset
        buf[:] = self.view[addr : addr + len(buf)]

    def writeblocks(self, block_num, buf, offset=None):
        addr = block_num * self.block_size + (offset or 0)
        self.view[addr : addr + len(buf)] = buf

    def ioctl(self, op, arg):
        if op == 4:  # block count
            return len(self.data) // self.block_size
        if op == 5:  # block size
            return self.block_size
        if op == 6:  # erase: nothing to do in RAM
            return 0
        return None


def _mounted(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


if not _mounted("/flash"):
    _bdev = RAMBlockDev(BLOCK_SIZE, BLOCKS)
    vfs.VfsLfs2.mkfs(_bdev)
    vfs.mount(vfs.VfsLfs2(_bdev), "/flash")
    os.chdir("/flash")
    for _p in ("/flash", "/flash/lib"):
        if _p not in sys.path:
            sys.path.append(_p)
    print("velxio: /flash is a %d KB littlefs in RAM" % (BLOCK_SIZE * BLOCKS // 1024))
