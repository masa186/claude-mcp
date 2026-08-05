#!/usr/bin/env python3
# colab_onecell.py と voicevox_colab.py を 押すだけ.ipynb のセル①に埋め込み直す。
#
# ノートブックは1ファイルで完結させたいので、パイプライン本体を r''' ''' の
# 文字列として持っている。手で貼り替えると事故るのでこれを使う。
#
#   python3 embed.py

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NB = os.path.join(HERE, "押すだけ.ipynb")
PARTS = [("PIPELINE", "colab_onecell.py"), ("VOICEVOX", "voicevox_colab.py")]


def block(name, fn):
    body = open(os.path.join(HERE, fn), encoding="utf-8").read()
    if "'''" in body:
        sys.exit("%s に ''' が入っています。r''' で囲めないので、"
                 "docstring を # のコメントに直してください。" % fn)
    if body.endswith("\\"):
        sys.exit("%s が円記号で終わっています。" % fn)
    return "%s = r'''\n%s'''\n" % (name, body)


def main():
    nb = json.load(open(NB, encoding="utf-8"))
    src = "".join(nb["cells"][1]["source"])

    for name, fn in PARTS:
        head = "\n%s = r'''\n" % name
        i = src.find(head)
        if i < 0:
            sys.exit("セル①に %s の埋め込み位置が見つかりません。" % name)
        j = src.find("\n'''\n", i + len(head))
        if j < 0:
            sys.exit("%s の終わりが見つかりません。" % name)
        src = src[:i + 1] + block(name, fn) + src[j + len("\n'''\n"):]

    nb["cells"][1]["source"] = src.splitlines(keepends=True)
    json.dump(nb, open(NB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("埋め込みました（%d文字）" % len(src))


if __name__ == "__main__":
    main()
