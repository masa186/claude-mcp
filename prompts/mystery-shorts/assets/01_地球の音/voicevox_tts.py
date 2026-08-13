#!/usr/bin/env python3
"""
VOICEVOX のローカルAPIを叩いて、41カット分のナレーションを一括生成する。

web版で41回コピペする必要はない。VOICEVOX のデスクトップ版（無料）を起動しておくと
localhost:50021 にREST APIが立つので、そこへ投げれば全部自動で終わる。

準備：
  1. VOICEVOX デスクトップ版を起動しておく（起動していれば勝手にAPIが立つ）
  2. python3 voicevox_tts.py --list-speakers  で話者IDを調べる
  3. python3 voicevox_tts.py --speaker <ID>

使い方：
  # 話者一覧（青山龍星のIDを確認する）
  python3 voicevox_tts.py --list-speakers

  # まず1本だけ作って話速を合わせる（9行目＝カット10、目標2.3秒）
  python3 voicevox_tts.py --speaker 13 --only 10

  # 本番。41本を cutNN.wav で書き出す
  python3 voicevox_tts.py --speaker 13 --speed 1.10

  # 読み間違いを直したカットだけ作り直す
  python3 voicevox_tts.py --speaker 13 --speed 1.10 --only 18,30 --force

出力：
  音声/ に cut01.wav 〜 cut44.wav（3・16・29はナンバーカードなので欠番）
  最後に各カットの長さと合計尺を表示する。目標86秒からズレていたら --speed を調整して再実行。
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
TEXT_FILE = os.path.join(HERE, "ナレーション原稿.txt")
HOST = os.environ.get("VOICEVOX_HOST", "http://127.0.0.1:50021")
OUTDIR = os.path.join(HERE, "音声")
os.makedirs(OUTDIR, exist_ok=True)

# ナンバーカードなので音声なし。行番号→カット番号の対応もこれで決まる
SILENT_CUTS = {3, 16, 29}
TARGET_TOTAL = 86.0     # 目標の合計尺（秒）


def line_to_cut():
    """テキストの行番号（1始まり）→ カット番号 の対応を作る。"""
    mapping, line = {}, 1
    for cut in range(1, 45):
        if cut in SILENT_CUTS:
            continue
        mapping[line] = cut
        line += 1
    return mapping


def api(path, data=None, params=None, timeout=120):
    url = f"{HOST}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, data=data, method="POST" if data is not None else "GET",
        headers={"Content-Type": "application/json"} if data is not None else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def check_engine():
    try:
        api("/version", timeout=8)
    except urllib.error.URLError:
        sys.exit(f"VOICEVOX に接続できません（{HOST}）\n"
                 "デスクトップ版を起動してから、もう一度実行してください。\n"
                 "別ポートの場合は VOICEVOX_HOST=http://127.0.0.1:ポート を設定。")


def list_speakers():
    check_engine()
    for sp in json.loads(api("/speakers")):
        print(f"\n{sp['name']}")
        for st in sp["styles"]:
            print(f"    ID {st['id']:>3}   {st['name']}")


def synth(text, speaker, speed, pitch, intonation):
    """audio_query でパラメータを作り、値を差し替えてから synthesis する。"""
    q = json.loads(api("/audio_query", data=b"", params={"text": text, "speaker": speaker}))
    q["speedScale"] = speed
    q["pitchScale"] = pitch
    q["intonationScale"] = intonation
    q["prePhonemeLength"] = 0.05      # 前後の余白は詰める。間は編集側で作る
    q["postPhonemeLength"] = 0.05
    return api("/synthesis", data=json.dumps(q).encode(),
               params={"speaker": speaker}, timeout=300)


def wav_seconds(path):
    with wave.open(path, "rb") as w:
        return w.getnframes() / w.getframerate()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-speakers", action="store_true")
    ap.add_argument("--speaker", type=int, help="話者ID（--list-speakers で確認）")
    ap.add_argument("--speed", type=float, default=1.10, help="話速（既定1.10）")
    ap.add_argument("--pitch", type=float, default=-0.02, help="音高。低いほど重い")
    ap.add_argument("--intonation", type=float, default=0.90,
                    help="抑揚。淡々とさせるので既定は0.90")
    ap.add_argument("--only", default="", help="カット番号をカンマ区切りで指定")
    ap.add_argument("--force", action="store_true", help="既存ファイルを上書き")
    a = ap.parse_args()

    if a.list_speakers:
        list_speakers()
        return
    if a.speaker is None:
        sys.exit("--speaker が必要です。--list-speakers でIDを確認してください。")

    check_engine()

    lines = [ln.rstrip("\n") for ln in open(TEXT_FILE, encoding="utf-8") if ln.strip()]
    mapping = line_to_cut()
    if len(lines) != len(mapping):
        sys.exit(f"行数が合いません：テキスト{len(lines)}行 / 想定{len(mapping)}行")

    want = {int(s) for s in a.only.split(",") if s.strip().isdigit()} if a.only else None

    print(f"話者ID {a.speaker} / 話速 {a.speed} / 音高 {a.pitch} / 抑揚 {a.intonation}\n")
    durations, made = {}, 0

    for idx, text in enumerate(lines, 1):
        cut = mapping[idx]
        if want and cut not in want:
            continue
        path = os.path.join(OUTDIR, f"cut{cut:02d}.wav")

        if os.path.exists(path) and not a.force:
            durations[cut] = wav_seconds(path)
            print(f"  cut{cut:02d}  skip（既存 {durations[cut]:.2f}秒）")
            continue

        try:
            open(path, "wb").write(synth(text, a.speaker, a.speed, a.pitch, a.intonation))
            durations[cut] = wav_seconds(path)
            made += 1
            print(f"  cut{cut:02d}  {durations[cut]:5.2f}秒  {text[:22]}")
        except Exception as e:                                  # noqa: BLE001
            print(f"  cut{cut:02d}  失敗 {type(e).__name__}: {e}")

    # 既存分も含めて合計を出す
    for cut in mapping.values():
        p = os.path.join(OUTDIR, f"cut{cut:02d}.wav")
        if cut not in durations and os.path.exists(p):
            durations[cut] = wav_seconds(p)

    speech = sum(durations.values())
    # ナンバーカード3枚(各1.8秒) + カット間の無音(0.25秒 × カット数)
    est = speech + len(SILENT_CUTS) * 1.8 + len(durations) * 0.25

    print(f"\n生成 {made}本 / 音声のあるカット {len(durations)}本")
    print(f"発話の合計       {speech:6.1f}秒")
    print(f"間を含めた推定尺 {est:6.1f}秒（目標 {TARGET_TOTAL:.0f}秒）")

    if durations:
        diff = est - TARGET_TOTAL
        if abs(diff) > 5:
            new = a.speed * (est / TARGET_TOTAL)
            print(f"\n{abs(diff):.0f}秒{'長い' if diff > 0 else '短い'}です。"
                  f"--speed {new:.2f} --force で作り直すと近づきます。")
        else:
            print("\n尺は許容範囲です。長いカット・短いカットを確認して次へ進んでください。")

        longest = sorted(durations.items(), key=lambda kv: -kv[1])[:3]
        print("最も長いカット: " +
              " / ".join(f"cut{c:02d} {d:.1f}秒" for c, d in longest))


if __name__ == "__main__":
    main()
