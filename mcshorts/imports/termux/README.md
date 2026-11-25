# imports/termux/

Termux に残っているファイルを、そのまま置く場所。

- 段階1では**中身を読まない**。`build_dataset.py` が名前・拡張子・大きさ・SHA-256 の目録を作り、
  `reports/coverage.md` に「形式確認待ち」として出すだけ
- whisper.cpp の出力だと分かっているものは `../whisper_cpp/` に置くと、そちらで読み込まれる
- 動画・音声は Git に入らない（`mcshorts/.gitignore`）
- 置かれたファイルの形式を確かめたら、読み込み処理を `adapters/` に足す
