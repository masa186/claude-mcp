"""黒板用の図をPNG（透過）で書き出す。CapCutにそのまま取り込める。"""
import zlib, struct, math, os

CHALK = (239, 233, 218)
HEAT  = (196, 99, 74)

def write_png(path, w, h, buf):
    raw = b''.join(b'\x00' + bytes(buf[y*w*4:(y+1)*w*4]) for y in range(h))
    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data +
                struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) +
           chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))
    open(path, 'wb').write(png)


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.buf = bytearray(w * h * 4)
        self.shapes = []

    def ring(self, cx, cy, r_out, r_in, color=CHALK):
        self.shapes.append(('ring', cx, cy, r_out, r_in, color))

    def disc(self, cx, cy, r, color=CHALK, alpha=1.0):
        self.shapes.append(('disc', cx, cy, r, alpha, color))

    def bar(self, x1, y1, x2, y2, width, color=CHALK):
        self.shapes.append(('bar', x1, y1, x2, y2, width / 2.0, color))

    def tri(self, p1, p2, p3, color=CHALK):
        self.shapes.append(('tri', p1, p2, p3, color))

    def box(self, x1, y1, x2, y2, width, color=CHALK):
        self.bar(x1, y1, x2, y1, width, color); self.bar(x2, y1, x2, y2, width, color)
        self.bar(x2, y2, x1, y2, width, color); self.bar(x1, y2, x1, y1, width, color)

    def arrow(self, x1, y1, x2, y2, width, color=CHALK, head=None):
        import math as _m
        head = head or width * 3.2
        a = _m.atan2(y2 - y1, x2 - x1)
        bx, by = x2 - head * _m.cos(a), y2 - head * _m.sin(a)
        self.bar(x1, y1, bx, by, width, color)
        n = a + _m.pi / 2
        self.tri((x2, y2),
                 (bx + head * .55 * _m.cos(n), by + head * .55 * _m.sin(n)),
                 (bx - head * .55 * _m.cos(n), by - head * .55 * _m.sin(n)), color)

    def wave(self, x1, x2, y, amp, cycles, width, color=CHALK, steps=64):
        import math as _m
        pts = [(x1 + (x2-x1)*i/steps, y + amp*_m.sin(2*_m.pi*cycles*i/steps))
               for i in range(steps+1)]
        for a, b in zip(pts, pts[1:]):
            self.bar(a[0], a[1], b[0], b[1], width, color)

    def plus(self, cx, cy, r, width, color=CHALK):
        self.bar(cx-r, cy, cx+r, cy, width, color); self.bar(cx, cy-r, cx, cy+r, width, color)

    def minus(self, cx, cy, r, width, color=CHALK):
        self.bar(cx-r, cy, cx+r, cy, width, color)

    def _cov(self, s, x, y):
        kind = s[0]
        if kind == 'ring':
            _, cx, cy, ro, ri, _ = s
            d = math.hypot(x - cx, y - cy)
            return 1.0 if ri <= d <= ro else 0.0
        if kind == 'tri':
            _, p1, p2, p3, _ = s
            def sign(a, b, c):
                return (a[0]-c[0])*(b[1]-c[1]) - (b[0]-c[0])*(a[1]-c[1])
            p = (x, y)
            d1, d2, d3 = sign(p, p1, p2), sign(p, p2, p3), sign(p, p3, p1)
            neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
            pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
            return 0.0 if (neg and pos) else 1.0
        if kind == 'disc':
            _, cx, cy, r, a, _ = s
            return a if math.hypot(x - cx, y - cy) <= r else 0.0
        _, x1, y1, x2, y2, hw, _ = s
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
        return 1.0 if math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)) <= hw else 0.0

    def bbox(self, s):
        kind = s[0]
        if kind == 'ring':
            _, cx, cy, ro, ri, _ = s
            return cx-ro-1, cy-ro-1, cx+ro+1, cy+ro+1
        if kind == 'disc':
            _, cx, cy, r, a, _ = s
            return cx-r-1, cy-r-1, cx+r+1, cy+r+1
        if kind == 'tri':
            _, p1, p2, p3, _ = s
            xs = (p1[0], p2[0], p3[0]); ys = (p1[1], p2[1], p3[1])
            return min(xs)-1, min(ys)-1, max(xs)+1, max(ys)+1
        _, x1, y1, x2, y2, hw, _ = s
        return min(x1,x2)-hw-1, min(y1,y2)-hw-1, max(x1,x2)+hw+1, max(y1,y2)+hw+1

    def _cov_grid(self, s, X, Y):
        import numpy as np
        kind = s[0]
        if kind == 'ring':
            _, cx, cy, ro, ri, _ = s
            d = np.hypot(X-cx, Y-cy)
            return ((d >= ri) & (d <= ro)).astype(np.float64)
        if kind == 'disc':
            _, cx, cy, r, a, _ = s
            return np.where(np.hypot(X-cx, Y-cy) <= r, float(a), 0.0)
        if kind == 'tri':
            _, p1, p2, p3, _ = s
            def sg(ax, ay, b, c):
                return (ax-c[0])*(b[1]-c[1]) - (b[0]-c[0])*(ay-c[1])
            d1 = sg(X, Y, p1, p2); d2 = sg(X, Y, p2, p3); d3 = sg(X, Y, p3, p1)
            neg = (d1 < 0) | (d2 < 0) | (d3 < 0)
            pos = (d1 > 0) | (d2 > 0) | (d3 > 0)
            return (~(neg & pos)).astype(np.float64)
        _, x1, y1, x2, y2, hw, _ = s
        dx, dy = x2-x1, y2-y1
        L2 = dx*dx + dy*dy
        t = np.zeros_like(X) if L2 == 0 else np.clip(((X-x1)*dx + (Y-y1)*dy)/L2, 0.0, 1.0)
        return (np.hypot(X-(x1+t*dx), Y-(y1+t*dy)) <= hw).astype(np.float64)

    def render(self, path):
        """図形ごとに、触れる範囲だけを numpy で塗る。
        全画素×全図形を回すと、線の多い図（波形など）で時間が現実的に収まらない。"""
        import numpy as np
        SS = (0.17, 0.5, 0.83)
        rgb = np.zeros((self.h, self.w, 3), dtype=np.float64)
        alp = np.zeros((self.h, self.w), dtype=np.float64)
        for sh in self.shapes:
            bx0, by0, bx1, by1 = self.bbox(sh)
            x0 = max(0, int(bx0)); y0 = max(0, int(by0))
            x1 = min(self.w, int(bx1) + 2); y1 = min(self.h, int(by1) + 2)
            if x1 <= x0 or y1 <= y0:
                continue
            xs = np.arange(x0, x1); ys = np.arange(y0, y1)
            cov = np.zeros((len(ys), len(xs)), dtype=np.float64)
            for oy in SS:
                for ox in SS:
                    X, Y = np.meshgrid(xs + ox, ys + oy)
                    cov += self._cov_grid(sh, X, Y)
            cov /= len(SS) ** 2
            if not (cov > 0).any():
                continue
            col = np.array(sh[-1][:3], dtype=np.float64)
            c3 = cov[..., None]
            rgb[y0:y1, x0:x1] = col * c3 + rgb[y0:y1, x0:x1] * (1 - c3)
            alp[y0:y1, x0:x1] = cov + alp[y0:y1, x0:x1] * (1 - cov)
        out = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8),
                         np.clip(alp * 255, 0, 255).astype(np.uint8)])
        self.buf = bytearray(out.tobytes())
        write_png(path, self.w, self.h, self.buf)
        print('  ' + os.path.basename(path) + '  %dx%d' % (self.w, self.h))


def molecule(c, cx, cy, scale=1.0, color=CHALK):
    """水分子：酸素1つ＋水素2つ。上を向いた状態で描く。"""
    R, r = 108 * scale, 62 * scale
    t = 15 * scale
    c.ring(cx, cy + 34 * scale, R, R - t, color)
    c.ring(cx - 128 * scale, cy - 108 * scale, r, r - t, color)
    c.ring(cx + 128 * scale, cy - 108 * scale, r, r - t, color)


OUT = os.path.dirname(os.path.abspath(__file__)) + '/assets'
os.makedirs(OUT, exist_ok=True)
print('書き出し中...')

# 1. 水分子（カット3・回転させる用）--------------------------------
c = Canvas(560, 560)
molecule(c, 280, 300)
c.render(OUT + '/01_water_molecule.png')

# 2. 分子の衝突（カット4）-------------------------------------------
c = Canvas(900, 460)
molecule(c, 210, 250, 0.66)
molecule(c, 690, 250, 0.66)
c.disc(450, 240, 62, HEAT, 0.85)
c.disc(450, 240, 96, HEAT, 0.30)
for ang in (-90, -35, 35, 90, 145, 215):
    a = math.radians(ang)
    c.bar(450 + 108 * math.cos(a), 240 + 108 * math.sin(a),
          450 + 152 * math.cos(a), 240 + 152 * math.sin(a), 12, HEAT)
c.render(OUT + '/02_collision.png')

# 3. 氷の格子（第2話・分子が固定されている図）------------------------
c = Canvas(900, 620)
for row in range(2):
    for col in range(3):
        molecule(c, 175 + col * 275, 175 + row * 270, 0.44)
for col in range(3):
    x = 175 + col * 275
    c.bar(x, 250, x, 400, 7)
for row in range(2):
    y = 210 + row * 270
    c.bar(120, y, 780, y, 7)
c.render(OUT + '/03_ice_lattice.png')


# 4. 電子レンジの断面（右から波が食べ物に当たる）------------------------
c = Canvas(940, 620)
c.box(60, 90, 880, 540, 13)                       # 本体
c.bar(330, 90, 330, 540, 9)                       # 扉の仕切り
for i in range(9):                                # 扉の網
    c.bar(90 + i*26, 150, 90 + i*26, 480, 4)
c.box(600, 150, 840, 300, 10)                     # マグネトロン
c.wave(590, 350, 380, 34, 3.2, 9)                 # 波が左へ
c.arrow(360, 380, 300, 380, 9, HEAT, 34)
c.ring(200, 400, 74, 60)                          # 食べ物
c.disc(200, 400, 44, HEAT, 0.9)
c.render(OUT + '/04_microwave.png')

# 5. マイクロ波の波形 --------------------------------------------------
c = Canvas(900, 320)
c.wave(40, 860, 160, 96, 4.0, 12)
c.arrow(40, 280, 860, 280, 7, CHALK, 26)
c.render(OUT + '/05_wave.png')

# 6. 電場が反転して分子が向きを変える ----------------------------------
c = Canvas(940, 460)
for k, (cx, flip) in enumerate(((240, 1), (700, -1))):
    c.ring(cx, 250, 74, 62)
    c.ring(cx - 86*flip, 250 - 78, 42, 32)
    c.ring(cx + 86*flip, 250 - 78, 42, 32)
    c.plus(cx - 150*flip, 130, 26, 9, HEAT)
    c.minus(cx + 150*flip, 130, 26, 9, HEAT)
c.arrow(430, 250, 520, 250, 11, HEAT, 40)
c.render(OUT + '/06_flip.png')

# 7. お皿と食べ物の比較（水があるか無いか）------------------------------
c = Canvas(940, 480)
c.ring(240, 250, 150, 136)                        # お皿（水なし）
c.bar(150, 250, 330, 250, 8)
c.ring(700, 250, 150, 136)                        # 食べ物
c.disc(700, 250, 104, HEAT, 0.85)
for a in (-90, -30, 30, 90, 150, 210):
    import math as _m
    r = _m.radians(a)
    c.bar(700 + 168*_m.cos(r), 250 + 168*_m.sin(r),
          700 + 216*_m.cos(r), 250 + 216*_m.sin(r), 12, HEAT)
c.render(OUT + '/07_plate_food.png')

# 8. 食べ物からお皿へ熱が移る ------------------------------------------
c = Canvas(940, 400)
c.ring(700, 200, 118, 104)
c.disc(700, 200, 78, HEAT, 0.85)
c.ring(230, 200, 130, 116)
c.bar(120, 200, 340, 200, 8)
for i, y in enumerate((130, 200, 270)):
    c.arrow(560, y, 380, y, 11, HEAT, 40)
c.render(OUT + '/08_heat_move.png')


# 10・11（翼の図）は mkanim.py が持っている。
# 矢印だけの図は「下に矢印がある」としか読めなかったので、注記の入った
# アニメと同じ形から静止画も書き出すようにした。二重管理をやめるため、
# ここでは呼ぶだけにする。
import mkanim
mkanim.stills()

# 口を開けた絵（クチパク用）
import mklips
mklips.build()

print('完了 → ' + OUT)
