# 段階4b 分類結果：Dream Clips（ドリームクリップ）

`mcshorts/analysis/codings.py` が自動で作るファイル。分類の中身は `decisions_claude_v1.json`（Claude が付けたもの）。

- **状態はすべて UNVERIFIED（未確認）**。Claude が文字起こし・ナレーションの「文」だけを読んで付けた。映像は見ていない
- すべての分類に、元ファイル名・引用（元の文そのまま）・分類の理由を付けている。引用は元ファイルと照合済み
- このチャンネルだけの結果で、もう一方のチャンネルとは混ぜていない。Gemini の読みは使っていない

## 1. 件数と照合

- 動画：58本 ／ 分類の記録：174件
- 引用の照合：153件すべてが元ファイルの文に含まれていた（1件でも無ければこのファイルは作られない）
- 元データ：`mcshorts/data/transcripts/dream/<動画ID>.json` の Whisper 全編（確認済み。元は `dream/data/asr/<動画ID>.json`）

## 冒頭のつかみ（フック）

| 分類 | 名前 | 本数 |
|---|---|---|
| `H_PROHIBIT` | 禁止・警告 | 2 |
| `H_RESULT` | 結果・結末の先出し | 27 |
| `H_TWIST` | 逆接・ひねりの予告 | 7 |
| `H_QUESTION` | 問いかけ | 1 |
| `H_SCALE` | 量・規模・数字・最上級 | 5 |
| `H_LABEL` | 強い評価・レッテル | 6 |
| `H_INTRO` | 人物・状況の紹介だけ | 5 |
| `H_OTHER` | その他 | 1 |
| `HX` | 判断不能 | 4 |

未分類・判断不能：**4本**（判断不能 4本、元の文なし 0本）

## 展開（中盤）

| 分類 | 名前 | 本数 |
|---|---|---|
| `D_REPEAT` | 繰り返し・天丼 | 4 |
| `D_ESCALATE` | 段階的なエスカレート | 7 |
| `D_BATTLE` | 対決・攻防 | 15 |
| `D_PROCESS` | 作業・手順の進行 | 5 |
| `D_DIALOGUE` | 会話・掛け合い | 14 |
| `DX` | 判断不能 | 13 |

未分類・判断不能：**13本**（判断不能 13本、元の文なし 0本）

## オチ（最後）

| 分類 | 名前 | 本数 |
|---|---|---|
| `P_REVERSAL` | 予想の裏切り・逆転 | 5 |
| `P_PUNISH` | 報い・失敗・やられる | 8 |
| `P_SUCCESS` | 予告どおりの達成・勝利 | 2 |
| `P_CONTINUE` | 続く・未完 | 2 |
| `P_COMMENT` | ツッコミ・感想の一言 | 16 |
| `PX` | 判断不能 | 25 |

未分類・判断不能：**25本**（判断不能 25本、元の文なし 0本）

## 確信が低いもの（flag あり）

- `0iK0gxEUo0U` hook `H_INTRO`：聞き間違いの可能性が高い
- `MzpvoTEXweE` hook `H_RESULT`：聞き間違いが多い
- `MzpvoTEXweE` payoff `P_PUNISH`：根拠が弱い
- `TSW_96CsF4Q` hook `H_OTHER`：聞き間違いの可能性が高い
- `bqyhes0V7Qc` hook `H_SCALE`：聞き間違いが多い

## 確認対象（約10%・6本）

フックの分類ごとの本数に比例させて選んだ（最大剰余法・乱数の種は固定）。本数の少ない分類は選ばれないことがあるので、上の「確信が低いもの」もあわせて確認してほしい。`review_sample.csv` の「確認結果」「正しい分類」「メモ」の列に記入してもらう想定。

割り当て：`H_INTRO` 1本、`H_LABEL` 1本、`H_RESULT` 3本、`H_TWIST` 1本

| 動画ID | 次元 | 分類 | 引用 |
|---|---|---|---|
| `0iK0gxEUo0U` | hook | `H_INTRO` 人物・状況の紹介だけ | マイクラの世界にやってきたボードナムズイですか? |
| `0iK0gxEUo0U` | development | `D_PROCESS` 作業・手順の進行 | An underground oven! |
| `0iK0gxEUo0U` | payoff | `P_COMMENT` ツッコミ・感想の一言 | こんなことをする料理人は滅多にいないでしょうね |
| `1U5Pu0pVtvM` | hook | `H_TWIST` 逆接・ひねりの予告 | ドリームとの決闘中ダクアビスがまさかの行動に出ます |
| `1U5Pu0pVtvM` | development | `D_BATTLE` 対決・攻防 | 最初は順調に勝ち進んでいたダクアビスですが彼はこの後本ミスを犯す戦況が一気に変わります |
| `1U5Pu0pVtvM` | payoff | `PX` 判断不能 | Ahahaha! |
| `D6srtcztceU` | hook | `H_RESULT` 結果・結末の先出し | テストをカンニングしたキッズの悲惨なマツローを |
| `D6srtcztceU` | development | `D_DIALOGUE` 会話・掛け合い | all right today's show and tell let's go i wonder what this guy brought |
| `D6srtcztceU` | payoff | `PX` 判断不能 | I'm not a hack. |
| `O_8PGIz3TLc` | hook | `H_LABEL` 強い評価・レッテル | マイクラ鬼ごっこでありえない着地を見せるドリームという男 |
| `O_8PGIz3TLc` | development | `D_BATTLE` 対決・攻防 | Oh, watch out, watch out, watch out! |
| `O_8PGIz3TLc` | payoff | `P_COMMENT` ツッコミ・感想の一言 | もはやここまで来ると彼はマイクラの神様なのかもしれませんね |
| `d2PlYjZcRo0` | hook | `H_RESULT` 結果・結末の先出し | ブロックスを プラスタらこうなんだ |
| `d2PlYjZcRo0` | development | `D_ESCALATE` 段階的なエスカレート | I'll get you a laptop. |
| `d2PlYjZcRo0` | payoff | `P_COMMENT` ツッコミ・感想の一言 | 普通にサイコパスだと思う方はチャンネル登録 |
| `i2o5r0vZOrg` | hook | `H_RESULT` 結果・結末の先出し | ドリームになってしまったドリームがついに限界を迎えます |
| `i2o5r0vZOrg` | development | `DX` 判断不能 | （引用なし） |
| `i2o5r0vZOrg` | payoff | `PX` 判断不能 | I DISOWED YOU!!! |
