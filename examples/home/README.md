# Home: the shell and a touch menu of apps (ESP32-4848S040)

At power-on the [shell](../shell/) on the display, with the keyboard of the serial terminal. A tap on
the terminal opens a menu of apps; a tap on an app resets the board and starts that app alone, with
all the memory. The home button at the top centre brings the shell back the same way. An entry of
the menu can be a folder (such as "Games") with a menu of its own. Everything but `main.py` lives on
the SD card.

Ported from `mpy_home` of [copper-and-code-linux-boards](https://github.com/Copper-And-Code/copper-and-code-linux-boards).
Tested on the ESP32-4848S040 with firmware v0.1.7.

| File | On the board | |
|---|---|---|
| [main.py](main.py) | `/main.py` | mounts the card, starts `/sd/lib/home.py`; without a card, the shell of the flash as before |
| [home.py](home.py) | `/sd/lib/home.py` | the home: shell, menus, start of the apps, home button |
| [home.json](home.json) | `/sd/home.json` | the menu: a name and a path for each app, or a name and `apps` for a folder |

Also on the card:

- `/sd/lib/`: `shell.py`, `ansiterm.py`, `ansifont.py` (and `OFL.txt`) from [examples/shell](../shell/);
- `/sd/bin/`: `vi.py`, `edit.py`, from the same folder;
- `/sd/apps/`: [weather.py](../weather.py) and the games [snake.py](../snake.py),
  [breakout.py](../breakout.py), [pong.py](../pong.py), [simon.py](../simon.py),
  [tictactoe.py](../tictactoe.py).

## Copper and Code Studio's apps

`home.json` here also lists three apps made with
[Copper and Code Studio](https://github.com/Copper-And-Code/copper-and-code-studio) and uploaded by
it to `/lms_apps/` on the flash: Settings, Forecast (the Studio's examples `settings` and
`forecast`) and EIM-01. The folder names in `/lms_apps/` are the ones the Studio gave on this
board: after an upload of your own, put yours in `home.json`, or remove those entries. A missing app
shows its error on the screen, and the home button goes back.

The brightness and the Wi-Fi networks come from `cac_settings.py`, the shared settings of the
Studio's apps (`/cac_settings.json` on the flash, written by its Settings app). The home sets the
brightness at every start and, before an app, connects to the best saved network in range. Without
`cac_settings.py` on the board the home works all the same, without either. The weather app keeps
its own network in `/sd/weather.json`.

## How it starts an app

The app's path goes to `/home.next` in the flash, then `machine.reset()`; at the next start
`home.py` finds it, deletes it and runs the app. `machine.soft_reset()` cannot be used: it works only
from the program's top level, and the tap arrives in an LVGL callback while the shell waits for a
key. A reset also gives every app a clean heap: the Studio's apps share module names (`ui`,
`app_events`) and could not run one after the other in the same session.

Thonny, `mpremote` and the Studio take the board as usual: two Ctrl-C on an empty line leave the
shell, and after a soft reset from the raw REPL `main.py` does not run.
