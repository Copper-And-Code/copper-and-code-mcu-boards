# copper-and-code-mcu-boards

**MicroPython and LVGL firmware for microcontroller boards with a touch screen.** Flash the board,
then `import display_driver`: the display, the touch and LVGL are running, and the same program
works on every board here. Write the GUI in Python, run it with `mpremote` or Thonny, or design it
in [Copper and Code Studio](https://copper-and-code.github.io/copper-and-code-studio/) and upload
it from there.

<div class="home-grid" markdown>
<div class="home-card" markdown>
**Download**

Ready images for every board in the
[releases](https://github.com/Copper-And-Code/copper-and-code-mcu-boards/releases), with their
SHA-256 sums.
</div>
<div class="home-card" markdown>
**One driver, every board**

`WIDTH`, `HEIGHT`, `start()`, `stop()`, `backlight()` and what a Ctrl-C does are the same
everywhere: [the display_driver contract](display-driver.md).
</div>
<div class="home-card" markdown>
**Upstream, unchanged**

MicroPython 1.29 and [omnipython-lvgl](https://github.com/PyDevices/omnipython-lvgl) as they are:
out-of-tree boards and C modules, no fork.
</div>
</div>

## Boards

| Board | MCU | Display | State |
|---|---|---|---|
| [Waveshare RP2350-Touch-LCD-4](boards/rp2350-touch-lcd-4.md) | RP2350B | 4" 480x480 RGB, touch | works. **240x240** as Waveshare ships it; **480x480** with an 8 MB PSRAM soldered on U9 |
| [STM32H7_CORE V1.3 and V1.0](stm32h743.md) | STM32H743 | RGB panel on LTDC, 1024x600 tested, touch | works, 58 fps |
| [DEV190806042](stm32h743.md) | STM32H743 | RGB panel on LTDC, 1024x600 tested, touch | works, 58 fps |
| [FK743M5-XIH6](stm32h743.md) | STM32H743 | RGB panel on LTDC, 1024x600 tested, touch | works, 58 fps |
| [ESP32-4848S040](esp32-4848s040.md) | ESP32-S3 | 4" 480x480 RGB, touch | works, 42 fps, SD card, audio |
| STM32F769I-DISCO | STM32F769NI | 4" 800x480 MIPI-DSI, touch | in development, in no release yet |

## Start

1. Download the image for your board from the
   [latest release](https://github.com/Copper-And-Code/copper-and-code-mcu-boards/releases/latest).
2. Flash it: the RP2350 takes the `.uf2` on its USB drive; the STM32 boards [with DFU](flash-dfu.md);
   the ESP32-4848S040 [with esptool](esp32-4848s040.md).
3. Run an [example](examples.md):

```python
import display_driver
import lvgl as lv

label = lv.label(lv.screen_active())
label.set_text("Hello")
label.center()
```

The program can end there: `display_driver` keeps LVGL running from a timer.

## Building

`scripts/build.sh <port> <BOARD> [VARIANT]` fetches the pinned sources and toolchain and writes the
firmware into `dist/`: see [Building](target.md) and the
[repository](https://github.com/Copper-And-Code/copper-and-code-mcu-boards).

> A personal, experimental project for makers, not affiliated with, sponsored or endorsed by any of
> the manufacturers of the boards and chips it uses; their names only identify the hardware.

MIT licence; third-party data and provenance in [Credits](CREDITS.md).
