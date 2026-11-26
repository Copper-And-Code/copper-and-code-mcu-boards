# The VELXIO variant (Velxio simulator, Renode): the board's manifest plus the
# modules only the simulator uses, so the firmware of the real board leaves
# them out. mpconfigvariant_VELXIO.mk selects it.
include("$(BOARD_DIR)/manifest.py")
# Touch from the simulator's mailbox (stm32_board.py imports it in Velxio).
module("velxio_touch.py", base_path="$(BOARD_DIR)/../../../python")
# Frozen boot file: a littlefs in RAM on /flash (MICROPY_BOARD_FROZEN_BOOT_FILE).
module("velxio_boot.py", base_path="$(BOARD_DIR)/../../../python")
