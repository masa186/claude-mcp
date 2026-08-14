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

    def _cov(self, s, x, y):
        kind = s[0]
        if kind == 'ring':
            _, cx, cy, ro, ri, _ = s
            d = math.hypot(x - cx, y - cy)
            return 1.0 if ri <= d <= ro else 0.0
        if kind == 'disc':
            _, cx, cy, r, a, _ = s
            return a if math.hypot(x - cx, y - cy) <= r else 0.0
        _, x1, y1, x2, y2, hw, _ = s
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
        return 1.0 if math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)) <= hw else 0.0

    def render(self, path):
        SS = [0.17, 0.5, 0.83]
        n = len(SS) ** 2
        for y in range(self.h):
            for x in range(self.w):
                acc_r = acc_g = acc_b = acc_a = 0.0
                for s in self.shapes:
                    c = 0.0
                    for oy in SS:
                        for ox in SS:
                            c += self._cov(s, x + ox, y + oy)
                    c /= n
                    if c <= 0:
                        continue
                    col = s[-1]
                    # source-over
                    acc_r = col[0] * c + acc_r * (1 - c)
                    acc_g = col[1] * c + acc_g * (1 - c)
                    acc_b = col[2] * c + acc_b * (1 - c)
                    acc_a = c + acc_a * (1 - c)
                if acc_a > 0:
                    i = (y * self.w + x) * 4
                    self.buf[i]     = int(acc_r + 0.5)
                    self.buf[i + 1] = int(acc_g + 0.5)
                    self.buf[i + 2] = int(acc_b + 0.5)
                    self.buf[i + 3] = int(acc_a * 255 + 0.5)
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

print('完了 → ' + OUT)
