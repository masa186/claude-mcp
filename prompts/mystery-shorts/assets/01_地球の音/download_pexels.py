#!/usr/bin/env python3
"""
素材調達リスト.md の「P」欄を読んで、Pexels から縦動画を自動ダウンロードする。

・検索ワードは 素材調達リスト.md から読む。リストを直せば挙動も変わる（二重管理しない）
・縦（portrait）のみ。横動画を掴んだら捨てる
・1カットにつき既定2本落とす。1本目が外れなことが多いので選べるようにしてある
・ライセンス控えを credits.csv に残す（収益化時に必要になる）

準備：
    https://www.pexels.com/api/ で無料のAPIキーを取得（登録だけ、課金なし）
    export PEXELS_API_KEY=xxxxxxxx

使い方：
    python3 download_pexels.py --dry-run          # 何を何本落とすか確認だけ
    python3 download_pexels.py                    # 全24カット
    python3 download_pexels.py --only 1,3,29      # カット指定
    python3 download_pexels.py --per-cut 3        # 1カットあたり3本
    python3 download_pexels.py --min-height 1280  # 最低解像度を下げる

・既にファイルがあるカットはスキップするので、失敗分だけ再実行できる
・Pexels無料枠は 200リクエスト/時。全カットでも十分収まる
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LIST_FILE = os.path.join(HERE, "素材調達リスト.md")
OUT = os.path.join(HERE, "pexels")
CREDITS = os.path.join(OUT, "credits.csv")

API = "https://api.pexels.com/videos/search"


# ── 素材調達リスト.md の P セクションを読む ──────────────────────────

def parse_list():
    """[(カット番号, 内容, [検索ワード...])] を返す。"""
    text = open(LIST_FILE, encoding="utf-8").read()

    # 「## P：」の見出しから、次の「## 」までを切り出す
    m = re.search(r"^##\s*P[：:].*?$(.*?)(?=^##\s)", text, re.M | re.S)
    if not m:
        sys.exit("素材調達リスト.md に「## P：」のセクションが見つかりません")

    rows = []
    for line in m.group(1).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not cells[0].isdigit():
            continue
        terms = re.findall(r"`([^`]+)`", cells[2])
        if not terms:
            terms = [t.strip() for t in cells[2].split("/") if t.strip()]
        rows.append((int(cells[0]), cells[1], terms))
    return sorted(rows)


def slug(s, n=40):
    s = re.sub(r"[^\w\s-]", "", s, flags=re.U).strip()
    return re.sub(r"[\s]+", "_", s)[:n]


# ── Pexels ────────────────────────────────────────────────────────

def search(term, key, per_page=15):
    url = f"{API}?" + urllib.parse.urlencode(
        {"query": term, "orientation": "portrait",
         "per_page": per_page, "size": "medium"})
    req = urllib.request.Request(url, headers={"Authorization": key})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read()).get("videos", [])
        except urllib.error.HTTPError as e:
            if e.code == 429:                      # レート制限。待って再試行
                wait = 2 ** attempt * 15
                print(f"      レート制限。{wait}秒待機")
                time.sleep(wait)
                continue
            raise
        except urllib.error.URLError:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    return []


def best_file(video, min_height):
    """縦向きで、min_height 以上のうち最も解像度の高いファイルを選ぶ。"""
    cands = [f for f in video.get("video_files", [])
             if f.get("width") and f.get("height")
             and f["height"] > f["width"]                    # 縦のみ
             and f["height"] >= min_height]
    if not cands:
        return None
    return max(cands, key=lambda f: f["height"])


def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=600) as r, open(path, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)


# ── 本体 ──────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="カット番号をカンマ区切りで指定")
    ap.add_argument("--per-cut", type=int, default=2, help="1カットあたりの本数")
    ap.add_argument("--min-height", type=int, default=1600, help="最低の縦解像度")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = parse_list()
    if a.only:
        want = {int(s) for s in a.only.split(",") if s.strip().isdigit()}
        rows = [r for r in rows if r[0] in want]

    print(f"対象 {len(rows)} カット × 最大{a.per_cut}本 "
          f"（縦{a.min_height}px以上）")
    if a.dry_run:
        for cut, desc, terms in rows:
            print(f"  #{cut:2d}  {desc}")
            for t in terms:
                print(f"        → {t}")
        return

    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        sys.exit("環境変数 PEXELS_API_KEY が未設定です。\n"
                 "https://www.pexels.com/api/ で無料取得できます。")

    os.makedirs(OUT, exist_ok=True)
    new_credits, got, missing = [], 0, []

    for cut, desc, terms in rows:
        existing = [f for f in os.listdir(OUT) if f.startswith(f"cut{cut:02d}_")]
        if len(existing) >= a.per_cut:
            print(f"#{cut:2d} skip（取得済み {len(existing)}本）")
            continue

        print(f"#{cut:2d} {desc}")
        picked, seen = [], set()

        for term in terms:                     # 足りなければ次の検索ワードへ
            if len(picked) >= a.per_cut:
                break
            try:
                videos = search(term, key)
            except Exception as e:             # noqa: BLE001
                print(f"      検索失敗 [{term}] {type(e).__name__}: {e}")
                continue
            print(f"      [{term}] {len(videos)}件")
            for v in videos:
                if len(picked) >= a.per_cut or v["id"] in seen:
                    continue
                seen.add(v["id"])
                vf = best_file(v, a.min_height)
                if vf:
                    picked.append((v, vf))
            time.sleep(0.6)

        if not picked:
            missing.append((cut, desc, terms))
            print("      該当なし → 手動で探すか --min-height を下げる")
            continue

        for i, (v, vf) in enumerate(picked, 1):
            name = f"cut{cut:02d}_{i}_{slug(desc)}_{vf['width']}x{vf['height']}.mp4"
            path = os.path.join(OUT, name)
            try:
                download(vf["link"], path)
                got += 1
                print(f"      ok  {name}")
                new_credits.append({
                    "カット": cut, "ファイル": name,
                    "解像度": f"{vf['width']}x{vf['height']}",
                    "Pexels動画ID": v["id"], "ページURL": v.get("url", ""),
                    "撮影者": v.get("user", {}).get("name", ""),
                    "撮影者URL": v.get("user", {}).get("url", ""),
                    "ライセンス": "Pexels License（商用可・クレジット表記不要）",
                })
            except Exception as e:             # noqa: BLE001
                print(f"      DL失敗 {type(e).__name__}: {e}")
                if os.path.exists(path):
                    os.remove(path)

    # ライセンス控えを追記
    if new_credits:
        cols = list(new_credits[0].keys())
        is_new = not os.path.exists(CREDITS)
        with open(CREDITS, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            if is_new:
                w.writeheader()
            w.writerows(new_credits)

    print(f"\n完了：{got}本 → {OUT}")
    print(f"ライセンス控え：{CREDITS}")
    if missing:
        print("\n見つからなかったカット（検索ワードを変えるか AI生成に回す）：")
        for cut, desc, terms in missing:
            print(f"  #{cut:2d} {desc}  試したワード: {' / '.join(terms)}")

    print("\n※ 人物が写っている素材（#18 #24 #25 #27）は、"
          "使う前に Pexels の利用規約を確認してください")


if __name__ == "__main__":
    main()
