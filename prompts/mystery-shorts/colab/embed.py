#!/usr/bin/env python3
# colab_onecell.py と voicevox_colab.py を 押すだけ.ipynb のセル①に埋め込み直す。
#
# ノートブックは1ファイルで完結させたいので、パイプライン本体を r''' ''' の
# 文字列として持っている。手で貼り替えると事故るのでこれを使う。
#
#   python3 embed.py

import hashlib
import json
import os
import re
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


GUARD = '''
import os as _os
EXPECT = "%s"
_have = open("pipeline.ver").read().strip() if _os.path.exists("pipeline.ver") else ""
if _have != EXPECT:
    raise SystemExit("ノートブックが新しくなっています。①をもう一度押してください。\\n"
                     "（①が pipeline.py を書き出します。押さないと古いままです）")
'''


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

    # ①を押さずに④を回すと、古い pipeline.py がそのまま動いて
    # 「差し替えたのに何も変わらない」になる。版を刻んで気づけるようにする
    # 版そのものを除いて計算する。含めると押すたびに値が変わってしまう
    bare = re.sub(r'VERSION = "[0-9a-f]*"', 'VERSION = ""', src)
    ver = hashlib.sha256(bare.encode("utf-8")).hexdigest()[:12]
    src = re.sub(r'VERSION = "[0-9a-f]*"', 'VERSION = "%s"' % ver, src)
    if 'VERSION = "' not in src:
        src = src.replace('open("pipeline.py", "w", encoding="utf-8").write(PIPELINE)',
                          'VERSION = "%s"\n'
                          'open("pipeline.py", "w", encoding="utf-8").write(PIPELINE)\n'
                          'open("pipeline.ver", "w").write(VERSION)' % ver)
    nb["cells"][1]["source"] = src.splitlines(keepends=True)

    for i in (2, 3, 4, 5):
        cell = "".join(nb["cells"][i]["source"])
        cell = re.sub(r'EXPECT = "[0-9a-f]*"', 'EXPECT = "%s"' % ver, cell)
        if "EXPECT" not in cell:
            head = cell.split("\n")
            k = next((j for j, l in enumerate(head)
                      if l.startswith("import ") or l.startswith("from ")), len(head))
            head.insert(k, GUARD % ver)
            cell = "\n".join(head)
        nb["cells"][i]["source"] = cell.splitlines(keepends=True)
    json.dump(nb, open(NB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("埋め込みました（%d文字）" % len(src))


if __name__ == "__main__":
    main()
