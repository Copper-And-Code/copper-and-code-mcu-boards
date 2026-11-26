# ESP32-4848S040 for the Velxio simulator (our QEMU's esp32s3-picsimlab machine), not
# for a board: esp_rgb shows its framebuffers on the emulator's virtual RGB display
# (MICROPY_HW_RGB_VELXIO, modules/esp_rgb/esp_rgb.c) instead of the ST7701 panel, and
# display_driver reads the GT911 on the hardware I2C. Run it with
# -m 8M -global ssi_psram.is_octal=true (the board's 8 MB octal PSRAM).
list(APPEND MICROPY_DEF_BOARD
    MICROPY_HW_BOARD_NAME="ESP32-4848S040 Velxio"
    MICROPY_HW_RGB_VELXIO=1
)
