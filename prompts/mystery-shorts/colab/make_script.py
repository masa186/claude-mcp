#!/usr/bin/env python3
# colab_onecell.py の NARRATION と BLOCKS から、収録用の台本を書き出す。
#
# 台本を手で持つと本体とすぐズレる。片方だけ直して録り直しになるので、
# 本体を正として毎回ここから出す。
#
#   python3 make_script.py

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "01_地球の音")
sys.path.insert(0, HERE)

import colab_onecell as C

HEAD = """VOICEVOX に1つずつ貼って、音声を保存してください。
保存する名前は 声1.wav / 声2.wav / … と、番号を順番につけること。
声0.wav はタイトルの読み上げ。作らなくても動くが、入れると頭が締まる。

設定は全ブロック共通で 速さ 1.05 / 高さ -0.04 / 抑揚 0.95。
（1.15 だと参考動画より1割ほど早口になります。実測 13.3拍/秒 対 11.4〜12.4拍/秒）
"""


def blocks():
    # 声0 があるときの割り当てに合わせる。タイトルは単独で1本
    return [[0]] + [[c for c in b if c != 0] for b in C.BLOCKS]


def main():
    lines = [HEAD]
    total = 0
    for i, block in enumerate(blocks()):
        body = "".join(C.NARRATION.get(c, "") for c in block)
        if not body:
            continue
        total += len(body)
        label = "・タイトル" if i == 0 else ""
        lines.append("━━━━━ 声%d.wav （%d文字%s）━━━━━" % (i, len(body), label))
        # 読点・句点で折り返す。改行そのものが間になるので、文の途中では折らない
        buf = ""
        for ch in body:
            buf += ch
            if ch in "。":
                lines.append(buf)
                buf = ""
        if buf:
            lines.append(buf)
        lines.append("")

    marks = sum(C.NARRATION.get(c, "").count(x)
                for b in blocks() for c in b for x in "。、")
    lines.append("計 %d文字 / 句読点 %d か所 + ブロックの継ぎ目 %d か所"
                 % (total, marks, len(blocks()) - 1))

    path = os.path.abspath(os.path.join(OUT, "ナレーション_分割.txt"))
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("書き出しました: %s" % path)

    full = os.path.abspath(os.path.join(OUT, "ナレーション_全文.txt"))
    body = []
    for cut in sorted(C.NARRATION):
        if cut == 0:
            continue
        body.append(C.NARRATION[cut])
    open(full, "w", encoding="utf-8").write("".join(body).replace("。", "。\n") + "\n")
    print("書き出しました: %s" % full)


if __name__ == "__main__":
    main()
