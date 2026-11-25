# whisper.cpp 出力のテスト用サンプル

**ここにあるファイルは、whisper.cpp の公開されている出力形式に合わせて手で作ったもの。実際に whisper.cpp を動かした出力ではない。**
文はテスト用の作り文。実ファイルが届いたら、その形式のサンプルをここに足して（`real_` で始まる名前にする）、テストで確かめる。

| ファイル | 対応する whisper.cpp のオプション |
|---|---|
| `sample_oj.json` | `-oj`（区間） |
| `sample_ojf.json` | `-ojf`（区間＋トークン） |
| `sample.srt` | `-osrt` |
| `sample.vtt` | `-ovtt` |
| `sample.csv` | `-ocsv`（時刻はミリ秒） |
| `sample.lrc` | `-olrc` |
| `sample.txt` | `-otxt`（時刻なし） |
| `sample_console.log` | 画面出力を保存したもの |
