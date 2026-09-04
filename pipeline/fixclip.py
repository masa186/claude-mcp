"""出来上がった切り抜きの体裁を直す。

    python3 pipeline/fixclip.py <元> <出力> "<画面タイトル>" <上端%> <下端%>

字幕はそのまま残す。触るのは
  ・上下の死んだ黒帯と、消し忘れた英語テロップ
  ・無料編集ソフトの透かし
  ・音量
  ・寸法とコマ数
だけ。SMPクリップの帯割り（上タイトル / 本編 / 下の黒帯）に組み直す。
"""
import subprocess, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clip import draw_block, COLORS, FF, W, H, PAD_X, TITLE_TOP, TITLE_BOT

def fix(src, out, title, top_pct, bot_pct, patch=None, work='/tmp/fixwork'):
    """patch=(x%, y%, w%, h%) を渡すと、その矩形を黒で塗り潰す。
    消し忘れた英語テロップが顔カメラと縦に重なっていて、
    切り落とすと頭が欠けるときに使う。"""
    os.makedirs(work, exist_ok=True)
    keep = bot_pct - top_pct                      # 残す高さの割合
    band_h = int(H * keep)                        # 1080 幅に直したときの高さ
    y0 = (H - band_h) * 55 // 100                 # 上のタイトル帯を少し広く取る

    t = draw_block(title, COLORS['y'], W - PAD_X * 2, TITLE_BOT - TITLE_TOP, start=84)
    tp = os.path.join(work, 'title.png'); t.save(tp)

    box = ''
    if patch:
        px, py, pw, ph = patch
        box = (f",drawbox=x={int(W*px)}:y={int(band_h*py)}"
               f":w={int(W*pw)}:h={int(band_h*ph)}:color=black@1:t=fill")
    vf = (f"crop=iw:ih*{keep}:0:ih*{top_pct},scale={W}:{band_h},setsar=1{box},"
          f"pad={W}:{H}:0:{y0}:black")
    fc = f"[0:v]{vf}[bg];[bg][1:v]overlay={(W - t.width)//2}:"\
         f"{TITLE_TOP + (TITLE_BOT - TITLE_TOP - t.height)//2}[v]"
    cmd = [FF, '-v', 'error', '-stats', '-y', '-i', src, '-i', tp,
           '-filter_complex', fc, '-map', '[v]', '-map', '0:a?',
           # 音は圧縮せずレンジを残したまま -14 まで上げる
           '-af', 'loudnorm=I=-14:TP=-1.0:LRA=20',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '19',
           '-pix_fmt', 'yuv420p', '-r', '30', '-c:a', 'aac', '-b:a', '192k', out]
    subprocess.run(cmd, check=True)
    return out

if __name__ == '__main__':
    pt = None
    if len(sys.argv) > 6:
        pt = tuple(float(v) for v in sys.argv[6].split(','))
    print('\n' + fix(sys.argv[1], sys.argv[2], sys.argv[3],
                     float(sys.argv[4]), float(sys.argv[5]), pt))
