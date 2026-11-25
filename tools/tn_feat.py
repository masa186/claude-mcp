"""3チャンネル（Dream Clips・SMPクリップ・みんくら）のタイトルとナレーションを分ける規則と集計。docs/title_narration_3ch.md 用。"""
import re, statistics
NAMES=r'(ドクタードーナツ|ドクター・ドーナツ|ドーナツ|ドナっさん|ドリーム|Dream|Jettism|ジェディズム|Carvs|ミスタービースト|ベリティ|フェレックス|Farex|ダッシュ|NoLimitDash|Daquavis|ダクアビス|ウェンブー|Wemmbu|パロット|Parrot|オーネピクセル|トゥイクセル|Grox|グロックス|Marlow|マーロウ|テクノブレ[ーイ]ド|Flamefrags|flamefrags|steak|Steak|センパイスパイダー|Judelow|JudeLow|ジュデロウ|Camman18|Evbo|Swight|スケッピー|コブハ|ジョージ|George|サップナップ|エイジェイザボールド|ゴードンラムゼイ|Rekrap|Sharpness|ItzRealMe|Clementdav)'
PERSON_END=NAMES+r'$|(男|男たち|漢達|女|子ども|子供|キッズ|ガキ|人|勢|達|たち|プレイヤー|ニキ|先生|視聴者|村人|管理者|検察官|配信者|彼女|民|ゴーレム|怪物|組|彼|ゲームたち|ゲーム達|ニワトリ|ペンギン|いじめっ子)$'
def clean(t):
    t=re.sub(r'（.*?）|\(.*?\)|［.*?］|\[.*?\]|…（未完）|〜','',t)
    return t.strip().rstrip('。.!！…‥ ')
def sentences(t):
    return [s for s in re.split(r'[。！!]|(?<=ます)、|(?<=です)、',clean(t)) if s.strip()]
def ending(t):
    t=clean(t)
    if re.search(r'[？?]$',t): return '問いかけ'
    if re.search(r'こちら(です)?$',t): return 'こちら'
    if re.search(r'(と|ら|ば)、?こうな(ります|る|りました)$',t): return 'こうなる'
    if re.search(r'てはいけません$|ないで(ください)?$',t): return '禁止'
    if re.search(r'(ました|でした|だった|た件|なりました)$',t): return '過去・結果'
    if re.search(r'(ですが|なんですが|けど|だが|ですけど)[.…]*$',t): return 'ですが止め'
    if re.search(r'(ます|ません)$',t): return 'ます(予告・現在)'
    if re.search(r'です$',t): return 'です(断定)'
    if re.search(r'(瞬間|方法|違い|結果|末路|理由|正体|映像|動画|姿|反応|集|件について|話)$',t): return '体言(物事)'
    if re.search(PERSON_END,t): return '体言(人物)'
    if re.search(r'(せよ|しろ|はたけ|けろ|め)$',t): return '命令・お題'
    return '体言・その他'
def watch(t): return bool(re.search(r'(を|と)(見る|見守る|見ます|見守ります|聴く|聞く)|を見る|見守る|と見る|を見ます',t))
def has_num(t): return bool(re.search(r'[0-9０-９]|[一二三四五六七八九十百千万億]+(人|秒|分|年|日|回|個|万|億|円|位|マス|ブロック|時間|週間|体)',t))
def superl(t): return bool(re.search(r'史上|最強|最大|最長|最速|最悪|最高|世界一|世界最|世界[0-9]|初めて|人類初|世界初|唯一|究極|伝説|神業|奇跡|不可能|天才|ありえない|とんでもない|絶体絶命',t))
def twist(t): return bool(re.search(r'ですが|しかし|だが|数秒後|この後|このあと|直後|と思ったら|かと思|見せかけ|予想外|まさか',t))
def news(t): return bool(re.search(r'ご報告|同棲|彼女の|泣い|号泣|登録者|お知らせ|速報|発表|が来る|追加される|日常|歓喜|祝われ|問題発言',t))
def dr(t): return bool(re.search(r'ドクタードーナツ|ドクター・ドーナツ|ドーナツSMP管理者|ドナっさん|管理者ドクター',t))
def med(xs): return statistics.median(xs) if xs else float('nan')
def table(rows,key,val='rel',order=None,minn=3):
    g={}
    for r in rows: g.setdefault(key(r),[]).append(r[val])
    ks=order or sorted(g,key=lambda k:-med(g[k]))
    out=[]
    for k in ks:
        if k in g and len(g[k])>=minn: out.append((k,len(g[k]),round(med(g[k]),2)))
    return out
