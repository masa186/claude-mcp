# 冷蔵庫サムネイル

「開けっぱなしにしたら部屋は涼しくなる？」用の縦型サムネイル（1080×1920）。

## 成果物

| ファイル | 内容 |
| --- | --- |
| `reizouko_thumbnail_1080x1920.jpg` | 完成サムネイル（1080×1920 / JPEG） |
| `assets/fridge_frame_source.jpg` | 素材：冷蔵庫の庫内カット（元動画から抜き出したフレーム） |
| `assets/otter_transparent.png` | 素材：カワウソキャラの背景透過PNG |
| `src/build_thumbnail.py` | 生成スクリプト |

## デザインの意図

前バージョンはイチゴのアップだけで「冷蔵庫」と認識しづらかったため、次の3点を変更した。

1. **冷蔵庫の形を見せる** — 庫内カットを冷蔵庫本体の枠にはめ込み、右側に開いたドア（ドアポケット付き）を描画。「開いている冷蔵庫」として一目で伝わる形にした。
2. **冷気を可視化** — 足元に冷気のもや・雪の結晶を追加し、「涼しくなる？」というテーマと画が一致するようにした。
3. **文字まわりの強化** — 冷蔵庫アイコン付きのバッジ、太字ラウンド書体＋濃い縁取りで、小さい表示でも見出しが読めるようにした。

## 再生成

```bash
pip install pillow numpy
# 本文用フォント（M PLUS Rounded 1c ExtraBold）を fonts/RoundedEB.ttf に配置
python src/build_thumbnail.py
```

スクリプトは実行ディレクトリから `base_fridge.jpg` / `base_room.jpg` / `otter_rgba.png` / `fonts/RoundedEB.ttf` を読み込む。
