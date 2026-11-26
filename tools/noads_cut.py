"""noads.mp4（ベリティのスピードラン）の自然版（約36秒・カット2回）の切り方と、字幕・ナレーションの秒（SRT）を出す。

    python3 tools/noads_cut.py <出力SRT>

区間は（元の開始秒, 元の終了秒, 速さ, 中身）。
- 前の約20秒の版（カットが多い）は tools/noads_cut_v3.py、34秒の版は tools/noads_cut_v2.py
- ユーザーの指摘「詰めすぎ・カットが多くて不自然」を受けて、カットはゲートの出入りと暗転の中の2回だけにした
"""
import sys

FIT_FIRST = False   # True なら最初の区間をナレーションの長さに伸ばす（前の版）。自然版では伸ばさない
ZOOM_FIRST = False  # True なら最初の区間を寄せる（前の版）
DUCK = True         # ナレーションの間、元の音を小さくする

SEG = [
    (5.78, 7.90, 1.0, '0秒：核爆弾（Nuclear TNT）を置いた瞬間（元の5.75秒にパッと出る）。ベリティと並ぶ → ゲートに火 → 飛び込む'),
    (12.20, 34.50, 1.0, 'ゲートから戻ると辺り一面クレーター（カット1：ゲートの出入りでつなぐ）→ 封印 → 2発目の核 → 宇宙の兵器 → 照準'),
    (39.00, 50.30, 1.0, '暗転の中でつなぐ（カット2）→ 発射 → 穴に飛び込む → 正体'),
]
FREEZE = 0.5  # 正体のコマを止めてツッコミを出す秒

# （種類, 元の秒 or None, 新しい秒 or None, 文）
LINES = [
    ('ナレーション', None, (0.0, 1.7), '3秒後、世界が消えます。'),
    ('見出し', (12.2, 12.9), None, '*ネザーから戻ると…*'),
    ('ベリティ', (13.8, 14.6), None, '…マジで？'),
    ('見出し', (15.6, 16.4), None, '*黒曜石で封印*'),
    ('ベリティ', (16.4, 18.7), None, 'その黒曜石、何に使うの？'),
    ('ベリティ', (20.0, 21.7), None, '待って、ボクを閉じ込めて行っちゃうの？'),
    ('ベリティ', (21.9, 23.2), None, 'ボクのこと忘れないでね！'),
    ('見出し', (23.2, 25.0), None, '*核爆弾 2発目*'),
    ('見出し', (28.0, 30.0), None, '*宇宙から撃つ兵器*'),
    ('見出し', (31.5, 34.5), None, '*照準中…*'),
    ('見出し', (41.0, 42.5), None, '*発射*'),
    ('見出し', (48.2, 49.4), None, '*確かめに行く*'),
]
END = '"もう二度とやらない"'


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
    print('つないだ長さ %.1f秒 ＋ 最後の止め %.1f秒 ＝ %.1f秒' % (total, FREEZE, total + FREEZE))
    acc = 0.0
    for a, b, sp, what in SEG:
        d = (b - a) / sp
        print('  新 %5.1f〜%5.1f ｜ 元 %5.2f〜%5.2f ×%.1f ｜ %s' % (acc, acc + d, a, b, sp, what)); acc += d
    out = []
    for kind, orig, new, text in LINES:
        s, e = new if new else (to_new(orig[0]), to_new(orig[1]))
        out.append((s, e, kind, text))
    out.append((total, total + FREEZE, '最後のツッコミ', END))
    out.sort()
    with open(sys.argv[1], 'w', encoding='utf-8') as f:
        for i, (s, e, kind, text) in enumerate(out, 1):
            f.write('%d\n%s --> %s\n[%s] %s\n\n' % (i, fmt(s), fmt(e), kind, text))
    for s, e, kind, text in out:
        print('  %5.1f〜%5.1f  %-8s %s' % (s, e, kind, text))
    for name, t in [('核とベリティ', 5.8), ('クレーターの床が見える', 12.75), ('クレーター全体とベリティ', 13.5), ('正体', 49.5)]:
        print('  %s：新 %.1f秒' % (name, to_new(t)))
