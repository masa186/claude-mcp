"""ナレーションを丸ごと録り直す。1本の中で声が混ざるのを断ち切るための作業用。

なぜ要るか:
  行ごとのキャッシュは「一番手のモデルの名前」で鍵を作っていた時期があり、
  枠切れで別のモデルに落ちた音が、同じ棚に混ざって積まれている。
  どの行がどのモデルで録れたのかは、もう音からは分からない（測ってみたが、
  短い行では中身の違いに埋もれて判別できなかった）。
  なので「選り分ける」のではなく「全部捨てて1つのモデルで録り直す」。

やること:
  1. 視聴者役の声を選ぶ。候補を1行ずつ合成して、カワウソ（Charon）から
     一番遠いものを取る。遠さは長時間平均スペクトルの距離で測る。
  2. その日に使えるモデルを1つ選び、全行をそのモデルだけで録る。
     途中で枠が切れたら、次のモデルへは行かず、そこで止める（混ぜない）。
  3. 何行録れたかを出す。全部録れていなければ、翌日もう一度走らせる。
     録れた行は残るので、続きから進む。

  python3 revoice.py             第1話を録り直す
  python3 revoice.py --audition  視聴者役の候補を聞き比べるだけ
  python3 revoice.py --plan      何をするかだけ出す（APIを叩かない）
"""
import os, sys, time
import numpy as np
import gtts, voice, render

EPISODE = 'ep01.py'
CANDIDATES = ['Iapetus', 'Sadaltager', 'Algenib']   # 視聴者役の候補
SAMPLE = 'え、なんでなん。ほんまに？'


def shots():
    src = open(EPISODE, encoding='utf-8').read()
    body = src[src.index('render.SHOTS = ['):src.index('render.CHAPTERS')]
    ns = {'render': render, 'MUSTARD': render.MUSTARD, 'CRIMSON': render.CRIMSON}
    exec(body, ns)
    render.DURATION = render.build()
    return render.SHOTS


def ltas(x, nb=32):
    """長時間平均スペクトル。声の持ち主の癖が出る。"""
    v = x[np.abs(x) > 0.01]
    if len(v) < 4096:
        return None
    W = 2048; w = np.hanning(W); acc = np.zeros(W // 2 + 1); n = 0
    for i in range(0, len(v) - W, W // 2):
        acc += np.abs(np.fft.rfft(v[i:i + W] * w)); n += 1
    S = acc / n
    fr = np.fft.rfftfreq(W, 1 / voice.SR)
    ed = np.logspace(np.log10(80), np.log10(8000), nb + 1)
    e = np.log10(np.array([S[(fr >= a) & (fr < b)].sum()
                           for a, b in zip(ed[:-1], ed[1:])]) + 1e-9)
    return (e - e.mean()) / (e.std() + 1e-9)


def usable_model():
    """今日まだ喋れるモデルを1つ返す。短い1行を投げて確かめる。"""
    for m in gtts.MODELS:
        if len(gtts.say('てすと。', model=m)):
            return m
    return None


def audition(model):
    """視聴者役を選ぶ。カワウソから一番遠い声を取る。"""
    base = gtts.say(SAMPLE, voice=gtts.VOICE, model=model)
    if not len(base):
        return None
    b = ltas(voice.resample(base, gtts.SR))
    best = None
    for v in CANDIDATES:
        x = gtts.say(SAMPLE, voice=v, model=model)
        if not len(x):
            print('  %s は録れなかった' % v); continue
        f = ltas(voice.resample(x, gtts.SR))
        d = float(np.linalg.norm(f - b)) if f is not None and b is not None else 0.0
        print('  %-12s カワウソからの遠さ %.2f' % (v, d))
        if best is None or d > best[1]:
            best = (v, d)
    return best[0] if best else None


def main():
    sh = shots()
    ls = voice.lines(sh)
    who = [voice._who_of(sh[i]) for i, _ in ls]
    print('第1話 %d行（カワウソ %d / 視聴者 %d）'
          % (len(ls), sum(1 for w in who if w == gtts.VOICE),
             sum(1 for w in who if w != gtts.VOICE)))
    if '--plan' in sys.argv:
        for (i, t), w in zip(ls, who):
            print('  %-10s %s' % (w, t))
        return

    model = usable_model()
    if not model:
        print('今日はどのモデルも枠切れ。明日もう一度走らせる。')
        return
    print('使うモデル: %s' % model)

    if '--audition' in sys.argv:
        v = audition(model)
        print('→ 視聴者役は %s。GEMINI_VOICE_VIEWER に入れて使う' % v)
        return

    # ここから本番。全行を1つのモデルだけで録る。
    made = skipped = 0
    for key in sorted(set(zip(who, [voice._style_of(sh[i]) for i, _ in ls]))):
        w, st = key
        grp = [k for k, ((i, t), ww) in enumerate(zip(ls, who))
               if (ww, voice._style_of(sh[i])) == key]
        need = [k for k in grp
                if not os.path.exists(voice._line_file(ls[k][1], st, model, w))]
        if not need:
            skipped += len(grp); continue
        print('  %s: %d行' % (w, len(need)))
        segs = gtts.say_script([ls[k][1] for k in need], voice=w,
                               style=gtts.STYLES.get(st), model=model)
        if segs is None:
            print('    ここで枠切れ。次のモデルへは行かない（声を混ぜない）')
            break
        for k, x in zip(need, segs):
            y = voice.squeeze(voice.trim_silence(
                voice.resample(x, gtts.SR), 0.010))
            voice._save_line(voice._line_file(ls[k][1], st, model, w), y)
            made += 1
        time.sleep(2)

    have = sum(os.path.exists(voice._line_file(
        t, voice._style_of(sh[i]), model, w)) for (i, t), w in zip(ls, who))
    print('\n%s で %d/%d行（今回作った %d / もとからあった %d）'
          % (model, have, len(ls), made, skipped))
    if have < len(ls):
        print('まだ足りない。枠が戻った日にもう一度走らせると続きから進む。')
    else:
        print('全行そろった。python3 ep01.py で書き出せる。')


if __name__ == '__main__':
    main()
