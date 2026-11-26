# Programming the RP2350-Touch-LCD-4 and the ESP32-4848S040

From a board in its box to your own program on the screen, starting at power-on. Both boards
run the same MicroPython and LVGL, with the same [`display_driver`](display-driver.md), so a
program written for one runs on the other.

| | Waveshare RP2350-Touch-LCD-4 | ESP32-4848S040 |
|---|---|---|
| Connection | native USB, `/dev/ttyACM0` on Linux | CH340 USB-serial, `/dev/ttyUSB0` |
| Firmware | `WAVESHARE_RP2350_TOUCH_LCD_4-<version>.uf2` | `ESP32_4848S040-<version>.bin` |
| Resolution LVGL draws at | 240x240, or 480x480 with an 8 MB PSRAM on U9 | 480x480 |
| Memory for the program | about 190 KB without PSRAM | 8 MB of PSRAM |
| Storage | 12 MiB of flash | 16 MB flash, SD card |
| Extras | buzzer, connector for a C64 keyboard | Wi-Fi, speaker, SD card |
| Tried here with `mpremote` | yes | not yet |

## 1. What you need

- A USB cable that carries data, not only power.
- [`mpremote`](https://docs.micropython.org/en/latest/reference/mpremote.html), the
  MicroPython command line tool: `pip install mpremote`. Or
  [Thonny](https://thonny.org/), an editor with the board's files in a side panel. Or
  [Copper and Code Studio](https://copper-and-code.github.io/copper-and-code-studio/), to draw
  the screens instead of writing them.
- For the ESP32: `esptool` (`pip install esptool`), to write the firmware.
- On Linux, your user in the `dialout` group to open the serial port.

## 2. The firmware

Take the image for your board from the
[latest release](https://github.com/Copper-And-Code/copper-and-code-mcu-boards/releases/latest)
and check it against `SHA256SUMS`.

**RP2350:** hold BOOT and plug the USB cable (or press RESET with BOOT held). The board
appears as a drive called `RP2350`: copy the `.uf2` onto it. It restarts by itself with the
new firmware. Your files are kept: the filesystem lives after the firmware in the flash.
Details in [the board's page](boards/rp2350-touch-lcd-4.md#flash).

**ESP32:** the image is complete and goes at offset 0:

```bash
esptool.py --chip esp32s3 -p /dev/ttyUSB0 -b 460800 write_flash 0x0 ESP32_4848S040-<version>.bin
```

If the board had other firmware before, run
`esptool.py --chip esp32s3 -p /dev/ttyUSB0 erase_flash` first. That erases the files too.
Without it the board can stop at boot with "The filesystem appears to be corrupted".

## 3. The REPL and a first program

Open the REPL, the MicroPython prompt on the serial port:

```bash
mpremote connect /dev/ttyACM0 repl      # RP2350
mpremote connect /dev/ttyUSB0 repl      # ESP32
```

Then type:

```python
import display_driver
import lvgl as lv

label = lv.label(lv.screen_active())
label.set_text("Hello")
label.center()
```

"Hello" appears on the screen. `import display_driver` started the panel, the touch and
LVGL, and keeps LVGL running in the background: the program needs no loop of its own, and
the prompt stays free. Ctrl-] leaves `mpremote`.

What `display_driver` gives a program, the same on every board:

- `display_driver.WIDTH`, `display_driver.HEIGHT`: the size of the screen in LVGL's pixels.
- `display_driver.backlight(percent)`: the brightness, 0 to 100.
- `display_driver.indev`: the touch, or `None` if it did not answer.
- `display_driver.stop()` and `start()`: for a program that calls `lv.timer_handler()` in
  its own loop.

The full list is in [the display_driver contract](display-driver.md).

## 4. A program in a file

Write the program in a file on the computer, `app.py`, and run it:

```bash
mpremote connect /dev/ttyACM0 run app.py
```

`run` sends the file and runs it, but does not leave it on the board. The examples of this
repository are the place to start: `mpremote run examples/button.py`. See
[Examples](examples.md).

To keep the program on the board and start it at every power-on, copy it as `main.py`:

```bash
mpremote connect /dev/ttyACM0 cp app.py :main.py
mpremote connect /dev/ttyACM0 reset
```

Use `main.py`, not `boot.py`: `boot.py` also runs when Thonny or `mpremote` take the board,
and a program with a screen there keeps them out.

Other files: `mpremote cp ui_parts.py :` copies a module next to `main.py`, `mpremote ls`
lists the files, `mpremote rm :old.py` deletes one. A program can import the modules you
copied as usual.

## 5. Thonny and Copper and Code Studio

**Thonny:** in Tools > Options > Interpreter choose "MicroPython (generic)" and the board's
port. The editor runs the open file with F5 and shows the board's files; saving a file as
`main.py` on the board makes it start at power-on. Thonny stops the running program with
Ctrl-C when it connects, so a program in `main.py` does not keep it out (one in `boot.py`
can). Thonny has not been tried with these boards yet, only its serial protocol, on the
ESP32.

**Copper and Code Studio:** draw the screens, write the handlers in Python, try them in the
simulator, then connect to the board and upload. The Studio puts each app in a folder of
its own in `/lms_apps/` and can install it to start at power-on. See
[its documentation](https://copper-and-code.github.io/copper-and-code-studio/).

Close Thonny or the Studio before using `mpremote`: only one program at a time can hold the
serial port.

## 6. What changes between the two boards

**Sizes.** The RP2350 draws at 240x240 (480x480 with the PSRAM), the ESP32 at 480x480. A
program that takes its sizes from `WIDTH` and `HEIGHT`, or uses LVGL's alignment, looks
the same on both. The module `ui`, in the firmware of both boards, helps with that:

```python
import ui
button.set_size(ui.px(120), ui.px(40))   # 120x40 at 240 px, twice that at 480 px
label.set_style_text_font(ui.font(24), 0)  # the closest font in the firmware
```

**Memory on the RP2350 without PSRAM.** About 190 KB are free after `import display_driver`,
for LVGL's objects and for the program. Two things fill it quickly:

- Opacity, rotation and scaling on large widgets: LVGL draws them in a separate buffer of 4
  bytes per pixel, allocated in one piece. If that fails the screen stops updating. See
  [the board's page](boards/rp2350-touch-lcd-4.md#memory-limits-no-psram).
- Large modules compiled on the board. Compile them on the computer with `mpy-cross` and copy
  the `.mpy`: the shell of the examples needs that.

**SD card on the ESP32.** Mount it after `import display_driver`, which shares two of the
card's lines with the panel:

```python
import display_driver, machine, os
os.mount(machine.SDCard(slot=2, sck=48, miso=41, mosi=47, cs=42, freq=10_000_000), "/sd")
```

**Wi-Fi on the ESP32.** `network` and `socket` work as in MicroPython. In a program with a
screen, read sockets in non-blocking mode: a blocking read can hold LVGL for up to 100 ms.
Measurements in [the board's page](esp32-4848s040.md#wifi).

**Sound.** `buzzer.beep(880)` and the other functions of `buzzer` work on both: on the RP2350
through the buzzer, on the ESP32 through the speaker. On the ESP32 the module `audio` also
plays WAV files.

**The ESP32's home.** [examples/home](https://github.com/Copper-And-Code/copper-and-code-mcu-boards/tree/main/examples/home)
turns the ESP32 into a small computer: a menu of apps on the touch screen, a shell, the
weather and the games, all on the SD card.

## 7. When something goes wrong

- **Ctrl-C** stops the program and the screen stays as it was; LVGL goes on running
  (firmware v0.1.7 and later).
- **Ctrl-D** at the empty prompt is a soft reset: Python starts again, `main.py` runs again.
- **A program in `main.py` blocks the board.** Ctrl-C in the REPL stops it; then
  `mpremote rm :main.py`. On the ESP32, the last resort is `erase_flash` and the firmware
  again, which also erases the files.
- **`MemoryError`** on the RP2350: see the memory section above.
- **The ESP32 does not start, or stays in its bootloader** after the port is opened: on that
  board the port's DTR line drives the boot pin. The scripts of this repository open the
  port with DTR low (`scripts/uart_run.py --dtr 0`). With `mpremote` and Thonny this board
  has not been tried yet.
