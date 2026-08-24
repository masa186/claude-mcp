# -*- coding: utf-8 -*-
"""Lo-fi study room: カワウソが勉強しているループアニメーションを描画する"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

W, H = 1920, 1080
FPS = 24
LOOP = 24.0                       # ループ長（秒）
NF = int(LOOP * FPS)

# ---- キャラの色（元イラストから抽出）
FUR       = (197, 146, 126)
FUR_DK    = (159, 112,  98)
LINE      = ( 88,  58,  48)
CREAM     = (243, 237, 224)
VEST      = (213, 161,  63)
VEST_DK   = (186, 136,  48)
BOW       = ( 97, 150, 137)
BOW_DK    = ( 70, 116, 105)

# ---- 部屋の色
WALL_T    = ( 45,  39,  66)
WALL_B    = ( 32,  28,  50)
DESK      = (107,  74,  52)
DESK_EDGE = ( 78,  53,  37)
FRAME     = ( 74,  59,  51)
SKY       = ( 20,  31,  56)
WARM      = (255, 201, 126)

DESK_Y = 690
CX     = 900                      # カワウソの中心X

rng = np.random.default_rng(7)


def rr(d, box, r, fill=None, outline=None, width=0):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)


def vgrad(size, top, bottom):
    w, h = size
    t = np.linspace(0, 1, h)[:, None, None]
    a, b = np.array(top, float)[None, None, :], np.array(bottom, float)[None, None, :]
    return Image.fromarray((a + (b - a) * t).repeat(w, axis=1).astype(np.uint8), "RGB")


def glow(size, center, radius, color, strength):
    """やわらかい光。ガウスぼかしより速い距離減衰"""
    w, h = size
    y, x = np.mgrid[0:h, 0:w]
    dist = np.hypot(x - center[0], y - center[1]) / radius
    a = np.clip(1 - dist, 0, 1) ** 2 * strength
    img = np.zeros((h, w, 4), np.uint8)
    img[..., 0], img[..., 1], img[..., 2] = color
    img[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(img, "RGBA")


# ================================================================ 背景（静止）
def build_background():
    bg = vgrad((W, H), WALL_T, WALL_B).convert("RGBA")
    d = ImageDraw.Draw(bg)

    # --- 窓
    wx0, wy0, wx1, wy1 = 120, 92, 690, 616
    d.rectangle([wx0 - 16, wy0 - 16, wx1 + 16, wy1 + 16], fill=FRAME)
    sky = vgrad((wx1 - wx0, wy1 - wy0), SKY, (34, 46, 72)).convert("RGBA")
    sd = ImageDraw.Draw(sky)
    for _ in range(90):                                   # 遠くの街の灯り
        x = rng.integers(0, sky.width); y = rng.integers(int(sky.height * 0.42), sky.height)
        r = rng.integers(2, 7)
        c = (255, 214, 150) if rng.random() < 0.72 else (150, 214, 255)
        sd.ellipse([x - r, y - r, x + r, y + r], fill=c + (rng.integers(70, 190),))
    sky = sky.filter(ImageFilter.GaussianBlur(2.2))
    sd = ImageDraw.Draw(sky)
    for _ in range(16):                                   # ビルのシルエット
        bw = rng.integers(40, 110); bx = rng.integers(-40, sky.width)
        by = rng.integers(int(sky.height * 0.45), int(sky.height * 0.72))
        sd.rectangle([bx, by, bx + bw, sky.height], fill=(16, 22, 40))
        for wy in range(by + 14, sky.height - 10, 26):
            for wxx in range(bx + 10, bx + bw - 10, 22):
                if rng.random() < 0.3:
                    sd.rectangle([wxx, wy, wxx + 9, wy + 12],
                                 fill=(255, 208, 140, rng.integers(90, 200)))
    bg.alpha_composite(sky, (wx0, wy0))
    d = ImageDraw.Draw(bg)
    d.rectangle([wx0, wy0, wx1, wy1], outline=FRAME, width=4)
    mx = (wx0 + wx1) // 2; my = (wy0 + wy1) // 2
    d.rectangle([mx - 8, wy0, mx + 8, wy1], fill=FRAME)
    d.rectangle([wx0, my - 8, wx1, my + 8], fill=FRAME)
    d.rectangle([wx0 - 34, wy1 + 16, wx1 + 34, wy1 + 44], fill=(88, 70, 60))  # 窓台

    # --- 壁の棚
    sx0, sx1, sy = 1180, 1800, 300
    d.rectangle([sx0, sy, sx1, sy + 18], fill=(96, 74, 62))
    d.rectangle([sx0, sy + 18, sx1, sy + 26], fill=(70, 53, 44))
    bx = sx0 + 40
    for hgt, col in [(96, (120, 78, 74)), (110, (86, 106, 108)), (84, (150, 118, 66)),
                     (104, (96, 84, 118)), (92, (110, 92, 72))]:
        bwid = int(rng.integers(22, 34))
        d.rectangle([bx, sy - hgt, bx + bwid, sy], fill=col)
        d.rectangle([bx, sy - hgt, bx + bwid, sy - hgt + 8], fill=tuple(int(c * 1.25) for c in col))
        bx += bwid + 5
    # 棚の上の観葉植物
    px = sx1 - 150
    d.rectangle([px, sy - 54, px + 62, sy], fill=(126, 92, 72))
    for a in range(9):
        ang = -math.pi / 2 + (a - 4) * 0.34
        ex, ey = px + 31 + math.cos(ang) * 70, sy - 54 + math.sin(ang) * 74
        d.line([px + 31, sy - 54, ex, ey], fill=(74, 116, 82), width=9)
        d.ellipse([ex - 15, ey - 11, ex + 15, ey + 11], fill=(86, 132, 92))
    # カセットテープ
    cx0 = sx1 - 300
    d.rounded_rectangle([cx0, sy - 46, cx0 + 96, sy], 6, fill=(198, 176, 150))
    d.rounded_rectangle([cx0 + 12, sy - 34, cx0 + 84, sy - 12], 4, fill=(120, 100, 86))
    for hx in (cx0 + 30, cx0 + 66):
        d.ellipse([hx - 8, sy - 30, hx + 8, sy - 14], fill=(60, 50, 44))

    # --- 額に入ったポスター
    fx0, fy0, fx1, fy1 = 1150, 392, 1400, 600
    d.rectangle([fx0, fy0, fx1, fy1], fill=(58, 48, 44), outline=(96, 78, 66), width=6)
    d.rectangle([fx0 + 16, fy0 + 16, fx1 - 16, fy1 - 16], fill=(72, 84, 104))
    d.ellipse([fx0 + 60, fy0 + 46, fx0 + 130, fy0 + 116], fill=(240, 228, 190))   # 月
    d.polygon([(fx0 + 16, fy1 - 16), (fx0 + 110, fy0 + 130), (fx0 + 200, fy1 - 16)],
              fill=(52, 66, 78))
    d.polygon([(fx0 + 90, fy1 - 16), (fx0 + 180, fy0 + 150), (fx1 - 16, fy1 - 16)],
              fill=(44, 56, 68))

    # --- 机
    d.rectangle([0, DESK_Y, W, H], fill=DESK)
    d.rectangle([0, DESK_Y, W, DESK_Y + 10], fill=(132, 94, 66))
    for i in range(26):                                    # 木目
        y = DESK_Y + 26 + i * 15
        d.line([0, y, W, y + rng.integers(-3, 4)], fill=(100, 69, 49), width=1)
    d.rectangle([0, H - 96, W, H], fill=DESK_EDGE)
    d.rectangle([0, H - 100, W, H - 92], fill=(140, 100, 70))
    return bg


def draw_desk_items(bg):
    """机の上の小物（静止しているもの）"""
    d = ImageDraw.Draw(bg)
    # 本の山（左）
    stack = [((176, 664), 300, 44, (128, 78, 76)), ((194, 622), 268, 42, (88, 110, 112)),
             ((166, 586), 292, 36, (156, 122, 68))]
    for (x, y), bw, bh, col in stack:
        d.rounded_rectangle([x, y, x + bw, y + bh], 5, fill=col)
        d.rounded_rectangle([x, y, x + bw, y + 9], 4, fill=tuple(min(255, int(c * 1.3)) for c in col))
        d.line([x + 12, y + bh - 8, x + bw - 12, y + bh - 8], fill=(238, 232, 216), width=6)
    # ペン立て（右奥）
    d.rounded_rectangle([1264, 636, 1352, 752], 12, fill=(92, 108, 116))
    for i, c in enumerate([(214, 96, 86), (232, 190, 90), (110, 158, 148)]):
        px = 1282 + i * 25
        d.line([px, 640, px - 6 + i * 3, 556 + i * 10], fill=c, width=10)
    # ヘッドホン（右手前）
    d.arc([1420, 880, 1620, 1010], 180, 360, fill=(48, 44, 52), width=16)
    for hx in (1420, 1600):
        d.ellipse([hx - 26, 936, hx + 26, 1010], fill=(58, 54, 64))
        d.ellipse([hx - 18, 946, hx + 18, 1000], fill=(38, 35, 44))
    return bg


def draw_lamp(bg):
    d = ImageDraw.Draw(bg)
    bx, by = 1690, 726
    d.ellipse([bx - 80, by - 26, bx + 80, by + 16], fill=(64, 76, 86))
    d.line([bx, by - 14, bx + 6, 486], fill=(64, 76, 86), width=15)
    d.line([bx + 6, 486, bx - 96, 430], fill=(64, 76, 86), width=15)
    d.polygon([(bx - 186, 496), (bx - 16, 496), (bx - 56, 392), (bx - 146, 392)],
              fill=(86, 102, 112))
    d.polygon([(bx - 186, 496), (bx - 16, 496), (bx - 24, 512), (bx - 178, 512)],
              fill=(240, 208, 148))
    return bg


# ================================================================ カワウソ
_head_src = Image.open("src/otter_rgba.png").convert("RGBA").crop((40, 45, 530, 400))
HEAD_W = 366
HEAD = _head_src.resize((HEAD_W, int(_head_src.height * HEAD_W / _head_src.width)), Image.LANCZOS)
_hd = ImageDraw.Draw(HEAD)                          # 開いた口を消して穏やかな口元にする
_hd.ellipse([152, 184, 202, 236], fill=CREAM)
_hd.arc([158, 188, 196, 216], 18, 162, fill=LINE, width=5)
HS = HEAD_W / _head_src.width                       # 縮尺
# 元画像でのレンズ中心（クロップ基準）
LENS = [((192 - 40) * HS, (213 - 45) * HS), ((348 - 40) * HS, (213 - 45) * HS)]
LENS_R = 46 * HS


def head_sprite(blink):
    """blink=0..1 でまぶたを下ろした頭部を返す"""
    if blink <= 0.02:
        return HEAD
    im = HEAD.copy()
    d = ImageDraw.Draw(im)
    for (lx, ly) in LENS:
        h = LENS_R * 1.5 * blink
        d.rectangle([lx - LENS_R * 0.95, ly - LENS_R, lx + LENS_R * 0.95, ly - LENS_R + h],
                    fill=CREAM)
        d.arc([lx - LENS_R * 0.8, ly - LENS_R * 0.6 + h - 14, lx + LENS_R * 0.8,
               ly - LENS_R * 0.6 + h + 14], 200, 340, fill=LINE, width=5)
    return im


def draw_body(d, bob):
    """机の向こうに見える胴体。頭より先に描く"""
    top = 520 + bob
    # 肩・胴
    d.rounded_rectangle([CX - 196, top, CX + 196, DESK_Y + 120], 120, fill=FUR,
                        outline=LINE, width=8)
    # シャツ
    d.polygon([(CX - 104, top + 44), (CX + 104, top + 44), (CX + 74, DESK_Y + 40),
               (CX - 74, DESK_Y + 40)], fill=CREAM)
    # ベスト
    for sgn in (-1, 1):
        d.polygon([(CX + sgn * 186, top + 40), (CX + sgn * 60, top + 52),
                   (CX + sgn * 30, DESK_Y + 60), (CX + sgn * 186, DESK_Y + 60)],
                  fill=VEST, outline=LINE)
    d.line([CX - 60, top + 52, CX - 30, DESK_Y + 60], fill=VEST_DK, width=5)
    d.line([CX + 60, top + 52, CX + 30, DESK_Y + 60], fill=VEST_DK, width=5)
    # 蝶ネクタイ
    by = top + 66
    d.polygon([(CX - 84, by - 34), (CX - 18, by), (CX - 84, by + 34)], fill=BOW, outline=LINE)
    d.polygon([(CX + 84, by - 34), (CX + 18, by), (CX + 84, by + 34)], fill=BOW, outline=LINE)
    d.rounded_rectangle([CX - 22, by - 20, CX + 22, by + 20], 8, fill=BOW_DK, outline=LINE, width=3)


def draw_arms(d, t, bob):
    """机の上に出ている腕と手。机やノートより後に描く"""
    write = math.sin(t * 2 * math.pi / 1.5)            # 書く動き（1.5秒周期）
    jitter = math.sin(t * 2 * math.pi / 0.25) * 2.5

    def limb(pts, w):
        d.line(pts, fill=LINE, width=w + 22, joint="curve")
        d.line(pts, fill=FUR, width=w, joint="curve")

    def paw(cx, cy, r=60, rot=0.0):
        d.ellipse([cx - r, cy - r * 0.86, cx + r, cy + r * 0.86], fill=FUR,
                  outline=LINE, width=9)
        for k in (-1, 0, 1):
            fx = cx + k * r * 0.44
            d.arc([fx - 13, cy - r * 0.62, fx + 13, cy + r * 0.12], 250, 290,
                  fill=LINE, width=6)

    # 左腕：ノートを押さえる
    lhx, lhy = CX - 350, DESK_Y + 226
    limb([(CX - 176, DESK_Y - 52 + bob), (CX - 300, DESK_Y + 84), (lhx + 6, lhy - 40)], 58)
    paw(lhx, lhy)

    # 右腕：鉛筆を持って書く
    hx = CX + 186 + write * 24
    hy = DESK_Y + 206 + jitter
    limb([(CX + 176, DESK_Y - 52 + bob), (CX + 268, DESK_Y + 76), (hx + 26, hy - 36)], 58)
    paw(hx, hy, rot=write)

    # 鉛筆
    ang = math.radians(-62)
    tipx, tipy = hx - 40, hy + 40
    ex, ey = tipx + math.cos(ang) * 158, tipy + math.sin(ang) * 158
    d.line([tipx, tipy, ex, ey], fill=(60, 52, 48), width=19)
    d.line([tipx, tipy, ex, ey], fill=(238, 186, 66), width=13)
    d.line([ex, ey, ex + math.cos(ang) * 26, ey + math.sin(ang) * 26], fill=(226, 118, 110), width=13)
    d.line([tipx, tipy, tipx - math.cos(ang) * 20, tipy - math.sin(ang) * 20],
           fill=(60, 52, 48), width=9)


def draw_notebook(d):
    x0, y0, x1, y1 = CX - 330, DESK_Y + 72, CX + 230, DESK_Y + 322
    d.rounded_rectangle([x0 + 8, y0 + 10, x1 + 8, y1 + 10], 10, fill=(58, 40, 30))
    d.rounded_rectangle([x0, y0, x1, y1], 10, fill=(246, 242, 230))
    d.line([(x0 + 255, y0), (x0 + 255, y1)], fill=(214, 206, 190), width=3)
    for i in range(9):                                   # 罫線
        ly = y0 + 34 + i * 30
        d.line([x0 + 24, ly, x0 + 238, ly], fill=(198, 208, 224), width=3)
        d.line([x0 + 272, ly, x1 - 24, ly], fill=(198, 208, 224), width=3)
    for i in range(6):                                   # 書かれた文字っぽい線
        ly = y0 + 34 + i * 30 - 6
        d.line([x0 + 30, ly, x0 + 30 + (150 if i % 2 else 196), ly], fill=(96, 104, 126), width=5)
    for sy in range(y0 + 6, y1 - 4, 26):                 # リング
        d.arc([x0 + 244, sy, x0 + 268, sy + 20], 200, 20, fill=(150, 152, 158), width=5)


def draw_mug(d):
    x, y = 470, 812
    d.rounded_rectangle([x - 58, y - 104, x + 58, y], 16, fill=(222, 226, 232),
                        outline=(178, 184, 194), width=4)
    d.arc([x + 40, y - 84, x + 104, y - 20], 270, 90, fill=(210, 214, 222), width=14)
    d.ellipse([x - 50, y - 112, x + 50, y - 84], fill=(96, 62, 44))


def steam_layer(t):
    """マグから立ちのぼる湯気（周期4秒でループ）"""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for k in range(3):
        ph = (t / 4.0 + k / 3.0) % 1.0
        y = 706 - ph * 190
        a = int(120 * math.sin(math.pi * ph) ** 1.2)
        if a <= 2:
            continue
        x = 470 + math.sin(ph * 6.0 + k * 2.1) * 26
        r = 16 + ph * 26
        d.ellipse([x - r * 0.7, y - r, x + r * 0.7, y + r], fill=(230, 236, 244, a))
    return lay.filter(ImageFilter.GaussianBlur(9))


RAIN = [(rng.integers(120, 690), rng.random(), rng.integers(26, 54), rng.random())
        for _ in range(90)]


def rain_layer(t):
    """窓の外の雨。周期1.5秒でループ"""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for x, ph, ln, spd in RAIN:
        p = ((t / 1.5) * (0.7 + spd * 0.6) + ph) % 1.0
        y = 92 + p * (616 - 92)
        if y + ln > 616:
            continue
        d.line([x, y, x - 5, y + ln], fill=(186, 206, 234, 90), width=2)
    return lay


LIGHTS = [(120 + i * 106, 96 + int(38 * math.sin(i * 0.55)), (i * 0.7) % 1.0) for i in range(17)]


def string_lights(t):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    pts = [(x, y) for x, y, _ in LIGHTS]
    d.line(pts, fill=(58, 50, 46, 220), width=4)
    for x, y, ph in LIGHTS:
        tw = 0.68 + 0.32 * math.sin(2 * math.pi * (t / 3.0 + ph))
        d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=WARM + (int(255 * tw),))
    return ImageChops.add(lay, lay.filter(ImageFilter.GaussianBlur(11)))


GRAIN = [(rng.normal(0, 1, (H // 2, W // 2)) * 3.0).astype(np.int16) for _ in range(9)]


def apply_grain(img, i):
    g = GRAIN[(i // 4) % len(GRAIN)]
    gi = Image.fromarray((g + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    return ImageChops.add(ImageChops.subtract(img, gi.convert("RGB").point(lambda v: max(0, v - 128))),
                          gi.convert("RGB").point(lambda v: max(0, 128 - v)))


VIGNETTE = None
LAMP_GLOW = None
TITLE = None


def build_title():
    from PIL import ImageFont
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    f1 = ImageFont.truetype("fonts/RoundedEB.ttf", 46)
    f2 = ImageFont.truetype("fonts/RoundedEB.ttf", 30)
    d.text((72, H - 138), "lofi beats to study", font=f1, fill=(246, 238, 224, 232))
    d.text((74, H - 78), "カワウソと勉強する部屋", font=f2, fill=(226, 210, 190, 190))
    return lay


def build_overlays():
    global VIGNETTE, LAMP_GLOW
    y, x = np.mgrid[0:H, 0:W]
    dist = np.hypot((x - W / 2) / (W / 2), (y - H / 2) / (H / 2))
    a = (np.clip(dist - 0.55, 0, 2) / 1.1) ** 1.5
    v = np.zeros((H, W, 4), np.uint8)
    v[..., 3] = (np.clip(a, 0, 1) * 190).astype(np.uint8)
    VIGNETTE = Image.fromarray(v, "RGBA")
    global TITLE
    TITLE = build_title()
    LAMP_GLOW = glow((W, H), (1540, 560), 700, WARM, 0.30)
    LAMP_GLOW.alpha_composite(glow((W, H), (960, 880), 620, WARM, 0.20))


def render_frame(i, bg_static):
    t = i / FPS
    bob = math.sin(2 * math.pi * t / 4.0) * 7
    img = bg_static.copy()
    d = ImageDraw.Draw(img)

    draw_body(d, bob)
    hs = head_sprite(blink_amount(t))
    ang = math.sin(2 * math.pi * t / 6.0) * 2.2
    hr = hs.rotate(ang, Image.BICUBIC, expand=True)
    img.alpha_composite(hr, (CX - hr.width // 2, int(300 + bob * 1.3) - (hr.height - hs.height) // 2))

    # 机とその上のもの（胴体を隠す）
    desk = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(desk)
    dd.rectangle([0, DESK_Y, W, H], fill=DESK)
    dd.rectangle([0, DESK_Y, W, DESK_Y + 10], fill=(132, 94, 66))
    for k in range(26):
        yy = DESK_Y + 26 + k * 15
        dd.line([0, yy, W, yy + ((k * 37) % 7 - 3)], fill=(100, 69, 49), width=1)
    dd.rectangle([0, H - 96, W, H], fill=DESK_EDGE)
    dd.rectangle([0, H - 100, W, H - 92], fill=(140, 100, 70))
    img.alpha_composite(desk)

    draw_desk_items(img)
    draw_lamp(img)
    d = ImageDraw.Draw(img)
    draw_mug(d)
    draw_notebook(d)
    draw_arms(d, t, bob)

    img.alpha_composite(rain_layer(t))
    img.alpha_composite(steam_layer(t))
    img.alpha_composite(string_lights(t))
    img.alpha_composite(LAMP_GLOW)
    img.alpha_composite(VIGNETTE)
    img.alpha_composite(TITLE)
    return apply_grain(img.convert("RGB"), i)


BLINKS = (2.4, 7.9, 13.1, 15.0, 20.6)


def blink_amount(t):
    a = 0.0
    for bt in BLINKS:
        dt = (t - bt) % LOOP
        if dt < 0.18:
            a = max(a, math.sin(math.pi * dt / 0.18))
    return a
