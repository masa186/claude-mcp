# 伏線の補正レイヤー（v2）

v1 の伏線の分類（`codings/dream/foreshadow_claude_v1.jsonl`、Claude・UNVERIFIED、51件）は**変更しない**。
ユーザーの確認・指示と、ユーザーが承認した規則A〜Dを重ねた**有効データ**を別のファイルに作る。Dream だけ。

```bash
mcshorts/.venv/bin/python mcshorts/analysis/narration/foreshadow_corrections.py
mcshorts/.venv/bin/python -m pytest mcshorts/tests/test_foreshadow_corrections.py
```

## ファイル

| パス | 中身 |
|---|---|
| `codebook_foreshadow_v2.json` | 規則A〜D、状態、保留の理由、根拠の種類、関係、参考の場面の種類、判定の出どころ |
| `codings/dream/foreshadow_decisions_v2.json` | 元データ（手で書く）。`decisions`＝ユーザーの確認・指示、`ai_proposals`＝Claude の判定案（confirmed=false） |
| `codings/dream/role_decisions_v2.json` | 役割についてのユーザーの新しい判断（review_roles.csv に無いもの） |
| `foreshadow_corrections.py` | 照合・検査して有効データを作る |
| `codings/dream/foreshadow_effective_v2.jsonl` | 出力：51件の有効データ（AI案は入れない） |
| `codings/dream/foreshadow_corrections_log.jsonl` | 出力：変更の履歴（v1 → ユーザーの確認 → 規則 → 有効データ） |

## 規則（2026-11-25 にユーザーが承認）

- **A**：個別分析の [画面] の行を根拠に使う（`doc_fact_line`、DOC_OBSERVED）。[考察]・Gemini は使わない。時刻は不明（`time_known=false`）として、前後の判定をしない
- **B**：予告の字幕の行が**終わる前に**始まった場面は、回収の根拠にしない（`concurrent`＝同時の説明、または `reference`＝参考の場面へ）
- **C**：起点の役割が保留なら、伏線も `HOLD`（`ROLE_HOLD`）
- **D**：予告の要素の一部しか確認できなければ `PARTIAL`（`not_confirmed` に要素と理由）

## 有効データの欄

- `status`：`LINKED`／`PARTIAL`／`NOT_FOUND_IN_TEXT`／`HOLD`（HOLD は `hold_reason`＝`ROLE_HOLD` か `NEEDS_REVIEW`。NOT_FOUND とは別）
- `evidence`：回収の根拠だけ（`timing` は `after`、[画面] の行だけ `unknown`）
- `concurrent`：予告の字幕の行が終わる前に始まる場面（回収に数えない）
- `reference`：参考の場面（`before_state`・`reference_nearest`・`pending_candidate`・`past_confirmed_evidence`。回収に数えない）
- `not_confirmed`：確認できない要素
- `decision_status`：`USER_CONFIRMED`／`USER_DIRECTED`／`RULE`／`V1_UNCHANGED`
- `confirmed`：確定済みデータの集計には `confirmed=true` だけを使う
- `v1_sha256`：v1 の元の行の SHA-256
- `notes`：時間の語（数秒後など）と根拠の時刻の差。判定には使わない

## 決まりごと

- 根拠は時刻の範囲と引用で指定し、tracks と元の個別分析（`dream/individual/*.md`）の行の両方で照合する。合わなければ止める
- AI案（`ai_proposals`）も同じ照合・規則で検査するが、有効データには入れない
- v1・review_roles.csv・既存の段階4cのファイルは読むだけ
