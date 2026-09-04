"""YouTube の URL を直接 Gemini に見せる（ダウンロードせずに中身を見る）。

    python3 ytask.py <videoId> "<聞きたいこと>"
"""
import os, sys, json, urllib.request
HOST='https://generativelanguage.googleapis.com'
MODEL=os.environ.get('GEMINI_MODEL','gemini-3-flash-preview')
for p in ('/root/yt-analysis/.env', os.path.join(os.path.dirname(os.path.abspath(__file__)),'.env')):
    if os.path.exists(p):
        for line in open(p,encoding='utf-8'):
            k,_,v=line.strip().partition('=')
            if k and v: os.environ.setdefault(k,v.strip())

def ask(vid, prompt, model=None, start=None, end=None):
    """start/end に "1:23:45" を渡すと、その区間だけを見せられる。
    11時間の配信から場面を探すのに要る。"""
    part = {'file_data': {'file_uri': 'https://www.youtube.com/watch?v=' + vid}}
    if start or end:
        md = {}
        if start: md['startOffset'] = start
        if end:   md['endOffset'] = end
        part['videoMetadata'] = md
    body=json.dumps({'contents':[{'parts':[part,{'text':prompt}]}],
        'generationConfig':{'temperature':0.3,'maxOutputTokens':4000}}).encode()
    r=urllib.request.Request(HOST+'/v1beta/models/%s:generateContent'%(model or MODEL),
        data=body, headers={'x-goog-api-key':os.environ['GEMINI_API_KEY'],
                            'Content-Type':'application/json'}, method='POST')
    with urllib.request.urlopen(r,timeout=600) as resp:
        j=json.loads(resp.read())
    try: return ''.join(p.get('text','') for p in j['candidates'][0]['content']['parts'])
    except Exception: return json.dumps(j,ensure_ascii=False)[:1200]

if __name__=='__main__':
    a=sys.argv[1:]
    print(ask(a[0], a[1], start=(a[2] if len(a)>2 else None),
              end=(a[3] if len(a)>3 else None)))
