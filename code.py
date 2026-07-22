#Code.py for Adafruit Qualia ESP32-S3 RGB-666
import displayio
import vectorio
import supervisor
import sys
import time
import board
import neopixel
import math
import random
from adafruit_qualia.graphics import Graphics, Displays

graphics = Graphics(Displays.ROUND40, default_bg=0x000000)
display = graphics.display

pixels = neopixel.NeoPixel(board.A0, 16, brightness=1.0, auto_write=False)

main_group = displayio.Group()

# Black background
bg_bitmap = displayio.Bitmap(720, 720, 1)
bg_palette = displayio.Palette(1)
bg_palette[0] = 0x000000
bg = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette)
main_group.append(bg)

# Scanline overlay
scanline_bitmap = displayio.Bitmap(720, 720, 2)
scanline_palette = displayio.Palette(2)
scanline_palette[0] = 0x000000
scanline_palette.make_transparent(0)
scanline_palette[1] = 0x0a0a0a
for y in range(0, 720, 4):
    for x in range(720):
        scanline_bitmap[x, y] = 1
scanline_layer = displayio.TileGrid(scanline_bitmap, pixel_shader=scanline_palette)
main_group.append(scanline_layer)

# Display ring
ring_pal = displayio.Palette(1)
ring_pal[0] = 0x000000
display_ring = vectorio.Circle(pixel_shader=ring_pal, radius=355, x=360, y=360)
main_group.append(display_ring)
ring_inner_pal = displayio.Palette(1)
ring_inner_pal[0] = 0x000000
display_ring_inner = vectorio.Circle(pixel_shader=ring_inner_pal, radius=338, x=360, y=360)
main_group.append(display_ring_inner)

# Thinking dots
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

# Eyebrows — simple rectangles above each eye
def make_eyebrow(x, y, group):
    bp = displayio.Palette(1); bp[0] = 0xCCCCCC
    brow = vectorio.Rectangle(pixel_shader=bp, x=x-45, y=y, width=90, height=10)
    group.append(brow)
    return brow

left_brow = make_eyebrow(155, 215, main_group)
right_brow = make_eyebrow(520, 215, main_group)

def make_eye(x, y, group):
    wp = displayio.Palette(1); wp[0] = 0xF0F0F0
    white = vectorio.Circle(pixel_shader=wp, radius=130, x=x, y=y)
    group.append(white)
    lp = displayio.Palette(1); lp[0] = 0x0a0a0a
    group.append(vectorio.Circle(pixel_shader=lp, radius=88, x=x, y=y))
    ip = displayio.Palette(1); ip[0] = 0x0066FF
    iris = vectorio.Circle(pixel_shader=ip, radius=82, x=x, y=y)
    group.append(iris)
    i2p = displayio.Palette(1); i2p[0] = 0x0044CC
    inner = vectorio.Circle(pixel_shader=i2p, radius=60, x=x, y=y)
    group.append(inner)
    pp = displayio.Palette(1); pp[0] = 0x000000
    pupil = vectorio.Circle(pixel_shader=pp, radius=38, x=x, y=y)
    group.append(pupil)
    prp = displayio.Palette(1); prp[0] = 0x000000
    proc_ring = vectorio.Circle(pixel_shader=prp, radius=90, x=x, y=y)
    group.append(proc_ring)
    ip2 = displayio.Palette(1); ip2[0] = 0x0066FF
    iris2 = vectorio.Circle(pixel_shader=ip2, radius=82, x=x, y=y)
    group.append(iris2)
    i2p2 = displayio.Palette(1); i2p2[0] = 0x0044CC
    group.append(vectorio.Circle(pixel_shader=i2p2, radius=60, x=x, y=y))
    pp2 = displayio.Palette(1); pp2[0] = 0x000000
    pupil2 = vectorio.Circle(pixel_shader=pp2, radius=38, x=x, y=y)
    group.append(pupil2)
    gp = displayio.Palette(1); gp[0] = 0xFFFFFF
    group.append(vectorio.Circle(pixel_shader=gp, radius=16, x=x+23, y=y-24))
    g2p = displayio.Palette(1); g2p[0] = 0xFFFFFF
    group.append(vectorio.Circle(pixel_shader=g2p, radius=7, x=x-17, y=y+18))
    elp = displayio.Palette(1); elp[0] = 0x000000
    eyelid = vectorio.Circle(pixel_shader=elp, radius=135, x=x, y=y-270)
    group.append(eyelid)
    return pupil2, eyelid, white, proc_ring, iris2, iris, inner

left_pupil, left_eyelid, left_white, left_proc, left_iris2, left_iris, left_inner = make_eye(155, 370, main_group)
right_pupil, right_eyelid, right_white, right_proc, right_iris2, right_iris, right_inner = make_eye(565, 370, main_group)

# Nose
for nx in [335, 385]:
    np_ = displayio.Palette(1); np_[0] = 0x50B4FF
    main_group.append(vectorio.Circle(pixel_shader=np_, radius=7, x=nx, y=510))

display.root_group = main_group

# --- State ---
mode = "closed"
emotion = "neutral"
buf = ""
t = 0
current_volume = 0.0
target_volume = 0.0
think_angle = 0.0
eye_x = 0
eye_y = 0

# Blink
last_blink_left = time.monotonic()
last_blink_right = time.monotonic()
blink_interval = 10.0
is_blinking_left = False
is_blinking_right = False
blink_t_left = 0.0
blink_t_right = 0.0
glitch_active = False
glitch_t = 0.0

# Micro tremor
tremor_x = 0
tremor_y = 0
tremor_target_x = 0
tremor_target_y = 0
last_tremor = time.monotonic()
tremor_interval = 2.0

# Saccade
saccade_x = 0
saccade_y = 0
saccade_target_x = 0
saccade_target_y = 0
last_saccade = time.monotonic()
saccade_interval = random.uniform(4.0, 8.0)
in_saccade = False
saccade_t = 0.0

# Processing glow
proc_pulse_t = 0.0

# Pupil
pupil_radius = 38
pupil_target_radius = 38

# Heartbeat
heartbeat_t = 0.0

# Focus breathing
breathe_t = 0.0

# Iris color cycling
iris_hue_t = 0.0

# Glitch burst
last_glitch = time.monotonic()
glitch_burst_interval = random.uniform(15.0, 40.0)
glitch_burst_active = False
glitch_burst_t = 0.0

# Startup animation
startup_done = False
startup_t = 0.0

def hsv_to_rgb(h, s, v):
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p = int(v * (1 - s) * 255)
    q = int(v * (1 - f * s) * 255)
    t_ = int(v * (1 - (1 - f) * s) * 255)
    v = int(v * 255)
    i = i % 6
    if i == 0: return (v, t_, p)
    if i == 1: return (q, v, p)
    if i == 2: return (p, v, t_)
    if i == 3: return (p, q, v)
    if i == 4: return (t_, p, v)
    return (v, p, q)

def rgb_to_hex(r, g, b):
    return (r << 16) | (g << 8) | b

def set_eyelid(eyelid, amount, base_y=370):
    offset = int(amount * 270)
    eyelid.y = base_y - 270 + offset

def set_mouth(volume):
    base = 5
    boost = int(volume * 250)
    g = min(255, int((base + boost) * 0.47))
    b = min(255, base + boost)
    pixels.fill((0, g, b))
    pixels.show()

def set_emotion(emo):
    global pupil_target_radius
    if emo == "happy":
        left_iris.pixel_shader[0] = 0x00FF88
        right_iris.pixel_shader[0] = 0x00FF88
        left_iris2.pixel_shader[0] = 0x00FF88
        right_iris2.pixel_shader[0] = 0x00FF88
        left_inner.pixel_shader[0] = 0x00AA55
        right_inner.pixel_shader[0] = 0x00AA55
        # Eyebrows slightly raised
        left_brow.y = 205
        right_brow.y = 205
        pupil_target_radius = 42
    elif emo == "angry":
        left_iris.pixel_shader[0] = 0xFF2200
        right_iris.pixel_shader[0] = 0xFF2200
        left_iris2.pixel_shader[0] = 0xFF2200
        right_iris2.pixel_shader[0] = 0xFF2200
        left_inner.pixel_shader[0] = 0xAA1100
        right_inner.pixel_shader[0] = 0xAA1100
        # Eyebrows angled inward (lower inner edge)
        left_brow.y = 225
        right_brow.y = 225
        pupil_target_radius = 30
    elif emo == "surprised":
        left_iris.pixel_shader[0] = 0xFFFF00
        right_iris.pixel_shader[0] = 0xFFFF00
        left_iris2.pixel_shader[0] = 0xFFFF00
        right_iris2.pixel_shader[0] = 0xFFFF00
        left_inner.pixel_shader[0] = 0xAAAA00
        right_inner.pixel_shader[0] = 0xAAAA00
        # Eyebrows raised high
        left_brow.y = 190
        right_brow.y = 190
        pupil_target_radius = 55
    else:  # neutral
        left_iris.pixel_shader[0] = 0x0066FF
        right_iris.pixel_shader[0] = 0x0066FF
        left_iris2.pixel_shader[0] = 0x0066FF
        right_iris2.pixel_shader[0] = 0x0066FF
        left_inner.pixel_shader[0] = 0x0044CC
        right_inner.pixel_shader[0] = 0x0044CC
        left_brow.y = 215
        right_brow.y = 215
        pupil_target_radius = 38

dot_colors_idle = [
    0x001133, 0x002266, 0x003399, 0x0044CC, 0x0055FF,
    0x0066FF, 0x0055FF, 0x0044CC, 0x003399, 0x002266
]
dot_colors_thinking = [
    0x003333, 0x006666, 0x009999, 0x00CCCC, 0x00FFFF,
    0x00CCCC, 0x009999, 0x006666, 0x003333, 0x001111
]

while True:
    now = time.monotonic()

    # --- Startup animation ---
    if not startup_done:
        startup_t += 0.03
        amount = max(0.0, 1.0 - startup_t)
        set_eyelid(left_eyelid, amount)
        set_eyelid(right_eyelid, amount)
        if startup_t >= 1.0:
            startup_done = True
            mode = "closed"
        time.sleep(0.05)
        continue

    # --- Micro tremor ---
    if now - last_tremor > tremor_interval:
        tremor_target_x = random.randint(-2, 2)
        tremor_target_y = random.randint(-2, 2)
        tremor_interval = random.uniform(1.5, 3.5)
        last_tremor = now
    tremor_x = int(tremor_x * 0.7 + tremor_target_x * 0.3)
    tremor_y = int(tremor_y * 0.7 + tremor_target_y * 0.3)

    # --- Saccade ---
    if now - last_saccade > saccade_interval and mode == "idle":
        saccade_target_x = random.randint(-30, 30)
        saccade_target_y = random.randint(-20, 20)
        in_saccade = True
        saccade_t = 0.0
        saccade_interval = random.uniform(4.0, 8.0)
        last_saccade = now
    if in_saccade:
        saccade_t += 0.2
        saccade_x = int(saccade_x * 0.5 + saccade_target_x * 0.5)
        saccade_y = int(saccade_y * 0.5 + saccade_target_y * 0.5)
        if saccade_t > 2.0:
            in_saccade = False
            saccade_x = 0
            saccade_y = 0

    # --- Heartbeat ---
    heartbeat_t += 0.04
    heartbeat = int(abs(math.sin(heartbeat_t * 1.1)) * 8)
    scanline_palette[1] = rgb_to_hex(heartbeat, heartbeat, heartbeat + 5)

    # --- Focus breathing ---
    breathe_t += 0.015
    breathe_offset = int(math.sin(breathe_t) * 3)

    # --- Iris color cycling (idle only) ---
    if mode == "idle" and emotion == "neutral":
        iris_hue_t += 0.001
        r, g, b = hsv_to_rgb(0.58 + math.sin(iris_hue_t) * 0.08, 1.0, 1.0)
        col = rgb_to_hex(r, g, b)
        left_iris.pixel_shader[0] = col
        right_iris.pixel_shader[0] = col
        left_iris2.pixel_shader[0] = col
        right_iris2.pixel_shader[0] = col

    # --- Glitch burst ---
    if now - last_glitch > glitch_burst_interval and mode != "closed":
        glitch_burst_active = True
        glitch_burst_t = 0.0
        last_glitch = now
        glitch_burst_interval = random.uniform(15.0, 40.0)
    if glitch_burst_active:
        glitch_burst_t += 0.15
        if int(glitch_burst_t * 20) % 2 == 0:
            scanline_palette[1] = 0x222222
        else:
            scanline_palette[1] = 0x030303
        if glitch_burst_t > 1.0:
            glitch_burst_active = False

    # --- Processing glow ---
    if mode == "thinking":
        proc_pulse_t += 0.08
        glow = int(abs(math.sin(proc_pulse_t)) * 255)
        col = rgb_to_hex(glow // 4, glow, 255)
        left_proc.pixel_shader[0] = col
        right_proc.pixel_shader[0] = col
        pupil_target_radius = 50 + breathe_offset
    else:
        left_proc.pixel_shader[0] = 0x000000
        right_proc.pixel_shader[0] = 0x000000
        proc_pulse_t = 0.0
        if mode == "idle":
            pupil_target_radius = 38 + breathe_offset
        else:
            pupil_target_radius = 38

    # Smooth pupil size
    pupil_radius = int(pupil_radius * 0.85 + pupil_target_radius * 0.15)
    left_pupil.radius = pupil_radius
    right_pupil.radius = pupil_radius

    # --- Asymmetric blink ---
    if mode == "closed":
        set_eyelid(left_eyelid, 1.0)
        set_eyelid(right_eyelid, 1.0)
    else:
        if not is_blinking_left and (now - last_blink_left) > blink_interval:
            is_blinking_left = True
            blink_t_left = 0.0
            glitch_active = True
            glitch_t = 0.0
            # Right eye blinks slightly after left
            is_blinking_right = True
            blink_t_right = -0.2

        if glitch_active:
            glitch_t += 0.3
            if int(glitch_t * 10) % 2 == 0:
                scanline_palette[1] = 0x111111
            else:
                scanline_palette[1] = 0x050505
            if glitch_t > 1.5:
                glitch_active = False

        if is_blinking_left:
            blink_t_left += 0.4
            if blink_t_left < 1.0:
                set_eyelid(left_eyelid, max(0.0, blink_t_left))
            elif blink_t_left < 2.0:
                set_eyelid(left_eyelid, max(0.0, 2.0 - blink_t_left))
            else:
                set_eyelid(left_eyelid, 0.0)
                is_blinking_left = False
                last_blink_left = now
                last_blink_right = now
                blink_interval = random.uniform(7.0, 13.0)
        else:
            set_eyelid(left_eyelid, 0.0)

        if is_blinking_right:
            blink_t_right += 0.4
            if blink_t_right < 0.0:
                set_eyelid(right_eyelid, 0.0)
            elif blink_t_right < 1.0:
                set_eyelid(right_eyelid, blink_t_right)
            elif blink_t_right < 2.0:
                set_eyelid(right_eyelid, 2.0 - blink_t_right)
            else:
                set_eyelid(right_eyelid, 0.0)
                is_blinking_right = False
        else:
            set_eyelid(right_eyelid, 0.0)

    # --- Mode animations ---
    if mode == "thinking":
        ring_pal[0] = 0x00FFFF
        ring_inner_pal[0] = 0x000000
        think_angle += 0.05
        ox = int(20 * math.sin(think_angle))
        oy = int(15 * math.cos(think_angle))
        left_pupil.x = 155 + ox + tremor_x
        left_pupil.y = 370 + oy + tremor_y
        right_pupil.x = 565 + ox + tremor_x
        right_pupil.y = 370 + oy + tremor_y
        for i, dot in enumerate(dots):
            phase = (t + i * 2) % len(dot_colors_thinking)
            dot_palettes[i][0] = dot_colors_thinking[phase]
    else:
        ring_pal[0] = 0x000000
        fx = eye_x + tremor_x + saccade_x
        fy = eye_y + tremor_y + saccade_y
        left_pupil.x = 155 + fx
        left_pupil.y = 370 + fy
        right_pupil.x = 565 + fx
        right_pupil.y = 370 + fy
        for i, dot in enumerate(dots):
            phase = (t + i * 3) % len(dot_colors_idle)
            dot_palettes[i][0] = dot_colors_idle[phase]

    t = (t + 1) % 10

    # --- Mouth ---
    set_mouth(current_volume)
    current_volume = current_volume * 0.85 + target_volume * 0.15
    target_volume = max(0.0, target_volume - 0.02)

    # --- Serial input ---
    if supervisor.runtime.serial_bytes_available:
        c = sys.stdin.read(1)
        if c == "\n":
            try:
                if buf.startswith("v:"):
                    target_volume = float(buf[2:])
                elif buf.startswith("mode:"):
                    mode = buf[5:].strip()
                elif buf.startswith("emotion:"):
                    emotion = buf[8:].strip()
                    set_emotion(emotion)
                else:
                    x, y = buf.strip().split(",")
                    ox = int((int(x) - 320) / 320 * 55)
                    oy = int((int(y) - 240) / 240 * 55)
                    eye_x = ox
                    eye_y = oy
            except:
                pass
            buf = ""
        else:
            buf += c

    time.sleep(0.05)
