"""動画の音声を Whisper で時刻付きに書き起こす（日本語の回と英語の回の2回）。

    python3 tools/dream_asr.py <videos.json> <書き出し先ディレクトリ>

日本語の回: 日本語ナレーション（合成音声）を拾う。英語の部分も英字で出る。
英語の回  : 元の配信者の英語の台詞を、英語として正しく区切って拾う。
どちらも直前の文に引っ張られて同じ文を繰り返す癖があるので、
condition_on_previous_text は切る。no_speech_prob も残して、怪しい区間を後で判定できるようにする。

faster-whisper の音声読み込みが手元の PyAV と合わないので、ffmpeg で 16kHz に落として渡す。
"""
import os, sys, json, time, subprocess
import numpy as np
from faster_whisper import WhisperModel


def load(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', '16000',
                          '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def run(m, a, lang, words):
    segs, info = m.transcribe(a, language=lang, beam_size=5,
                              condition_on_previous_text=False,
                              word_timestamps=words)
    out = []
    for s in segs:
        d = dict(start=round(s.start, 2), end=round(s.end, 2), text=s.text.strip(),
                 no_speech=round(s.no_speech_prob, 2), logprob=round(s.avg_logprob, 2))
        if words and s.words:
            d['words'] = [(round(w.start, 2), round(w.end, 2), w.word) for w in s.words]
        out.append(d)
    return dict(lang=info.language, prob=round(info.language_probability, 2), segs=out)


if __name__ == '__main__':
    vids = json.load(open(sys.argv[1]))
    dst = sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    m = WhisperModel('large-v3-turbo', device='cpu', compute_type='int8', cpu_threads=3)
    for v in vids:
        p = os.path.join(dst, v['id'] + '.json')
        if os.path.exists(p):
            continue
        t = time.time()
        a = load(v['path'])
        try:
            ja = run(m, a, 'ja', True)
        except IndexError:
            # 語ごとの時刻合わせが空の区間で落ちることがある（faster-whisper の find_alignment）。
            # そのときは語の時刻なしで取り直す。
            ja = run(m, a, 'ja', False)
            ja['no_word_times'] = True
        r = dict(id=v['id'], ja=ja, en=run(m, a, 'en', False))
        json.dump(r, open(p, 'w'), ensure_ascii=False, indent=1)
        print('%s %s %.0fs' % (v['no'], v['id'], time.time() - t), flush=True)
    print('済', flush=True)
