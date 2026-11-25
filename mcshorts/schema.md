# 共通形式（段階1）

`build_dataset.py` が作るファイルの形。どのファイルも**値を1つに決めず、出どころごとに残す**。

## 原則

- 値が無いときは `null`（または項目なし）にし、**必ず欠損理由のコードを付ける**。推測・補間・既定値では埋めない
- すべての値に出どころ（`source`。`config/sources.json` の `id`）を付ける
- 取得日時は `observed_at`（実際の取得日時）と `observed_before`（上限）に分けて持つ。既存データの `observed_at` はすべて `null`
- 出どころで値が食い違うときは両方残し、`reports/conflicts.md` に出す

## 状態と欠損理由のコード

| 状態 | 意味 |
|---|---|
| `ok` | 値があり、既存の記録で確かめられている |
| `UNVERIFIED` | 値はあるが確かめていない |
| `REJECTED` | 値はあるが、実ファイルと合わず不採用と記録されている。照合用に残すだけで、分析には使わない |

| 欠損コード | 意味 |
|---|---|
| `NOT_COLLECTED` | まだ取得していない |
| `SOURCE_LOST` | 元データが失われた |
| `QUOTA_LIMIT` | 無料枠の上限で取得できなかった |
| `NO_MEDIA` | 動画ファイルがない |
| `UNVERIFIED` | 確かめていない |
| `REJECTED` | 実ファイルと合わず不採用 |
| `NOT_AVAILABLE` | 外部からは原理的に取得できない（視聴維持率など） |
| `UNMATCHED` | 動画IDを特定できない |
| `UNKNOWN` | 記録がなく不明 |

欠損は `{"code": "...", "note": "..."}` の形で書く。

## data/videos.jsonl（1行1動画）

```json
{
 "channel": "dream | smp",
 "video_id": "11文字",
 "url": "https://www.youtube.com/watch?v=...",
 "title":        [{"value": "...", "source": "...", "observed_at": null, "observed_before": "...", "observed_at_note": "..."}],
 "published":    [同上。API は UTC の日時、ユーザー提供の一覧は YYYYMMDD],
 "duration_sec": [同上],
 "views":        [{"views": 0, "likes": 0|null, "comments": 0|null, "source": "...", "observed_at": null, "observed_before": "..."}],
 "in_sources":   ["..."],
 "extra":        {"dream_no": 1, "list_membership": "..."},
 "missing":      {"views_observed_at": {"code": "UNKNOWN", "note": "..."}}
}
```

「最新の再生数」のような代表値は作らない（取得日時が分からないため）。段階2で取得日時付きの観測を足す。

## data/transcripts/{channel}/{video_id}.json

```json
{
 "channel": "...", "video_id": "...",
 "transcripts": [
  {
   "source": "dream_asr | dream_asr_edges | dream_gemini | dream_tn58 | smp_tn299 | smp_open | smp_full | smp_voice | whisper_cpp",
   "method": "whisper | whisper_cpp | gemini | user_csv | claude8s",
   "tool": "モデル名（分かるときだけ）",
   "kind": "speech | narration_subtitle | narration_voice | narration_text | subtitle_sequence | ...",
   "scope": "full | head_5s | tail_7s | opening_8s | opening_narration | narration",
   "lang": "ja | en | ...",
   "status": "ok | UNVERIFIED | REJECTED",
   "file": "元ファイルのパス（あるとき）",
   "segments": [{"start": 0.0 | null, "end": 2.1 | null, "text": "..."}],
   "missing": {"timestamps": {"code": "NOT_COLLECTED", "note": "..."}}
  }
 ]
}
```

- 秒が無いものは `start` / `end` を `null` にする（0 などで埋めない）
- Dream の Whisper の単語ごとの時刻は写していない。`file` の元ファイルにある
- whisper.cpp の取り込みには `format` `sha256` `matched_by`（`manifest` / `filename`）`run_date` が付く

## data/features.jsonl（1行＝1動画×1出どころ）

```json
{"channel": "...", "video_id": "...", "source": "...", "status": "ok | UNVERIFIED", "fields": {元の項目名のまま}}
```

既存の分析結果（フックの型・ナレーションの型・相対再生 `rel` など）を、**項目名も値もそのまま**写す。計算し直しはしない。

## data/imports.json

`imports/whisper_cpp/` と `imports/termux/` に置かれたファイルの一覧と、それぞれの結果（`IMPORTED` / `UNMATCHED` / `OUT_OF_SCOPE` / `UNSUPPORTED` / `PARSE_ERROR` / `PENDING_FORMAT_CHECK`）。

## 段階2：YouTube API の取得結果（snapshots/youtube/）

取得結果1回分が、1つの出どころ `yt_<channel>_<run_id>`（例 `yt_dream_20261126T031000Z`）になる。

- 観測の `observed_at` は、その動画を取得した `videos.list` の呼び出し時刻（UTC）。段階1の観測（`observed_at` が null）はそのまま残る
- 説明欄・タグ・カテゴリ・字幕トラックの有無・公開状態などは `data/features.jsonl` にその出どころで入る
- 高評価数・コメント数が非公開・無効のときは `null`（0 にしない）。`missing` に `NOT_AVAILABLE`
- API が返さなかった動画は `reports/conflicts.md` に一覧で出る（理由は区別できないので書かない）
- 正確な取得日時がある観測どうしで再生数が減っていれば、直さずに `reports/conflicts.md` に出す
- 「最新の再生数」のような代表値は、引き続き作らない（どの時点を使うかは段階4で決める）

取得結果のファイルの形（`snapshots/youtube/<channel>/snapshots/<run_id>.json`）：

```json
{
 "schema_version": 1, "channel": "dream", "channel_id": "UC...",
 "started_at": "UTC", "finished_at": "UTC", "code_commit": "git のコミット",
 "channel_stats": {"subscribers": "丸められた値 | null", "view_count": 0, "video_count": 0, "fetched_at": "UTC", ...},
 "uploads_count": 0, "playlist_pages": 0, "extra_ids_requested": ["既存データにあり一覧に無いID"],
 "videos": [{"video_id": "...", "fetched_at": "UTC", "title": "...", "description": "...", "tags": [...] | null,
             "published_at": "...", "duration_sec": 0, "views": 0, "likes": 0 | null, "comments": 0 | null,
             "privacy_status": "...", "in_uploads_playlist": true, "missing": {...}, ...}],
 "not_returned": [{"video_id": "...", "in_uploads_playlist": false, "note": "..."}],
 "foreign": [{"video_id": "...", "channel_id": "別チャンネル"}],
 "calls": [{"endpoint": "videos", "params": {"キーを含まない"}, "at": "UTC", "status": 200, "server_date": "...", "units": 1}],
 "units_total": 0
}
```

## reports/

| ファイル | 中身 |
|---|---|
| `coverage.md` | チャンネル×項目の充足表、欠損の理由、分析できない項目、出どころと取得日時、取り込みフォルダの状態 |
| `coverage.csv` | 同じ内容を1本ずつ |
| `conflicts.md` | 出どころで食い違う値（題名・投稿日・長さ）、一覧どうしの差 |
