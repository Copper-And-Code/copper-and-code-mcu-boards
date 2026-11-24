# Home: the shell and a touch menu of apps (ESP32-4848S040)

At power-on the [shell](../shell/) on the display, with the keyboard of the serial terminal. A tap on
the terminal opens a menu of apps; a tap on an app resets the board and starts that app alone, with
all the memory. The home button brings the shell back the same way. It is hidden while the app
runs, so that it covers nothing and takes none of the app's touches: a pull down from the top edge
of the screen shows it at the top centre for three seconds (and it shows for the first three
seconds of every app, as a hint). An entry of the menu can be a folder (such as "Games") with a menu of its own. Everything but `main.py` lives on
the SD card.

At power-on an app can start instead of the shell: the one chosen on the Start page of the Settings
app of Copper and Code Studio, or else the one that `home.json` names in `"start"`. For two seconds
the screen names it, and a touch then gives the shell instead: the way out of an app that does not
let the board be used. The home button of an app always goes to the menu, with no shell behind it:
its Shell tile starts the shell, after a reset as an app.

Ported from `mpy_home` of [copper-and-code-linux-boards](https://github.com/Copper-And-Code/copper-and-code-linux-boards).
Tested on the ESP32-4848S040 with firmware v0.1.7.

| File | On the board | |
|---|---|---|
| [main.py](main.py) | `/main.py` | mounts the card, starts `/sd/lib/home.py`; without a card, the shell of the flash as before |
| [home.py](home.py) | `/sd/lib/home.py` | the home: shell, menus, start of the apps, home button |
| [home.json](home.json) | `/sd/home.json` | the menu: a name and a path for each app, or a name and `apps` for a folder, and a `"name_it"` for Italian; `"start"`, the path of the app of power-on |

Also on the card:

- `/sd/lib/`: `shell.py`, `ansiterm.py`, `ansifont.py` (and `OFL.txt`) from [examples/shell](../shell/);
- `/sd/bin/`: `vi.py`, `edit.py`, from the same folder;
- `/sd/apps/`: the games [snake.py](../snake.py),
  [breakout.py](../breakout.py), [pong.py](../pong.py), [simon.py](../simon.py),
  [tictactoe.py](../tictactoe.py).

## Copper and Code Studio's apps

`home.json` here lists apps made with
[Copper and Code Studio](https://github.com/Copper-And-Code/copper-and-code-studio), each in a
folder of `/sd/apps`: Settings, Forecast, EIM-01, FTP Server and Photo Frame, and games in the
Games folder. The Studio's `tools/esp32_sd.py` fills a card that way, with this home, the shell,
the games of `examples/` and those apps, and writes the menu for them; it brings a card up to date
too, writing only what changed. An app uploaded from the Studio instead goes to `/lms_apps/` on the
flash: put its path in `home.json`. A missing app shows its error on the screen; the home button,
pulled down from the top edge, goes back.

The brightness and the Wi-Fi networks come from `cac_settings.py`, the shared settings of the
Studio's apps (`/cac_settings.json` on the flash, written by its Settings app). The home sets the
brightness at every start and, before an app, connects to the best saved network in range. Without
`cac_settings.py` on the board the home works all the same, without either. The Settings app also
keeps there the app of power-on, in the section `home`, and the language, in the section `general`:
the home and the games of `examples/` speak English or Italian with it. An app gets its own copy of
`cac_settings.py`, from its folder: the one `boot.py` imported from the flash may be older.

## How it starts an app

The app's path goes to `/home.next` in the flash, then `machine.reset()`; at the next start
`home.py` finds it, deletes it and runs the app. `machine.soft_reset()` cannot be used: it works only
from the program's top level, and the tap arrives in an LVGL callback while the shell waits for a
key. A reset also gives every app a clean heap: the Studio's apps share module names (`ui`,
`app_events`) and could not run one after the other in the same session.

Thonny, `mpremote` and the Studio take the board as usual: two Ctrl-C on an empty line leave the
shell, and after a soft reset from the raw REPL `main.py` does not run.
