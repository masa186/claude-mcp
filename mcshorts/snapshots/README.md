# snapshots/

API などから取得した結果を、**取得した時点のまま**残す場所。一度書いたファイルは書き換えない。

```
snapshots/youtube/<channel>/index.jsonl              取得の記録（1回1行・追記だけ。ファイルの SHA-256 付き）
snapshots/youtube/<channel>/snapshots/<run_id>.json  整えた取得結果
snapshots/youtube/<channel>/raw/<run_id>.json.gz     API の応答そのもの
snapshots/youtube/<channel>/failed.jsonl             失敗の記録（API キーは含まない）
```

- 作るのは `fetch_youtube.py`（1回に1チャンネル）
- `data/` と `reports/` への反映は `integrate.py --apply`（段階1の記録がすべて残っていると確かめてから反映）
- `index.jsonl` の SHA-256 と合わないファイルは、書き換えられたとみなして読み込まない
