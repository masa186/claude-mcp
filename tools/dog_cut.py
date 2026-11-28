"""犬の動画（That was not my dog・16.2秒）の切り方と、字幕・ナレーションの秒（SRT）を出す。

    python3 tools/dog_cut.py <出力SRT>
    CUT_MODULE=dog_cut python3 tools/noads_sample.py <元の動画> <ナレーションの wav> <作業フォルダ> <出力.mp4>

中身（元の秒）：
- 0.0〜4.4  骨を飾った犬小屋に入り、外を見て犬を待つ（犬は2.4秒ごろ遠くに小さく出る）
- 4.44     名札「Wolfy」の犬が入ってくる。4.6 で座らせる。4.7〜5.0 こちらを向いて座る
- 8.25〜10.75 寝室。犬は赤いじゅうたんで寝ている
- 12.5〜14.85 外に出て野原を見る → 14.85 振り返る
- 15.30    犬が2本足で立ち上がり、人のように走って逃げる（叫び声のような音。BGM の和音もここで変わる）
- 15.85    メニューを開いて「セーブしてタイトルへ」→ 16.15 タイトル画面で終わり

BGM は約2.2秒ごとに和音が変わる（2.24・4.44・6.61・…・15.30）。4.44 から始めると、和音の頭から始まる。
"""
import sys

FIT_FIRST = False
ZOOM_FIRST = False
DUCK = True
FADE = 0.0
SHIFT_Y = 106   # 元の動画のゲーム画面は 216px から。上部タイトルの帯（0〜322px）に隠れないよう、下へずらす

SEG = [
    (4.44, 16.23, 1.0, '0秒：名札「Wolfy」の犬が入ってくる → 座らせる → 寝室 → 外へ → 振り返ると2本足で立って逃げる → 即セーブして終了'),
]
FREEZE = 0.0

TOP = ('帰ってきた愛犬', '最後の1秒で即ログアウト')

# （種類, 元の秒 or None, 新しい秒 or None, 文）
LINES = [
    ('ナレーション', None, (0.0, 2.4), '10秒後、この犬は犬じゃなくなります。'),
    # 外を見ていて、振り返る直前。答え（15.30）の直前に「来るぞ」と知らせる。答えそのものには文字を重ねない
    ('見出し', (13.84, 15.24), None, '*振り返ると…*'),
    # メニューを開いた所でツッコミ（宝箱の「*マイクラに命捧げてて草*」と同じ、最後の一言）
    ('見出し', (15.85, 16.23), None, '*お前誰だよ*'),
]
# 100万超えの3本とベリティは、ナレーションの字幕が全部白
NARR_CHUNKS = [('10秒後、', 0.27, 'white'), ('この犬は', 0.25, 'white'), ('犬じゃなくなります', 0.48, 'white')]
END = ''


def to_new(t):
    acc = 0.0
    for a, b, sp, _ in SEG:
        if a <= t <= b:
            return acc + (t - a) / sp
        acc += (b - a) / sp
    return None


def fmt(t):
    s = t % 60
    return '%02d:%02d:%02d,%03d' % (int(t // 3600), int(t % 3600 // 60), int(s), round((s - int(s)) * 1000))


if __name__ == '__main__':
    total = sum((b - a) / sp for a, b, sp, _ in SEG)
    print('長さ %.2f秒' % total)
    out = []
    for kind, orig, new, text in LINES:
        s, e = new if new else (to_new(orig[0]), to_new(orig[1]))
        out.append((s, e, kind, text))
    out.sort()
    with open(sys.argv[1], 'w', encoding='utf-8') as f:
        for i, (s, e, kind, text) in enumerate(out, 1):
            f.write('%d\n%s --> %s\n[%s] %s\n\n' % (i, fmt(s), fmt(e), kind, text))
    for s, e, kind, text in out:
        print('  %5.2f〜%5.2f  %-8s %s' % (s, e, kind, text))
    for name, t in [('犬が入ってくる', 4.44), ('座ってこっちを見る', 4.8), ('寝室', 8.25), ('外へ', 12.5), ('振り返る', 14.85), ('2本足で立つ', 15.30), ('メニュー', 15.85), ('タイトル画面', 16.15)]:
        print('  %s：新 %.2f秒' % (name, to_new(t)))
