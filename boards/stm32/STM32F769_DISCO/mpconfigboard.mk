# STM32F769I-DISCO (MB1225B, MB1166 display), out-of-tree board:
# make -C ports/stm32 BOARD_DIR=<this directory>. From MicroPython's STM32F769DISC: the program
# in the internal flash, the filesystem in the external QSPI flash (64 MB).
USE_MBOOT ?= 0

# MCU settings
MCU_SERIES = f7
CMSIS_MCU = STM32F769xx
MICROPY_FLOAT_IMPL = double
# LVGL also needs a few float functions (sinf, ...): see this file.
include $(BOARD_DIR)/../lvgl_libm.mk
include $(BOARD_DIR)/../lvgl_pool.mk
AF_FILE = boards/stm32f767_af.csv

# The HAL's DSI driver, for the display (modules/st_ltdc); the port does not build it.
HAL_SRC_C += $(addprefix $(STM32LIB_HAL_BASE)/Src/stm32$(MCU_SERIES)xx_, hal_dsi.c)

# This board's copy of boards/stm32f769.ld, with the whole 2 MB (MicroPython's has 1 MB).
LD_FILES = $(BOARD_DIR)/stm32f769.ld boards/common_basic.ld
TEXT0_ADDR = 0x08000000

# MicroPython settings: Ethernet with lwIP and mbedTLS, as MicroPython's STM32F769DISC. With LVGL
# the program is about 1.3 MB of the 2 MB internal flash (it did not fit in the 1 MB of
# MicroPython's linker script, the reason the network was off at first).
MICROPY_VFS_LFS2 = 1
MICROPY_PY_LWIP = 1
MICROPY_PY_SSL = 1
MICROPY_SSL_MBEDTLS = 1

FROZEN_MANIFEST ?= $(BOARD_DIR)/manifest.py

# The C module and manifest of omnipython-lvgl (PyDevices), its ports/micropython, used as
# $(LVMP_DIR) in manifest.py: as for the STM32H7_CORE (see its mpconfigboard.mk).
ifneq ($(LVMP_DIR),)
MICROPY_MANIFEST_LVMP_DIR ?= $(LVMP_DIR)
else
MICROPY_MANIFEST_LVMP_DIR ?= $(abspath $(BOARD_DIR)/../../../../omnipython-lvgl/ports/micropython)
endif
