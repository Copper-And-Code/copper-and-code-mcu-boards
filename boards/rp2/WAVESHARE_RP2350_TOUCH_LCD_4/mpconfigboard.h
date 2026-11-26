// Board and hardware specific configuration
#ifndef MICROPY_HW_BOARD_NAME
#define MICROPY_HW_BOARD_NAME "Waveshare RP2350-Touch-LCD-4"
#endif

// UART0 on the header pins (GPIO46 TX, GPIO45 RX).
#define MICROPY_HW_UART0_TX     (46)
#define MICROPY_HW_UART0_RX     (45)
#define MICROPY_HW_UART0_CTS    (-1)
#define MICROPY_HW_UART0_RTS    (-1)

// UART1 on GPIO8 TX, GPIO9 RX.
#define MICROPY_HW_UART1_TX     (8)
#define MICROPY_HW_UART1_RX     (9)
#define MICROPY_HW_UART1_CTS    (-1)
#define MICROPY_HW_UART1_RTS    (-1)

// I2C1 (GT911 touch, PCF85063 RTC, QMI8658 IMU) is the default bus, on
// GPIO6 SDA / GPIO7 SCL: see PICO_DEFAULT_I2C in waveshare_rp2350_touch_lcd_4.h.

// RGB panel framebuffer scale (modules/rgbpanel): 0 = chosen at boot, 1 = full 480x480
// (needs PSRAM on U9), 2 = 240x240 shown as 2x2 pixels (SRAM only).
#ifndef MICROPY_HW_RGBPANEL_SCALE
#define MICROPY_HW_RGBPANEL_SCALE (0)
#endif

// With PSRAM fitted the system clock goes to this value at boot, before main.c sets the
// flash and PSRAM timing: the GC heap is then in PSRAM, which this makes faster.
// Without PSRAM the board stays at the default 150 MHz.
#ifndef MICROPY_HW_RGBPANEL_PSRAM_SYS_CLK_KHZ
#define MICROPY_HW_RGBPANEL_PSRAM_SYS_CLK_KHZ (240000)
#endif
void rgbpanel_board_startup(void);
#define MICROPY_BOARD_STARTUP() rgbpanel_board_startup()
// The framebuffer comes from the end of the SRAM heap area, chosen before gc_init():
// 480x480 with PSRAM (the GC heap then lives in PSRAM), else 240x240 (patches/micropython).
#include <stddef.h>
#include <stdint.h>
void rgbpanel_board_sram_heap(uint8_t **start, uint8_t **end, size_t psram_size);
#define MICROPY_BOARD_SRAM_HEAP(start, end, psram_size) rgbpanel_board_sram_heap(start, end, psram_size)

// Soft reset: let modules/rgbpanel drop LVGL's state (see rgbpanel_board_end_soft_reset).
void rgbpanel_board_end_soft_reset(void);
#define MICROPY_BOARD_END_SOFT_RESET() rgbpanel_board_end_soft_reset()

// LVGL's memory pools (omnipython-lvgl#15): LVGL's allocations in TLSF pools held in GC
// blocks, so they do not walk the GC heap. Here, not in the cmake file, so that the scan
// for root pointers sees it too. LVMP_POOLS=none (scripts/build.sh) sets 0.
#ifndef LVMP_POOL_TLSF
#define LVMP_POOL_TLSF (1)
#endif
