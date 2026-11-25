# 取り込みフォルダ

外（Termux など）で作ったデータを置く場所。置いたあと `python3 mcshorts/build_dataset.py` を実行すると、
`data/` と `reports/` に反映される。**置いたファイルは書き換えない・消さない。**

| フォルダ | 置くもの | 段階1での扱い |
|---|---|---|
| `whisper_cpp/` | whisper.cpp の出力（`.json` `.srt` `.vtt` `.csv` `.lrc` `.txt`、画面出力を保存した `.log`） | 読み込んで `data/transcripts/` に入れる（状態は UNVERIFIED） |
| `termux/` | Termux に残っているその他のファイル（何でも） | **目録だけ作る**（名前・大きさ・SHA-256）。形式を確かめるまで中身は読まない |
| `sqlite/` | SQLite の分析データ | **読み取り専用で目録だけ作る**（表・列・型・行数）。中身は取り込まない（`sqlite/README.md`） |

動画・音声（mp4, wav, m4a など）は `.gitignore` で除外している。テキストの出力だけを置く。

## 確認状況

| 項目 | 状態 |
|---|---|
| whisper.cpp の各形式の読み込み | **公開仕様に合わせた自作サンプルでのみ確認**（`tests/fixtures/whisper_cpp/`）。実ファイルでは未確認 |
| 実ファイルのファイル名の付け方 | 未確認 |
| Termux にあるファイルの種類 | 未確認 |

実ファイルが届いたら、ここを更新する。

## whisper.cpp の出力を動画に対応付ける決まり

推測では対応付けない。次の順に決める。

1. `whisper_cpp/manifest.csv` に書かれていれば、それに従う
2. 書かれていなければ、**ファイル名に既知の動画ID（11文字）がちょうど1つ含まれる**ときだけ対応付ける
   - 例：`cUbDNWd0j24.wav.json`、`タイトル [ichRl_cub_U].srt`
3. それ以外は取り込まず、`reports/coverage.md` の「取り込みフォルダ」に理由付きで出す

| 結果 | 意味 |
|---|---|
| `IMPORTED` | 取り込んだ |
| `UNMATCHED` | 動画IDを決められない（無い・複数ある・manifest の値が不正） |
| `OUT_OF_SCOPE` | Dream Clips・SMP Clips 以外 |
| `UNSUPPORTED` | 読めない拡張子 |
| `PARSE_ERROR` | 読もうとして失敗した（理由を残す） |

## manifest.csv

`whisper_cpp/manifest.example.csv` をまねて `whisper_cpp/manifest.csv` を作る。

| 列 | 中身 | 無いとき |
|---|---|---|
| `file` | `whisper_cpp/` からの相対パス | 必須 |
| `video_id` | YouTube の動画ID | ファイル名から探す |
| `channel` | `dream` か `smp` | 既知の一覧から決める。一覧に無い動画は必須 |
| `model` | 使ったモデル（例 `ggml-large-v3-turbo`） | JSON の中に書かれていればそれ。無ければ欠損 `UNKNOWN` |
| `language` | 指定した言語（`ja` / `en` / `auto`） | 同上 |
| `scope` | `full`（全編）など | `full` |
| `run_date` | 実行した日（`YYYY-MM-DD`） | 欠損 `UNKNOWN`（ファイルの更新日時では埋めない） |
| `note` | メモ | — |
