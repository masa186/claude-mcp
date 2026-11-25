# mcshorts/analysis/narration — 段階4c（ナレーション分析）

今あるのは **Dream の 4c-1（元データの整理）と 4c-2（動画ごとの個別分析）だけ**。SMP・みんくら、4c-3 以降はまだ。

```bash
mcshorts/.venv/bin/python mcshorts/analysis/narration/build_tracks.py   # 4c-1
mcshorts/.venv/bin/python mcshorts/analysis/narration/roles.py          # 役割・伏線の分類を検査
mcshorts/.venv/bin/python mcshorts/analysis/narration/per_video.py      # 4c-2
mcshorts/.venv/bin/python -m pytest mcshorts/tests/test_narration_4c.py
```

形態素解析（fugashi・unidic-lite）はプロジェクト専用の仮想環境 `mcshorts/.venv/` にだけ入っている。
バージョンと辞書の情報は、出力の `tool` と `tracks/dream/manifest.json` に記録する。

## 確かさのラベル

| ラベル | 意味 |
|---|---|
| `ok` | Whisper の書き起こし・実測・音タグ（機械的な値。Whisper は聞き間違いあり、直していない） |
| `DOC_OBSERVED` | 文書の観察。`dream/narration_list.md` の字幕（本文の基準）、個別分析の [画面][実測][書き起こし][音タグ] の表・行 |
| `DOC_INTERPRETATION` | 文書の考察（[考察] の行、構成の表の「段階」）。事実としては使わない |
| `UNVERIFIED` | Claude の分類（役割・伏線・段階4b）、ユーザー提供CSV |
| `INTERPRETATION` | 規則による盛り上がりの候補。断定しない |

Gemini の行は使わない。

## 決まりごと

- 字幕の文単位の時刻と Whisper の単語単位の時刻は別々に持つ。対応付けない（時間が重なるかだけを記録）
- 字幕・Whisper・CSV の食い違いは消さない（`tracks/dream/discrepancies.md`）
- 窓（0〜1・0〜3・0〜5秒）をまたぐ字幕の行は、窓の中の文字数を推測しない
- 伏せ字（〇など）は数字と数えない
- 段階4bの確認結果は、元の分類を書き換えずに重ねる（`code` と `effective_code`）
- 役割・伏線の確認結果は `codings/dream/review_roles.csv` に記入し、元の分類（`roles_claude_v1.json`）は書き換えない

## 出力

| パス | 中身 |
|---|---|
| `tracks/dream/<id>.json` | 4c-1：動画ごとの元データ（字幕・Whisper・CSV・個別分析・実測・音タグ・段階4b） |
| `tracks/dream/discrepancies.md` | 字幕・Whisper・CSV の違い |
| `tracks/dream/manifest.json` | 入力の SHA-256 と形態素解析のバージョン |
| `codebook_roles.json` | 文の役割と伏線の分類基準 |
| `codings/dream/roles_claude_v1.json` | Claude の分類そのもの |
| `codings/dream/roles_claude_v1.jsonl`・`foreshadow_claude_v1.jsonl` | 検査済みの分類（引用の照合つき） |
| `codings/dream/review_roles.csv` | 確認対象（部分13件・伏線6件） |
| `per_video/dream/<id>.json`・`<id>.md` | 4c-2：10項目の個別分析 |
| `per_video/dream/summary.md` | 一覧と、分析できなかった項目・該当なしの本数 |
