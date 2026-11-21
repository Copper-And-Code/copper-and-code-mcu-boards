# A printable box for the RP2350-Touch-LCD-4

**Not printed yet: the fit is untested.** A box for the [Waveshare RP2350-Touch-LCD-4](../../boards/rp2/WAVESHARE_RP2350_TOUCH_LCD_4/README.md):
the board sits on four standoffs, the display's bezel rests in a ledge at the top.

| File | |
|---|---|
| [make_box.py](make_box.py) | the parametric model, in [CadQuery](https://github.com/CadQuery/cadquery) |
| `RP2350_Touch_LCD_4_Box.stl` | for the slicer |
| `RP2350_Touch_LCD_4_Box.step` | for a CAD program |

Outside about 89.4 x 89.4 x 18 mm, corners rounded at 3 mm. Inside:

- a 2 mm ledge for the 84.2 x 84.2 mm bezel, 0.4 mm of play;
- a 76.5 x 78.5 mm cavity, 14 mm deep, for the 74.5 x 76.5 mm PCB;
- four standoffs 66.5 x 68.5 mm apart, with 2.3 mm holes for M2.5 self-tapping screws
  (3.2 mm for M2 heat-set inserts: change `hole_d`);
- an opening at the bottom for the green terminal block, and a slot on the left side for the
  USB-C, the microSD and the RST/BOOT buttons.

The board dimensions come from Waveshare's dimension drawing for the board
([wiki](https://www.waveshare.com/wiki/RP2350-Touch-LCD-4)); the drawing itself is Waveshare's
and is not copied here.

## Changing it

The parameters are at the top of `make_box.py` (tolerance, walls, floor, depth, holes). Then:

```bash
pip install cadquery
python3 make_box.py      # writes the .stl and .step into the current folder
```

## To check on the first print

- The side slot is centred on the face. `usbc_center_y`, the USB-C's height from the drawing,
  is computed but not used yet: on a print, check that the slot is over the USB-C, the card and the
  buttons, or move it there.
- The 0.4 mm play suits a 0.4 mm nozzle; tighter printers may need less.

Licence: MIT, as the rest of the repository.
