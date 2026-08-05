#!/usr/bin/env python3
"""
Colab の1セルから呼ばれる、全部入りのパイプライン。

このファイルだけで完結する（cuts.csv も検索ワードも埋め込み済み）。
リポジトリの取得も、フォルダ構成の準備も要らない。

  python3 colab_onecell.py --key <PEXELSキー> --range 10
"""
import argparse, csv, json, os, re, shutil, subprocess, sys, time
import urllib.error, urllib.parse, urllib.request, wave

W, H, FPS = 1080, 1920, 30
NUMCARD_SEC, GAP, GAP_ITEM_END = 1.8, 0.25, 0.60
COLORS = {"red": "#FF2A2A", "yellow": "#FFD400", "": "#FFFFFF"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv"}

CUTS = [
    {'cut': '1', 'telop1': '誰も正体を', 'telop2': '特定できていない音', 'hl': '特定できていない', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A01', 'item_end': '0'},
    {'cut': '2', 'telop1': '記録は残っている', 'telop2': 'だが音源が分からない', 'hl': '音源', 'hl_color': 'yellow', 'camera': 'zoomin', 'asset': 'A02', 'item_end': '0'},
    {'cut': '3', 'telop1': '1.アップスウィープ', 'telop2': '', 'hl': 'ALL', 'hl_color': 'red', 'camera': 'zoomout', 'asset': 'A03', 'item_end': '0'},
    {'cut': '4', 'telop1': '1991年', 'telop2': 'アメリカの観測機関が', 'hl': '1991年', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A04', 'item_end': '0'},
    {'cut': '5', 'telop1': '太平洋の海中で', 'telop2': '奇妙な音を捉えた', 'hl': '奇妙な音', 'hl_color': 'yellow', 'camera': 'pandown', 'asset': 'A05', 'item_end': '0'},
    {'cut': '6', 'telop1': '周波数が', 'telop2': '上昇していく音が', 'hl': '上昇', 'hl_color': 'yellow', 'camera': 'zoomin', 'asset': 'A06', 'item_end': '0'},
    {'cut': '7', 'telop1': '延々と', 'telop2': '繰り返される', 'hl': '延々と', 'hl_color': 'red', 'camera': 'panright', 'asset': 'A06', 'item_end': '0'},
    {'cut': '8', 'telop1': 'アップスウィープと', 'telop2': '名付けられた', 'hl': 'アップスウィープ', 'hl_color': 'yellow', 'camera': 'zoomin', 'asset': 'A07', 'item_end': '0'},
    {'cut': '9', 'telop1': '音源は', 'telop2': '南太平洋の一点', 'hl': '一点', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A08', 'item_end': '0'},
    {'cut': '10', 'telop1': 'そこは陸から', 'telop2': '遠く離れた海域だった', 'hl': '遠く離れた', 'hl_color': 'yellow', 'camera': 'zoomout', 'asset': 'A09', 'item_end': '0'},
    {'cut': '11', 'telop1': 'この音には', 'telop2': '季節変動がある', 'hl': '季節変動', 'hl_color': 'yellow', 'camera': 'panleft', 'asset': 'A03', 'item_end': '0'},
    {'cut': '12', 'telop1': '春と秋に', 'telop2': 'ピークを迎える', 'hl': 'ピーク', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A10', 'item_end': '0'},
    {'cut': '13', 'telop1': '海底火山の活動では', 'telop2': 'ないかとされるが', 'hl': '海底火山', 'hl_color': 'yellow', 'camera': 'zoomin', 'asset': 'A11', 'item_end': '0'},
    {'cut': '14', 'telop1': '音源は', 'telop2': '特定されていない', 'hl': '特定されていない', 'hl_color': 'red', 'camera': 'zoomout', 'asset': 'A08', 'item_end': '0'},
    {'cut': '15', 'telop1': 'そして今も', 'telop2': '鳴り続けている', 'hl': '今も', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A12', 'item_end': '1'},
    {'cut': '16', 'telop1': '2.ザ・ハム', 'telop2': '', 'hl': 'ALL', 'hl_color': 'red', 'camera': 'zoomout', 'asset': 'A13', 'item_end': '0'},
    {'cut': '17', 'telop1': '世界各地で', 'telop2': '同じ報告が上がっている', 'hl': '同じ報告', 'hl_color': 'yellow', 'camera': 'zoomin', 'asset': 'A14', 'item_end': '0'},
    {'cut': '18', 'telop1': '低い唸り声のような', 'telop2': '音が聞こえる', 'hl': '唸り声', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A15', 'item_end': '0'},
    {'cut': '19', 'telop1': 'エンジンが遠くで', 'telop2': '回っているような音', 'hl': 'エンジン', 'hl_color': 'yellow', 'camera': 'panright', 'asset': 'A16', 'item_end': '0'},
    {'cut': '20', 'telop1': 'ハムと', 'telop2': '呼ばれている', 'hl': 'ハム', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A17', 'item_end': '0'},
    {'cut': '21', 'telop1': '1970年代', 'telop2': 'イギリス ブリストル', 'hl': '1970年代', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'S01', 'item_end': '0'},
    {'cut': '22', 'telop1': '1990年代', 'telop2': 'アメリカ タオス', 'hl': '1990年代', 'hl_color': 'red', 'camera': 'panleft', 'asset': 'A18', 'item_end': '0'},
    {'cut': '23', 'telop1': 'タオスでは住民の', 'telop2': 'およそ2%が', 'hl': '2%', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A19', 'item_end': '0'},
    {'cut': '24', 'telop1': 'その音が', 'telop2': '聞こえると答えた', 'hl': '聞こえる', 'hl_color': 'yellow', 'camera': 'zoomin', 'asset': 'A20', 'item_end': '0'},
    {'cut': '25', 'telop1': 'しかし残りの98%には', 'telop2': '聞こえない', 'hl': '98%', 'hl_color': 'red', 'camera': 'zoomout', 'asset': 'A21', 'item_end': '0'},
    {'cut': '26', 'telop1': '工業機械 地殻の振動', 'telop2': '耳鳴り', 'hl': '', 'hl_color': '', 'camera': 'pandown', 'asset': 'A22', 'item_end': '0'},
    {'cut': '27', 'telop1': 'あらゆる説が', 'telop2': '検証されたが', 'hl': '検証', 'hl_color': 'yellow', 'camera': 'zoomin', 'asset': 'A23', 'item_end': '0'},
    {'cut': '28', 'telop1': '発生源はいまだに', 'telop2': '特定されていない', 'hl': '特定されていない', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A13', 'item_end': '1'},
    {'cut': '29', 'telop1': '3.52ヘルツのクジラ', 'telop2': '', 'hl': 'ALL', 'hl_color': 'red', 'camera': 'zoomout', 'asset': 'A01', 'item_end': '0'},
    {'cut': '30', 'telop1': '1989年', 'telop2': '米海軍の探知網が', 'hl': '1989年', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A24', 'item_end': '0'},
    {'cut': '31', 'telop1': '太平洋である', 'telop2': '鳴き声を拾った', 'hl': '鳴き声', 'hl_color': 'yellow', 'camera': 'panright', 'asset': 'A25', 'item_end': '0'},
    {'cut': '32', 'telop1': '52ヘルツ', 'telop2': '', 'hl': 'ALL', 'hl_color': 'red', 'camera': 'still', 'asset': 'A26a', 'item_end': '0'},
    {'cut': '33', 'telop1': 'クジラの声としては', 'telop2': '異常に高い', 'hl': '異常に高い', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A27', 'item_end': '0'},
    {'cut': '34', 'telop1': 'シロナガスクジラは', 'telop2': '10〜39ヘルツ', 'hl': '10〜39', 'hl_color': 'yellow', 'camera': 'panleft', 'asset': 'A28', 'item_end': '0'},
    {'cut': '35', 'telop1': 'この個体だけが', 'telop2': '違う周波数で鳴いていた', 'hl': 'この個体だけ', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A28', 'item_end': '0'},
    {'cut': '36', 'telop1': 'つまり', 'telop2': '仲間には届かない', 'hl': '届かない', 'hl_color': 'red', 'camera': 'zoomout', 'asset': 'A28', 'item_end': '0'},
    {'cut': '37', 'telop1': '研究者は30年以上', 'telop2': '追跡を続けた', 'hl': '30年以上', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A29', 'item_end': '0'},
    {'cut': '38', 'telop1': '回遊経路はどの種とも', 'telop2': '一致しない', 'hl': '一致しない', 'hl_color': 'yellow', 'camera': 'panright', 'asset': 'A30', 'item_end': '0'},
    {'cut': '39', 'telop1': '種の特定も', 'telop2': '姿の確認もできていない', 'hl': 'できていない', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A31', 'item_end': '0'},
    {'cut': '40', 'telop1': '世界で最も', 'telop2': '孤独なクジラ', 'hl': '孤独', 'hl_color': 'red', 'camera': 'zoomout', 'asset': 'A27', 'item_end': '1'},
    {'cut': '41', 'telop1': '3つの音に', 'telop2': '共通するのは', 'hl': '', 'hl_color': '', 'camera': 'zoomin', 'asset': 'A32', 'item_end': '0'},
    {'cut': '42', 'telop1': '記録は', 'telop2': '残っているのに', 'hl': '記録', 'hl_color': 'yellow', 'camera': 'pandown', 'asset': 'A33', 'item_end': '0'},
    {'cut': '43', 'telop1': '音源だけが', 'telop2': '見つかっていない', 'hl': '見つかっていない', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A08', 'item_end': '0'},
    {'cut': '44', 'telop1': '地球はまだ', 'telop2': '静かではない', 'hl': '静かではない', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A34', 'item_end': '0'},
]

SEARCH = {
    1: ['deep ocean light rays underwater', 'abyss dark water'],
    3: ['ocean at night aerial', 'moonlight on sea'],
    8: ['vintage tape reel closeup', 'old cassette label'],
    11: ['ocean timelapse sky', 'sea clouds timelapse'],
    13: ['underwater volcano vent', 'hydrothermal vent'],
    15: ['buoy at night sea', 'ocean buoy dark'],
    16: ['empty street night streetlight', 'suburban street 3am'],
    17: ['world map pins wall', 'map with pushpins dark'],
    18: ['insomnia lying awake bed night'],
    19: ['industrial plant night', 'factory lights distance night'],
    21: ['terraced houses england grey sky', 'bristol street uk'],
    22: ['adobe buildings desert town', 'taos new mexico'],
    23: ['small town night aerial few lights'],
    24: ['hand on ear listening closeup'],
    25: ['crowd walking motion blur one person still'],
    27: ['researcher headphones field equipment night'],
    28: ['empty road night streetlight flicker'],
    29: ['underwater blue ocean sunbeam'],
    30: ['sonar room green screens', 'vintage radar control room'],
    31: ['underwater cable descending deep'],
    33: ['whale silhouette deep blue water'],
    34: ['blue whales swimming together'],
    37: ['desk covered documents notes lamp'],
    42: ['archive shelves tape reels storage'],
}

WORK = os.path.abspath("shorts_work")
VID = os.path.join(WORK, "素材_動画")
IMG = os.path.join(WORK, "素材_画像")
TMP = os.path.join(WORK, "_作業中")


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-1200:])


def ffmpeg_bin():
    if shutil.which("ffmpeg"):
        return shutil.which("ffmpeg")
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def find_font():
    import glob
    for pat in ("/usr/share/fonts/**/NotoSansCJK*Black*",
                "/usr/share/fonts/**/NotoSansCJK*",
                "/usr/share/fonts/**/ipag*"):
        hits = sorted(glob.glob(pat, recursive=True))
        if hits:
            return hits[0]
    return ""


# ── 図版（カット6・7・32）。ナレーションが述べる内容そのものなので用意する ──

def render_figures():
    import numpy as np, matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    from PIL import Image
    rng = np.random.default_rng(7)
    os.makedirs(IMG, exist_ok=True)

    def finish(fig, name, telop_dim, vignette):
        path = os.path.join(IMG, name)
        fig.savefig(path, dpi=100, facecolor="#000000", pad_inches=0)
        plt.close(fig)
        im = np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255
        h, w, _ = im.shape
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.sqrt(((yy - h / 2) / (h / 2)) ** 2 + ((xx - w / 2) / (w / 2)) ** 2)
        im *= (1 - vignette * np.clip(r - .45, 0, None) ** 1.6)[..., None]
        band = np.zeros(h, np.float32)
        band[int(h * .52):int(h * .72)] = 1
        im *= (1 - telop_dim * band)[:, None, None]
        im = np.clip(im + rng.normal(0, .03, im.shape), 0, 1)
        Image.fromarray((im * 255).astype(np.uint8)).save(path)

    # アップスウィープ：20→95Hz のチャープ列を合成して STFT にかける
    fs, dur = 1000.0, 20.0
    t = np.arange(0, dur, 1 / fs)
    x = rng.normal(0, .03, t.size)
    for s in np.arange(1.0, dur - 2.9, 4.6):
        m = (t >= s) & (t < s + 2.9)
        tt = t[m] - s
        x[m] += np.sin(np.pi * tt / 2.9) ** 2 * np.sin(
            2 * np.pi * (20 * tt + .5 * ((95 - 20) / 2.9) * tt ** 2))
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    fig.patch.set_facecolor("#000")
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor("#000")
    ax.specgram(x, NFFT=1024, Fs=fs, noverlap=960, vmin=-42, vmax=14,
                cmap=LinearSegmentedColormap.from_list(
                    "s", ["#000000", "#02160c", "#0b6b3a", "#3fd07a", "#c8f06a", "#ffd98a"]))
    ax.set_ylim(0, 140); ax.axis("off")
    finish(fig, "A06_upsweep.png", .62, .65)

    # 52ヘルツ：孤立した1本のピーク
    f = np.linspace(0, 100, 2400)
    spec = np.abs(.02 + rng.normal(0, .006, f.size)) + np.exp(-((f - 52) ** 2) / .30)
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    fig.patch.set_facecolor("#000")
    ax = fig.add_axes([.08, .08, .84, .36]); ax.set_facecolor("#000")
    pk = (f > 48) & (f < 56)
    for lw, al in ((14, .06), (7, .13), (3, .35), (1.5, 1)):
        ax.plot(f[pk], spec[pk], color="#ff2a2a", lw=lw, alpha=al)
    ax.plot(f, spec, color="#8899aa", lw=.8, alpha=.30, zorder=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_xlim(0, 100); ax.set_ylim(0, 1.25)
    finish(fig, "A26a_52hz.png", .28, .60)


# ── Pexels ──

def pexels(key, cuts_wanted, per_cut=2, min_h=1400):
    os.makedirs(VID, exist_ok=True)
    got, miss = 0, []
    for cut in sorted(SEARCH):
        if cut not in cuts_wanted:
            continue
        if [f for f in os.listdir(VID) if f.startswith("cut%02d_" % cut)]:
            continue
        picked, seen = [], set()
        for term in SEARCH[cut]:
            if len(picked) >= per_cut:
                break
            url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode(
                {"query": term, "orientation": "portrait", "per_page": 15, "size": "medium"})
            req = urllib.request.Request(url, headers={"Authorization": key})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    vids = json.loads(r.read()).get("videos", [])
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    sys.exit("Pexelsのキーが違うようです。もう一度確認してください。")
                if e.code == 429:
                    time.sleep(20); continue
                print("   カット%-2d  検索に失敗（%s）" % (cut, e.code)); continue
            except Exception as e:
                print("   カット%-2d  つながりません（%s）" % (cut, type(e).__name__)); continue
            for v in vids:
                if len(picked) >= per_cut or v["id"] in seen:
                    continue
                seen.add(v["id"])
                cands = [g for g in v.get("video_files", [])
                         if g.get("height") and g.get("width")
                         and g["height"] > g["width"] and g["height"] >= min_h]
                if cands:
                    picked.append(max(cands, key=lambda g: g["height"]))
            time.sleep(.5)
        if not picked:
            miss.append(cut); continue
        for i, vf in enumerate(picked, 1):
            path = os.path.join(VID, "cut%02d_%d_%dx%d.mp4" % (cut, i, vf["width"], vf["height"]))
            try:
                rq = urllib.request.Request(vf["link"], headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(rq, timeout=600) as r, open(path, "wb") as fh:
                    shutil.copyfileobj(r, fh)
                got += 1
                print("   カット%-2d  取得" % cut)
            except Exception:
                if os.path.exists(path):
                    os.remove(path)
    return got, miss


# ── テロップ ──

def telop(row, font, out):
    from PIL import Image, ImageDraw, ImageFont
    numcard = row["hl"] == "ALL"
    size = 84 if numcard else 72
    fnt = ImageFont.truetype(font, size)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def split(line):
        if numcard:
            return [(line, COLORS["red"])]
        hl = row["hl"]
        if hl and hl in line:
            i = line.index(hl)
            segs = []
            if line[:i]:
                segs.append((line[:i], "#FFFFFF"))
            segs.append((hl, COLORS.get(row["hl_color"], "#FFFFFF")))
            if line[i + len(hl):]:
                segs.append((line[i + len(hl):], "#FFFFFF"))
            return segs
        return [(line, "#FFFFFF")]

    lines = [l for l in (row["telop1"], row["telop2"]) if l]
    lh = int(size * 1.28)
    y = int(H * .58) - (len(lines) - 1) * lh // 2
    for line in lines:
        segs = split(line)
        x = (W - sum(d.textlength(t, font=fnt) for t, _ in segs)) / 2
        for txt, col in segs:
            d.text((x, y), txt, font=fnt, fill=col,
                   stroke_width=6 if col != "#FFFFFF" else 5, stroke_fill="black")
            x += d.textlength(txt, font=fnt)
        y += lh
    im.save(out)


def camera(kind, n):
    n = max(n, 2)
    if kind == "zoomout":
        z, x, y = "max(1.08-%f*on,1.0)" % (.08 / n), "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif kind == "panleft":
        z, x, y = "1.06", "(iw-iw/zoom)*(1-on/%d)" % n, "ih/2-(ih/zoom/2)"
    elif kind == "panright":
        z, x, y = "1.06", "(iw-iw/zoom)*(on/%d)" % n, "ih/2-(ih/zoom/2)"
    elif kind == "pandown":
        z, x, y = "1.06", "iw/2-(iw/zoom/2)", "(ih-ih/zoom)*(on/%d)" % n
    elif kind == "still":
        z, x, y = "1.0", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    else:
        z, x, y = "min(1.0+%f*on,1.08)" % (.08 / n), "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    return ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
            "zoompan=z='%s':d=%d:x='%s':y='%s':s=%dx%d:fps=%d"
            % (W * 2, H * 2, W * 2, H * 2, z, n, x, y, W, H, FPS))


def find_asset(row, cut):
    for d in (IMG, VID):
        if not os.path.isdir(d):
            continue
        hits = sorted(os.path.join(d, f) for f in os.listdir(d)
                      if f.startswith(row["asset"][:3]) or f.startswith("cut%02d_" % cut))
        hits = [h for h in hits if os.path.splitext(h)[1].lower() in VIDEO_EXT | {".png", ".jpg", ".jpeg"}]
        if hits:
            ok = [h for h in hits if "_ok" in os.path.basename(h)]
            return (ok or hits)[0]
    return None


ASSET_ALIAS = {"6": "A06", "7": "A06", "32": "A26"}


def build(font, only_n, out):
    FF = ffmpeg_bin()
    os.makedirs(TMP, exist_ok=True)
    segs = []
    for row in CUTS:
        cut = int(row["cut"])
        if only_n and cut > only_n:
            break
        r = dict(row)
        if row["cut"] in ASSET_ALIAS:
            r["asset"] = ASSET_ALIAS[row["cut"]]
        asset = find_asset(r, cut)
        if asset is None:
            continue
        dur = (NUMCARD_SEC if r["hl"] == "ALL" else 2.2)
        dur += GAP_ITEM_END if r["item_end"] == "1" else GAP
        tp = os.path.join(TMP, "t%02d.png" % cut)
        seg = os.path.join(TMP, "s%02d.mp4" % cut)
        telop(r, font, tp)
        frames = int(round(dur * FPS))
        args = [FF, "-hide_banner", "-loglevel", "error", "-y"]
        if os.path.splitext(asset)[1].lower() in VIDEO_EXT:
            args += ["-stream_loop", "-1", "-i", asset]
            vf = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,fps=%d"
                  % (W, H, W, H, FPS))
        else:
            args += ["-loop", "1", "-i", asset]
            vf = camera(r["camera"], frames)
        args += ["-i", tp, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                 "-filter_complex",
                 "[0:v]%s[bg];[bg][1:v]overlay=0:0:format=auto[v]" % vf,
                 "-map", "[v]", "-map", "2:a", "-t", "%.3f" % dur, "-r", str(FPS),
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                 "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                 "-ar", "44100", "-ac", "2", seg]
        sh(args)
        segs.append(seg)
        print("   カット%-2d  %s" % (cut, os.path.basename(asset)[:38]))
    if not segs:
        sys.exit("素材が1つも無いので作れませんでした。")
    lst = os.path.join(TMP, "list.txt")
    with open(lst, "w") as f:
        for s in segs:
            f.write("file '%s'\n" % s)
    sh([FF, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])
    return len(segs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--range", type=int, default=0, help="0なら全部")
    ap.add_argument("--out", default="動画.mp4")
    a = ap.parse_args()

    os.makedirs(WORK, exist_ok=True)
    only = a.range or None
    wanted = {c for c in SEARCH if not only or c <= only}

    print("1/3  図版をつくる")
    render_figures()

    print("2/3  Pexelsから映像を落とす（%dカット）" % len(wanted))
    got, miss = pexels(a.key, wanted)
    print("     %d本 取得" % got)
    if miss:
        print("     見つからなかったカット: %s" % ", ".join(map(str, miss)))

    font = find_font()
    if not font:
        sys.exit("日本語フォントが見つかりません。")

    print("3/3  動画を組み立てる")
    n = build(font, only, a.out)
    print("\n完成： %s（%dカット）" % (a.out, n))


if __name__ == "__main__":
    main()
