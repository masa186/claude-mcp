# データの充足状況（段階1）

`mcshorts/build_dataset.py` が自動で作るファイル。手で直さない。

- **ok**：値があり、既存の記録で確かめられている
- **UNVERIFIED**：値はあるが確かめていない（Gemini の読み・ユーザー提供CSV・形式未確認の取り込みなど）
- **REJECTED**：値はあるが、実ファイルと合わず不採用と記録されている
- **欠損:コード**：値が無い。推測では埋めていない。コードの意味は下の表

| コード | 意味 |
|---|---|
| `NOT_COLLECTED` | まだ取得していない |
| `SOURCE_LOST` | 元データが失われた |
| `QUOTA_LIMIT` | 無料枠の上限で取得できなかった |
| `NO_MEDIA` | 動画ファイルがない |
| `UNVERIFIED` | 確かめていない |
| `REJECTED` | 実ファイルと合わず不採用 |
| `NOT_AVAILABLE` | 外部からは原理的に取得できない |
| `UNMATCHED` | 動画IDを特定できない |
| `UNKNOWN` | 記録がなく不明 |

## 1. 件数

| チャンネル | 動画（どれかの出どころにある） | API一覧にある | 書き起こしファイル |
|---|---|---|---|
| Dream Clips（ドリームクリップ） | 58 | 58 | 58 |
| SMP Clips（SMPクリップ） | 347 | 347 | 300 |

- SMP Clips（SMPクリップ）：smp_api_0830 にあり smp_api_1124 に無い動画 **7本**。削除・非公開などの理由は記録が無いので書かない。段階2の取り直しで状態を確かめる
  - `-xfMTkaPEUc`, `8OgEniAPYeU`, `FeJgAep4-c4`, `XrqD3Z-f6f8`, `uecODJpLBqc`, `wIfigxLXGAg`, `waJSDfwF1lE`

## 2. 項目ごとの充足

### Dream Clips（ドリームクリップ）（58本）

| 項目 | ok | UNVERIFIED | REJECTED | 欠損（コード別） |
|---|---|---|---|---|
| 一覧（YouTube API） | 58 | 0 | 0 | — |
| 再生数の観測 | 58 | 0 | 0 | — |
| 上部タイトル | 58 | 0 | 0 | — |
| ナレーション文（CSV由来） | 0 | 58 | 0 | — |
| 冒頭の書き起こし | 58 | 0 | 0 | — |
| 全編の書き起こし | 58 | 0 | 0 | — |
| whisper.cpp の取り込み | 0 | 0 | 0 | `NOT_COLLECTED` 58 |
| Gemini の映像・音の読み | 0 | 14 | 0 | `QUOTA_LIMIT` 44 |
| 実測（カット・字幕・音量） | 58 | 0 | 0 | — |
| 音タグ | 58 | 0 | 0 | — |
| 構成の分類（個別分析） | 58 | 0 | 0 | — |
| 動画ファイル | 0 | 0 | 0 | `NO_MEDIA` 58 |

欠損の理由（記録されているもの）：
- Gemini の映像・音の読み `QUOTA_LIMIT`：Gemini の無料枠の上限で取得できなかった（dream/README.md）
- 動画ファイル `NO_MEDIA`：videos.json の path（前のセッションの一時フォルダ）にファイルが無い
- whisper.cpp の取り込み `NOT_COLLECTED`：imports/whisper_cpp/ に該当ファイルなし

### SMP Clips（SMPクリップ）（347本）

| 項目 | ok | UNVERIFIED | REJECTED | 欠損（コード別） |
|---|---|---|---|---|
| 一覧（YouTube API） | 347 | 0 | 0 | — |
| 再生数の観測 | 347 | 0 | 0 | — |
| 上部タイトル | 30 | 270 | 0 | `NOT_COLLECTED` 47 |
| ナレーション文（CSV由来） | 0 | 299 | 0 | `NOT_COLLECTED` 48 |
| 冒頭の書き起こし | 0 | 55 | 0 | `NOT_COLLECTED` 292 |
| 全編の書き起こし | 0 | 0 | 26 | `NOT_COLLECTED` 321 |
| whisper.cpp の取り込み | 0 | 0 | 0 | `NOT_COLLECTED` 347 |
| Gemini の映像・音の読み | 0 | 0 | 0 | `NOT_COLLECTED` 347 |
| 実測（カット・字幕・音量） | 0 | 0 | 0 | `NOT_COLLECTED` 347 |
| 音タグ | 0 | 0 | 0 | `NOT_COLLECTED` 347 |
| 構成の分類（個別分析） | 0 | 0 | 0 | `NOT_COLLECTED` 347 |
| 動画ファイル | 0 | 0 | 0 | `NO_MEDIA` 347 |

欠損の理由（記録されているもの）：
- 音タグ `NOT_COLLECTED`：動画ファイルが必要
- 構成の分類（個別分析） `NOT_COLLECTED`：Dream のような1本ずつの構成分類は SMP では作られていない（smp_tn299 の分類は narration_text 側）
- 実測（カット・字幕・音量） `NOT_COLLECTED`：SMP の実測データは構造化されていない（文書のみ）。動画ファイルが必要
- 動画ファイル `NO_MEDIA`：過去に一部の実ファイルを読んだ記録（docs/smp_real.md など）はあるが、ファイルはリポジトリに無い
- ナレーション文（CSV由来） `NOT_COLLECTED`：tn_smp299 に含まれない（元CSVの「未確認」「欠番」行、または一覧外。1本ずつの理由は記録なし）
- whisper.cpp の取り込み `NOT_COLLECTED`：imports/whisper_cpp/ に該当ファイルなし

## 3. 分析できない項目（両チャンネル共通）

| 項目 | コード | 理由 |
|---|---|---|
| 視聴維持率・平均視聴時間 | `NOT_AVAILABLE` | YouTube Analytics の数字はチャンネルの持ち主しか見られない |
| インプレッション数・クリック率 | `NOT_AVAILABLE` | 同上 |
| 流入経路・視聴者の属性 | `NOT_AVAILABLE` | 同上 |
| スワイプ率（Shorts フィードで見られた／スワイプされた割合） | `NOT_AVAILABLE` | 同上 |
| 既存の再生数を取得した正確な日時 | `UNKNOWN` | どの出どころにも記録なし。observed_before（コミット日時）が上限 |
| どの再生数が最新か | `UNKNOWN` | 取得日時が不明なので決めていない。段階2で取得日時付きで取り直す |

## 4. 出どころと取得日時

`observed_at`（実際の取得日時）はどの既存ファイルにも記録が無い。`observed_before` は取り込み元ブランチに初めてコミットされた日時で、取得日時の上限。

| 出どころ | ファイル | 方法 | 状態 | observed_at | observed_before |
|---|---|---|---|---|---|
| `dream_videos` | `dream/data/videos.json` | user_provided_list | ok | 不明 | 2026-11-24T16:15:28+00:00 |
| `dream_api_five` | `tools/five.json` | youtube_data_api | ok | 不明 | 2026-08-31T16:01:35+00:00 |
| `smp_api_0830` | `tools/smp.json` | youtube_data_api | ok | 不明 | 2026-08-30T12:02:02+00:00 |
| `smp_api_1124` | `tools/smp_1124.json` | youtube_data_api | ok | 不明 | 2026-11-25T00:00:12+00:00 |
| `smp_top40` | `tools/smp_top40.json` | derived | ok | 不明 | 2026-11-25T00:12:54+00:00 |
| `smp_topbottom` | `tools/smp_topbottom.json` | derived | ok | 不明 | 2026-11-25T00:00:12+00:00 |
| `dream_coded_rows` | `dream/data/coded_rows.json` | claude_analysis | ok | 不明 | 2026-11-24T18:45:02+00:00 |
| `dream_tn58` | `tools/tn_dream58.json` | user_csv+claude_analysis | UNVERIFIED | 不明 | 2026-11-25T04:43:57+00:00 |
| `smp_tn299` | `tools/tn_smp299.json` | user_csv+claude_analysis | UNVERIFIED | 不明 | 2026-11-25T04:43:57+00:00 |
| `dream_asr` | `dream/data/asr` | whisper | ok | 不明 | 2026-11-24T16:15:28+00:00 |
| `dream_asr_edges` | `dream/data/asr_edges` | whisper | ok | 不明 | 2026-11-24T16:38:27+00:00 |
| `dream_gemini` | `dream/data/gemini` | gemini | UNVERIFIED | 不明 | 2026-11-24T16:15:28+00:00 |
| `dream_measure` | `dream/data/measure` | ffmpeg+numpy | ok | 不明 | 2026-11-24T16:15:28+00:00 |
| `dream_audiotag` | `dream/data/audiotag` | ast_audioset | ok | 不明 | 2026-11-24T16:15:28+00:00 |
| `smp_open` | `tools/smp_open.json` | gemini | UNVERIFIED | 不明 | 2026-11-25T00:00:12+00:00 |
| `smp_full` | `tools/smp_full.json` | gemini | REJECTED | 不明 | 2026-11-25T00:13:18+00:00 |
| `smp_voice` | `tools/smp_voice.json` | gemini | REJECTED | 不明 | 2026-11-25T00:13:18+00:00 |
| `whisper_cpp` | `mcshorts/imports/whisper_cpp` | whisper_cpp | UNVERIFIED | 不明 | — |
| `termux` | `mcshorts/imports/termux` | none | UNVERIFIED | 不明 | — |

## 5. 文書としてだけ残っている資料（段階1では読み込んでいない）

- `dream/individual/`（dream）：58本の個別分析（秒付き）
- `dream/narration_list.md`（dream）：58本のナレーション字幕一覧（字幕を正、Whisper で確認）
- `dream/comparison.csv`（dream）：coded_rows.json から作った比較表（派生物）
- `docs/smp_real.md`（smp）：歴代上位5本の字幕を実ファイルから全部読んだもの
- `docs/smp_20.md`（smp）：20本を実ファイルから読んだもの
- `docs/smp_40.md`（smp）：36本を実ファイルから読んだもの
- `docs/smp_52.md`（smp）：52本の実測
- `docs/smp_top40_narration.md`（smp）：上位40本の上部タイトルと冒頭ナレーション
- `docs/smp_opening_topbottom.md`（smp）：上位15・下位15の冒頭比較

## 6. 取り込みフォルダ

- `imports/whisper_cpp/`：ファイル 0 件、取り込み 0 件
- `imports/termux/`：ファイル 0 件（すべて形式確認待ち。中身は読んでいない）

## 7. 段階1で行っていないこと

- 出どころが違う書き起こし（CSV・Whisper・Gemini）の文の照合。すべて残してあり、照合は段階4で行う
- 再生数の取り直し（段階2）、文字起こしの追加（段階3）
- 相対再生の計算し直し。既存の値（`rel`）を出どころ付きで `data/features.jsonl` に残しているだけ
