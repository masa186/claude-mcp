# imports/whisper_cpp/

whisper.cpp の出力を置く場所。決まりは `../README.md` を参照。

- ファイル名に動画IDを入れる（例 `cUbDNWd0j24.wav.json`）か、`manifest.csv` に書く
- 実行した日・モデル名は `manifest.csv` に書く（書かないと欠損 `UNKNOWN` として記録される）
- `manifest.example.csv` は書き方の見本で、読み込まれない
