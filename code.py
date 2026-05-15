import displayio
import vectorio
import supervisor
import sys
import time
import board
import neopixel
from adafruit_qualia.graphics import Graphics, Displays

graphics = Graphics(Displays.ROUND40, default_bg=0x000000)
display = graphics.display

pixels = neopixel.NeoPixel(board.A0, 16, brightness=0.01, auto_write=False)

main_group = displayio.Group()

bg_bitmap = displayio.Bitmap(720, 720, 1)
bg_palette = displayio.Palette(1)
bg_palette[0] = 0x000000
bg = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette)
main_group.append(bg)

dot_positions = [(240, 155), (360, 125), (480, 155)]
dot_palettes = []
dots = []
for dx, dy in dot_positions:
    pal = displayio.Palette(1)
    pal[0] = 0x0066FF
    dot = vectorio.Circle(pixel_shader=pal, radius=10, x=dx, y=dy)
    dot_palettes.append(pal)
    dots.append(dot)
    main_group.append(dot)

def make_eye(x, y, group):
    wp = displayio.Palette(1); wp[0] = 0xF0F0F0
    group.append(vectorio.Circle(pixel_shader=wp, radius=130, x=x, y=y))
    lp = displayio.Palette(1); lp[0] = 0x0a0a0a
    group.append(vectorio.Circle(pixel_shader=lp, radius=88, x=x, y=y))
    ip = displayio.Palette(1); ip[0] = 0x0066FF
    group.append(vectorio.Circle(pixel_shader=ip, radius=82, x=x, y=y))
    i2p = displayio.Palette(1); i2p[0] = 0x0044CC
    group.append(vectorio.Circle(pixel_shader=i2p, radius=60, x=x, y=y))
    pp = displayio.Palette(1); pp[0] = 0x000000
    pupil = vectorio.Circle(pixel_shader=pp, radius=38, x=x, y=y)
    group.append(pupil)
    gp = displayio.Palette(1); gp[0] = 0xFFFFFF
    group.append(vectorio.Circle(pixel_shader=gp, radius=16, x=x+23, y=y-24))
    g2p = displayio.Palette(1); g2p[0] = 0xFFFFFF
    group.append(vectorio.Circle(pixel_shader=g2p, radius=7, x=x-17, y=y+18))
    return pupil

left_pupil = make_eye(155, 370, main_group)
right_pupil = make_eye(525, 370, main_group)

for nx in [335, 385]:
    np_ = displayio.Palette(1); np_[0] = 0x50B4FF
    main_group.append(vectorio.Circle(pixel_shader=np_, radius=7, x=nx, y=510))

display.root_group = main_group

def move_eyes(offset_x, offset_y):
    max_travel = 55
    ox = max(-max_travel, min(max_travel, offset_x))
    oy = max(-max_travel, min(max_travel, offset_y))
    left_pupil.x = 155 + ox
    left_pupil.y = 370 + oy
    right_pupil.x = 525 + ox
    right_pupil.y = 370 + oy

dot_colors = [
    0x001133, 0x002266, 0x003399, 0x0044CC, 0x0055FF,
    0x0066FF, 0x0055FF, 0x0044CC, 0x003399, 0x002266
]

buf = ""
t = 0
current_volume = 0.0
target_volume = 0.0

while True:
    lit = int(current_volume * 16)
    for i in range(16):
        if i < lit:
            pixels[i] = (0, 120, 255)
        else:
            pixels[i] = (0, 0, 0)
    pixels.show()
    for i, dot in enumerate(dots):
        phase = (t + i * 3) % len(dot_colors)
        dot_palettes[i][0] = dot_colors[phase]
    t = (t + 1) % len(dot_colors)
    current_volume = current_volume * 0.85 + target_volume * 0.15
    target_volume = max(0.0, target_volume - 0.02)
    if supervisor.runtime.serial_bytes_available:
        c = sys.stdin.read(1)
        if c == "\n":
            try:
                if buf.startswith("v:"):
                    target_volume = float(buf[2:])
                else:
                    x, y = buf.strip().split(",")
                    ox = int((int(x) - 320) / 320 * 55)
                    oy = int((int(y) - 240) / 240 * 55)
                    move_eyes(ox, oy)
            except:
                pass
            buf = ""
        else:
            buf += c
    time.sleep(0.05)
    