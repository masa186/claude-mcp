# mcshorts/analysis/codings — 段階4b（フック・展開・オチの分類）

**分類はすべて Claude が付けたもので、状態は UNVERIFIED（未確認）。** Dream と SMP は別々のフォルダで、混ぜない。

```bash
python3 mcshorts/analysis/codings.py   # 引用を照合し、claude_v1.jsonl・review_sample.csv・summary.md を作り直す
```

## ファイル

| ファイル | 中身 | 手で直すか |
|---|---|---|
| `../codebook.json` | 分類の基準（フック・展開・オチの分類、優先順位、判断不能の扱い） | 基準を変えるときだけ |
| `<channel>/decisions_claude_v1.json` | Claude の分類そのもの（分類・副分類・引用・理由・flag） | 分類を直すときはここ |
| `<channel>/claude_v1.jsonl` | 上に元ファイル名・引用した区間の秒・状態を付けたもの | 直さない（自動） |
| `<channel>/review_sample.csv` | 確認対象（約1割）。「確認結果」「正しい分類」「メモ」の列に記入する | 記入する |
| `<channel>/summary.md` | 件数・未分類・確信が低いもの・確認対象の一覧 | 直さない（自動） |

## 元データ

| チャンネル | 元データ | 分類する次元 |
|---|---|---|
| Dream | Whisper 全編（`data/transcripts/dream/`、確認済み。元は `dream/data/asr/`）。日本語指定と英語指定の両方 | フック・展開・オチ |
| SMP | 冒頭ナレーション（`data/transcripts/smp/` の `smp_tn299`、ユーザー提供CSV由来・未確認） | **フックだけ**（展開・オチは元データが無いので推測しない） |

Gemini の読み（`dream_gemini`・`smp_open`）は使っていない。

## 決まりごと

- 引用は元ファイルの文をそのまま写す。`codings.py` が全件を照合し、1件でも見つからなければ止まる
- 文から判断できないものは `HX` / `DX` / `PX`（判断不能）。元の文が無いものは未分類（NO_TEXT）
- SMP は規則で下書きを作り、Claude が全件を読んで確認・修正した（`overridden` / `draft_code` で分かる）
- 確認対象はフックの分類ごとの本数に比例させて選ぶ（最大剰余法・乱数の種は固定）。確信が低いもの（flag）は summary.md に別に全件を出す
