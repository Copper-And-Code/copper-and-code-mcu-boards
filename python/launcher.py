# SPDX-License-Identifier: MIT
# A menu of the apps installed by Copper and Code Studio, for the microcontroller boards: one
# button per app; a tap starts it, the board's user button comes back to the menu.
#
#   /flash/main.py:        import launcher; launcher.main()
#   /flash/launcher.json:  {"title": "Games", "apps": [{"name": "Snake", "dir": "app_1e39a0a11344"}, ...]}
#
# Studio apps share module names (ui, app_events), so each one starts after a soft reset, alone:
# the menu writes the app's folder to NEXT and asks for a reset; at the next start main() runs
# that app. The user button (mpy_board's "button") asks for a reset again, back to the menu.
# machine.soft_reset() works only from the program's top level: it raises SystemExit, which an
# LVGL callback or a scheduled function (with the REPL waiting) prints and drops. So main() does
# not return: it waits in a light loop (LVGL runs in display_driver's timer) and soft-resets there
# when asked. machine.reset() is not used: on the STM32F769I-DISCO the board did not come back
# from it (2026-11-20). Ctrl-C stops the loop, as any main.py; the Studio's runs and uploads go
# through the raw REPL, where main.py does not run.
import json
import os
import sys

import time

import machine

_reset_asked = False

ROOT = "/flash/lms_apps"
CONFIG = "/flash/launcher.json"
NEXT = "/flash/launcher.next"


def _config():
    try:
        with open(CONFIG) as f:
            return json.load(f)
    except (OSError, ValueError):
        # No list: every installed app, by its folder name.
        apps = [{"name": d, "dir": d} for d in sorted(os.listdir(ROOT)) if not d.endswith(".previous")]
        return {"title": "Apps", "apps": apps}


def _back_button():
    # The board's user button resets to the menu (STM32F769I-DISCO: B1, PA0, high when pressed).
    try:
        import mpy_board

        spec = mpy_board.describe().get("button")
    except ImportError:
        spec = None
    if not spec:
        return None
    pin = machine.Pin(spec["pin"], machine.Pin.IN)
    edge = machine.Pin.IRQ_FALLING if spec.get("active_low") else machine.Pin.IRQ_RISING

    def pressed(p):
        global _reset_asked
        _reset_asked = True

    pin.irq(pressed, edge)
    return pin


def _run(folder):
    path = "%s/%s/app_main.py" % (ROOT, folder)
    _back_button()
    # display_driver starts drawing as soon as it is imported; the app builds its screens after,
    # and calls display_driver.start() itself when done. Stopped until then, LVGL's empty default
    # screen is never drawn: no flash between the last image and the app's first one.
    import display_driver

    display_driver.stop()
    with open(path) as f:
        code = f.read()
    exec(code, {"__name__": "__main__", "__file__": path})


def _start(folder):
    global _reset_asked
    with open(NEXT, "w") as f:
        f.write(folder)
    _reset_asked = True


def menu():
    import display_driver
    import lvgl as lv

    display_driver.stop()  # as in _run: draw nothing until the menu is built

    cfg = _config()
    apps = [a for a in cfg.get("apps", []) if _installed(a["dir"])]
    w, h = display_driver.WIDTH, display_driver.HEIGHT
    scr = lv.obj()
    scr.set_style_bg_color(lv.color_hex(0x10151F), 0)
    title = lv.label(scr)
    title.set_text(cfg.get("title", "Apps"))
    title.set_style_text_font(lv.font_montserrat_32, 0)
    title.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
    title.align(lv.ALIGN.TOP_MID, 0, 16)
    hint = lv.label(scr)
    hint.set_text("Tap a game. The blue button comes back here.")
    hint.set_style_text_color(lv.color_hex(0x8FA0B8), 0)
    hint.align(lv.ALIGN.BOTTOM_MID, 0, -12)
    cols = 3
    gap = 16
    top = 70
    bw = (w - gap * (cols + 1)) // cols
    rows = max(1, (len(apps) + cols - 1) // cols)
    bh = min(120, (h - top - 50 - gap * rows) // rows)
    colors = (0x2F6FDE, 0x2E9E6A, 0xE0742F, 0x8A5CF6, 0xC0392B, 0x2B8A9E, 0xB8860B, 0x5D6D7E)
    for i, app in enumerate(apps):
        b = lv.button(scr)
        b.set_size(bw, bh)
        b.set_pos(gap + (i % cols) * (bw + gap), top + (i // cols) * (bh + gap))
        b.set_style_bg_color(lv.color_hex(colors[i % len(colors)]), 0)
        l = lv.label(b)
        l.set_text(app["name"])
        l.set_style_text_font(lv.font_montserrat_24, 0)
        l.center()
        b.add_event_cb(lambda e, d=app["dir"]: _start(d), lv.EVENT.CLICKED, None)
    if not apps:
        hint.set_text("No apps installed: upload them from Copper and Code Studio.")
    lv.screen_load(scr)
    display_driver.start()


def _installed(folder):
    try:
        os.stat("%s/%s/app_main.py" % (ROOT, folder))
        return True
    except OSError:
        return False


def main():
    try:
        with open(NEXT) as f:
            folder = f.read().strip()
        os.remove(NEXT)
    except OSError:
        folder = None
    if folder and _installed(folder):
        _run(folder)
    else:
        menu()
        _back_button()  # in the menu too: a reset that rebuilds it
    while not _reset_asked:
        time.sleep_ms(20)
    machine.soft_reset()
