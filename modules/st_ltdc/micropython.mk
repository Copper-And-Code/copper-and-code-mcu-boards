# st_ltdc: LTDC + DMA2D display driver for the STM32 boards of this repo.
ST_LTDC_MOD_DIR := $(USERMOD_DIR)

SRC_USERMOD_C += $(ST_LTDC_MOD_DIR)/st_ltdc.c
CFLAGS_USERMOD += -I$(ST_LTDC_MOD_DIR)

# STM32F7 with a DSI panel (the STM32F769I-DISCO): the panel controller's set-up from ST
# (otm8009a.c, BSD-3). The HAL's DSI driver is added by the board (HAL_SRC_C).
ifeq ($(MCU_SERIES),f7)
SRC_USERMOD_LIB_C += $(ST_LTDC_MOD_DIR)/otm8009a.c
endif
