# -*- coding: utf-8 -*-
"""冷蔵庫サムネイル生成 / 1080x1920"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance, ImageChops

W, H = 1080, 1920
FONT = "fonts/RoundedEB.ttf"
f = lambda s: ImageFont.truetype(FONT, s)

def vgrad(size, top, bottom):
    w, h = size
    t = np.linspace(0, 1, h)[:, None, None]
    a, b = np.array(top, float)[None, None, :], np.array(bottom, float)[None, None, :]
    return Image.fromarray((a + (b - a) * t).repeat(w, axis=1).astype(np.uint8), "RGB")

def hgrad(size, left, right):
    return vgrad((size[1], size[0]), left, right).transpose(Image.ROTATE_270)

def cover(img, size):
    tw, th = size
    iw, ih = img.size
    s = max(tw / iw, th / ih)
    nw, nh = int(iw * s + 0.5), int(ih * s + 0.5)
    img = img.resize((nw, nh), Image.LANCZOS)
    x, y = (nw - tw) // 2, (nh - th) // 2
    return img.crop((x, y, x + tw, y + th))

def rrect_mask(size, radius, box=None):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle(box or [0, 0, size[0] - 1, size[1] - 1], radius, fill=255)
    return m

def shadow_layer(mask, blur, spread=0, alpha=140, offset=(0, 0), color=(0, 0, 0)):
    m = mask
    if spread:
        m = m.filter(ImageFilter.MaxFilter(spread * 2 + 1))
    m = m.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * alpha / 255))
    tmp = Image.new("L", (W, H), 0)
    tmp.paste(m, offset)
    lay = Image.new("RGBA", (W, H), color + (255,))
    lay.putalpha(tmp)
    return lay

def poly_mask(pts):
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m

# ============================================================ 部屋（背景）
canvas = vgrad((W, H), (250, 244, 234), (232, 221, 205)).convert("RGBA")
FLOOR = 1690
floor = vgrad((W, H - FLOOR), (198, 178, 152), (162, 141, 116)).convert("RGBA")
canvas.alpha_composite(floor, (0, FLOOR))
# 壁と床の境目の陰
band = Image.new("RGBA", (W, 60), (0, 0, 0, 0))
ImageDraw.Draw(band).rectangle([0, 0, W, 26], fill=(120, 104, 86, 90))
canvas.alpha_composite(band.filter(ImageFilter.GaussianBlur(14)), (0, FLOOR - 20))
# 上部を落として文字を読ませる
veil = np.zeros((H, W, 4), np.uint8)
veil[..., 3] = (np.clip(np.linspace(1.0, 0.0, H) * 1.9, 0, 1)[:, None] * 90).astype(np.uint8)
canvas.alpha_composite(Image.fromarray(veil, "RGBA"))
# ふんわり光
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(glow).ellipse([-260, 240, 900, 1500], fill=(255, 252, 244, 90))
canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(140)))

# ============================================================ 冷蔵庫
BX0, BY0, BX1, BY1 = 58, 452, 786, 1772
R, IN = 46, 22
OX0, OY0, OX1, OY1 = BX0 + IN, BY0 + IN, BX1 - IN, BY1 - IN
DOOR = [(BX1 - 8, BY0 + 6), (1016, BY0 + 104), (1016, BY1 - 92), (BX1 - 8, BY1 - 6)]

# --- 開いたドア（内側の面が見える）
canvas.alpha_composite(shadow_layer(poly_mask(DOOR), 30, 3, alpha=95, offset=(16, 18)))
dl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
dd = ImageDraw.Draw(dl)
dd.polygon(DOOR, fill=(255, 255, 255, 255))
face = hgrad((W, H), (246, 249, 252), (208, 216, 226)).convert("RGBA")
face.putalpha(poly_mask(DOOR))
dl.alpha_composite(face)
dd = ImageDraw.Draw(dl)
def dx_at(y):  # ドア台形の左右端
    r = (y - (BY0 + 6)) / ((BY1 - 6) - (BY0 + 6))
    return BX1 - 8, 1016, r
for y0, y1 in [(BY0 + 210, BY0 + 350), (BY0 + 560, BY0 + 700), (BY0 + 910, BY0 + 1050)]:
    sl = 78  # 遠近のずれ
    dd.polygon([(BX1 + 12, y0), (1000, y0 + sl), (1000, y1 + sl), (BX1 + 12, y1)], fill=(228, 235, 243, 255))
    dd.polygon([(BX1 + 12, y1 - 30), (1000, y1 + sl - 30), (1000, y1 + sl), (BX1 + 12, y1)], fill=(196, 207, 219, 255))
    dd.line([(BX1 + 12, y0), (1000, y0 + sl)], fill=(178, 190, 203, 255), width=4)
dd.line([DOOR[1], DOOR[2]], fill=(150, 163, 178, 255), width=12)   # ドアの小口
dd.line([DOOR[0], DOOR[1]], fill=(210, 219, 229, 255), width=5)
dd.line([DOOR[2], DOOR[3]], fill=(190, 200, 212, 255), width=5)
canvas.alpha_composite(dl)

# --- 本体
body_mask = rrect_mask((W, H), R, [BX0, BY0, BX1, BY1])
canvas.alpha_composite(shadow_layer(body_mask, 38, 8, alpha=120, offset=(6, 22)))
body = vgrad((W, H), (252, 253, 254), (203, 211, 220)).convert("RGBA")
body.putalpha(body_mask)
canvas.alpha_composite(body)

# --- 庫内写真
photo = Image.open("base_fridge.jpg").convert("RGB")
photo = cover(photo, (OX1 - OX0, OY1 - OY0))
photo = ImageEnhance.Brightness(photo).enhance(1.05)
photo = ImageEnhance.Color(photo).enhance(1.15)
photo = ImageEnhance.Contrast(photo).enhance(1.06)
pm = rrect_mask(photo.size, 28)
photo = photo.convert("RGBA"); photo.putalpha(pm)
canvas.alpha_composite(photo, (OX0, OY0))

# --- 庫内のふち影＋冷たい青
ov = Image.new("RGBA", photo.size, (0, 0, 0, 0))
od = ImageDraw.Draw(ov)
for i in range(30):
    a = int(105 * (1 - i / 30) ** 2)
    od.rounded_rectangle([i, i, ov.width - 1 - i, ov.height - 1 - i], 28, outline=(26, 48, 76, a), width=1)
ov.putalpha(ImageChops.multiply(ov.split()[3], pm))
canvas.alpha_composite(ov, (OX0, OY0))

# ============================================================ 冷気
cold = Image.new("RGBA", (W, H), (0, 0, 0, 0))
cd = ImageDraw.Draw(cold)
for (cx, cy, rx, ry, a) in [(380, 1876, 470, 120, 235), (170, 1905, 330, 105, 215),
                            (640, 1900, 330, 100, 190), (300, 1822, 250, 70, 150),
                            (830, 1930, 300, 100, 150), (60, 1848, 200, 70, 150),
                            (520, 1938, 400, 110, 180)]:
    cd.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(206, 233, 250, a))
cold = cold.filter(ImageFilter.GaussianBlur(42))
canvas.alpha_composite(cold)
# 開口部から下へこぼれる冷気
spill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sd = ImageDraw.Draw(spill)
sd.polygon([(OX0 + 60, OY1 - 20), (OX1 - 60, OY1 - 20), (OX1 + 90, 1920), (OX0 - 120, 1920)],
           fill=(208, 234, 251, 150))
canvas.alpha_composite(spill.filter(ImageFilter.GaussianBlur(46)))

def snowflake(d, cx, cy, r, col, w):
    for k in range(3):
        a = math.radians(k * 60 + 15)
        dx, dy = math.cos(a) * r, math.sin(a) * r
        d.line([cx - dx, cy - dy, cx + dx, cy + dy], fill=col, width=w)
        for sgn in (1, -1):
            ex, ey = cx + dx * sgn, cy + dy * sgn
            for ba in (a + math.radians(140), a - math.radians(140)):
                d.line([ex, ey, ex + math.cos(ba) * r * 0.42, ey + math.sin(ba) * r * 0.42],
                       fill=col, width=max(2, w - 3))
sf = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sd = ImageDraw.Draw(sf)
for (x, y, r, a, w) in [(112, 1848, 36, 240, 9), (262, 1898, 24, 210, 7), (30, 1908, 21, 185, 6),
                        (396, 1856, 20, 195, 6), (548, 1900, 28, 205, 8), (664, 1836, 17, 170, 6)]:
    snowflake(sd, x, y, r, (255, 255, 255, a), w)
canvas.alpha_composite(sf)

# ============================================================ キャラクター
otter = Image.open("otter_rgba.png")
oh = 650
otter = otter.resize((int(otter.width * oh / otter.height), oh), Image.LANCZOS)
ox, oy = W - otter.width - 22, H - oh - 30
om = Image.new("L", (W, H), 0); om.paste(otter.split()[3], (ox, oy))
canvas.alpha_composite(shadow_layer(om, 24, 4, alpha=105, offset=(0, 16)))
canvas.alpha_composite(otter, (ox, oy))

# ============================================================ 文字
d = ImageDraw.Draw(canvas)
INK = (28, 31, 36)
YEL = (255, 213, 58)

bf = f(74)
label = "冷蔵庫"
tw = d.textlength(label, font=bf)
icon_w, pad_x, bh, by0 = 64, 36, 114, 56
bw = int(tw + icon_w + 22 + pad_x * 2)
bx0 = (W - bw) // 2
d.rounded_rectangle([bx0, by0, bx0 + bw, by0 + bh], 32, fill=INK + (240,))
ix, iy = bx0 + pad_x, by0 + 19
d.rounded_rectangle([ix, iy, ix + icon_w, iy + 77], 11, fill=(255, 255, 255))
d.line([ix + 3, iy + 28, ix + icon_w - 3, iy + 28], fill=INK, width=6)
d.line([ix + icon_w - 15, iy + 9, ix + icon_w - 15, iy + 21], fill=INK, width=6)
d.line([ix + icon_w - 15, iy + 36, ix + icon_w - 15, iy + 52], fill=INK, width=6)
d.text((ix + icon_w + 22, by0 + bh // 2), label, font=bf, fill=YEL, anchor="lm")

l1, l2 = "開けっぱなしにしたら", "部屋は涼しくなる？"
hf = f(106)
y1, y2 = 212, 344
pw = max(d.textlength(l1, font=hf), d.textlength(l2, font=hf)) + 60
px0 = (W - pw) / 2
d.rounded_rectangle([px0, y1 - 24, px0 + pw, y2 + 136], 32, fill=(34, 38, 44, 200))
d.text((W / 2, y1), l1, font=hf, fill=(255, 255, 255), stroke_width=11, stroke_fill=INK, anchor="mt")
d.text((W / 2, y2), l2, font=hf, fill=YEL, stroke_width=11, stroke_fill=INK, anchor="mt")

out = canvas.convert("RGB")
out.save("thumb_v4.jpg", quality=95)
print("ok", out.size)
