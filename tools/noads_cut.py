"""noads.mp4（ベリティのスピードラン）の最強版（約20秒）の切り方と、字幕・ナレーションの秒（SRT）を出す。

    python3 tools/noads_cut.py <出力SRT>

区間は（元の開始秒, 元の終了秒, 速さ, 中身）。速さ 0.5 は半分の速さ（スロー）。
前の決定版（34秒）は tools/noads_cut_v2.py。
"""
import sys

SEG = [
    (7.00, 7.55, 0.4, '0秒：核爆弾ブロックとベリティが並ぶ画を、約0.4倍の速さで寄りながら（音は消す）'),
    (7.55, 8.05, 1.0, 'ゲートに入る'),
    (8.05, 8.55, 1.0, 'ネザー'),
    (12.0, 14.7, 1.0, '戻ると辺り一面クレーター・ベリティが浮いている・マジで？'),
    (16.4, 18.7, 1.0, '黒曜石で封印・その黒曜石何に使うの？'),
    (20.0, 23.2, 1.0, '閉じ込めて行っちゃうの？忘れないでね！'),
    (23.2, 25.0, 1.0, '2発目の核・空いっぱいの輪'),
    (28.0, 29.4, 1.0, '宇宙から撃つ兵器を出す'),
    (40.0, 41.0, 1.0, '照準の円が閉じる'),
    (41.0, 43.0, 1.0, '宇宙からビーム'),
    (48.2, 50.3, 1.0, '穴に飛び込む→正体'),
]
FREEZE = 0.6  # 正体のコマを止めてツッコミを出す秒

# （種類, 元の秒 or None, 新しい秒 or None, 文）
LINES = [
    ('ナレーション', None, (0.0, 1.4), '3秒後、世界が消えます。'),
    ('見出し', (7.55, 8.55), None, '*ネザーへ避難*'),
    ('見出し', (12.0, 12.7), None, '*戻ると…*'),
    ('ベリティ', (13.8, 14.6), None, '…マジで？'),
    ('ベリティ', (16.4, 18.7), None, 'その黒曜石、何に使うの？'),
    ('ベリティ', (20.0, 21.7), None, '待って、ボクを閉じ込めて行っちゃうの？'),
    ('ベリティ', (21.9, 23.2), None, 'ボクのこと忘れないでね！'),
    ('見出し', (23.2, 25.0), None, '*核爆弾 2発目*'),
    ('見出し', (28.0, 29.4), None, '*宇宙から撃つ兵器*'),
    ('見出し', (41.0, 42.5), None, '*発射*'),
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
    for name, t in [('クレーターの床が見える', 12.75), ('クレーター全体とベリティ', 13.5), ('正体', 49.5)]:
        print('  %s：新 %.1f秒' % (name, to_new(t)))
