# -*- coding: utf-8 -*-
# 「AIでも読めない 人類の文字 3選」bro口調版のデータ一式
TITLE_LINES = [("AIでも", "#FFFFFF", 0.48),
               ("読めない", "#FFD400", 0.86),
               ("人類の文字", "#FF1F1F", 1.00),
               ("3選", "#FFFFFF", 0.34)]

ROWS = [
 # cut, telop1, telop2, hl, hl_color, camera, narration
 (0,  "TITLE", "", "TITLE", "", "zoomin", "AIでも読めない、人類の文字、3選。"),
 (1,  "やあbroたち", "まだ読めない文字がある", "読めない", "red", "zoomin",
      "やあbroたち、人類がまだ読めてない文字があるの知ってるか？"),
 (2,  "AI使っても", "一文も読めてない", "AI", "yellow", "zoomout",
      "AI使っても、一文も読めてないんだぜ。"),
 (3,  "1", "ヴォイニッチ手稿", "ALL", "red", "zoomout", "1つ目、ヴォイニッチ手稿。"),
 (4,  "1912年に見つかった", "羊皮紙240ページの本", "240", "red", "zoomin",
      "1912年に見つかった、羊皮紙240ページの本な。"),
 (5,  "全部", "見たことない文字", "見たことない", "red", "pandown",
      "全部、見たことない文字で書かれてる。"),
 (6,  "挿絵の植物が", "どれも実在しない", "実在しない", "red", "zoomin",
      "挿絵の植物が、どれも実在しないんだよ。"),
 (7,  "作られたのは", "15世紀の前半", "15世紀", "red", "panright",
      "作られたのは15世紀の前半な。"),
 (8,  "暗号解読者もAIも", "全員敗北", "全員", "yellow", "zoomin",
      "暗号解読者が全員挑んで、AIまで投入された。"),
 (9,  "それでも", "一文も確定してない", "一文も", "red", "zoomin",
      "それでも一文も確定してない。"),
 (10, "2", "線文字A", "ALL", "red", "zoomout", "2つ目、線文字A。"),
 (11, "1900年 クレタ島", "二種類の文字が出た", "1900年", "red", "zoomin",
      "1900年、クレタ島で二種類の文字が出た。"),
 (12, "線文字Bは", "1952年に解読された", "1952年", "red", "panleft",
      "線文字Bのほうは1952年に解読された。"),
 (13, "正体は", "古い形のギリシャ語", "ギリシャ語", "yellow", "zoomin",
      "正体は古い形のギリシャ語だ。"),
 (14, "でも", "Aは違った", "違った", "red", "zoomin", "でもAは違った。"),
 (15, "同じ島 同じ時代", "の文字なのに", "同じ", "yellow", "pandown",
      "同じ島、同じ時代の文字なのにな。"),
 (16, "120年経った今も", "読めない", "120年", "red", "zoomin",
      "120年経った今も読めないんだ。"),
 (17, "なんでか", "分かるか？", "なんで", "yellow", "zoomout", "なんでか分かるか？"),
 (18, "何語で書かれてるか", "それすら分かってない", "何語", "red", "zoomin",
      "何語で書かれてるのか、それすら分かってない。"),
 (19, "資料は1400点", "文字数が足りない", "1400点", "red", "zoomin",
      "資料が1400点しかなくて、文字数が足りない。"),
 (20, "3", "ロンゴロンゴ", "ALL", "red", "zoomout", "3つ目、ロンゴロンゴ。"),
 (21, "イースター島に", "ロンゴロンゴという文字", "ロンゴロンゴ", "red", "zoomin",
      "イースター島に、ロンゴロンゴって文字があるんだ。"),
 (22, "木の板に刻まれた", "記号の列", "記号の列", "yellow", "panright",
      "木の板に刻まれた記号の列な。"),
 (23, "残ってる板は", "世界にたった26点", "26点", "red", "zoomin",
      "残ってる板は、世界にたった26点。"),
 (24, "19世紀に", "宣教師が来た頃には", "19世紀", "yellow", "zoomin",
      "19世紀に宣教師が来た頃には、"),
 (25, "読める島民が", "もういなかった", "いなかった", "red", "zoomout",
      "もう読める島民がいなくなってた。"),
 (26, "文字か記号かも", "決着がついてない", "ついてない", "red", "zoomin",
      "文字なのか記号なのかも、決着がついてない。"),
 (27, "ただ2024年", "板の一枚を測ったら", "2024年", "red", "zoomin",
      "ただ2024年、板の一枚を測ったらな、"),
 (28, "15世紀のものかも", "しれないと出た", "15世紀", "red", "panleft",
      "15世紀のものかもしれないと出たんだ。"),
 (29, "ヨーロッパ人が", "来るより前だ", "前", "red", "zoomin",
      "ヨーロッパ人が来るより前だぜ。"),
 (30, "人類が自力で作った", "数少ない例かも", "自力で", "yellow", "zoomout",
      "人類が自力で文字を作った、数少ない例かもしれない。"),
 (31, "文字は残った", "読める奴が消えた", "消えた", "red", "zoomin",
      "この三つ、文字のほうは残ってるんだ。"),
 (32, "文明が途切れるのは", "文字が消えた時じゃない", "文字が消えた時", "yellow", "zoomin",
      "消えたのは、読める人間のほうだ。"),
 (33, "今書いてるこの文字も", "いつか誰も読めなくなる", "誰も読めなくなる", "red", "zoomout",
      "今broたちが読んでるこの文字も、いつかそうなる。"),
 (34, "broたちはどれが", "一番読めそうだと思う？", "どれ", "yellow", "zoomin", None),
]

ITEM_END = {9, 19, 30}          # 項目の終わりで少し長めに間を取る

BLOCKS = [[0, 1, 2, 3, 4],
          [5, 6, 7, 8, 9],
          [10, 11, 12, 13, 14],
          [15, 16, 17, 18, 19],
          [20, 21, 22, 23, 24],
          [25, 26, 27, 28],
          [29, 30, 31, 32, 33, 34]]

# Pexels で拾えるカット
SEARCH = {
 4:  ["old manuscript pages", "ancient book parchment"],
 5:  ["handwritten manuscript closeup", "old ink writing"],
 7:  ["medieval library candle", "old books shelf dark"],
 8:  ["vintage typewriter dark", "old machine gears closeup"],
 11: ["archaeological excavation site", "ancient ruins stone"],
 12: ["ancient greek ruins", "stone inscription closeup"],
 15: ["mediterranean island coast", "greek island sea"],
 16: ["dust falling light beam", "abandoned archive shelves"],
 19: ["museum artifact vitrine", "clay tablet ancient"],
 21: ["easter island moai", "moai statues sunset"],
 22: ["carved wooden surface", "wood grain texture macro"],
 24: ["19th century sailing ship", "old wooden ship sea"],
 25: ["empty village dusk", "abandoned island shore"],
 29: ["old world map ocean", "antique globe closeup"],
 31: ["dark empty library", "faded document closeup"],
 32: ["night sky stars slow", "dark ocean horizon"],
}

_BASE = ("cinematic photorealistic, vertical 9:16 composition, dramatic "
         "directional lighting, shallow depth of field, subtle film grain, "
         "dust motes in the air, negative space in the center of the frame, "
         "no text, no watermark, no letters, no logos")

# 3つの項目で色を変える。全部同じ色だと、話が変わったことが絵で伝わらない
_A = "warm amber and candlelit gold color grade, aged parchment tones, " + _BASE
_B = "cold blue grey and pale limestone color grade, mediterranean daylight, " + _BASE
_C = "deep teal and volcanic black color grade, overcast pacific light, " + _BASE
_N = "near monochrome, cold neutral grey color grade, " + _BASE

PROMPTS = {
 33: "A modern smartphone screen glowing in total darkness, the text on it fading away character by character, " + _N,
 1: "Three ancient documents from different civilisations laid side by side on a dark table under a single lamp, each covered in a different unreadable script, " + _N,
 2: "A modern computer screen glowing in a dark room displaying scrolling unreadable symbols, nobody present, " + _N,
 3: "Closed leather bound medieval codex resting on dark cloth, brass clasps, single shaft of light, " + _A,
 6: "Botanical illustration of an impossible plant with wrong leaf structure and unnatural roots, faded pigments on aged vellum, " + _A,
 9: "A cluttered desk covered in decipherment attempts, crossed out notes and abandoned charts, dim lamp, nobody there, " + _A,
 10: "Fragment of a clay tablet incised with linear script, resting on grey stone, raking side light, " + _B,
 13: "Weathered marble slab carved with ancient greek lettering, moss in the grooves, overcast light, " + _B,
 14: "Two clay tablets side by side, one lit clearly and one falling into deep shadow, " + _B,
 17: "Close macro of unknown incised characters on clay, extreme shallow focus, most of the frame dark, " + _B,
 18: "A single clay tablet floating in complete darkness, lit from one side only, " + _B,
 20: "Row of weathered wooden tablets covered in tiny carved glyphs, arranged in a dark museum drawer, " + _C,
 23: "A wooden tablet under museum glass, catalogue label beside it, dramatic spot lighting, deep shadows, " + _C,
 26: "Extreme macro of carved glyph rows on dark wood, grain and tool marks visible, " + _C,
 27: "Laboratory bench with a small wood sample under analytical instruments, cold clinical light, " + _C,
 28: "Aged wooden tablet fragment held in gloved hands against a black background, " + _C,
 30: "Silhouetted human hand carving the first mark into a blank wooden board by firelight, " + _C,
 34: "Vast dark archive of unreadable documents receding into blackness, single dim light above, " + _N,
}
