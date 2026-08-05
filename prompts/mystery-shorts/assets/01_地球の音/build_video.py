#!/usr/bin/env python3
"""
cuts.csv・素材・ナレーションから、動画を丸ごと組み立てる。

【要点】カットの長さはナレーション音声の実測値から決まる。
台本の秒数は目安でしかない。実際のTTS出力に合わせて自動で尺が決まるので、
編集ソフトで44箇所の切れ目を耳で探す作業が丸ごと消える。

各カットでやること：
  素材を 1080x1920 に整える → ゆっくりズーム/パン → テロップを合成
  → ナレーション音声を貼り、末尾に無音を足す
最後に全カットを連結し、BGMがあれば敷いて書き出す。

準備：
  音声/cutNN.wav        voicevox_tts.py で生成
  素材_画像/ 素材_動画/  素材（ファイル名に素材IDかcutNNを含めておく）

候補が複数あるカットは、採用したいファイル名に _ok を足すとそれが選ばれる。

使い方：
  python3 build_video.py --check              # 素材が揃っているか確認
  python3 build_video.py --only 1-10          # 一部だけ試作
  python3 build_video.py                      # 全部
  python3 build_video.py --bgm bgm.mp3 --bgm-db -24

テロップのフォントは --font で指定する。太いゴシックを推奨。
"""

import argparse
import csv
import os
import shutil
import subprocess
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
CUTS = os.path.join(HERE, "cuts.csv")
NARR = os.path.join(HERE, "音声")
WORK = os.path.join(HERE, "_作業中")
ASSET_DIRS = [os.path.join(HERE, "素材_画像"), os.path.join(HERE, "素材_動画")]

W, H = 1080, 1920
FPS = 30
NUMCARD_SEC = 1.8      # ナンバーカードの尺
GAP = 0.25             # カット間の無音
GAP_ITEM_END = 0.60    # 項目の切れ目はもう少し空ける

COLORS = {"red": "#FF2A2A", "yellow": "#FFD400", "": "#FFFFFF"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def ffmpeg_bin():
    for cand in ("ffmpeg", shutil.which("ffmpeg")):
        if cand and shutil.which(cand):
            return shutil.which(cand)
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:                                           # noqa: BLE001
        sys.exit("ffmpeg が見つかりません。インストールするか "
                 "pip install imageio-ffmpeg してください。")


FF = ffmpeg_bin()


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-1500:])
    return p


def read_cuts():
    with open(CUTS, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def find_asset(asset_id, cut):
    """素材IDか cutNN を含むファイルを探す。見つからなければ None。

    候補が複数あるときは、ファイル名に _ok が入っているものを優先する。
    Pexels は1カットに2本落とすので、良いほうの名前に _ok を足せば
    そちらが採用される（ドライブアプリ上で名前を変えるだけでよい）。
    """
    for d in ASSET_DIRS:
        if not os.path.isdir(d):
            continue
        hits = []
        for fn in sorted(os.listdir(d)):
            ext = os.path.splitext(fn)[1].lower()
            if ext not in VIDEO_EXT | IMAGE_EXT:
                continue
            if fn.startswith(asset_id) or fn.startswith(f"cut{cut:02d}_"):
                hits.append(os.path.join(d, fn))
        if hits:
            picked = [h for h in hits if "_ok" in os.path.basename(h)]
            return (picked or hits)[0]
    return None


def wav_seconds(path):
    with wave.open(path, "rb") as w:
        return w.getnframes() / w.getframerate()


# ── テロップ ──────────────────────────────────────────────────────

def render_telop(row, font_path, out_path):
    from PIL import Image, ImageDraw, ImageFont

    l1, l2 = row["telop1"], row["telop2"]
    hl, color_name = row["hl"], row["hl_color"]
    is_numcard = hl == "ALL"

    size = 84 if is_numcard else 72
    font = ImageFont.truetype(font_path, size)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def split(line):
        """強調語だけ色を変えるため、行を (文字列, 色) に分解する。"""
        if is_numcard:
            return [(line, COLORS["red"])]
        if hl and hl in line:
            i = line.index(hl)
            out = []
            if line[:i]:
                out.append((line[:i], "#FFFFFF"))
            out.append((hl, COLORS.get(color_name, "#FFFFFF")))
            if line[i + len(hl):]:
                out.append((line[i + len(hl):], "#FFFFFF"))
            return out
        return [(line, "#FFFFFF")]

    lines = [l for l in (l1, l2) if l]
    line_h = int(size * 1.28)
    y = int(H * 0.58) - (len(lines) - 1) * line_h // 2

    for line in lines:
        segs = split(line)
        total = sum(d.textlength(t, font=font) for t, _ in segs)
        x = (W - total) / 2
        for text, col in segs:
            d.text((x, y), text, font=font, fill=col,
                   stroke_width=6 if col != "#FFFFFF" else 5, stroke_fill="black")
            x += d.textlength(text, font=font)
        y += line_h

    img.save(out_path)


# ── カメラワーク ──────────────────────────────────────────────────

def camera_filter(camera, frames):
    """静止画にかけるゆっくりした動き。素材を2倍に拡大してから切り出す。"""
    n = max(frames, 2)
    if camera == "zoomout":
        z = f"max(1.08-{0.08 / n:.6f}*on,1.0)"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif camera == "panleft":
        z, x, y = "1.06", f"(iw-iw/zoom)*(1-on/{n})", "ih/2-(ih/zoom/2)"
    elif camera == "panright":
        z, x, y = "1.06", f"(iw-iw/zoom)*(on/{n})", "ih/2-(ih/zoom/2)"
    elif camera == "pandown":
        z, x, y = "1.06", "iw/2-(iw/zoom/2)", f"(ih-ih/zoom)*(on/{n})"
    elif camera == "still":
        z, x, y = "1.0", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    else:                                     # zoomin（既定）
        z = f"min(1.0+{0.08 / n:.6f}*on,1.08)"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    return (f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,"
            f"crop={W * 2}:{H * 2},"
            f"zoompan=z='{z}':d={n}:x='{x}':y='{y}':s={W}x{H}:fps={FPS}")


# ── 1カットを作る ─────────────────────────────────────────────────

def build_cut(row, dur, asset, telop_png, out_mp4, wav):
    frames = int(round(dur * FPS))
    is_video = os.path.splitext(asset)[1].lower() in VIDEO_EXT

    args = [FF, "-hide_banner", "-loglevel", "error", "-y"]
    if is_video:
        # 実写素材は既に動いているのでズームはかけない。足りなければループ
        args += ["-stream_loop", "-1", "-i", asset]
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
              f"crop={W}:{H},fps={FPS}")
    else:
        args += ["-loop", "1", "-i", asset]
        vf = camera_filter(row["camera"], frames)

    args += ["-i", telop_png]
    if wav:
        args += ["-i", wav]
        amap = "[2:a]apad[a]"
    else:
        args += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        amap = "[2:a]anull[a]"

    args += ["-filter_complex",
             f"[0:v]{vf}[bg];[bg][1:v]overlay=0:0:format=auto[v];{amap}",
             "-map", "[v]", "-map", "[a]",
             "-t", f"{dur:.3f}",
             "-r", str(FPS),
             "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
             out_mp4]
    run(args)


# ── 本体 ──────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", default="/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
                    help="テロップのフォント。太いゴシック推奨")
    ap.add_argument("--only", default="", help="カット範囲。例 1-10 や 3,7,12")
    ap.add_argument("--bgm", default="", help="BGMファイル")
    ap.add_argument("--bgm-db", type=float, default=-24.0, help="BGMの音量(dB)")
    ap.add_argument("--out", default=os.path.join(HERE, "完成", "地球の音.mp4"))
    ap.add_argument("--check", action="store_true", help="素材の過不足を確認して終了")
    a = ap.parse_args()

    rows = read_cuts()

    if a.only:
        want = set()
        for part in a.only.split(","):
            if "-" in part:
                s, e = part.split("-")
                want |= set(range(int(s), int(e) + 1))
            elif part.strip():
                want.add(int(part))
        rows = [r for r in rows if int(r["cut"]) in want]

    # 素材とナレーションの棚卸し
    plan, missing_asset, missing_wav = [], [], []
    for r in rows:
        cut = int(r["cut"])
        asset = find_asset(r["asset"], cut)
        wav = os.path.join(NARR, f"cut{cut:02d}.wav")
        wav = wav if os.path.exists(wav) else None
        is_numcard = r["hl"] == "ALL"

        if asset is None:
            missing_asset.append((cut, r["asset"]))
        if wav is None and not is_numcard:
            missing_wav.append(cut)

        dur = (NUMCARD_SEC if is_numcard
               else (wav_seconds(wav) if wav else 2.2))
        dur += GAP_ITEM_END if r.get("item_end") == "1" else GAP
        plan.append((r, cut, asset, wav, dur))

    total = sum(p[4] for p in plan)
    print(f"カット {len(plan)} / 推定尺 {total:.1f}秒")
    if missing_asset:
        print(f"\n素材が無いカット {len(missing_asset)}件:")
        for cut, aid in missing_asset:
            print(f"  cut{cut:02d}  {aid}")
    if missing_wav:
        print(f"\nナレーションが無いカット: {', '.join(f'{c:02d}' for c in missing_wav)}")

    if a.check:
        return
    if missing_asset:
        sys.exit("\n素材が足りません。--check で確認して埋めてください。")
    if not os.path.exists(a.font):
        sys.exit(f"フォントが見つかりません: {a.font}\n--font で指定してください。")

    os.makedirs(WORK, exist_ok=True)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    segments = []

    for r, cut, asset, wav, dur in plan:
        telop = os.path.join(WORK, f"telop{cut:02d}.png")
        seg = os.path.join(WORK, f"seg{cut:02d}.mp4")
        render_telop(r, a.font, telop)
        try:
            build_cut(r, dur, asset, telop, seg, wav)
            segments.append(seg)
            print(f"  cut{cut:02d}  {dur:5.2f}秒  {os.path.basename(asset)[:40]}")
        except Exception as e:                                  # noqa: BLE001
            sys.exit(f"cut{cut:02d} で失敗:\n{e}")

    # 連結
    listfile = os.path.join(WORK, "concat.txt")
    with open(listfile, "w", encoding="utf-8") as f:
        for s in segments:
            f.write(f"file '{s}'\n")

    joined = os.path.join(WORK, "joined.mp4")
    run([FF, "-hide_banner", "-loglevel", "error", "-y",
         "-f", "concat", "-safe", "0", "-i", listfile, "-c", "copy", joined])

    if a.bgm and os.path.exists(a.bgm):
        run([FF, "-hide_banner", "-loglevel", "error", "-y",
             "-i", joined, "-stream_loop", "-1", "-i", a.bgm,
             "-filter_complex",
             f"[1:a]volume={a.bgm_db}dB[b];[0:a][b]amix=inputs=2:duration=first:"
             f"dropout_transition=0,alimiter=limit=0.95[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "192k", a.out])
    else:
        shutil.copy(joined, a.out)
        if a.bgm:
            print(f"\nBGMが見つかりません: {a.bgm}（BGM無しで書き出しました）")

    print(f"\n完成 → {a.out}")
    print(f"作業ファイルは {WORK} に残してあります（不要なら削除可）")


if __name__ == "__main__":
    main()
