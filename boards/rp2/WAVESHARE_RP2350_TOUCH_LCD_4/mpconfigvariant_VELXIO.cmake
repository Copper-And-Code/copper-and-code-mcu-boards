# Velxio variant: the board in our QEMU's RP2350 machine (raspi-pico2,
# Copper-And-Code qemu). Build: scripts/build.sh rp2 WAVESHARE_RP2350_TOUCH_LCD_4 VELXIO
#  - the REPL on UART0 (GPIO46/45, the emulator's serial port), no USB device;
#  - no coprocessors beyond the FPU, which the machine does not have: GPIO
#    through the SIO registers, software doubles, floats on the M33 FPU
#    (MICROPY_RP2350_NO_DCP, patches/micropython/0002), and modules/rgbpanel's
#    FPU-only start-up in place of the SDK's coprocessor init.
set(PICO_PLATFORM "rp2350")
set(PICO_DEFAULT_DOUBLE_IMPL compiler)
set(MICROPY_RP2350_NO_DCP 1)

list(APPEND MICROPY_DEF_BOARD
    MICROPY_HW_BOARD_NAME="Waveshare RP2350-Touch-LCD-4 Velxio"
    MICROPY_HW_ENABLE_UART_REPL=1
    MICROPY_HW_ENABLE_USBDEV=0
    MICROPY_HW_RGBPANEL_VELXIO=1
    PICO_USE_GPIO_COPROCESSOR=0
    PICO_RUNTIME_SKIP_INIT_PER_CORE_ENABLE_COPROCESSORS=1
)
