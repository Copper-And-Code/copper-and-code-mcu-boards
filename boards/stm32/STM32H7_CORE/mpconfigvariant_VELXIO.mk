# STM32H7_CORE V1.3 for the Velxio simulator (Renode), not for a board: no USB and
# no SD card (Renode models neither), its own board name so that stm32_board.py
# does not look for the GT911.
CFLAGS += -DBOARD_V13 -DBOARD_VELXIO
