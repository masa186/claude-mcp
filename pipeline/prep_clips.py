"""動画素材を、黒板スクリーンに映す用のフレーム連番に切り出す。

黒板は縦長なので、16:9の素材をそのまま貼ると余白だらけになる。
実際の教室と同じで「黒板の前にスクリーンが降りてくる」形にするため、
16:9のスクリーン矩形に合わせて中央を切り出す。
"""
import os, subprocess, sys
import imageio_ffmpeg as ie

FF = ie.get_ffmpeg_exe()
W = 900                      # スクリーンの横幅（1080幅の動画に対して）
H = int(W * 9 / 16)

# 名前: (元ファイル, 開始秒, 長さ秒, 拡大率)
CLIPS = {
    'plane':   ('clips/src1.mp4', 1.0, 4.0, 1.0),   # 高高度の飛行機と飛行機雲
    'plane2':  ('clips/src2.mp4', 2.0, 3.5, 1.0),   # 別アングル
    'prop':    ('clips/src3.mp4', 1.5, 3.5, 1.0),   # プロペラ機
    'wing':    ('clips/src4.mp4', 2.0, 4.0, 1.0),   # 翼のアップ（縦素材）
    # 第3話（ペンギン）。実測で1コマ目は実写13/20・明るい16/20だった。
    # 黒板から始めた第1話は冒頭離脱71.1%、実写から始めた第2話は43.2%。
    # 最後の数字は寄せ具合。1.0のまま切ったら、スクリーンの中で被写体が
    # 小さすぎた。スマホの実寸では何が写っているか分からない。
    'peng':    ('clips/src5.mp4', 1.0, 4.0, 1.8),   # 雪の上に1羽。奥に暗い海（縦素材）
    'peng2':   ('clips/src6.mp4', 0.5, 4.0, 2.2),   # 皇帝ペンギンの群れ。氷原で明るい
    'peng3':   ('clips/src7.mp4', 3.0, 3.5, 1.0),   # 顔のアップ（縦素材）
    'peng4':   ('clips/src8.mp4', 1.0, 3.5, 1.4),   # 明るい砂地に1羽
    # 第5話（冷蔵庫）。実測では1コマ目は 実写13/20・明るい16/20 だった。
    'fridge':  ('clips/src9.mp4',  0.3, 2.8, 1.0),  # 明るい庫内。野菜と手（縦素材）
    'fridge2': ('clips/src10.mp4', 1.5, 3.5, 1.0),  # 扉を開けているところ
    'fridge3': ('clips/src11.mp4', 2.0, 3.0, 1.0),  # 庫内から取り出す人（縦素材）
    'fridge4': ('clips/src12.mp4', 4.0, 3.0, 1.2),  # 白いキッチン
    # 第7話（缶詰）。参考3チャンネル6本の画面の埋まりは66〜85%、こちらは30%
    # だった。内訳を測ると board のショットが11.6%で、黒板の緑が空いている。
    # 実写のショットは画面を全部使えるので、埋まりを上げるならここが効く。
    'cans':    ('clips/src18.mp4', 2.0, 3.5, 1.0),  # 棚にぎっしり並んだ缶詰
    'cans2':   ('clips/src19.mp4', 0.5, 3.0, 1.0),  # 店の棚（縦素材）
    'canline': ('clips/src13.mp4', 1.0, 3.0, 1.0),  # 製造ライン。缶が流れる
    'oldcan':  ('clips/src15.mp4', 1.5, 3.0, 1.3),  # 錆びた古い缶。昔の話に
    'rusty':   ('clips/src16.mp4', 2.0, 3.5, 1.0),  # 吊るされた錆缶（縦素材）
    'pulltab': ('clips/src14.mp4', 3.0, 3.5, 1.0),  # プルタブで開ける手元（縦素材）
    'pulltab2':('clips/src17.mp4', 2.0, 3.0, 1.0),  # 別アングル（縦素材）
    # 全面に敷く用（9:16で切る）。0秒はフィードでサムネになるので、
    # ここだけは画面いっぱいに実写を出す
    'cansV':   ('clips/src18.mp4', 2.0, 3.5, 1.0),
    'cans2V':  ('clips/src19.mp4', 0.5, 3.0, 1.0),
    'canlineV':('clips/src13.mp4', 1.0, 3.0, 1.0),
    'rustyV':  ('clips/src16.mp4', 2.0, 3.5, 1.0),
    'pulltabV':('clips/src14.mp4', 3.0, 3.5, 1.0),
    'pulltab2V':('clips/src17.mp4', 2.0, 3.0, 1.0),
    'jarV':    ('clips/src20.mp4', 1.0, 3.0, 1.0),   # 瓶のフタを握る（縦素材）
    'jaropenV':('clips/src20.mp4', 12.5, 3.0, 1.0),  # フタが外れる瞬間（縦素材）
}


# 全面に敷く用は縦（9:16）で切り出す。スクリーンに映す用の16:9を
# あとから縦に切り直すと、横長のときに端しか残らない。
# 実際、錆缶の回は草しか映らなくなっていた。
VW, VH = 720, 1280
VERT = {'cansV', 'cans2V', 'canlineV', 'rustyV', 'pulltabV', 'pulltab2V',
        'jarV', 'jaropenV'}


def prep(name, src, ss, dur, zoom=1.0):
    out = 'clips/%s' % name
    os.makedirs(out, exist_ok=True)
    if os.listdir(out):
        print('  %-8s 既にあり' % name)
        return
    if name in VERT:
        vf = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d"
              % (int(VW*zoom), int(VH*zoom), VW, VH))
    else:
        # 中央を切って16:9に合わせる
        vf = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d"
              % (int(W*zoom), int(H*zoom), W, H))
    subprocess.run([FF, '-y', '-v', 'error', '-ss', str(ss), '-t', str(dur),
                    '-i', src, '-vf', vf + ',fps=30',
                    '-q:v', '3', out + '/%04d.jpg'], check=True)
    print('  %-8s %d枚' % (name, len(os.listdir(out))))


if __name__ == '__main__':
    print('スクリーン用に切り出し中（%dx%d）...' % (W, H))
    for n, (src, ss, dur, z) in CLIPS.items():
        if os.path.exists(src):
            prep(n, src, ss, dur, z)
        else:
            print('  %-8s 元ファイルなし: %s' % (n, src))
