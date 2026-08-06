# -*- coding: utf-8 -*-
# colab_onecell.py の作品データを project.py の内容に差し替える
import importlib.util, re, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = "/home/user/claude-mcp/prompts/mystery-shorts/colab/colab_onecell.py"

s = importlib.util.spec_from_file_location("p", os.path.join(HERE, "project.py"))
P = importlib.util.module_from_spec(s); s.loader.exec_module(P)

def q(t):
    assert "'" not in t, t
    return "'%s'" % t

cuts = []
for cut, t1, t2, hl, hlc, cam, _ in P.ROWS:
    cuts.append("    {'cut': '%d', 'telop1': %s, 'telop2': %s, 'hl': %s, "
                "'hl_color': %s, 'camera': %s, 'asset': 'A00', 'item_end': '%d'},"
                % (cut, q(t1), q(t2), q(hl), q(hlc), q(cam),
                   1 if cut in P.ITEM_END else 0))
CUTS = "CUTS = [\n" + "\n".join(cuts) + "\n]"

narr = ["    %d: %s," % (c, q(n)) for c, _, _, _, _, _, n in P.ROWS if n]
NARR = "NARRATION = {\n" + "\n".join(narr) + "\n}"

BLOCKS = "BLOCKS = [\n" + "\n".join("    %r," % b for b in P.BLOCKS) + "\n]"
SEARCH = "SEARCH = {\n" + "\n".join("    %d: %r," % (k, v) for k, v in sorted(P.SEARCH.items())) + "\n}"
PROMPTS = "PROMPTS = {\n" + "\n".join("    %d: %s," % (k, q(v)) for k, v in sorted(P.PROMPTS.items())) + "\n}"
TITLE = "TITLE_LINES = [" + ",\n               ".join(repr(x) for x in P.TITLE_LINES) + "]"

src = open(TARGET, encoding="utf-8").read()

def replace_block(text, name, new, closer):
    m = re.search(r"^%s = [\[\{]\n.*?^[\]\}]" % name, text, re.S | re.M)
    assert m, name
    return text[:m.start()] + new + text[m.end():]

src = replace_block(src, "CUTS", CUTS, "]")
src = replace_block(src, "NARRATION", NARR, "}")
src = replace_block(src, "BLOCKS", BLOCKS, "]")
src = replace_block(src, "SEARCH", SEARCH, "}")
src = replace_block(src, "PROMPTS", PROMPTS, "}")

m = re.search(r"^TITLE_LINES = \[.*?\]\n", src, re.S | re.M)
assert m
src = src[:m.start()] + TITLE + "\n" + src[m.end():]

src = re.sub(r"^OUTRO_CUT, OUTRO_SEC = \d+, [\d.]+",
             "OUTRO_CUT, OUTRO_SEC = %d, 2.6" % P.ROWS[-1][0], src, flags=re.M)
src = re.sub(r"^ASSET_ALIAS = \{[^}]*\}", "ASSET_ALIAS = {}", src, flags=re.M)
# この作品に図版は無い
src = src.replace("def render_figures():\n", "def render_figures():\n    return\n", 1)

open(TARGET, "w", encoding="utf-8").write(src)
print("差し替えました")
