# mcshorts — Minecraft Shorts 制作システム

Dream Clips（ドリームクリップ）と SMP Clips（SMPクリップ）を参考に、Minecraft のショート動画を作るための仕組み。
今は**段階1（既存データを共通の形式にまとめ、欠損を一覧にする）**まで。

## 決まりごと

- 既存の `dream/` `tools/` `docs/` `clips/` は**読むだけ**。書き込まない・消さない（テストで確かめている）
- 新しく作るものは、すべて `mcshorts/` に置く
- 対象は Dream Clips と SMP Clips の2チャンネルだけ（`config/channels.json`）
- **欠損は推測で埋めない。** 値が無いものは理由のコード付きで「無い」と書く（`schema.md`）
- すべての値に出どころと取得日時（分からなければ上限）を付ける

## 使い方

```bash
python3 mcshorts/integrate.py                       # 作り直して、既存の記録が残るか確かめるだけ（反映しない）
python3 mcshorts/integrate.py --apply               # 確かめてから data/ と reports/ に反映する
python3 mcshorts/build_dataset.py                   # integrate.py --apply と同じ（直接は書かない）
python3 mcshorts/build_dataset.py --out DIR         # 別の場所に作る（テスト・確認用）
cd mcshorts && python3 -m pytest -q                 # テスト（ネットワークは使わない）
```

### YouTube API で取り直す（段階2）

```bash
python3 mcshorts/fetch_youtube.py --channel dream --dry-run   # 予定と消費ユニットだけ表示（接続しない）
python3 mcshorts/fetch_youtube.py --channel dream --live      # 取得して snapshots/youtube/dream/ に保存
python3 mcshorts/integrate.py --apply                         # 段階1の記録が残ると確かめてから反映
```

- キーは環境変数 `YOUTUBE_API_KEY` だけから読む（`.env` などのファイルは読まない）。値は表示しない
- キーは `X-Goog-Api-Key` ヘッダーで送り、URL・記録・エラー表示には残さない
- 1回に1チャンネル。`videos.list` は1回50本まで、一覧は最後のページまで取る
- 取得結果は書き換えない（同じ名前があれば止まる）。失敗は `failed.jsonl` に残り、取得結果は作られない
- 取れない項目（視聴維持率・低評価数・字幕の本文など）は `reports/coverage.md` に理由付きで出る

whisper.cpp の出力や Termux のファイルは `imports/` に置いてから `build_dataset.py` を実行する（`imports/README.md`）。

## 構成

| パス | 中身 |
|---|---|
| `config/channels.json` | 対象チャンネル |
| `config/sources.json` | 既存データの台帳（パス・方法・状態・取得日時の上限・注記） |
| `adapters/dream.py` `adapters/smp.py` | 既存データの読み込み |
| `adapters/whisper_cpp.py` | whisper.cpp の出力の読み込み |
| `adapters/termux.py` | Termux のファイルの目録 |
| `adapters/collector.py` | 集めて共通形式に組み立てる |
| `adapters/youtube_api.py` | YouTube Data API の呼び出し（キーの扱い・再試行・ページ送り） |
| `adapters/youtube_snapshots.py` | 取得結果の保存（上書きしない）と読み込み |
| `adapters/sqlite_inventory.py` | SQLite の目録（読み取り専用。中身は取り込まない） |
| `build_dataset.py` | 組み立てとレポートの作成 |
| `integrate.py` | 作り直し → 既存の記録が残るか確認 → 反映 |
| `fetch_youtube.py` | YouTube API の取得（`--dry-run` / `--live`） |
| `snapshots/` | 取得結果（取得した時点のまま。`snapshots/README.md`） |
| `schema.md` | 共通形式と欠損コードの定義 |
| `imports/` | 外から持ってきたデータを置く場所 |
| `data/` | 生成物：`videos.jsonl` `transcripts/` `features.jsonl` `imports.json` |
| `reports/` | 生成物：`coverage.md` `coverage.csv` `conflicts.md` |
| `tests/` | テスト（whisper.cpp のサンプルは自作。`tests/fixtures/whisper_cpp/README.md`） |

`data/` と `reports/` は生成物だが、GitHub で確かめられるようにコミットする。
手で直さず、`build_dataset.py` で作り直す（テストが、コミットされた中身と作り直した結果が一致することを確かめる）。

## 段階

| 段階 | 中身 | 状態 |
|---|---|---|
| 0 | 既存の分析を取り込む | 完了 |
| 1 | 共通形式・欠損一覧・取り込みフォルダ | 完了 |
| 2 | YouTube API で取り直す（取得日時付き） | 実装とテストまで（実際の取得はまだ） |
| 3 | 文字起こしの欠けを埋める | 未着手 |
| 4 | 再生数・タイトル・構成の分析を作り直せる形に | 未着手 |
| 5 | 制作シート（タイトル5案・ナレーション・素材・字幕・秒ごとの編集） | 未着手 |
