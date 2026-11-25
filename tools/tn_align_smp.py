"""SMP 332 の CSV 行を、自分の SMP チャンネル一覧（340本）に並び順でそろえる（Needleman-Wunsch）。"""
import csv, json, re, unicodedata, sys
SRC='/root/.claude/uploads/d40b6abd-0539-56e4-afba-6b5304d9c386/e7808219-SMP_clips_all_332_analysis_2.csv'
rows=list(csv.DictReader(open(SRC,encoding='utf-8-sig')))
rows=sorted(rows,key=lambda r:-int(r['動画番号']))  # 古い順
vids=sorted(json.load(open('tools/smp_1124.json'))['SMPクリップ']['vs'],key=lambda v:v['at'])
def norm(t):
    t=re.sub(r'#\S+','',t); t=unicodedata.normalize('NFKC',t)
    return re.sub(r'[\s、。,.!?！？「」『』()（）・…]+','',t).lower()
def bg(t): return {t[i:i+2] for i in range(len(t)-1)} or {t}
def sim(a,b):
    A,B=bg(norm(a)),bg(norm(b))
    return len(A&B)/max(1,min(len(A),len(B)))
def man(s):
    s=s.strip()
    m=re.match(r'([\d.]+)万',s)
    return float(m.group(1))*1e4 if m else None
def score(r,v):
    ph='未記録' in r['投稿タイトル']
    if not ph:
        s=3*sim(r['投稿タイトル'],v['title'])
        c=man(r['再生数'])
        if c:
            q=v['views']/c
            s+= 1.5 if 0.97<=q<=2.5 else (-1.5 if q<0.9 or q>6 else 0)
        return s
    return 2*max(sim(r['実際の冒頭ナレーション'],v['title']),sim(r['黄色タイトル'],v['title']))
n,m=len(rows),len(vids)
GR,GV=-1.0,-0.3
S=[[0.0]*(m+1) for _ in range(n+1)]; P=[[None]*(m+1) for _ in range(n+1)]
for i in range(1,n+1): S[i][0]=S[i-1][0]+GR; P[i][0]='u'
for j in range(1,m+1): S[0][j]=S[0][j-1]+GV; P[0][j]='l'
for i in range(1,n+1):
    for j in range(1,m+1):
        a=S[i-1][j-1]+score(rows[i-1],vids[j-1]); b=S[i-1][j]+GR; c=S[i][j-1]+GV
        S[i][j],P[i][j]=max((a,'d'),(b,'u'),(c,'l'))
i,j=n,m; pairs=[]
while i>0 or j>0:
    p=P[i][j]
    if p=='d': pairs.append((i-1,j-1)); i-=1; j-=1
    elif p=='u': pairs.append((i-1,None)); i-=1
    else: pairs.append((None,j-1)); j-=1
pairs.reverse()
out=[]
for a,b in pairs:
    if a is None: continue
    r=rows[a]; v=vids[b] if b is not None else None
    out.append({'no':int(r['動画番号']),'csv_title':r['投稿タイトル'],'csv_views':r['再生数'],
        'narration':r['実際の冒頭ナレーション'],'sec':r['発話秒数'],'chars':r['文字数'],'hook':r['フックの種類（0〜3秒映像）'],
        'top':r['黄色タイトル'],'feat':r['字幕・音声の特徴'],
        'id':v and v['id'],'title':v and v['title'],'views':v and v['views'],'at':v and v['at'][:10],'dur':v and v['sec'],
        'score':round(score(r,v),2) if v else None})
json.dump(out,open(sys.argv[1],'w'),ensure_ascii=False,indent=1)
print('rows',len(out),'unmatched rows',sum(1 for o in out if not o['id']),'skipped vids',sum(1 for a,b in pairs if a is None))
print('skipped vids:',[ (vids[b]['at'][:10],vids[b]['title'][:20],vids[b]['views']) for a,b in pairs if a is None])
