# SPDX-License-Identifier: MIT
# The ESP32-4848S040's home, on the SD card: at power-on the shell on the display (keyboard from
# the serial terminal); a tap on the terminal opens a menu of apps. An app runs alone after a
# reset of the board, and the home button brings the shell back the same way. The home button is
# hidden while the app runs, so that it covers nothing: a pull down from the top edge of the screen
# shows it at the top centre for a few seconds.
#
# Ported from mpy_home of lvgl-mpy-linux. The apps of the menu are in /sd/home.json, each a
# Python file on the board and a name:
#
#   {"apps": [{"name": "Weather", "path": "/sd/apps/weather.py"},
#             {"name": "Games", "apps": [{"name": "Snake", "path": "/sd/apps/snake.py"}]}]}
#
# An entry with "apps" instead of "path" is a folder: its tile opens a menu of its own apps, with
# a tile to go back. An entry can have a "name_it" too, its name when the board speaks Italian:
# the language is the one chosen in the Settings app of Copper and Code Studio.
#
# A Copper and Code Studio app is given by the entry point the Studio uploaded (app_main.py).
#
# At power-on an app can start instead of the shell: the one chosen in the Settings app of
# Copper and Code Studio (the section "home", key "start", of cac_settings.json in the flash), or
# else the "start" of home.json, a path as in the list. An empty start, or a path that is not on
# the board, keeps the shell. For START_WAIT_MS the screen names the app: a touch then gives the
# shell instead, the way out of an app that does not let the board be used. The home button of
# an app goes to the menu, not to the app of power-on.
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
import time

import lvgl as lv
import machine

import display_driver

NEXT = "/home.next"  # in the flash: the SD card is mounted again only by main.py
MENU = "menu"  # in NEXT: the home button asked for the menu, and not for the app of power-on
SHELL = "shell"  # in NEXT: the Shell tile of the menu asked for the shell
CONFIG = "/sd/home.json"
START_WAIT_MS = 2000  # the app of power-on is named this long before it starts: a touch gives the shell
W, H = display_driver.WIDTH, display_driver.HEIGHT
BACK = 0x121820
TILE = 0x1E2633
FOLDER = 0x3A3F7A
ACCENT = 0x2F6FDE


def _cac_settings():
    # The shared settings of Copper and Code Studio's apps, when cac_settings.py is on the board.
    try:
        import cac_settings

        if not hasattr(cac_settings, "language"):  # boot.py took an older copy, from the flash
            sys.modules.pop("cac_settings", None)
            import cac_settings
        return cac_settings
    except ImportError:
        return None


IT = {
    "Apps": "App",
    "Back": "Indietro",
    "Starting...": "Avvio...",
    "Touch the screen for the shell": "Tocca lo schermo per la shell",
    "No apps: add them to /sd/home.json": "Nessuna app: aggiungile in /sd/home.json",
    "Pull down from the top edge for the home button.": "Trascina giu' dal bordo in alto per la casetta.",
}
_italian = None


def _t(text):
    """text in the language chosen in the Settings app, English or Italian: English without it."""
    global _italian
    if _italian is None:
        shared = _cac_settings()
        try:
            _italian = shared is not None and shared.language() == "it"
        except AttributeError:  # a cac_settings.py from before the language
            _italian = False
    return IT.get(text, text) if _italian else text


def _app_name(app):
    """The name of an app or a folder of the menu: its "name_it" in Italian, when the menu has one."""
    _t("")
    return app.get("name_it", app["name"]) if _italian else app["name"]


def _valid(listed):
    # Apps with a path, and folders with a list of apps.
    if not isinstance(listed, list):
        return []
    return [a for a in listed if isinstance(a, dict) and a.get("name") and (a.get("path") or isinstance(a.get("apps"), list))]


def _config():
    try:
        with open(CONFIG) as source:
            config = json.load(source)
        return config if isinstance(config, dict) else {}
    except (OSError, ValueError):
        return {}


def apps():
    return _valid(_config().get("apps", []))


def start_app():
    """The path of the app that starts at power-on, or None for the shell.

    The choice of the Settings app comes first, an empty one included; then the start of
    home.json. A path that is not on the board is the shell."""
    shared = _cac_settings()
    chosen = shared.section("home") if shared else {}
    path = chosen["start"] if "start" in chosen else _config().get("start")
    if not isinstance(path, str) or not path:
        return None
    try:
        os.stat(path)
    except OSError:
        print("home: the app of power-on is not on the board:", path)
        return None
    return path


def _name_of(path, listed=None):
    """The name the menu gives to path, else its folder or file name."""
    for app in listed if listed is not None else apps():
        if app.get("path") == path:
            return _app_name(app)
        if app.get("apps"):
            name = _name_of(path, _valid(app["apps"]))
            if name:
                return name
    if listed is not None:
        return None
    parts = path.rstrip("/").split("/")
    return parts[-2] if parts[-1] == "app_main.py" and len(parts) > 1 else parts[-1]


def _shell_asked(path):
    """The app of power-on is named for START_WAIT_MS; True if the screen is touched meanwhile."""
    screen = lv.obj()
    screen.set_style_bg_color(lv.color_hex(BACK), 0)
    title = _label(screen, lv.SYMBOL.PLAY + "  " + _name_of(path), 24, 0xFFFFFF)
    title.align(lv.ALIGN.CENTER, 0, -24)
    note = _label(screen, _t("Touch the screen for the shell"), 16, 0x9AA6B8)
    note.align(lv.ALIGN.CENTER, 0, 24)
    lv.screen_load(screen)
    lv.refr_now(None)
    touch = getattr(display_driver, "touch", None)  # the GT911 read directly: LVGL is not served yet
    end = time.ticks_add(time.ticks_ms(), START_WAIT_MS)
    asked = False
    while not asked and time.ticks_diff(end, time.ticks_ms()) > 0:
        try:
            asked = touch is not None and touch.read()[0]
        except OSError:
            pass
        time.sleep_ms(30)
    # Deleted when the app or the shell loads a screen of its own: deleted now, while active, LVGL
    # would still use it at its next refresh.
    screen.add_event_cb(lambda e: screen.delete_async(), lv.EVENT.SCREEN_UNLOADED, None)
    return asked


def launch(path):
    with open(NEXT, "w") as target:
        target.write(path)
    _restart()


def go_home():
    with open(NEXT, "w") as target:
        target.write(MENU)  # the menu after the reset, and not the app of power-on
    _restart()


def _restart():
    # A word on the screen first: the reset and the start of the next program take a few seconds.
    screen = lv.obj()
    screen.set_style_bg_color(lv.color_hex(BACK), 0)
    _label(screen, lv.SYMBOL.REFRESH + "  " + _t("Starting..."), 24, 0xFFFFFF).center()
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
    # The shell: shown again if it runs behind the menu, else started by a reset, as an app is.
    if "shell" in sys.modules:
        import ansiterm

        ansiterm.term.show()
    else:
        with open(NEXT, "w") as target:
            target.write(SHELL)
        _restart()


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
    _label(screen, _app_name(folder) if folder else _t("Apps"), 24, 0xFFFFFF).set_pos(4, 0)
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
            _tile(grid, _app_name(app), TILE, lambda p=app["path"]: launch(p))
        else:
            _tile(grid, lv.SYMBOL.DIRECTORY + "  " + _app_name(app), FOLDER, lambda f=app: menu(f))
    if folder:
        _tile(grid, lv.SYMBOL.LEFT + "  " + _t("Back"), ACCENT, lambda: menu())
    else:
        _tile(grid, lv.SYMBOL.KEYBOARD + "  Shell", ACCENT, _terminal)
    if not listed:
        note = _label(screen, _t("No apps: add them to /sd/home.json"), 14, 0x9AA6B8)
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


HOME_SHOW_MS = 3000  # the home button stays this long after a pull from the top edge
EDGE = 24  # a pull begins this close to the top edge
PULL = 40  # and goes down at least this much

_home = None
_touch = None
_point = None
_pull_from = None  # y where a touch began at the top edge, while it lasts
_was_pressed = False
_hide_at = 0


def _home_button():
    # The home button is hidden while the app runs, so it covers nothing of the app and takes none
    # of its touches. A pull down from the top edge of the screen shows it at the top centre, over
    # every screen, for HOME_SHOW_MS; a tap on it goes home. It is shown too for the first seconds
    # of the app, as a hint. A timer reads the touch screen directly instead of an object catching
    # touches: the app gets every touch as before.
    global _home, _touch, _point, _hide_at
    b = lv.button(lv.layer_top())
    b.set_size(96, 44)
    b.align(lv.ALIGN.TOP_MID, 0, 0)
    b.set_style_radius(10, 0)
    b.set_style_bg_color(lv.color_hex(0x000000), 0)
    b.set_style_bg_opa(170, 0)
    b.set_style_shadow_width(0, 0)
    _label(b, lv.SYMBOL.HOME, 24, 0xFFFFFF).center()
    b.add_event_cb(lambda e: go_home(), lv.EVENT.CLICKED, None)
    _home = b
    _point = lv.point_t()
    _touch = getattr(display_driver, "indev", None)  # the GT911, None without a touch screen
    _hide_at = time.ticks_add(time.ticks_ms(), HOME_SHOW_MS)
    lv.timer_create(_watch_touch, 30, None)


def _watch_touch(timer):
    global _pull_from, _was_pressed, _hide_at
    now = time.ticks_ms()
    pressed = _touch is not None and _touch.get_state() == lv.INDEV_STATE.PRESSED
    if pressed:
        _touch.get_point(_point)
        if not _was_pressed:
            _pull_from = _point.y if _point.y <= EDGE else None
        elif _pull_from is not None and _point.y - _pull_from >= PULL:
            _pull_from = None
            _touch.wait_release()  # the rest of this touch is the pull's: nothing of the app gets a click
            _hide_at = time.ticks_add(now, HOME_SHOW_MS)
            _home.remove_flag(lv.obj.FLAG.HIDDEN)
    _was_pressed = pressed
    if not pressed and time.ticks_diff(_hide_at, now) <= 0 and not _home.has_flag(lv.obj.FLAG.HIDDEN):
        _home.add_flag(lv.obj.FLAG.HIDDEN)


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
    note = _label(screen, "%s\n\n%s\n\n%s" % (path, repr(error), _t("Pull down from the top edge for the home button.")), 16, 0xFFFFFF)
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
    sys.modules.pop("cac_settings", None)  # the app imports its own copy, from its folder, first in sys.path
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
        os.remove(NEXT)  # read once: the next reset is a start as at power-on
    except OSError:
        path = None
    if path is None:  # power-on, or a reset that did not come from the menu
        path = start_app()
        if path and _shell_asked(path):
            path = None
    if path and path not in (MENU, SHELL):  # an app
        print("home: running", path)
        run_app(path)
        return
    if path == MENU:  # back from an app: the menu alone, with no shell; its Shell tile starts one
        menu()
        display_driver.start()
        return
    _hook_terminal()
    import shell

    shell.main()
