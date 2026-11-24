"""冒頭5秒と最後7秒だけを、日本語指定で書き起こし直す。

    python3 tools/dream_asr_edges.py <videos.json> <書き出し先ディレクトリ>

全編を一度に書き起こすと、英語の元音声が大きい動画では日本語ナレーションが英語に負けて消える
（#16, #17 で実際に起きた）。ナレーションは冒頭と最後にしか無いことが多いので、
そこだけ切り出し、「日本語のナレーション」という手がかりを与えて書き起こす。
"""
import os, sys, json, subprocess
import numpy as np
from faster_whisper import WhisperModel


def load(p, ss=None, t=None):
    cmd = ['ffmpeg', '-v', 'error']
    if ss is not None:
        cmd += ['-ss', str(ss)]
    cmd += ['-i', p]
    if t is not None:
        cmd += ['-t', str(t)]
    cmd += ['-ac', '1', '-ar', '16000', '-f', 'f32le', '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)


def run(m, a, off):
    segs, _ = m.transcribe(a, language='ja', beam_size=5, condition_on_previous_text=False,
                           initial_prompt='日本語のナレーション')
    return [dict(start=round(s.start + off, 2), end=round(s.end + off, 2), text=s.text.strip(),
                 no_speech=round(s.no_speech_prob, 2)) for s in segs]


if __name__ == '__main__':
    vids = json.load(open(sys.argv[1]))
    dst = sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    m = WhisperModel('large-v3-turbo', device='cpu', compute_type='int8', cpu_threads=2)
    for v in vids:
        p = os.path.join(dst, v['id'] + '.json')
        if os.path.exists(p):
            continue
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                    '-of', 'csv=p=0', v['path']], capture_output=True, text=True).stdout)
        head = run(m, load(v['path'], t=5.0), 0.0)
        ss = max(0.0, dur - 7.0)
        tail = run(m, load(v['path'], ss=ss), ss)
        json.dump(dict(id=v['id'], head=head, tail=tail), open(p, 'w'), ensure_ascii=False, indent=1)
        print(v['no'], v['id'], ' / '.join(s['text'] for s in head)[:60], '||',
              ' / '.join(s['text'] for s in tail)[:60], flush=True)
    print('済', flush=True)
