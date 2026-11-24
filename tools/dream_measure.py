"""縦型ショートを ffmpeg だけで測り、時刻付きのコマ一覧（シート画像）を作る。

    python3 tools/dream_measure.py <videos.json> <測定JSONの書き出し先> <シート画像の書き出し先> [id ...]

測るもの
  レイアウト  行ごとの明るさと時間方向の変化から、上部テロップ帯・プレイ画面・黒帯を分ける
  カット      プレイ画面だけを 64x? に落とし、隣のコマとの平均絶対差（MAE）で見る。
              周り（±1秒）の中央値の 3 倍以上、かつ 14 以上で「切り替わり」。
              連続して大きいもの（ズーム・パン・暗転）は1つにまとめ、長さも残す。
  字幕        白文字＋黒フチ（白い画素のすぐ横に黒い画素がある）の画素を「文字」とみなす。
              字幕が一番よく出る帯を自動で探し、そこの文字の形が変わった時刻を拾う。
  上部テロップ テロップ帯が変わった時刻
  音          50ms ごとの音量（dBFS）。中央値より 8dB 以上大きい瞬間を「突出」として拾う。
              最初に音が出る時刻（-45dBFS を超える最初の時刻）も残す。

シート
  intro  0.00〜3.00秒を 0.25秒刻みで13コマ（冒頭フックを見るため）
  tl_N   字幕の切り替わり・カット・最後のコマ（1枚24コマまで）
各コマの左上に秒を書く。
"""
import os, sys, json, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def probe(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                        'stream=width,height,r_frame_rate:format=duration', '-of', 'json', p],
                       capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    s = j['streams'][0]
    a, b = s['r_frame_rate'].split('/')
    return int(s['width']), int(s['height']), float(a) / float(b), float(j['format']['duration'])


def frames(p, w, h, fps):
    """fps で RGB を全部読む（縦型240x426なら 60秒×15fps で 280MB 程度）"""
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-vf', 'fps=%g' % fps,
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True, check=True).stdout
    n = len(raw) // (w * h * 3)
    return np.frombuffer(raw[:n * w * h * 3], np.uint8).reshape(n, h, w, 3)


def audio_db(p, sr=16000, hop=0.05):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', str(sr),
                          '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32)
    k = int(sr * hop)
    n = len(a) // k
    if n == 0:
        return np.array([])
    rms = np.sqrt(np.mean(a[:n * k].reshape(n, k) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-9)


def layout(g):
    """g: (n,h,w) グレー。行ごとに 黒 / 静止(テロップ) / 動く(プレイ画面) を分ける"""
    mean = g.mean(axis=(0, 2))
    std = g.std(axis=0).mean(axis=1)
    h = g.shape[1]
    play = std > max(12.0, np.percentile(std, 60) * 0.5)
    rows = np.where(play)[0]
    if len(rows) == 0:
        return dict(play=[0, h], top=[0, 0], content=[0, h])
    # 一番長く続く「動く行」の塊をプレイ画面とする
    runs, s = [], rows[0]
    for a, b in zip(rows[:-1], rows[1:]):
        if b != a + 1:
            runs.append((s, a + 1)); s = b
    runs.append((s, rows[-1] + 1))
    p0, p1 = max(runs, key=lambda r: r[1] - r[0])
    nonblack = np.where(mean > 12)[0]
    c0 = int(nonblack[0]) if len(nonblack) else 0
    c1 = int(nonblack[-1]) + 1 if len(nonblack) else h
    return dict(play=[int(p0), int(p1)], top=[c0, int(p0)], content=[c0, c1])


def text_mask(rgb):
    """白文字＋黒フチの画素（字幕・テロップの白文字）"""
    g = rgb.astype(np.int16).min(axis=-1)
    white = g > 205
    dark = rgb.astype(np.int16).max(axis=-1) < 60
    d = dark.copy()
    for dy in (-2, -1, 1, 2):
        d |= np.roll(dark, dy, axis=-2)
    for dx in (-2, -1, 1, 2):
        d |= np.roll(dark, dx, axis=-1)
    return white & d


def runs_of(idx, gap):
    out = []
    for i in idx:
        if out and i - out[-1][1] <= gap:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def measure(v, sheet_dir):
    p = v['path']
    w, h, vfps, dur = probe(p)
    FPS = 15.0
    rgb = frames(p, w, h, FPS)
    g = rgb.mean(axis=-1).astype(np.float32)
    lay = layout(g)
    p0, p1 = lay['play']

    # --- カット（プレイ画面だけ）
    small = g[:, p0:p1, :][:, ::4, ::4]
    mae = np.abs(np.diff(small, axis=0)).mean(axis=(1, 2))
    mae = np.concatenate([[0], mae])
    # 明るさの分布（32段）の変化。カメラが速く動いているだけなら分布はあまり変わらない
    def hist(x):
        hh = np.histogram(x, bins=32, range=(0, 256))[0].astype(np.float32)
        return hh / max(hh.sum(), 1)
    hs = [hist(x) for x in small]
    hd = np.concatenate([[0], [0.5 * np.abs(hs[i + 1] - hs[i]).sum() for i in range(len(hs) - 1)]])
    cuts, moves = [], []
    win = int(FPS)
    hits = []
    for i in range(1, len(mae)):
        lo, hi = max(1, i - win), min(len(mae), i + win + 1)
        local = np.median(mae[lo:hi])
        nb = max(mae[i - 1], mae[i + 1] if i + 1 < len(mae) else 0)
        # カメラが速く動く場面では周りの差も大きいので、「周りの中央値の3倍」だけだと本物の切り替わりを落とす。
        # 1コマだけ飛び抜けている（両隣の2倍以上）か、明るさの分布が大きく変わったものも切り替わりとする。
        if mae[i] >= 14 and (mae[i] >= 3 * max(local, 1.0)
                             or (mae[i] >= 2 * nb and mae[i] >= 1.5 * local)
                             or hd[i] >= 0.25):
            hits.append(i)
    for a, b in runs_of(hits, 2):
        t = a / FPS
        if b - a <= 2:
            cuts.append(round(t, 2))
        else:
            moves.append([round(t, 2), round((b + 1) / FPS, 2)])
    shots = [0.0] + cuts + [round(dur, 2)]
    lens = np.diff(shots)

    # --- 字幕（白文字＋黒フチ）の帯と、変わった時刻
    tm = np.stack([text_mask(f[p0:p1]) for f in rgb])        # (n, ph, w)
    rowd = tm.mean(axis=(0, 2))
    band = None
    if rowd.max() > 0.002:
        c = int(np.argmax(np.convolve(rowd, np.ones(24) / 24, mode='same')))
        band = [max(0, c - 18), min(p1 - p0, c + 18)]
    sub_changes, sub_on = [], []
    if band:
        b = tm[:, band[0]:band[1], :]
        on = b.sum(axis=(1, 2)) > 25
        prev = None
        for i in range(len(b)):
            cur = b[i] if on[i] else None
            changed = False
            if (cur is None) != (prev is None):
                changed = True
            elif cur is not None:
                inter = (cur & prev).sum(); uni = (cur | prev).sum()
                changed = uni > 0 and inter / uni < 0.45
            if changed and i > 0:
                sub_changes.append(round(i / FPS, 2))
            prev = cur
        # 細かく揺れるもの（1コマだけの変化）をまとめる
        merged = []
        for t in sub_changes:
            if merged and t - merged[-1] < 0.25:
                continue
            merged.append(t)
        sub_changes = merged
        sub_on = round(float(on.mean()), 2)

    # --- 上部テロップ帯の変化
    t0, t1 = lay['top']
    top_changes = []
    if t1 - t0 > 8:
        tg = g[:, t0:t1, :][:, ::2, ::2]
        d = np.abs(np.diff(tg, axis=0)).mean(axis=(1, 2))
        for a, b in runs_of(list(np.where(d > 10)[0] + 1), 3):
            top_changes.append(round(a / FPS, 2))

    # --- 音
    db = audio_db(p)
    au = {}
    if len(db):
        med = float(np.median(db))
        onset = next((i * 0.05 for i, x in enumerate(db) if x > -45), None)
        peaks = [i for i in range(len(db)) if db[i] > med + 8]
        spikes = [round(a * 0.05, 2) for a, b in runs_of(peaks, 2)]
        au = dict(median_db=round(med, 1), p95_db=round(float(np.percentile(db, 95)), 1),
                  max_db=round(float(db.max()), 1), onset=onset and round(onset, 2),
                  spikes=spikes,
                  first3s_db=[round(float(x), 1) for x in db[:60:4]])

    out = dict(id=v['id'], no=v['no'], w=w, h=h, fps=round(vfps, 2), dur=round(dur, 2),
               layout=lay, cuts=cuts, moves=moves, n_shots=len(lens),
               shot_mean=round(float(lens.mean()), 2), shot_median=round(float(np.median(lens)), 2),
               cuts_first3s=[c for c in cuts if c <= 3], sub_band=band, sub_on_ratio=sub_on,
               sub_changes=sub_changes, n_subs=len(sub_changes), top_changes=top_changes,
               motion_median=round(float(np.median(mae[1:])), 2), audio=au)

    # --- シート
    c0, c1 = lay['content']
    c1 = max(c1, min(h, p1 + 4))
    font = ImageFont.load_default(size=15)

    def tile(t):
        # 秒はコマの上の帯に書く（コマに重ねるとテロップの1文字目が隠れる）
        i = min(len(rgb) - 1, int(round(t * FPS)))
        fr = Image.fromarray(rgb[i][c0:c1])
        im = Image.new('RGB', (fr.width, fr.height + 18), (0, 0, 0))
        im.paste(fr, (0, 18))
        ImageDraw.Draw(im).text((3, 1), '%.2f' % (i / FPS), fill=(255, 255, 0), font=font)
        return im

    def sheet(ts, cols, name):
        tiles = [tile(t) for t in ts]
        tw, th = tiles[0].size
        rows = (len(tiles) + cols - 1) // cols
        S = Image.new('RGB', (cols * (tw + 4), rows * (th + 4)), (40, 40, 40))
        for k, im in enumerate(tiles):
            S.paste(im, ((k % cols) * (tw + 4), (k // cols) * (th + 4)))
        S.save(os.path.join(sheet_dir, name), quality=88)

    sheet([k * 0.25 for k in range(13)], 7, v['id'] + '_intro.jpg')
    ts = sorted(set([round(t + 0.2, 2) for t in sub_changes] + [round(t + 0.1, 2) for t in cuts]))
    keep = []
    for t in ts:
        if t >= dur - 0.05:
            continue
        if keep and t - keep[-1] < 0.5:
            continue
        keep.append(t)
    keep.append(round(dur - 0.1, 2))
    if keep[0] > 0.3:
        keep.insert(0, 0.0)
    # 字幕の検出が外れても見落とさないよう、2.5秒より空いたところは等間隔に足す
    filled = [keep[0]]
    for t in keep[1:]:
        gap = t - filled[-1]
        if gap > 2.5:
            k = int(gap // 2.0)
            filled += [round(filled[-1] + gap * j / (k + 1), 2) for j in range(1, k + 1)]
        filled.append(t)
    keep = filled
    out['sheet_times'] = keep
    for k in range(0, len(keep), 24):
        sheet(keep[k:k + 24], 8, '%s_tl_%d.jpg' % (v['id'], k // 24 + 1))
    out['n_sheets'] = (len(keep) + 23) // 24
    return out


if __name__ == '__main__':
    vids = json.load(open(sys.argv[1]))
    dst, sheets = sys.argv[2], sys.argv[3]
    only = set(sys.argv[4:])
    os.makedirs(dst, exist_ok=True); os.makedirs(sheets, exist_ok=True)
    for v in vids:
        if only and v['id'] not in only:
            continue
        o = measure(v, sheets)
        json.dump(o, open(os.path.join(dst, v['id'] + '.json'), 'w'), ensure_ascii=False, indent=1)
        print(v['no'], v['id'], o['dur'], 'cuts', len(o['cuts']), 'subs', o['n_subs'],
              'sheets', o['n_sheets'], o['layout'], flush=True)
