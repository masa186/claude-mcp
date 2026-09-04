# 切り抜きの作り方（こちらができること・できないこと）

## できないこと ── YouTube からの取得

`yt-dlp` を入れて試したが、プロキシが 403 を返して落とせない。

    ERROR: Unable to download API page: Tunnel connection failed: 403 Forbidden

ネットワーク方針で塞がれているので、ここは迂回しない。
**元動画のダウンロードは、そちらの手元でやってもらう必要がある。**

## できること ── URL だけで中身を読んで和訳する

Gemini は YouTube の URL をそのまま読める。**ダウンロードは要らない。**
`tools/ytask.py` にまとめた。

    python3 tools/ytask.py <videoId> "<聞きたいこと>"

これで次のことが URL だけでできる:

  ・一字一句の書き起こし（秒数つき）
  ・切り抜き用の日本語訳（直訳ではなくネット実況の言葉に置換）
  ・話者の割り当て
  ・「一番おいしい区間」の指定
  ・企画・カット・くだり・画面・音の分析

手元にファイルがある場合は `tools/askav.py <ファイル> "<質問>"`。

## 実際に出た字幕（33.9秒の見本から）

    [00:00-00:02] Speed | Die! Die! Die!            | 死ね！死ね！死ね！
    [00:02-00:04] Speed | Kai we about to do it.     | やば、Kai、いけるぞ！
    [00:04-00:06] Speed | Get him! One more!         | やれ！やれ！あと一発！
    [00:06-00:08] Speed | GET HIM! YEAH!             | いったあああ！よっしゃ！
    [00:08-00:11] Kai   | [Screaming]                | [絶叫]
    [00:11-00:13] Speed | Oh my god!                 | まじかよ！
    [00:16-00:19] Speed | Say wallahi we did it bro! | マジで勝ったわ、ブラザー！
    [00:27-00:29] Speed | We fucking did it chat.    | マジで勝ったぞ、お前ら！
    [00:31-00:33] Speed | [Dancing]                  | [ダンス]

    → 一番おいしい区間 00:04-00:11

**書き起こしは鵜呑みにしない。** 0.5秒ごとの音量を測って、
字幕が付いている区間すべてに実際に音があることを確かめた
（最小 -33.4dB、全区間で発声あり）。無音に字幕を当てる捏造は無かった。
ただし話者の割り当ては誤りが混じる（21〜27秒を Donut 一人にしていたが、
実際は掛け合いに見える）。ここは目で確認すること。

## 分担

    そちら  元配信をダウンロードする／編集して書き出す
    こちら  URL から書き起こし・和訳・区間の選定・型の分析
            効果音の合成、画面の割り付けの数値、実測での検証

**URL を送ってもらうだけで、字幕の台本まで出せる。**
ファイルを上げてもらう必要すらない。

## 素材の在り処（2026年8月のエンダードラゴン回）

    iShowSpeed 公式（生配信のアーカイブ）
      MINECRAFT HARDCORE ALL BOSSES DAY 1  2026-08-08
      MINECRAFT HARDCORE ALL BOSSES DAY 5  2026-08-12  ft. KaiCenat
      （見本の画面には DAY 6 と出ていたので、最終回は別途探す）

    ドクタードーナツ側
      DrDonut Reacts   登録457,000 / 2,535本  ← リアクション専門
      DrDonut Archive  登録 30,000 /    20本
      DrDonut          本体
      DrDonut Clips    切り抜き

**DrDonut Reacts は本人が6〜30秒の切り抜きを大量に出していて、
それ自体がよく伸びている。**

    30秒  8,109,340回  cursed minecraft.exe
     6秒    837,674回  "its just a prank bro"
     9秒    668,071回  The Bench Edit
     8秒    237,043回  FAREX PULL MY PEARL!!!!

素材の出どころであると同時に、**短尺で伸びる証拠**でもある。
