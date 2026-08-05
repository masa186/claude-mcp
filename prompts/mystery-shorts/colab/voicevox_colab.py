#!/usr/bin/env python3
# Colab上に VOICEVOX ENGINE を落として起動する。
#
# 公式のLinux CPU版リリースを GitHub から取得する。URLは版が上がると変わるので、
# 固定せずにリリース情報を引いて選ぶ。分割書庫（.7z.001, .002 …）にも対応する。
#
#   python3 voicevox_colab.py            # 取得して起動
#   python3 voicevox_colab.py --check    # 起動しているかだけ確認

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

HOST = "http://127.0.0.1:50021"
ROOT = os.path.abspath("voicevox_engine")
RELEASES = "https://api.github.com/repos/VOICEVOX/voicevox_engine/releases/latest"


def alive(timeout=5):
    try:
        urllib.request.urlopen(HOST + "/version", timeout=timeout).read()
        return True
    except Exception:
        return False


def pick_assets(assets):
    # リリースの添付から Linux CPU 版を選ぶ。分割書庫なら全部返す
    def ok(name):
        n = name.lower()
        if "linux" not in n:
            return False
        if any(x in n for x in ("gpu", "nvidia", "cuda", "directml", "macos", "windows")):
            return False
        return "cpu" in n

    hits = [a for a in assets if ok(a["name"])]
    if not hits:
        return []
    # 分割書庫は .7z.001 のように連番。同じ基底名のものをまとめる
    base = sorted(hits, key=lambda a: a["name"])[0]["name"].rsplit(".", 1)[0]
    parts = sorted((a for a in hits if a["name"].startswith(base.rsplit(".7z", 1)[0])),
                   key=lambda a: a["name"])
    return parts or sorted(hits, key=lambda a: a["name"])


def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=1800) as r, open(path, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)


def fetch_engine():
    os.makedirs(ROOT, exist_ok=True)
    print("リリース情報を取得しています…")
    req = urllib.request.Request(RELEASES, headers={"User-Agent": "Mozilla/5.0"})
    rel = json.loads(urllib.request.urlopen(req, timeout=60).read())
    parts = pick_assets(rel.get("assets", []))
    if not parts:
        sys.exit("Linux CPU版が見つかりませんでした。\n"
                 "https://github.com/VOICEVOX/voicevox_engine/releases から\n"
                 "linux-cpu のファイルを手で落として、このフォルダに置いてください。")

    print("版 %s / ファイル %d個" % (rel.get("tag_name", "?"), len(parts)))
    local = []
    for i, a in enumerate(parts, 1):
        dst = os.path.join(ROOT, a["name"])
        if os.path.exists(dst) and os.path.getsize(dst) == a.get("size", -1):
            print("  %d/%d %s（取得済み）" % (i, len(parts), a["name"]))
        else:
            print("  %d/%d %s  %.0fMB" % (i, len(parts), a["name"],
                                          a.get("size", 0) / 1e6))
            download(a["browser_download_url"], dst)
        local.append(dst)

    if not shutil.which("7z"):
        subprocess.run("apt-get -qq install -y p7zip-full", shell=True, capture_output=True)

    print("展開しています…")
    first = local[0]
    if len(local) > 1 and first.endswith(".001"):
        joined = os.path.join(ROOT, "engine.7z")
        with open(joined, "wb") as out:
            for p in local:
                with open(p, "rb") as f:
                    shutil.copyfileobj(f, out, 1 << 20)
        first = joined
    r = subprocess.run(["7z", "x", "-y", "-o" + ROOT, first], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("展開に失敗しました:\n" + r.stderr[-800:])


def find_run():
    for root, _, files in os.walk(ROOT):
        for fn in files:
            if fn == "run" or fn == "run.exe":
                return os.path.join(root, fn)
    return None


def start():
    run = find_run()
    if not run:
        sys.exit("エンジン本体（run）が見つかりません。展開に失敗している可能性があります。")
    os.chmod(run, 0o755)
    print("起動しています。初回は2〜3分かかります…")
    subprocess.Popen([run, "--host", "127.0.0.1", "--port", "50021"],
                     cwd=os.path.dirname(run),
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(90):
        if alive():
            return True
        time.sleep(2)
        if i and i % 15 == 0:
            print("  まだ起動中… (%d秒)" % (i * 2))
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    if alive():
        print("VOICEVOX は起動しています。")
        try:
            names = sorted({s["name"] for s in
                            json.loads(urllib.request.urlopen(HOST + "/speakers", timeout=20).read())})
            print("使える話者: " + "、".join(names))
        except Exception:
            pass
        return
    if a.check:
        sys.exit("VOICEVOX は起動していません。")

    if not find_run():
        fetch_engine()
    if start():
        print("起動しました。③へ進んでください。")
        main()
    else:
        sys.exit("起動できませんでした。もう一度このセルを押すか、"
                 "声なしで作ってから CapCut で足してください。")


if __name__ == "__main__":
    main()
