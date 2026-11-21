// This board is confirmed to operate using stlink and openocd.
// REPL is on UART(1) and is available through the stlink USB-UART device.
// To use openocd run "OPENOCD_CONFIG=boards/openocd_stm32f7.cfg" in
// the make command.
// STM32F769I-DISCO (MB1225B) with the MB1166 DSI display: MicroPython's STM32F769DISC with the
// SDRAM on (the GC heap there) and LVGL. Out-of-tree board of copper-and-code-mcu-boards.
#define MICROPY_HW_BOARD_NAME       "STM32F769I-DISCO"

// The MB1166 display (modules/st_ltdc): an OTM8009A on a 2-lane MIPI-DSI link in video
// mode, DSI PLL from ST's BSP (HSE 25 MHz / 5 x 2 x 100 / 1 = 1 GHz, lanes at 500 Mbit/s,
// lane byte clock 62.5 MHz). Two RGB565 framebuffers of 800x480 (750 KB each) in the top
// 2 MB of the SDRAM, out of the GC heap. Reset PJ15; brightness by DCS command.
#define MICROPY_HW_LTDC_DSI             (1)
#define MICROPY_HW_LTDC_DSI_PLL_NDIV    (100)
#define MICROPY_HW_LTDC_DSI_PLL_IDF     (5)     // DSI_PLL_IN_DIV5
#define MICROPY_HW_LTDC_DSI_PLL_ODF     (0)     // DSI_PLL_OUT_DIV1
#define MICROPY_HW_LTDC_DSI_LANES       (1)     // DSI_TWO_DATA_LANES
#define MICROPY_HW_LTDC_RST             (pin_J15)
#define MICROPY_HW_LTDC_FB_BYTES        (2 * 1024 * 1024)

// End of soft reset: clear LVGL's GC state (modules/st_ltdc/st_ltdc.c).
struct _boardctrl_state_t;
void st_ltdc_board_end_soft_reset(struct _boardctrl_state_t *state);
#define MICROPY_BOARD_END_SOFT_RESET st_ltdc_board_end_soft_reset
#define MICROPY_HW_MCU_NAME         "STM32F769"

#define MICROPY_HW_HAS_SWITCH       (1)
#define MICROPY_HW_HAS_FLASH        (1)
#define MICROPY_HW_ENABLE_RNG       (1)
#define MICROPY_HW_ENABLE_RTC       (1)
#define MICROPY_HW_ENABLE_USB       (1)
#define MICROPY_HW_ENABLE_SERVO     (1)
#define MICROPY_HW_ENABLE_SDCARD    (1)

#define MICROPY_BOARD_EARLY_INIT    board_early_init
void board_early_init(void);

// HSE is 25MHz
// VCOClock = HSE * PLLN / PLLM = 25 MHz * 384 / 25 = 384 MHz
// SYSCLK = VCOClock / PLLP = 384 MHz / 2 = 192 MHz
// USB/SDMMC/RNG Clock = VCOClock / PLLQ = 384 MHz / 8 = 48 MHz
// 192 MHz, not MicroPython's 216: the SDRAM's clock is half of SYSCLK and must stay at or below
// 100 MHz (96 here), as MicroPython's own note on this board's SDRAM says.
#define MICROPY_HW_CLK_PLLM (25)
#define MICROPY_HW_CLK_PLLN (384)
#define MICROPY_HW_CLK_PLLP (RCC_PLLP_DIV2)
#define MICROPY_HW_CLK_PLLQ (8)

#define MICROPY_HW_FLASH_LATENCY    FLASH_LATENCY_6 // 180-210 MHz at 2.7-3.6 V: 6 wait states

// 512MBit external QSPI flash, used for either the filesystem or XIP memory mapped
#define MICROPY_HW_QSPIFLASH_SIZE_BITS_LOG2 (29)
#define MICROPY_HW_QSPIFLASH_CS     (pin_B6)
#define MICROPY_HW_QSPIFLASH_SCK    (pin_B2)
#define MICROPY_HW_QSPIFLASH_IO0    (pin_C9)
#define MICROPY_HW_QSPIFLASH_IO1    (pin_C10)
#define MICROPY_HW_QSPIFLASH_IO2    (pin_E2)
#define MICROPY_HW_QSPIFLASH_IO3    (pin_D13)

// SPI flash, block device config (when used as the filesystem)
extern const struct _mp_spiflash_config_t spiflash_config;
extern struct _spi_bdev_t spi_bdev;
#if !USE_QSPI_XIP
#define MICROPY_HW_ENABLE_INTERNAL_FLASH_STORAGE (0)
#define MICROPY_HW_SPIFLASH_ENABLE_CACHE (1)
#define MICROPY_HW_BDEV_SPIFLASH    (&spi_bdev)
#define MICROPY_HW_BDEV_SPIFLASH_CONFIG (&spiflash_config)
#define MICROPY_HW_BDEV_SPIFLASH_SIZE_BYTES ((1 << MICROPY_HW_QSPIFLASH_SIZE_BITS_LOG2) / 8)
#define MICROPY_HW_BDEV_SPIFLASH_EXTENDED (&spi_bdev) // for extended block protocol
#endif

// UART config
#define MICROPY_HW_UART1_TX         (pin_A9)
#define MICROPY_HW_UART1_RX         (pin_A10)
#define MICROPY_HW_UART5_TX         (pin_C12)
#define MICROPY_HW_UART5_RX         (pin_D2)
// The Arduino connector's D1 (TX) and D0 (RX), as on an Arduino Uno.
#define MICROPY_HW_UART6_TX         (pin_C6)
#define MICROPY_HW_UART6_RX         (pin_C7)
#define MICROPY_HW_UART_REPL        PYB_UART_1
#define MICROPY_HW_UART_REPL_BAUD   115200

// I2C buses
#define MICROPY_HW_I2C1_SCL         (pin_B8)
#define MICROPY_HW_I2C1_SDA         (pin_B9)
// I2C4: the touch controller of the display and the audio codec (ST's BSP and pin data).
// MicroPython's STM32F769DISC has I2C3 on PH7/PH8 here, but PH8 is the SDRAM's data line D16 on
// this board: using it corrupts the memory MicroPython runs in.
#define MICROPY_HW_I2C4_SCL         (pin_D12)
#define MICROPY_HW_I2C4_SDA         (pin_B7)

// SPI buses
#define MICROPY_HW_SPI2_NSS         (pin_A11)
#define MICROPY_HW_SPI2_SCK         (pin_A12)
#define MICROPY_HW_SPI2_MISO        (pin_B14)
#define MICROPY_HW_SPI2_MOSI        (pin_B15)

// CAN buses
#define MICROPY_HW_CAN1_TX          (pin_B9)
#define MICROPY_HW_CAN1_RX          (pin_B8)
#define MICROPY_HW_CAN2_TX          (pin_B13)
#define MICROPY_HW_CAN2_RX          (pin_B12)

// USRSW is pulled low. Pressing the button makes the input go high.
#define MICROPY_HW_USRSW_PIN        (pin_A0)
#define MICROPY_HW_USRSW_PULL       (GPIO_NOPULL)
#define MICROPY_HW_USRSW_EXTI_MODE  (GPIO_MODE_IT_RISING)
#define MICROPY_HW_USRSW_PRESSED    (1)

// LEDs
#define MICROPY_HW_LED1             (pin_J13) // red
#define MICROPY_HW_LED2             (pin_J5) // green
#define MICROPY_HW_LED3             (pin_A12) // green
#define MICROPY_HW_LED_ON(pin)      (mp_hal_pin_high(pin))
#define MICROPY_HW_LED_OFF(pin)     (mp_hal_pin_low(pin))

// SD card
#define MICROPY_HW_SDCARD_SDMMC             (2)
#define MICROPY_HW_SDCARD_CK                (pin_D6)
#define MICROPY_HW_SDCARD_CMD               (pin_D7)
#define MICROPY_HW_SDCARD_D0                (pin_G9)
#define MICROPY_HW_SDCARD_D1                (pin_G10)
#define MICROPY_HW_SDCARD_D2                (pin_B3)
#define MICROPY_HW_SDCARD_D3                (pin_B4)
#define MICROPY_HW_SDCARD_DETECT_PIN        (pin_I15)
#define MICROPY_HW_SDCARD_DETECT_PULL       (GPIO_PULLUP)
#define MICROPY_HW_SDCARD_DETECT_PRESENT    (GPIO_PIN_RESET)

// USB config (CN15 - USB OTG HS with external PHY)
#define MICROPY_HW_USB_HS (1)
#define MICROPY_HW_USB_HS_ULPI_NXT  (pin_H4)
#define MICROPY_HW_USB_HS_ULPI_DIR  (pin_I11)

// Before boot.py: boot.py and main.py from /flash even with an SD card in (board_boot.py).
#define MICROPY_BOARD_FROZEN_BOOT_FILE "board_boot.py"

// Audio: the WM8994 codec on SAI1 block A (modules/st_audio, python/stm32/audio.py)
#define MICROPY_HW_AUDIO_SAI1       (1)

// Ethernet via RMII (the board's RJ45 jack, 10/100 Mbit)
#if 1
#define MICROPY_HW_ETH_MDC          (pin_C1)
#define MICROPY_HW_ETH_MDIO         (pin_A2)
#define MICROPY_HW_ETH_RMII_REF_CLK (pin_A1)
#define MICROPY_HW_ETH_RMII_CRS_DV  (pin_A7)
#define MICROPY_HW_ETH_RMII_RXD0    (pin_C4)
#define MICROPY_HW_ETH_RMII_RXD1    (pin_C5)
#define MICROPY_HW_ETH_RMII_TX_EN   (pin_G11)
#define MICROPY_HW_ETH_RMII_TXD0    (pin_G13)
#define MICROPY_HW_ETH_RMII_TXD1    (pin_G14)
#endif

#if 1
// The SDRAM (16 MB, 32 bits): the GC heap. SYSCLK 192 MHz (above), so a 96 MHz SD clock.

#define MICROPY_HW_SDRAM_SIZE (128 * 1024 * 1024 / 8) // 128 Mbit
#define MICROPY_HW_SDRAM_STARTUP_TEST (0)
#define MICROPY_HEAP_START sdram_start()
// The top MICROPY_HW_LTDC_FB_BYTES of the SDRAM are the display's framebuffers.
#define MICROPY_HEAP_END ((void *)((uint8_t *)sdram_end() - MICROPY_HW_LTDC_FB_BYTES))

// Timings of ST's BSP for this board (stm32f769i_discovery_sdram.c: at 100 MHz with CAS latency 3),
// here at 96 MHz (10.4 ns).
#define MICROPY_HW_SDRAM_TIMING_TMRD        (2)
#define MICROPY_HW_SDRAM_TIMING_TXSR        (7)
#define MICROPY_HW_SDRAM_TIMING_TRAS        (4)
#define MICROPY_HW_SDRAM_TIMING_TRC         (7)
#define MICROPY_HW_SDRAM_TIMING_TWR         (2)
#define MICROPY_HW_SDRAM_TIMING_TRP         (2)
#define MICROPY_HW_SDRAM_TIMING_TRCD        (2)
#define MICROPY_HW_SDRAM_REFRESH_RATE       (64) // ms

#define MICROPY_HW_SDRAM_BURST_LENGTH       1
#define MICROPY_HW_SDRAM_CAS_LATENCY        3
#define MICROPY_HW_SDRAM_FREQUENCY_KHZ      (96000) // 96 MHz
#define MICROPY_HW_SDRAM_COLUMN_BITS_NUM    8
#define MICROPY_HW_SDRAM_ROW_BITS_NUM       12
#define MICROPY_HW_SDRAM_MEM_BUS_WIDTH      32
#define MICROPY_HW_SDRAM_INTERN_BANKS_NUM   4
#define MICROPY_HW_SDRAM_CLOCK_PERIOD       2
#define MICROPY_HW_SDRAM_RPIPE_DELAY        0
#define MICROPY_HW_SDRAM_RBURST             (1)
#define MICROPY_HW_SDRAM_WRITE_PROTECTION   (0)
#define MICROPY_HW_SDRAM_AUTOREFRESH_NUM    (8)
#define MICROPY_HW_SDRAM_REFRESH_CYCLES     8192

// See pins.csv for CPU pin mapping
#define MICROPY_HW_FMC_SDCKE0  (pyb_pin_FMC_SDCKE0)
#define MICROPY_HW_FMC_SDNE0   (pyb_pin_FMC_SDNE0)
#define MICROPY_HW_FMC_SDCLK   (pyb_pin_FMC_SDCLK)
#define MICROPY_HW_FMC_SDNCAS  (pyb_pin_FMC_SDNCAS)
#define MICROPY_HW_FMC_SDNRAS  (pyb_pin_FMC_SDNRAS)
#define MICROPY_HW_FMC_SDNWE   (pyb_pin_FMC_SDNWE)
#define MICROPY_HW_FMC_BA0     (pyb_pin_FMC_BA0)
#define MICROPY_HW_FMC_BA1     (pyb_pin_FMC_BA1)
#define MICROPY_HW_FMC_NBL0    (pyb_pin_FMC_NBL0)
#define MICROPY_HW_FMC_NBL1    (pyb_pin_FMC_NBL1)
#define MICROPY_HW_FMC_NBL2    (pyb_pin_FMC_NBL2)
#define MICROPY_HW_FMC_NBL3    (pyb_pin_FMC_NBL3)
#define MICROPY_HW_FMC_A0      (pyb_pin_FMC_A0)
#define MICROPY_HW_FMC_A1      (pyb_pin_FMC_A1)
#define MICROPY_HW_FMC_A2      (pyb_pin_FMC_A2)
#define MICROPY_HW_FMC_A3      (pyb_pin_FMC_A3)
#define MICROPY_HW_FMC_A4      (pyb_pin_FMC_A4)
#define MICROPY_HW_FMC_A5      (pyb_pin_FMC_A5)
#define MICROPY_HW_FMC_A6      (pyb_pin_FMC_A6)
#define MICROPY_HW_FMC_A7      (pyb_pin_FMC_A7)
#define MICROPY_HW_FMC_A8      (pyb_pin_FMC_A8)
#define MICROPY_HW_FMC_A9      (pyb_pin_FMC_A9)
#define MICROPY_HW_FMC_A10     (pyb_pin_FMC_A10)
#define MICROPY_HW_FMC_A11     (pyb_pin_FMC_A11)
#define MICROPY_HW_FMC_A12     (pyb_pin_FMC_A12)
#define MICROPY_HW_FMC_D0      (pyb_pin_FMC_D0)
#define MICROPY_HW_FMC_D1      (pyb_pin_FMC_D1)
#define MICROPY_HW_FMC_D2      (pyb_pin_FMC_D2)
#define MICROPY_HW_FMC_D3      (pyb_pin_FMC_D3)
#define MICROPY_HW_FMC_D4      (pyb_pin_FMC_D4)
#define MICROPY_HW_FMC_D5      (pyb_pin_FMC_D5)
#define MICROPY_HW_FMC_D6      (pyb_pin_FMC_D6)
#define MICROPY_HW_FMC_D7      (pyb_pin_FMC_D7)
#define MICROPY_HW_FMC_D8      (pyb_pin_FMC_D8)
#define MICROPY_HW_FMC_D9      (pyb_pin_FMC_D9)
#define MICROPY_HW_FMC_D10     (pyb_pin_FMC_D10)
#define MICROPY_HW_FMC_D11     (pyb_pin_FMC_D11)
#define MICROPY_HW_FMC_D12     (pyb_pin_FMC_D12)
#define MICROPY_HW_FMC_D13     (pyb_pin_FMC_D13)
#define MICROPY_HW_FMC_D14     (pyb_pin_FMC_D14)
#define MICROPY_HW_FMC_D15     (pyb_pin_FMC_D15)
#define MICROPY_HW_FMC_D16     (pyb_pin_FMC_D16)
#define MICROPY_HW_FMC_D17     (pyb_pin_FMC_D17)
#define MICROPY_HW_FMC_D18     (pyb_pin_FMC_D18)
#define MICROPY_HW_FMC_D19     (pyb_pin_FMC_D19)
#define MICROPY_HW_FMC_D20     (pyb_pin_FMC_D20)
#define MICROPY_HW_FMC_D21     (pyb_pin_FMC_D21)
#define MICROPY_HW_FMC_D22     (pyb_pin_FMC_D22)
#define MICROPY_HW_FMC_D23     (pyb_pin_FMC_D23)
#define MICROPY_HW_FMC_D24     (pyb_pin_FMC_D24)
#define MICROPY_HW_FMC_D25     (pyb_pin_FMC_D25)
#define MICROPY_HW_FMC_D26     (pyb_pin_FMC_D26)
#define MICROPY_HW_FMC_D27     (pyb_pin_FMC_D27)
#define MICROPY_HW_FMC_D28     (pyb_pin_FMC_D28)
#define MICROPY_HW_FMC_D29     (pyb_pin_FMC_D29)
#define MICROPY_HW_FMC_D30     (pyb_pin_FMC_D30)
#define MICROPY_HW_FMC_D31     (pyb_pin_FMC_D31)
#endif

/******************************************************************************/
// Bootloader configuration

// Give Mboot access to the external QSPI flash
#define MBOOT_SPIFLASH_ADDR                     (0x90000000)
#define MBOOT_SPIFLASH_BYTE_SIZE                (512 * 128 * 1024)
#define MBOOT_SPIFLASH_LAYOUT                   "/0x90000000/512*128Kg"
#define MBOOT_SPIFLASH_ERASE_BLOCKS_PER_PAGE    (128 / 4) // 128k page, 4k erase block
#define MBOOT_SPIFLASH_CONFIG                   (&spiflash_config)
#define MBOOT_SPIFLASH_SPIFLASH                 (&spi_bdev.spiflash)
