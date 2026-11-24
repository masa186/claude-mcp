# キャラ画像5枚の生成プロンプト

`render.py` が読む5枚。ファイル名は**必ずこの通り**にして `assets/` に置く。

| ファイル名 | 表情 | 使いどころ |
| --- | --- | --- |
| `char_explain.png` | 解説顔 | **一番多く出る。最初にこれを作る** |
| `char_surprise.png` | 驚き顔 | フック |
| `char_serious.png` | 真面目顔 | 仕組みの説明 |
| `char_proud.png` | ドヤ顔 | オチ・予告 |
| `char_blink.png` | 目を閉じた顔 | まばたき（0.1秒だけ差し込む） |

---

## 前のプロンプトから変わった3点

レンダラーが教室・黒板・指し棒を自分で描くようになったので、**画像にはカワウソ本体しか要りません。**

| | 前 | 今 |
| --- | --- | --- |
| 背景 | 教室と黒板を含めて生成 | **背景なし（白一色）。カワウソだけ** |
| 指し棒 | 持たせて生成 | **持たせない。**棒はコード側で描いて動かす |
| 比率 | 9:16 | **縦長のポートレート（1024×1408）。**全身が入ればいい |

黒板の中身も文字もコード側で描くので、**画像に文字を入れさせない**のは前と同じです。

---

## 共通ブロック（5枚すべてに入れる）

**マスター参照画像を必ず添付する。** 添付なしで生成するとキャラが変わります。

```
Same character as the reference image, completely unchanged design:
a brown otter with round glasses, a white short-sleeved shirt,
a mustard yellow vest, and a teal bow tie.
Keep the same art style, same line weight, same colors, same proportions.

Full body, standing upright, facing the viewer, centered in the frame.
Plain solid white background only.
No background scene, no chalkboard, no classroom, no furniture,
no pointer stick, no props, no shadow on the ground.
Nothing in the image except the character.

<<< ここに下の表情を入れる >>>

Vertical portrait 1024x1408, single character only,
no text, no letters, no watermark.
Keep the character the same size and the same framing in every image.
```

---

## 表情ごとの差し替え部分

### 1. `char_explain.png` — 解説顔（最初にこれを作る）

```
Expression and pose: a friendly explaining expression, mouth slightly
open as if speaking, eyes open and looking at the viewer.
One paw raised to chest height with an open palm, the other paw
relaxed at his side.
```

### 2. `char_surprise.png` — 驚き顔

```
Expression and pose: a surprised expression with wide open eyes and
raised eyebrows, mouth open in a small round shape.
Both paws raised slightly in surprise.
```

### 3. `char_serious.png` — 真面目顔

```
Expression and pose: a focused, serious teaching expression.
Mouth closed, eyebrows slightly lowered, calm and confident eyes.
One paw raised to chest height as if about to point at something.
```

### 4. `char_proud.png` — ドヤ顔

```
Expression and pose: a confident, proud smile with the eyes closed in
happy upward curves, chest puffed out slightly.
Both paws relaxed at his sides.
```

### 5. `char_blink.png` — 目を閉じた顔

**これだけは `char_explain.png` を参照画像にして生成する。** 解説顔とポーズが1ドットでも違うと、
まばたきの瞬間に画面が跳ねます。

```
Exactly the same character, same pose, same body position, same clothing,
same framing as the reference image. Change one thing only:
both eyes are fully closed in a simple relaxed blink (two short curved lines).
Everything else must be identical to the reference.
```

---

## 背景の抜き方

生成ツールが透過PNGを出せるならそれが一番きれいです。出せない場合は**白一色の背景**で生成して、
あとから抜きます。

- **白背景で生成する。**グレーやグラデーションにしない
- 影を落とさせない（`no shadow on the ground` を入れてある理由）
- 抜きは Canva・Photopea・remove.bg などで数秒

透過なしの白背景のままでも、レンダラーは動きます（教室の壁がクリーム色なので、
そこまで破綻しません）。**まず白背景のまま1本作って、気になったら抜く**で十分です。

---

## 作ったあとの確認

- **5枚を並べて、顔の高さと体の大きさが揃っているか。** ここがブレると話ごとにキャラが伸縮して見える
- **`char_blink.png` が `char_explain.png` とぴったり重なるか。** ずれているとまばたきが跳ねる
- **指し棒が写っていないか。** 写っているとコードが描く棒と二重になる
- **文字や記号が入っていないか**
- **カワウソが1体だけか**

---

## 置き場所

```
pipeline/
  assets/
    char_explain.png
    char_surprise.png
    char_serious.png
    char_proud.png
    char_blink.png
```

Colabなら、ファイルをドラッグしてからノートブックの手順2を実行すれば `assets/` に移動します。
画像が無くてもグレーの代役で動くので、**先に流れだけ確認してから作っても構いません。**
