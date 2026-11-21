# SPDX-License-Identifier: MIT
# The ESP32-4848S040's home, on the SD card: at power-on the shell on the display (keyboard from
# the serial terminal); a tap on the terminal opens a menu of apps. An app runs alone after a
# reset of the board, and the home button at the top brings the shell back the same way.
#
# Ported from mpy_home of lvgl-mpy-linux. The apps of the menu are in /sd/home.json, each a
# Python file on the board and a name:
#
#   {"apps": [{"name": "Weather", "path": "/sd/apps/weather.py"},
#             {"name": "Games", "apps": [{"name": "Snake", "path": "/sd/apps/snake.py"}]}]}
#
# An entry with "apps" instead of "path" is a folder: its tile opens a menu of its own apps, with
# a tile to go back.
#
# A Copper and Code Studio app is given by the entry point the Studio uploaded (app_main.py).
#
# The board starts the app with machine.reset(), not machine.soft_reset(): a soft reset works only
# from the program's top level, and here the tap arrives in an LVGL callback while the shell waits
# for a key. The app to run is written to /home.next in the internal flash first.
#
# The brightness and the Wi-Fi networks are in /cac_settings.json in the flash, written by the
# Settings app of Copper and Code Studio (its examples/settings) and read through cac_settings.py,
# which goes in the root of the flash with that example's boot.py. The home sets the brightness at
# every start and, before an app, connects to the best saved network in range, when boot.py has
# not done it already. Without cac_settings.py the home works all the same, with neither.
#
# Thonny, mpremote and Copper and Code Studio take the board as usual: two Ctrl-C on an empty line
# leave the shell, and after a soft reset from the raw REPL main.py does not run.

import json
import os
import sys

import lvgl as lv
import machine

import display_driver

NEXT = "/home.next"  # in the flash: the SD card is mounted again only by main.py
CONFIG = "/sd/home.json"
W, H = display_driver.WIDTH, display_driver.HEIGHT
BACK = 0x121820
TILE = 0x1E2633
FOLDER = 0x3A3F7A
ACCENT = 0x2F6FDE


def _cac_settings():
    # The shared settings of Copper and Code Studio's apps, when cac_settings.py is on the board.
    try:
        import cac_settings

        return cac_settings
    except ImportError:
        return None


def _valid(listed):
    # Apps with a path, and folders with a list of apps.
    if not isinstance(listed, list):
        return []
    return [a for a in listed if isinstance(a, dict) and a.get("name") and (a.get("path") or isinstance(a.get("apps"), list))]


def apps():
    try:
        with open(CONFIG) as source:
            return _valid(json.load(source).get("apps", []))
    except (OSError, ValueError, AttributeError):
        return []


def launch(path):
    with open(NEXT, "w") as target:
        target.write(path)
    _restart()


def go_home():
    try:
        os.remove(NEXT)
    except OSError:
        pass
    _restart()


def _restart():
    # A word on the screen first: the reset and the start of the next program take a few seconds.
    screen = lv.obj()
    screen.set_style_bg_color(lv.color_hex(BACK), 0)
    _label(screen, lv.SYMBOL.REFRESH + "  Starting...", 24, 0xFFFFFF).center()
    lv.screen_load(screen)
    lv.refr_now(None)
    try:
        os.umount("/sd")  # the card's writes are done before the reset
    except OSError:
        pass
    machine.reset()


def _label(parent, text, size, color):
    o = lv.label(parent)
    o.set_text(text)
    o.set_style_text_font(getattr(lv, "font_montserrat_%d" % size, lv.font_montserrat_16), 0)
    o.set_style_text_color(lv.color_hex(color), 0)
    return o


def _tile(parent, text, color, callback):
    b = lv.button(parent)
    b.set_size(140, 72)
    b.set_style_bg_color(lv.color_hex(color), 0)
    b.set_style_radius(14, 0)
    b.set_style_shadow_width(0, 0)
    t = _label(b, text, 16, 0xFFFFFF)
    t.set_width(124)
    t.set_long_mode(lv.label.LONG_MODE.WRAP)
    t.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
    t.center()
    b.add_event_cb(lambda e: callback(), lv.EVENT.CLICKED, None)
    return b


_menus = {}  # the menus built, by folder name ("" for the first one): built once, then shown


def _terminal():
    import ansiterm

    ansiterm.term.show()


def menu(folder=None):
    # The app menu, over the shell, or the menu of a folder. The shell keeps running behind it.
    # Each menu is built the first time and kept: going from one to the other only shows it, with
    # nothing to allocate or delete (a rebuild made the board wait for the garbage collector).
    key = folder["name"] if folder else ""
    screen = _menus.get(key)
    if screen is None:
        screen = _menus[key] = _build_menu(folder)
    if lv.screen_active() != screen:
        lv.screen_load(screen)


def _build_menu(folder):
    screen = lv.obj()
    screen.set_style_bg_color(lv.color_hex(BACK), 0)
    screen.set_style_pad_all(12, 0)
    screen.remove_flag(lv.obj.FLAG.SCROLLABLE)
    _label(screen, folder["name"] if folder else "Apps", 24, 0xFFFFFF).set_pos(4, 0)
    grid = lv.obj(screen)
    grid.set_size(lv.pct(100), H - 24 - 44)
    grid.set_pos(0, 40)
    grid.set_style_bg_opa(0, 0)
    grid.set_style_border_width(0, 0)
    grid.set_style_pad_all(4, 0)
    grid.set_style_pad_row(10, 0)
    grid.set_style_pad_column(10, 0)
    grid.set_flex_flow(lv.FLEX_FLOW.ROW_WRAP)
    listed = _valid(folder["apps"]) if folder else apps()
    for app in listed:
        if app.get("path"):
            _tile(grid, app["name"], TILE, lambda p=app["path"]: launch(p))
        else:
            _tile(grid, lv.SYMBOL.DIRECTORY + "  " + app["name"], FOLDER, lambda f=app: menu(f))
    if folder:
        _tile(grid, lv.SYMBOL.LEFT + "  Back", ACCENT, lambda: menu())
    else:
        _tile(grid, lv.SYMBOL.KEYBOARD + "  Shell", ACCENT, _terminal)
    if not listed:
        note = _label(screen, "No apps: add them to /sd/home.json", 14, 0x9AA6B8)
        note.align(lv.ALIGN.BOTTOM_LEFT, 4, 0)
    return screen


def _on_terminal(screen):
    screen.add_flag(lv.obj.FLAG.CLICKABLE)
    screen.add_event_cb(lambda e: menu(), lv.EVENT.CLICKED, None)


def _hook_terminal():
    # Every terminal screen opens the menu on a tap, also one built again after an app deleted it.
    import ansiterm

    build = ansiterm.Terminal.build

    def build_and_hook(self):
        build(self)
        _on_terminal(self.screen)

    ansiterm.Terminal.build = build_and_hook


def _home_button():
    # A small tab at the top centre, over every screen of the app.
    b = lv.button(lv.layer_top())
    b.set_size(64, 30)
    b.align(lv.ALIGN.TOP_MID, 0, 0)
    b.set_style_radius(8, 0)
    b.set_style_bg_color(lv.color_hex(0x000000), 0)
    b.set_style_bg_opa(140, 0)
    b.set_style_shadow_width(0, 0)
    _label(b, lv.SYMBOL.HOME, 16, 0xFFFFFF).center()
    b.add_event_cb(lambda e: go_home(), lv.EVENT.CLICKED, None)


def _brightness():
    shared = _cac_settings()
    level = shared.section("display").get("brightness") if shared else None
    if isinstance(level, int) and 5 <= level <= 100:
        display_driver.backlight(level)


def _wifi():
    # Usually boot.py has connected already and this returns at once; otherwise one scan and the
    # saved networks in range, a few seconds, before the app starts.
    shared = _cac_settings()
    if shared is None:
        return
    try:
        shared.connect()
    except Exception as error:
        print("Wi-Fi:", repr(error))


def _failed(path, error):
    screen = lv.obj()
    screen.set_style_bg_color(lv.color_hex(BACK), 0)
    note = _label(screen, "%s\n\n%s\n\nThe home button goes back." % (path, repr(error)), 16, 0xFFFFFF)
    note.set_width(W - 40)
    note.set_long_mode(lv.label.LONG_MODE.WRAP)
    note.center()
    lv.screen_load(screen)


def run_app(path):
    folder = path.rsplit("/", 1)[0]
    if folder not in sys.path:
        sys.path.insert(0, folder)
    _wifi()
    _home_button()  # first: some apps never return (their own loop)
    try:
        with open(path) as source:
            code = source.read()
        exec(code, {"__name__": "__main__", "__file__": path})
    except KeyboardInterrupt:
        raise
    except Exception as error:  # a missing or broken app: say so; the home button stays
        sys.print_exception(error)
        _failed(path, error)


def main():
    _brightness()
    try:
        with open(NEXT) as source:
            path = source.read().strip()
        os.remove(NEXT)  # the next reset, or the home button, goes back to the shell
    except OSError:
        path = None
    if path:
        print("home: running", path)
        run_app(path)
        return
    _hook_terminal()
    import shell

    shell.main()
