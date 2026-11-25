"""音の中身を AudioSet の分類器（AST）で1秒ごとにタグ付けする。

    python3 tools/dream_audiotag.py <videos.json> <書き出し先> <ASTモデルのディレクトリ>

こちら（Claude）は音を直接聞けない。Gemini も無料枠が尽きたので、
BGM・効果音・笑い声などは、この分類器の判定を「自動判定」として使う。
判定は確率なので、BGM があるかどうかは「Music 系のスコアが続いているか」で見る。

モデル: Xenova/ast-finetuned-audioset-10-10-0.4593（ONNX, 量子化版）
特徴量: Kaldi 互換の対数メルフィルタバンク（128本, 25ms/10ms, ハニング窓, プリエンファシス0.97）を
        numpy で計算。transformers の ASTFeatureExtractor が torch を要求するので自前で書いた。
        1024フレームまで0で埋め、平均 -4.2677393 / 標準偏差 4.5689974×2 で正規化（AST と同じ）。
窓    : 2秒の窓を1秒ずつずらす（短い効果音も拾うため）
"""
import os, sys, json, subprocess
import numpy as np
import onnxruntime as ort

SR = 16000


def _mel_banks(n_mels=128, nfft=512, sr=SR, low=20.0, high=None):
    high = high or sr / 2
    mel = lambda f: 1127.0 * np.log(1.0 + f / 700.0)
    ml, mh = mel(low), mel(high)
    d = (mh - ml) / (n_mels + 1)
    fm = mel(np.arange(nfft // 2) * sr / nfft)
    B = np.zeros((n_mels, nfft // 2 + 1), np.float64)
    for i in range(n_mels):
        l, c, r = ml + i * d, ml + (i + 1) * d, ml + (i + 2) * d
        up = (fm - l) / (c - l)
        dn = (r - fm) / (r - c)
        B[i, :nfft // 2] = np.maximum(0, np.minimum(up, dn))
    return B


_BANKS = _mel_banks()
_WIN = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(400) / 399)


def fbank(w):
    w = w.astype(np.float64)
    if len(w) < 400:
        w = np.pad(w, (0, 400 - len(w)))
    n = 1 + (len(w) - 400) // 160
    idx = np.arange(400)[None, :] + 160 * np.arange(n)[:, None]
    fr = w[idx]
    fr = fr - fr.mean(axis=1, keepdims=True)
    pre = fr.copy()
    pre[:, 1:] = fr[:, 1:] - 0.97 * fr[:, :-1]
    pre[:, 0] = fr[:, 0] - 0.97 * fr[:, 0]
    pre *= _WIN
    spec = np.abs(np.fft.rfft(pre, n=512)) ** 2
    m = spec @ _BANKS.T
    return np.log(np.maximum(m, np.finfo(np.float32).eps)).astype(np.float32)


def ast_input(w):
    f = fbank(w)[:1024]
    if len(f) < 1024:
        f = np.pad(f, ((0, 1024 - len(f)), (0, 0)))
    return ((f - (-4.2677393)) / (4.5689974 * 2))[None].astype(np.float32)
# BGM や効果音を見るのに使うラベル（AudioSet の名前そのまま）
WATCH = ['Speech', 'Music', 'Musical instrument', 'Electronic music', 'Synthesizer', 'Drum',
         'Piano', 'Orchestra', 'Heavy metal', 'Hip hop music', 'Video game music',
         'Laughter', 'Giggle', 'Screaming', 'Shout', 'Yell', 'Gasp',
         'Explosion', 'Boom', 'Whoosh, swoosh, swish', 'Boing', 'Sound effect',
         'Beep, bleep', 'Ding', 'Bell', 'Chime', 'Clapping', 'Cheering', 'Applause',
         'Silence', 'Burping, eructation', 'Fart', 'Squeak', 'Pop', 'Slap, smack',
         'Gunshot, gunfire', 'Crowd', 'Child speech, kid speaking', 'Female speech, woman speaking',
         'Male speech, man speaking', 'Narration, monologue', 'Tick', 'Thump, thud', 'Crunch']


def load(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', str(SR),
                          '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


if __name__ == '__main__':
    vids = json.load(open(sys.argv[1]))
    dst, mdir = sys.argv[2], sys.argv[3]
    os.makedirs(dst, exist_ok=True)
    cfg = json.load(open(os.path.join(mdir, 'config.json')))
    id2 = {int(k): v for k, v in cfg['id2label'].items()}
    lab2 = {v: k for k, v in id2.items()}
    watch = [w for w in WATCH if w in lab2]
    so = ort.SessionOptions(); so.intra_op_num_threads = 2
    sess = ort.InferenceSession(os.path.join(mdir, 'model_quantized.onnx'), so)
    iname = sess.get_inputs()[0].name
    only = set(sys.argv[4:])
    for v in vids:
        if only and v['id'] not in only:
            continue
        p = os.path.join(dst, v['id'] + '.json')
        if os.path.exists(p):
            continue
        a = load(v['path'])
        n = int(len(a) / SR)
        rows = []
        for t in range(0, max(1, n - 1)):
            seg = a[t * SR:(t + 2) * SR]
            x = ast_input(seg)
            logit = sess.run(None, {iname: x})[0][0]
            prob = 1 / (1 + np.exp(-logit))
            top = np.argsort(-prob)[:5]
            rows.append(dict(t=t, top=[(id2[int(i)], round(float(prob[i]), 2)) for i in top],
                             w={w: round(float(prob[lab2[w]]), 2) for w in watch}))
        json.dump(dict(id=v['id'], win=2, hop=1, rows=rows), open(p, 'w'), ensure_ascii=False)
        print(v['no'], v['id'], len(rows), flush=True)
    print('済', flush=True)
