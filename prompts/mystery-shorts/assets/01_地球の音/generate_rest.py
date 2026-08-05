#!/usr/bin/env python3
"""
残り26点の画像を、Higgsfield 以外のサービスで生成する。

`画像プロンプト_全32点.txt` を読んで、素材ID順に生成し `素材_画像/` に保存する。
APIキーは環境変数から読む。キーを持っているサービスを --provider で選ぶ。

  # Google（Imagen）— 9:16をそのまま出せるので第一候補
  export GEMINI_API_KEY=...
  python3 generate_rest.py --provider gemini

  # OpenAI（gpt-image-1）— 2:3までなので9:16への調整が要る
  export OPENAI_API_KEY=...
  python3 generate_rest.py --provider openai

  # Replicate（FLUX）— 9:16対応
  export REPLICATE_API_TOKEN=...
  python3 generate_rest.py --provider replicate

オプション:
  --only A01,A05   指定した素材IDだけ生成
  --dry-run        何を何点生成するかだけ表示して終了
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPT_FILE = os.path.join(HERE, "画像プロンプト_全32点.txt")
OUT = os.path.join(HERE, "素材_画像")

NEGATIVE = ("text, letters, watermark, logo, signature, caption, subtitles, cartoon, "
            "anime, illustration, 3d render, cgi, plastic skin, distorted face, "
            "extra fingers, deformed hands, low resolution, blurry, oversaturated")


def parse_prompts():
    """プロンプトファイルから [(素材ID, カット, 見出し, プロンプト)] を取り出す。"""
    lines = open(PROMPT_FILE, encoding="utf-8").read().splitlines()
    items, i = [], 0
    header = re.compile(r"^(A\d+)\s+→\s+カット\s+([\d,\s]+?)\s{2,}(.+?)\s*$")
    while i < len(lines):
        m = header.match(lines[i])
        if m:
            asset_id, cuts, title = m.group(1), m.group(2).strip(), m.group(3).strip()
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or set(lines[j].strip()) <= {"-"}):
                j += 1
            if j < len(lines):
                items.append((asset_id, cuts, title, lines[j].strip()))
            i = j
        i += 1
    return items


def post(url, payload, headers, timeout=300):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get(url, headers, timeout=120):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def fetch(url, timeout=300):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


# ── 各サービス。戻り値はいずれも PNG/JPEG のバイト列 ────────────────

def gen_gemini(prompt, key):
    """Imagen。9:16 をネイティブに出せるので調整不要。"""
    url = ("https://generativelanguage.googleapis.com/v1beta/"
           "models/imagen-4.0-generate-001:predict")
    res = post(url,
               {"instances": [{"prompt": prompt}],
                "parameters": {"sampleCount": 1, "aspectRatio": "9:16",
                               "negativePrompt": NEGATIVE}},
               {"x-goog-api-key": key})
    return base64.b64decode(res["predictions"][0]["bytesBase64Encoded"])


def gen_openai(prompt, key):
    """gpt-image-1。最も縦長でも 1024x1536（2:3）なので、後で 9:16 に調整する。"""
    res = post("https://api.openai.com/v1/images/generations",
               {"model": "gpt-image-1", "prompt": prompt,
                "size": "1024x1536", "n": 1},
               {"Authorization": f"Bearer {key}"})
    d = res["data"][0]
    return base64.b64decode(d["b64_json"]) if "b64_json" in d else fetch(d["url"])


def gen_replicate(prompt, key):
    """FLUX。9:16 対応。予測が終わるまでポーリングする。"""
    h = {"Authorization": f"Bearer {key}", "Prefer": "wait"}
    res = post("https://api.replicate.com/v1/models/black-forest-labs/flux-1.1-pro/predictions",
               {"input": {"prompt": prompt, "aspect_ratio": "9:16",
                          "output_format": "png", "safety_tolerance": 2}}, h)
    for _ in range(120):
        if res.get("status") == "succeeded":
            out = res["output"]
            return fetch(out[0] if isinstance(out, list) else out)
        if res.get("status") in ("failed", "canceled"):
            raise RuntimeError(f"replicate: {res.get('error')}")
        time.sleep(3)
        res = get(res["urls"]["get"], h)
    raise TimeoutError("replicate: タイムアウト")


PROVIDERS = {
    "gemini":    (gen_gemini,    ["GEMINI_API_KEY", "GOOGLE_API_KEY"], True),
    "openai":    (gen_openai,    ["OPENAI_API_KEY"],                   False),
    "replicate": (gen_replicate, ["REPLICATE_API_TOKEN"],              True),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, choices=sorted(PROVIDERS))
    ap.add_argument("--only", default="", help="素材IDをカンマ区切りで指定")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    fn, env_names, native_916 = PROVIDERS[a.provider]
    key = next((os.environ[n] for n in env_names if os.environ.get(n)), None)
    if not key and not a.dry_run:
        sys.exit(f"環境変数が未設定です: {' または '.join(env_names)}")

    items = parse_prompts()
    if a.only:
        want = {s.strip() for s in a.only.split(",")}
        items = [it for it in items if it[0] in want]

    print(f"{a.provider} で {len(items)} 点を生成します")
    if not native_916:
        print("※ このサービスは 2:3 までなので、書き出し後に 9:16 へ調整してください")
    if a.dry_run:
        for asset_id, cuts, title, _ in items:
            print(f"  {asset_id}  カット{cuts}  {title}")
        return

    os.makedirs(OUT, exist_ok=True)
    ok = failed = 0
    for asset_id, cuts, title, prompt in items:
        path = os.path.join(OUT, f"{asset_id}_cut{cuts.replace(', ', '-')}_{title}.png")
        if os.path.exists(path):
            print(f"  skip   {asset_id}（生成済み）")
            continue
        try:
            open(path, "wb").write(fn(prompt, key))
            ok += 1
            print(f"  ok     {asset_id}  {title}")
        except Exception as e:                                  # noqa: BLE001
            failed += 1
            print(f"  失敗   {asset_id}  {type(e).__name__}: {e}")
        time.sleep(1.2)

    print(f"\n完了：成功 {ok} / 失敗 {failed} → {OUT}")


if __name__ == "__main__":
    main()
