# SPDX-License-Identifier: MIT
# A printable box for the Waveshare RP2350-Touch-LCD-4 (see README.md here). CadQuery:
#   python3 make_box.py   ->   RP2350_Touch_LCD_4_Box.stl and .step in the current folder
import cadquery as cq

# --- FROM WAVESHARE'S DIMENSION DRAWING (mm) ---
bezel_w = 84.20       # front bezel width
bezel_h = 84.20       # front bezel height
pcb_w = 74.50         # PCB width
pcb_h = 76.50         # PCB height
hole_dx = 66.50       # horizontal distance between the mounting holes
hole_dy = 68.50       # vertical distance between the mounting holes

term_cut_w = 53.64    # width of the cut-out at the bottom of the PCB
left_tab = 11.08      # bottom left tab
right_tab = 9.78      # bottom right tab
usbc_y_from_bot = 26.57 # USB-C centre above the PCB's bottom edge

# --- PRINTING AND TOLERANCES (change as needed) ---
tol = 0.4             # print tolerance for the fits (mm)
wall = 2.4            # side walls (6 perimeters of 0.4 mm)
floor_t = 2.0         # floor of the box
internal_depth = 14.0 # inner depth (components and terminal block)
ledge_depth = 2.0     # depth of the ledge for the front glass
standoff_d = 6.0      # outer diameter of the screw standoffs
hole_d = 2.3          # hole for M2.5 self-tapping screws (or 3.2 for M2 heat-set inserts)

# --- GEOMETRY ---
outer_w = bezel_w + tol + (wall * 2)
outer_h = bezel_h + tol + (wall * 2)
total_z = floor_t + internal_depth + ledge_depth

# 1. Outer body with rounded corners
box = (
    cq.Workplane("XY")
    .box(outer_w, outer_h, total_z, centered=(True, True, False))
    .edges("|Z")
    .fillet(3.0)
)

# 2. Top pocket: seat for the display bezel, 84.20 x 84.20
box = (
    box.faces(">Z")
    .workplane()
    .rect(bezel_w + tol, bezel_h + tol)
    .cutBlind(-ledge_depth)
)

# 3. Inner cavity: the 74.50 x 76.50 PCB plus 2 mm of air
cavity_w = pcb_w + 2.0
cavity_h = pcb_h + 2.0
box = (
    box.faces(">Z")
    .workplane(offset=-ledge_depth)
    .rect(cavity_w, cavity_h)
    .cutBlind(-internal_depth)
)

# 4. Screw standoffs, 66.50 x 68.50 apart
standoff_h = internal_depth - 1.6  # leaves 1.6 mm for the PCB
pts = [
    (x * hole_dx / 2, y * hole_dy / 2)
    for x in (-1, 1)
    for y in (-1, 1)
]

box = (
    box.faces(">Z")
    .workplane(offset=-(ledge_depth + internal_depth))
    .pushPoints(pts)
    .circle(standoff_d / 2)
    .extrude(standoff_h)
    .faces(">Z")
    .workplane(offset=-ledge_depth - 1.6)
    .pushPoints(pts)
    .circle(hole_d / 2)
    .cutBlind(-standoff_h)
)

# 5. Bottom opening for the green terminal block (off-centre)
# the centre of the 53.64 mm cut-out is 0.65 mm off the PCB's centre
term_center_x = -pcb_w / 2 + left_tab + (term_cut_w / 2)
box = (
    box.faces("<Y")
    .workplane(centerOption="CenterOfBoundBox")
    .center(term_center_x, (floor_t - total_z / 2) + 5.0)
    .rect(term_cut_w + 1.0, 12.0)
    .cutBlind(-wall * 3)
)

# 6. Left side window for USB-C, microSD and the RST/BOOT buttons
# on the left side (-X). Not checked on a print: see README.md
usbc_center_y = -pcb_h / 2 + usbc_y_from_bot
box = (
    box.faces("<X")
    .workplane(centerOption="CenterOfBoundBox")
    .center(0, 0) # back to the centre of the face
    . slot2D(48.0, 9.0, 0) # a wide slot over USB-C, SD and buttons
    .cutBlind(-wall * 3)
)

# Export
cq.exporters.export(box, "RP2350_Touch_LCD_4_Box.stl")
cq.exporters.export(box, "RP2350_Touch_LCD_4_Box.step")
print("RP2350_Touch_LCD_4_Box.stl and .step written")