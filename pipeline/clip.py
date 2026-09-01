"""SMPクリップの型で切り抜きを焼く。

    python3 pipeline/clip.py <台本モジュール>

字幕を透明PNGに描いて、ffmpeg で元映像に重ねるだけ。
カワウソ（第12話まで）は1コマずつPILで描いていたが、切り抜きは
元映像が主役なので、文字だけ作って乗せる。SMPクリップ本人も同じ作り。
"""
import os, subprocess, sys, importlib
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FF = '/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
if not os.path.exists(FF):
    FF = 'ffmpeg'
FONT = '/usr/share/fonts/opentype/mplus/Mplus2-ExtraBold.otf'

# SMPクリップの4色。実測した色みに寄せてある
# 実ファイル5本から読み直した割り当て（docs/smp_real.md）。
# 色は「役割」ではなく「人」に固定する。人が増えたら色を足す。
COLORS = {
    'w': (255, 255, 255),   # ナレーション（編集者の地の文）
    'c': (95, 224, 255),    # ドクタードーナツ本人のセリフ
    'o': (255, 140, 26),    # 2人目の登場人物
    'r': (255, 59, 48),     # 実況の見出し（*〜* で囲む。音も指す）
    'y': (255, 214, 10),    # 固定タイトル
}

# タイトルは画面の上9%まで。3本とも顔の上の余白が9.2〜11.6%しかない
TITLE_TOP, TITLE_BOT = 8, 173
SUB_CENTER_Y = 1355          # 本家の字幕帯は画面の63〜77%。その真ん中
PAD_X = 48                   # 左右の余白


def fit(text, max_w, max_h, start=96, min_size=28, line_gap=1.14):
    """入る一番大きい字の大きさと、折り返した行を返す。"""
    for size in range(start, min_size - 1, -2):
        f = ImageFont.truetype(FONT, size)
        lines, cur = [], ''
        for ch in text:
            if ch == '\n':
                lines.append(cur); cur = ''; continue
            t = cur + ch
            if f.getbbox(t)[2] - f.getbbox(t)[0] <= max_w:
                cur = t
            else:
                lines.append(cur); cur = ch
        if cur:
            lines.append(cur)
        if len(lines) * size * line_gap <= max_h:
            return f, lines, size
    f = ImageFont.truetype(FONT, min_size)
    return f, [text], min_size


def draw_block(text, color, max_w, max_h, stroke_ratio=0.14, start=96):
    """太い黒フチ付きの文字を、透明な板に中央寄せで描く。"""
    f, lines, size = fit(text, max_w, max_h, start=start)
    stroke = max(6, int(size * stroke_ratio))
    gap = int(size * 1.14)
    pad = stroke * 2 + 8
    img = Image.new('RGBA', (max_w + pad * 2, gap * len(lines) + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        d.text((img.width // 2, pad + gap * i + gap // 2), ln, font=f, fill=color + (255,),
               anchor='mm', stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
    return img.crop(img.getbbox())


def build(spec, workdir):
    os.makedirs(workdir, exist_ok=True)
    plates = []

    # 全編ずっと出しっぱなしのタイトル。SMPクリップはこれを維持率の錨にしている
    t = draw_block(spec['title'], COLORS['y'], W - PAD_X * 2,
                   TITLE_BOT - TITLE_TOP, start=84)
    p = os.path.join(workdir, 'title.png'); t.save(p)
    plates.append((p, (W - t.width) // 2,
                   TITLE_TOP + (TITLE_BOT - TITLE_TOP - t.height) // 2, None, None))

    for i, (a, b, col, text) in enumerate(spec['subs']):
        im = draw_block(text, COLORS[col], W - PAD_X * 2, 320, start=88)
        p = os.path.join(workdir, f's{i:02d}.png'); im.save(p)
        plates.append((p, (W - im.width) // 2, SUB_CENTER_Y - im.height // 2, a, b))
    return plates


def render(spec, workdir):
    plates = build(spec, workdir)
    cmd = [FF, '-v', 'error', '-stats', '-y', '-i', spec['src']]
    for p, *_ in plates:
        cmd += ['-i', p]

    # 元素材は 480x854（縦横比0.5621）。1080x1920 は 0.5625 なので
    # 0.08% 伸びるだけ。切らずにそのまま入れる
    chain = [f"[0:v]scale={W}:{H},setsar=1[v0]"]
    last = 'v0'
    for i, (_, x, y, a, b) in enumerate(plates):
        tag = f'v{i+1}'
        en = '' if a is None else f":enable='between(t,{a},{b})'"
        chain.append(f"[{last}][{i+1}:v]overlay={x}:{y}{en}[{tag}]")
        last = tag
    fc = ';'.join(chain)

    # 音は圧縮しない。切り抜きは跳ねてナンボで、潰すと山が消える（第12話の失敗）
    cmd += ['-filter_complex', fc, '-map', f'[{last}]', '-map', '0:a?',
            '-af', 'loudnorm=I=-14:TP=-1.0:LRA=20',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
            '-pix_fmt', 'yuv420p', '-r', '30', '-c:a', 'aac', '-b:a', '192k',
            spec['out']]
    subprocess.run(cmd, check=True)
    return spec['out']


if __name__ == '__main__':
    mod = importlib.import_module(sys.argv[1].replace('/', '.').replace('.py', ''))
    out = render(mod.SPEC, sys.argv[2] if len(sys.argv) > 2 else '/tmp/clipwork')
    print('\n' + out)
