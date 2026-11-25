"""data/ と reports/ を安全に作り直す。

    python3 mcshorts/integrate.py           # 確かめるだけ（data/ と reports/ は変えない）
    python3 mcshorts/integrate.py --apply   # 確かめてから反映する

1. 一時フォルダに組み立てる（data/ と reports/ には書かない）
2. 今の data/ にある観測・書き起こし・分析結果が、すべて新しい方にも残っているかを確かめる
3. 1つでも消えていたら止める（何も反映しない）
4. --apply のときだけ、変わったファイルを data/ と reports/ に写す。ファイルは消さない
"""
import argparse
import filecmp
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_dataset  # noqa: E402

OBS_FIELDS = ('title', 'published', 'duration_sec', 'views')


def _jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]


def _key(d):
    return json.dumps(d, ensure_ascii=False, sort_keys=True)


def verify_preserved(old_dir, new_dir):
    """old_dir（今の data/）の中身が new_dir（作り直した data/）にすべて残っているか。問題の一覧を返す。"""
    problems = []
    old_v = {(r['channel'], r['video_id']): r for r in _jsonl(os.path.join(old_dir, 'videos.jsonl'))}
    new_v = {(r['channel'], r['video_id']): r for r in _jsonl(os.path.join(new_dir, 'videos.jsonl'))}
    for k, r in old_v.items():
        n = new_v.get(k)
        if n is None:
            problems.append(f'videos: {k} が消えた')
            continue
        for fld in OBS_FIELDS:
            have = {_key(o) for o in n.get(fld, [])}
            for o in r.get(fld, []):
                if _key(o) not in have:
                    problems.append(f'videos: {k} の {fld} の観測が消えた（source={o.get("source")}）')
        if not set(r.get('in_sources', [])) <= set(n.get('in_sources', [])):
            problems.append(f'videos: {k} の in_sources が減った')
        for ek, ev in r.get('extra', {}).items():
            if n.get('extra', {}).get(ek) != ev:
                problems.append(f'videos: {k} の extra.{ek} が変わった')

    tdir_old = os.path.join(old_dir, 'transcripts')
    for ch in sorted(os.listdir(tdir_old)) if os.path.isdir(tdir_old) else []:
        for name in sorted(os.listdir(os.path.join(tdir_old, ch))):
            po = os.path.join(tdir_old, ch, name)
            pn = os.path.join(new_dir, 'transcripts', ch, name)
            if not os.path.exists(pn):
                problems.append(f'transcripts: {ch}/{name} が消えた')
                continue
            old_t = json.load(open(po, encoding='utf-8'))['transcripts']
            new_t = {_key(t) for t in json.load(open(pn, encoding='utf-8'))['transcripts']}
            for t in old_t:
                if _key(t) not in new_t:
                    problems.append(f'transcripts: {ch}/{name} の書き起こしが消えた（source={t.get("source")}）')

    new_f = {_key(f) for f in _jsonl(os.path.join(new_dir, 'features.jsonl'))}
    for f in _jsonl(os.path.join(old_dir, 'features.jsonl')):
        if _key(f) not in new_f:
            problems.append(f"features: {f['channel']}/{f['video_id']} の {f['source']} が消えた")
    return problems


def _changed_files(src, dst):
    """src にあって、dst に無いか中身が違うファイル（相対パス）。"""
    out = []
    for dirpath, _, names in os.walk(src):
        for name in names:
            s = os.path.join(dirpath, name)
            rel = os.path.relpath(s, src)
            d = os.path.join(dst, rel)
            if not os.path.exists(d) or not filecmp.cmp(s, d, shallow=False):
                out.append(rel)
    return sorted(out)


def run(apply=False, staging=None, target=HERE, **build_kwargs):
    staging = staging or tempfile.mkdtemp(prefix='mcshorts-staging-')
    build_dataset.build(out=staging, **build_kwargs)
    problems = verify_preserved(os.path.join(target, 'data'), os.path.join(staging, 'data'))
    changed = {sub: _changed_files(os.path.join(staging, sub), os.path.join(target, sub))
               for sub in ('data', 'reports')}
    result = {'staging': staging, 'problems': problems, 'changed': changed, 'applied': False}
    if problems or not apply:
        return result
    for sub, rels in changed.items():
        for rel in rels:
            dst = os.path.join(target, sub, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(staging, sub, rel), dst)
    result['applied'] = True
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='確かめてから data/ と reports/ に反映する')
    args = ap.parse_args()
    r = run(apply=args.apply)
    print('作り直した場所:', r['staging'])
    if r['problems']:
        print(f"止めた：既存の記録が {len(r['problems'])} 件消える。何も反映していない")
        for p in r['problems'][:50]:
            print('  -', p)
        sys.exit(1)
    print('既存の記録はすべて残っている')
    for sub, rels in r['changed'].items():
        print(f'{sub}/ で変わる・増えるファイル: {len(rels)} 件')
        for rel in rels[:20]:
            print('  -', rel)
    print('反映した' if r['applied'] else '反映していない（--apply で反映）')


if __name__ == '__main__':
    main()
