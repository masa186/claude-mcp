#!/usr/bin/env python3
"""
Colab の1セルから呼ばれる、全部入りのパイプライン。

このファイルだけで完結する（cuts.csv も検索ワードも埋め込み済み）。
リポジトリの取得も、フォルダ構成の準備も要らない。

  python3 colab_onecell.py --key <PEXELSキー> --range 10
"""
import argparse, base64, csv, json, os, re, shutil, subprocess, sys, time
import urllib.error, urllib.parse, urllib.request, wave

W, H, FPS = 1080, 1920, 30
NUMCARD_SEC, GAP, GAP_ITEM_END = 1.8, 0.25, 0.60
TITLE_SEC = 2.2      # 声0.wav が無いときに、タイトルを出しておく長さ
COLORS = {"red": "#FF2A2A", "yellow": "#FFD400", "": "#FFFFFF"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv"}

CUTS = [
    {'cut': '0', 'telop1': 'TITLE', 'telop2': '', 'hl': 'TITLE', 'hl_color': '',
     'camera': 'zoomin', 'asset': 'A01', 'item_end': '0'},
    {'cut': '1', 'telop1': '地球には', 'telop2': '正体不明の音がある', 'hl': '正体不明', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A01', 'item_end': '0'},
    {'cut': '2', 'telop1': '記録は残っている', 'telop2': 'だが音源が分からない', 'hl': '音源', 'hl_color': 'yellow', 'camera': 'zoomin', 'asset': 'A02', 'item_end': '0'},
    {'cut': '3', 'telop1': '1', 'telop2': 'アップスウィープ', 'hl': 'ALL', 'hl_color': 'red', 'camera': 'zoomout', 'asset': 'A03', 'item_end': '0'},
    {'cut': '4', 'telop1': '1991年', 'telop2': 'アメリカの観測機関が', 'hl': '1991年', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A04', 'item_end': '0'},
    {'cut': '5', 'telop1': '太平洋の海中で', 'telop2': '奇妙な音を捉えた', 'hl': '奇妙な音', 'hl_color': 'yellow', 'camera': 'pandown', 'asset': 'A05', 'item_end': '0'},
    {'cut': '6', 'telop1': '周波数が', 'telop2': '上昇していく音が', 'hl': '上昇', 'hl_color': 'yellow', 'camera': 'zoomin', 'asset': 'A06', 'item_end': '0'},
    {'cut': '7', 'telop1': '延々と', 'telop2': '繰り返される', 'hl': '延々と', 'hl_color': 'red', 'camera': 'panright', 'asset': 'A06', 'item_end': '0'},
    {'cut': '8', 'telop1': 'アップスウィープと', 'telop2': '名付けられた', 'hl': 'アップスウィープ', 'hl_color': 'yellow', 'camera': 'zoomin', 'asset': 'A07', 'item_end': '0'},
    {'cut': '9', 'telop1': '音源は', 'telop2': '南太平洋の一点', 'hl': '一点', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A08', 'item_end': '0'},
    {'cut': '10', 'telop1': 'そこは陸から', 'telop2': '遠く離れた海域だった', 'hl': '遠く離れた', 'hl_color': 'yellow', 'camera': 'zoomout', 'asset': 'A09', 'item_end': '0'},
    {'cut': '11', 'telop1': 'この音には', 'telop2': '季節変動がある', 'hl': '季節変動', 'hl_color': 'yellow', 'camera': 'panleft', 'asset': 'A03', 'item_end': '0'},
    {'cut': '12', 'telop1': '春と秋に', 'telop2': 'ピークを迎える', 'hl': 'ピーク', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A10', 'item_end': '0'},
    {'cut': '13', 'telop1': '海底火山の活動では', 'telop2': 'ないかとされるが', 'hl': '海底火山', 'hl_color': 'yellow', 'camera': 'zoomin', 'asset': 'A11', 'item_end': '0'},
    {'cut': '14', 'telop1': '音源は', 'telop2': '特定されていない', 'hl': '特定されていない', 'hl_color': 'red', 'camera': 'zoomout', 'asset': 'A08', 'item_end': '0'},
    {'cut': '15', 'telop1': 'そして今も', 'telop2': '鳴り続けている', 'hl': '今も', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A12', 'item_end': '1'},
    {'cut': '16', 'telop1': '2', 'telop2': 'ザ・ハム', 'hl': 'ALL', 'hl_color': 'red', 'camera': 'zoomout', 'asset': 'A13', 'item_end': '0'},
    {'cut': '17', 'telop1': '世界各地で', 'telop2': '同じ報告が上がっている', 'hl': '同じ報告', 'hl_color': 'yellow', 'camera': 'zoomin', 'asset': 'A14', 'item_end': '0'},
    {'cut': '18', 'telop1': '低い唸り声のような', 'telop2': '音が聞こえる', 'hl': '唸り声', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A15', 'item_end': '0'},
    {'cut': '19', 'telop1': 'エンジンが遠くで', 'telop2': '回っているような音', 'hl': 'エンジン', 'hl_color': 'yellow', 'camera': 'panright', 'asset': 'A16', 'item_end': '0'},
    {'cut': '20', 'telop1': 'ハムと', 'telop2': '呼ばれている', 'hl': 'ハム', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A17', 'item_end': '0'},
    {'cut': '21', 'telop1': '1970年代', 'telop2': 'イギリス ブリストル', 'hl': '1970年代', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'S01', 'item_end': '0'},
    {'cut': '22', 'telop1': '1990年代', 'telop2': 'アメリカ タオス', 'hl': '1990年代', 'hl_color': 'red', 'camera': 'panleft', 'asset': 'A18', 'item_end': '0'},
    {'cut': '23', 'telop1': 'タオスでは住民の', 'telop2': 'およそ2%が', 'hl': '2%', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A19', 'item_end': '0'},
    {'cut': '24', 'telop1': 'その音が', 'telop2': '聞こえると答えた', 'hl': '聞こえる', 'hl_color': 'yellow', 'camera': 'zoomin', 'asset': 'A20', 'item_end': '0'},
    {'cut': '25', 'telop1': 'しかし残りの98%には', 'telop2': '聞こえない', 'hl': '98%', 'hl_color': 'red', 'camera': 'zoomout', 'asset': 'A21', 'item_end': '0'},
    {'cut': '26', 'telop1': '工業機械 地殻の振動', 'telop2': '耳鳴り', 'hl': '', 'hl_color': '', 'camera': 'pandown', 'asset': 'A22', 'item_end': '0'},
    {'cut': '27', 'telop1': 'あらゆる説が', 'telop2': '検証されたが', 'hl': '検証', 'hl_color': 'yellow', 'camera': 'zoomin', 'asset': 'A23', 'item_end': '0'},
    {'cut': '28', 'telop1': '発生源はいまだに', 'telop2': '特定されていない', 'hl': '特定されていない', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A13', 'item_end': '1'},
    {'cut': '29', 'telop1': '3', 'telop2': '52ヘルツのクジラ', 'hl': 'ALL', 'hl_color': 'red', 'camera': 'zoomout', 'asset': 'A01', 'item_end': '0'},
    {'cut': '30', 'telop1': '1989年', 'telop2': '米海軍の探知網が', 'hl': '1989年', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A24', 'item_end': '0'},
    {'cut': '31', 'telop1': '太平洋である', 'telop2': '鳴き声を拾った', 'hl': '鳴き声', 'hl_color': 'yellow', 'camera': 'panright', 'asset': 'A25', 'item_end': '0'},
    {'cut': '32', 'telop1': '52ヘルツ', 'telop2': '', 'hl': 'ALL', 'hl_color': 'red', 'camera': 'still', 'asset': 'A26a', 'item_end': '0'},
    {'cut': '33', 'telop1': 'クジラの声としては', 'telop2': '異常に高い', 'hl': '異常に高い', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A27', 'item_end': '0'},
    {'cut': '34', 'telop1': 'シロナガスクジラは', 'telop2': '10〜39ヘルツ', 'hl': '10〜39', 'hl_color': 'yellow', 'camera': 'panleft', 'asset': 'A28', 'item_end': '0'},
    {'cut': '35', 'telop1': 'この個体だけが', 'telop2': '違う周波数で鳴いていた', 'hl': 'この個体だけ', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A28', 'item_end': '0'},
    {'cut': '36', 'telop1': 'つまり', 'telop2': '仲間には届かない', 'hl': '届かない', 'hl_color': 'red', 'camera': 'zoomout', 'asset': 'A27', 'item_end': '0'},
    {'cut': '37', 'telop1': '研究者は30年以上', 'telop2': '追跡を続けた', 'hl': '30年以上', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A29', 'item_end': '0'},
    {'cut': '38', 'telop1': '回遊経路はどの種とも', 'telop2': '一致しない', 'hl': '一致しない', 'hl_color': 'yellow', 'camera': 'panright', 'asset': 'A30', 'item_end': '0'},
    {'cut': '39', 'telop1': '種の特定も', 'telop2': '姿の確認もできていない', 'hl': 'できていない', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A31', 'item_end': '0'},
    {'cut': '40', 'telop1': '世界で最も', 'telop2': '孤独なクジラ', 'hl': '孤独', 'hl_color': 'red', 'camera': 'zoomout', 'asset': 'A27', 'item_end': '1'},
    {'cut': '41', 'telop1': '3つの音に', 'telop2': '共通するのは', 'hl': '', 'hl_color': '', 'camera': 'zoomin', 'asset': 'A32', 'item_end': '0'},
    {'cut': '42', 'telop1': '記録は', 'telop2': '残っているのに', 'hl': '記録', 'hl_color': 'yellow', 'camera': 'pandown', 'asset': 'A33', 'item_end': '0'},
    {'cut': '43', 'telop1': '音源だけが', 'telop2': '見つかっていない', 'hl': '見つかっていない', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A08', 'item_end': '0'},
    {'cut': '44', 'telop1': '地球はまだ', 'telop2': '静かではない', 'hl': '静かではない', 'hl_color': 'red', 'camera': 'zoomin', 'asset': 'A34', 'item_end': '0'},
]

SEARCH = {
    1: ['deep ocean light rays underwater', 'abyss dark water'],
    3: ['ocean at night aerial', 'moonlight on sea'],
    8: ['vintage tape reel closeup', 'old cassette label'],
    11: ['ocean timelapse sky', 'sea clouds timelapse'],
    13: ['underwater volcano vent', 'hydrothermal vent'],
    15: ['buoy at night sea', 'ocean buoy dark'],
    16: ['empty street night streetlight', 'suburban street 3am'],
    17: ['world map pins wall', 'map with pushpins dark'],
    18: ['insomnia lying awake bed night'],
    19: ['industrial plant night', 'factory lights distance night'],
    21: ['terraced houses england grey sky', 'bristol street uk'],
    22: ['adobe buildings desert town', 'taos new mexico'],
    23: ['small town night aerial few lights'],
    24: ['hand on ear listening closeup'],
    25: ['crowd walking motion blur one person still'],
    27: ['researcher headphones field equipment night'],
    28: ['empty road night streetlight flicker'],
    29: ['underwater blue ocean sunbeam'],
    30: ['sonar room green screens', 'vintage radar control room'],
    31: ['underwater cable descending deep'],
    33: ['whale silhouette deep blue water'],
    34: ['blue whales swimming together'],
    37: ['desk covered documents notes lamp'],
    42: ['archive shelves tape reels storage'],
}

SILENT_CUTS = set()      # 番号カードも読み上げるので、無音のカットは無い
# 番号カードはセリフが短い。文字数どおりに割ると1秒ちょっとで消えて読めない
CARD_CUTS = {int(r["cut"]) for r in CUTS if r["hl"] == "ALL"}
CARD_WEIGHT = 17
NARRATION = {
    0: '今も正体が分かっていない地球の音、3選。',
    1: '地球には誰も正体を特定できていない音がある。',
    2: '観測記録は残っているが音源が分からない。',
    3: '1つ目、アップスウィープ。',
    4: '1991年、アメリカの観測機関が、',
    5: '太平洋の海中で奇妙な音を捉えた。',
    6: '周波数が上昇していく音が、',
    7: '延々と繰り返される。',
    8: 'アップスウィープと名付けられた。',
    9: '音源は南太平洋の一点で、',
    10: '陸から遠く離れた海域だった。',
    11: 'この音には季節変動があり',
    12: '春と秋にピークを迎える。',
    13: '海底火山の活動ではないかとされるが、',
    14: '音源は特定されていない。',
    15: 'そして今も鳴り続けている。',
    16: '2つ目、ザ・ハム。',
    17: '世界各地で同じ報告が上がっている。',
    18: '低い唸り声のような音が聞こえる。',
    19: 'エンジンが遠くで回っているような音で、',
    20: 'ハムと呼ばれている。',
    21: '1970年代のイギリス、ブリストル。',
    22: '1990年代のアメリカ、タオス。',
    23: 'タオスでは住民のおよそ2パーセントが、',
    24: 'その音が聞こえると答えた。',
    25: 'しかし残りの98パーセントには聞こえない。',
    26: '工業機械や地殻の振動、耳鳴り。',
    27: 'あらゆる説が検証されたが',
    28: '発生源はいまだに特定されていない。',
    29: '3つ目、52ヘルツのクジラ。',
    30: '1989年、アメリカ海軍の潜水艦探知網が、',
    31: '太平洋である鳴き声を拾った。',
    32: '52ヘルツ。',
    33: 'クジラの声としては異常に高い。',
    34: 'シロナガスクジラは10から39ヘルツだが、',
    35: 'この個体だけが違う周波数で鳴いていた。',
    36: 'つまり仲間には届かない。',
    37: '研究者は30年以上追跡を続けた。',
    38: '回遊経路はどの種とも一致せず、',
    39: '種の特定も姿の確認もできていない。',
    40: '世界で最も孤独なクジラと呼ばれている。',
    41: '3つの音に共通するのは、',
    42: '記録は残っているのに',
    43: '音源だけが見つかっていないという点だ。',
    44: '地球はまだ、静かではない。',
}

# 声1〜声9 のどのファイルにどのカットが入っているか。
# ファイルごとの実測時間でカットを割り振るので、途中でズレても次のファイルで戻る
BLOCKS = [
    [0, 1, 2, 3, 4, 5],
    [6, 7, 8, 9, 10, 11],
    [12, 13, 14, 15, 16, 17],
    [18, 19, 20, 21, 22],
    [23, 24, 25, 26, 27],
    [28, 29, 30, 31, 32, 33],
    [34, 35, 36, 37],
    [38, 39, 40, 41, 42],
    [43, 44],
]

PROMPTS = {
    1: 'Pitch black deep ocean with a single faint beam of light descending from the surface, suspended particles drifting slowly, immense emptiness, subject in lower half of frame, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold blue color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    2: 'Close up of a reel to reel tape machine running alone in a dark room, both reels slowly turning, a single small indicator lamp glowing amber, nobody present, dust drifting in a narrow beam of light, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    3: 'Vast dark ocean surface at night seen from high above, moonlight scattered across the waves, no land anywhere, heavy vignette, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold blue color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    4: 'Rows of analog recording equipment in a dim government monitoring facility, reel to reel tapes turning, early 1990s technology, cold fluorescent light, deep perspective down the aisle, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    5: 'Underwater hydrophone sensor suspended in the deep dark ocean, cable rising into blackness above, cold blue light from far above, marine snow drifting, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold blue color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    8: 'A handwritten paper label on an old magnetic tape reel box, ink blurred and completely unreadable, warm archive lighting from one side, extreme shallow focus, dust on the surface, cinematic photorealistic, vertical 9:16 composition, subtle film grain, muted desaturated color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    9: 'Earth seen from orbit showing the pacific side, almost entirely dark ocean with no landmass visible, thin glowing blue atmospheric limb along the curve, deep starfield behind, the planet occupying the lower half of the frame, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, subtle film grain, muted desaturated cold blue color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    10: 'Endless empty ocean horizon under a heavy grey overcast sky, no ships, no land, flat cold light, sense of total isolation, cinematic photorealistic, vertical 9:16 composition, shallow depth of field, subtle film grain, muted desaturated cold color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    11: 'Vast dark ocean surface at night seen from high above, moonlight scattered across the waves, no land anywhere, heavy vignette, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold blue color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    12: 'Aerial view of open ocean where two weather systems meet, warm hazy spring light on one side and cold dark autumn storm cloud on the other, a visible front line dividing the water, no land, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    13: 'Underwater volcanic vent erupting glowing orange magma into black abyssal water, superheated plume rising, dramatic contrast between fire and darkness, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    14: 'Earth seen from orbit showing the pacific side, almost entirely dark ocean with no landmass visible, thin glowing blue atmospheric limb along the curve, deep starfield behind, the planet occupying the lower half of the frame, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, subtle film grain, muted desaturated cold blue color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    15: 'Modern hydrophone buoy floating alone on a black night ocean, small blinking indicator light, stars above, gentle swell, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold blue color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    16: 'Empty suburban street at 3am, orange sodium streetlights, no people, parked cars, oppressive silence, heavy vignette, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    17: 'Large world map pinned on a dark wall with several small pins clustered in different continents, dim desk lamp lighting it from below, shallow depth of field, map deliberately out of focus and unreadable, cinematic photorealistic, vertical 9:16 composition, subtle film grain, muted desaturated color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    18: 'Close up of a person lying awake in bed at night with eyes open in the dark, only ambient blue light from a window, face partly in shadow, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold blue color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    19: 'Distant industrial complex at night with faint smoke and a few scattered lights, seen across a dark empty field, cold grade, low horizon, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    20: 'Row of high voltage transmission pylons silhouetted against a dark dusk sky, power lines converging into the distance, low oppressive clouds, empty field below, sense of a constant unheard hum, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    22: 'Adobe buildings in a high desert town under a huge blue sky, dry mountains in the distance, dusty warm afternoon light, no people, cinematic photorealistic, vertical 9:16 composition, shallow depth of field, subtle film grain, muted desaturated warm color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    23: 'Overhead night view of a small desert town, only a few windows lit, most of the town completely dark, empty streets, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    24: 'Close up of a hand pressed against an ear, eyes closed in concentration, harsh side lighting, dark background, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    25: 'A crowded city street where everyone walks normally except one person standing completely still with a troubled expression, heavy motion blur on the crowd, the still figure sharp, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    26: 'Triptych composition blending an industrial factory turbine, a seismograph needle tracing a line, and a human ear in extreme close up, all in cold desaturated tones, seamless transitions between the three, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    27: 'Researcher wearing headphones adjusting audio measurement equipment on a tripod in a dark open field at night, single lamp illuminating the equipment, stars above, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    28: 'Empty suburban street at 3am, orange sodium streetlights, no people, parked cars, oppressive silence, heavy vignette, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    29: 'Pitch black deep ocean with a single faint beam of light descending from the surface, suspended particles drifting slowly, immense emptiness, subject in lower half of frame, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold blue color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    30: 'Cold war era naval sonar station interior, green radar and waveform screens glowing in a dark room, 1980s military equipment, operator silhouettes at the consoles, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold green color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    31: 'Underwater listening array cables descending into the deep dark pacific, faint blue light from far above, cables converging toward the abyss, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold blue color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    33: 'A single whale silhouette suspended alone in an enormous expanse of empty dark blue ocean, no other life visible anywhere, the whale small in the frame, marine snow drifting, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold blue color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    34: 'Several blue whales swimming together in formation in deep blue water, calm and synchronized, seen from the side, shafts of surface light above them, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold blue color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    35: 'Several blue whales swimming together in formation in deep blue water, calm and synchronized, seen from the side, shafts of surface light above them, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold blue color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    36: 'Several blue whales swimming together in formation in deep blue water, calm and synchronized, seen from the side, shafts of surface light above them, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold blue color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    37: 'Desk covered with decades of printed sonar charts and handwritten notes stacked in thick layers, warm lamp light from one side, shallow focus on the nearest stack, papers yellowed with age, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, subtle film grain, muted desaturated warm color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    38: 'Worn paper nautical chart spread across a wooden desk under a warm lamp, brass dividers and a pencil resting on it, faint hand drawn marks, printed detail deliberately out of focus and unreadable, shallow focus on the nearest edge, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, subtle film grain, muted desaturated warm color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    39: 'An indistinct massive dark shape barely visible in murky deep water, form completely unresolvable, suspended particles between camera and subject, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold blue color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    40: 'A single whale silhouette suspended alone in an enormous expanse of empty dark blue ocean, no other life visible anywhere, the whale small in the frame, marine snow drifting, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold blue color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    41: 'Three small distant lights floating far apart from each other on a black night ocean, calm water reflecting them faintly, stars above, nothing else visible in any direction, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated cold blue color grade, volumetric atmosphere, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    42: 'Archive shelves full of magnetic tape reels in a dim storage room, deep perspective down a long aisle, dust in the air, single overhead light, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, shallow depth of field, subtle film grain, muted desaturated color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    43: 'Earth seen from orbit showing the pacific side, almost entirely dark ocean with no landmass visible, thin glowing blue atmospheric limb along the curve, deep starfield behind, the planet occupying the lower half of the frame, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, subtle film grain, muted desaturated cold blue color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
    44: 'Earth seen from deep space at night, faint city lights scattered on the dark side, thin blue atmospheric rim, stars behind, the planet in the lower half of the frame, cinematic photorealistic, vertical 9:16 composition, dramatic directional lighting, subtle film grain, muted desaturated cold blue color grade, negative space in the center of the frame, no text, no watermark, no letters, no logos',
}

WORK = os.path.abspath("shorts_work")
VID = os.path.join(WORK, "素材_動画")
IMG = os.path.join(WORK, "素材_画像")
TMP = os.path.join(WORK, "_作業中")
AUD = os.path.join(WORK, "音声")
MINE = "/content/素材"      # 自分で用意した素材を入れる場所
GEN  = "/content/生成"      # ③がつくった画像。手置きと違い透かしが無い


def sh(args):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-1200:])


def ffmpeg_bin():
    if shutil.which("ffmpeg"):
        return shutil.which("ffmpeg")
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def find_font():
    import glob
    for pat in ("/usr/share/fonts/**/NotoSansCJK*Black*",
                "/usr/share/fonts/**/NotoSansCJK*",
                "/usr/share/fonts/**/ipag*"):
        hits = sorted(glob.glob(pat, recursive=True))
        if hits:
            return hits[0]
    return ""


# 選べる見出し書体。①が /content/fonts に落としておく
FACES = {
    "ゴツい": "DelaGothicOne-Regular.ttf",
    "太ゴシック": "ZenKakuGothicNew-Black.ttf",
    "ポップ": "RocknRollOne-Regular.ttf",
    "丸ゴシック": "ZenMaruGothic-Black.ttf",
    "レトロ": "ReggaeOne-Regular.ttf",
    "筆っぽい": "KaiseiDecol-Bold.ttf",
}
FACE = "太ゴシック"      # --face で差し替える

# テロップの出し方。参考6本を測ると4本は動きなしの切り替えで、
# 動くものは 0.1秒ほどで 93% から等倍に戻る出方だった
ANIMS = ("なし", "ポップ", "ふわっと")
ANIM = "なし"

# カットの切り替え。参考動画のうち動きがあった2本は、文字ではなく
# 画面全体をボカして次に移っていた。頻度は 1分あたり 7〜19回
TRANS = ("半分", "節目だけ", "全部", "なし")
TRANS_MODE = "半分"
TRANS_SEC = 0.16


def wants_trans(i, row):
    # タイトルだけは終わりをボカして次へ渡す。参考動画もそこだけ強く飛ばしていた
    if TRANS_MODE == "なし":
        return ""
    if row["hl"] == "TITLE":
        return "out"
    if i == 1:
        return "in"          # タイトルがボケて飛んだ先。ここで戻さないと繋がらない
    if TRANS_MODE == "全部":
        return "in"
    if row["hl"] == "ALL" or row["item_end"] == "1":
        return "in"
    return "in" if (TRANS_MODE == "半分" and i % 2 == 0) else ""


def blur_chain(strong):
    z, sig, sft = (1.20, 34, 13) if strong else (1.06, 18, 7)
    return ("scale=iw*%.2f:ih*%.2f,crop=%d:%d,gblur=sigma=%d,rgbashift=rh=%d:bh=-%d"
            % (z, z, W, H, sig, sft, sft))


def trans_filter(mode, dur):
    # ボカした自分自身と重ねる。前後のカットを食い合わないので、
    # 尺は1フレームも動かない
    if not mode:
        return "[v]null[vv]"
    d = min(TRANS_SEC, max(dur * 0.4, 0.06))
    if mode == "in":
        return ("[v]split[sh][bl];[bl]%s[bb];"
                "[bb][sh]xfade=transition=fade:duration=%.2f:offset=0[vv]"
                % (blur_chain(False), d))
    # タイトルは終わり際にボカして飛ばす。長くなるぶんは切り戻す
    d = min(0.34, max(dur * 0.3, 0.10))
    return ("[v]split[sh][bl];[bl]%s[bb];"
            "[sh][bb]xfade=transition=fade:duration=%.2f:offset=%.3f,"
            "trim=0:%.3f,setpts=PTS-STARTPTS[vv]"
            % (blur_chain(True), d, max(dur - d, 0.02), dur))


def telop_filter():
    if ANIM == "なし":
        return "[bg][1:v]overlay=0:0:format=auto[v]"
    if ANIM == "ふわっと":
        return ("[1:v]fade=t=in:st=0:d=0.12:alpha=1[tp];"
                "[bg][tp]overlay=0:'H*0.010*(1-min(t/0.12,1))':format=auto[v]")
    return ("[1:v]scale=w='iw*(0.93+0.07*min(t/0.12,1))':h=-1:eval=frame,"
            "fade=t=in:st=0:d=0.08:alpha=1[tp];"
            "[bg][tp]overlay='(W-w)/2':'(H-h)/2':format=auto[v]")


def find_title_font():
    # タイトルとテロップの書体。無ければ本文用で代用する
    import glob
    want = FACES.get(FACE, FACES["太ゴシック"])
    for pat in ("/content/fonts/" + want,
                "/content/fonts/DelaGothicOne*.ttf",
                "/usr/share/fonts/**/DelaGothicOne*",
                "/usr/share/fonts/**/NotoSansCJK*Black*"):
        hits = sorted(glob.glob(pat, recursive=True))
        if hits:
            return hits[0]
    return find_font()


# ── 図版（カット6・7・32）。ナレーションが述べる内容そのものなので用意する ──

def render_figures():
    import numpy as np, matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    from PIL import Image
    rng = np.random.default_rng(7)
    os.makedirs(IMG, exist_ok=True)

    def finish(fig, name, telop_dim, vignette):
        path = os.path.join(IMG, name)
        fig.savefig(path, dpi=100, facecolor="#000000", pad_inches=0)
        plt.close(fig)
        im = np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255
        h, w, _ = im.shape
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.sqrt(((yy - h / 2) / (h / 2)) ** 2 + ((xx - w / 2) / (w / 2)) ** 2)
        im *= (1 - vignette * np.clip(r - .45, 0, None) ** 1.6)[..., None]
        band = np.zeros(h, np.float32)
        band[int(h * .52):int(h * .72)] = 1
        im *= (1 - telop_dim * band)[:, None, None]
        im = np.clip(im + rng.normal(0, .03, im.shape), 0, 1)
        Image.fromarray((im * 255).astype(np.uint8)).save(path)

    # アップスウィープ：20→95Hz のチャープ列を合成して STFT にかける
    fs, dur = 1000.0, 20.0
    t = np.arange(0, dur, 1 / fs)
    x = rng.normal(0, .03, t.size)
    for s in np.arange(1.0, dur - 2.9, 4.6):
        m = (t >= s) & (t < s + 2.9)
        tt = t[m] - s
        x[m] += np.sin(np.pi * tt / 2.9) ** 2 * np.sin(
            2 * np.pi * (20 * tt + .5 * ((95 - 20) / 2.9) * tt ** 2))
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    fig.patch.set_facecolor("#000")
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor("#000")
    ax.specgram(x, NFFT=1024, Fs=fs, noverlap=960, vmin=-42, vmax=14,
                cmap=LinearSegmentedColormap.from_list(
                    "s", ["#000000", "#02160c", "#0b6b3a", "#3fd07a", "#c8f06a", "#ffd98a"]))
    ax.set_ylim(0, 140); ax.axis("off")
    finish(fig, "A06_upsweep.png", .62, .65)

    # 52ヘルツ：孤立した1本のピーク
    f = np.linspace(0, 100, 2400)
    spec = np.abs(.02 + rng.normal(0, .006, f.size)) + np.exp(-((f - 52) ** 2) / .30)
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    fig.patch.set_facecolor("#000")
    ax = fig.add_axes([.08, .08, .84, .36]); ax.set_facecolor("#000")
    pk = (f > 48) & (f < 56)
    for lw, al in ((14, .06), (7, .13), (3, .35), (1.5, 1)):
        ax.plot(f[pk], spec[pk], color="#ff2a2a", lw=lw, alpha=al)
    ax.plot(f, spec, color="#8899aa", lw=.8, alpha=.30, zorder=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_xlim(0, 100); ax.set_ylim(0, 1.25)
    finish(fig, "A26a_52hz.png", .28, .60)


# ── Pexels ──

def pexels_search(key, term, portrait_only):
    # 縦だけに絞ると候補がほぼ無くなる素材が多い。まず縦、無ければ全部から探す
    q = {"query": term, "per_page": 20}
    if portrait_only:
        q["orientation"] = "portrait"
    url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode(q)
    # Colab のIPからだと素の urllib は 403 で弾かれる。ブラウザらしく名乗る
    req = urllib.request.Request(url, headers={
        "Authorization": key,
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.pexels.com/",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()).get("videos", []), None
    except urllib.error.HTTPError as e:
        if e.code == 401:
            sys.exit("Pexelsのキーが違うようです。貼り直して、もう一度押してください。")
        if e.code == 403:
            return [], "HTTP 403（キーが無効か、Colabからの接続が拒否されました）"
        return [], "HTTP %s" % e.code
    except Exception as e:
        return [], type(e).__name__


def best_file(v, min_h, portrait_only):
    # 縦向きを優先。無ければ横でも拾う（あとで中央を切り出して縦にする）
    files = [g for g in v.get("video_files", [])
             if g.get("height") and g.get("width") and g["height"] >= min_h]
    if not files:
        return None
    tate = [g for g in files if g["height"] > g["width"]]
    if tate:
        return max(tate, key=lambda g: g["height"])
    return None if portrait_only else max(files, key=lambda g: g["width"] * g["height"])


def pexels(key, cuts_wanted, per_cut=2, min_h=900):
    os.makedirs(VID, exist_ok=True)
    got, miss = 0, []
    for cut in sorted(SEARCH):
        if cut not in cuts_wanted:
            continue
        if [f for f in os.listdir(VID) if f.startswith("cut%02d_" % cut)]:
            print("   カット%-2d  取得済み" % cut)
            continue

        picked, seen, note = [], set(), ""
        # ①縦だけで探す → ②足りなければ向き不問で探す
        for portrait_only in (True, False):
            if len(picked) >= per_cut:
                break
            for term in SEARCH[cut]:
                if len(picked) >= per_cut:
                    break
                vids, err = pexels_search(key, term, portrait_only)
                if err:
                    note = err
                for v in vids:
                    if len(picked) >= per_cut or v["id"] in seen:
                        continue
                    seen.add(v["id"])
                    vf = best_file(v, min_h, portrait_only)
                    if vf:
                        picked.append(vf)
                time.sleep(.4)
            if picked and portrait_only:
                break

        if not picked:
            miss.append(cut)
            print("   カット%-2d  見つからず%s" % (cut, "（%s）" % note if note else ""))
            continue

        for i, vf in enumerate(picked, 1):
            tag = "縦" if vf["height"] > vf["width"] else "横→切出"
            path = os.path.join(VID, "cut%02d_%d_%dx%d.mp4" % (cut, i, vf["width"], vf["height"]))
            try:
                rq = urllib.request.Request(vf["link"], headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(rq, timeout=600) as r, open(path, "wb") as fh:
                    shutil.copyfileobj(r, fh)
                got += 1
                print("   カット%-2d  %s %dx%d" % (cut, tag, vf["width"], vf["height"]))
            except Exception as e:
                print("   カット%-2d  落とせず（%s）" % (cut, type(e).__name__))
                if os.path.exists(path):
                    os.remove(path)
    return got, miss



# ── VOICEVOX ──────────────────────────────────────────────────────

def vv_get(host, path, timeout=20):
    with urllib.request.urlopen(host + path, timeout=timeout) as r:
        return json.loads(r.read())


def vv_alive(host, timeout=5):
    try:
        urllib.request.urlopen(host + "/version", timeout=timeout).read()
        return True
    except Exception:
        return False


def vv_speakers(host):
    out = []
    for sp in vv_get(host, "/speakers"):
        for st in sp["styles"]:
            out.append((st["id"], sp["name"], st["name"]))
    return out


def vv_find_speaker(host, name):
    # 名前の一部が一致する話者を探す。ノーマル系のスタイルを優先する
    hits = [t for t in vv_speakers(host) if name in t[1]]
    if not hits:
        return None
    for t in hits:
        if t[2] in ("ノーマル", "normal"):
            return t
    return hits[0]


def vv_synth(host, speaker, text, speed, pitch, intonation):
    q = json.loads(urllib.request.urlopen(urllib.request.Request(
        host + "/audio_query?" + urllib.parse.urlencode({"text": text, "speaker": speaker}),
        data=b"", method="POST"), timeout=60).read())
    q["speedScale"] = speed
    q["pitchScale"] = pitch
    q["intonationScale"] = intonation
    q["prePhonemeLength"] = 0.05
    q["postPhonemeLength"] = 0.05
    req = urllib.request.Request(
        host + "/synthesis?" + urllib.parse.urlencode({"speaker": speaker}),
        data=json.dumps(q).encode(), method="POST",
        headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=300).read()


def wav_seconds(path):
    with wave.open(path, "rb") as w:
        return w.getnframes() / w.getframerate()


AUDIO_EXT = (".wav", ".mp3", ".m4a", ".ogg", ".aac", ".flac")
NOT_VOICE = ("bgm", "music", "narration", "no_audio", "se_")


def voice_order(path):
    # audio(1).wav / 声1.wav / 音声 2.mp3 … 名前の中の数字を順番とみなす。
    # 数字が無いものは先頭（1本目は audio.wav のように番号が付かない）
    n = os.path.basename(path)
    m = re.findall(r"\d+", os.path.splitext(n)[0])
    return (int(m[0]) if m else -1, n)


def adopt_cut_voices():
    # カット番号が付いた音声（cut04.wav / カット4.mp3）が置いてあれば、
    # それをそのカットの声として使う。1カット＝1ファイルなら、
    # 長さがそのまま尺になるので、どこで切り替えるかを推測しなくてよい
    import glob
    valid = {int(r["cut"]) for r in CUTS}
    got = {}
    for d in ("/content", ".", AUD):
        if not os.path.isdir(d):
            continue
        for fp in sorted(glob.glob(os.path.join(d, "*"))):
            if os.path.splitext(fp)[1].lower() not in AUDIO_EXT:
                continue
            n = os.path.basename(fp)
            m = re.match(r"(?:cut|カット)[ _\-]?(\d+)", n, re.I)
            if m and int(m.group(1)) in valid:
                got.setdefault(int(m.group(1)), fp)
    if not got:
        return 0
    os.makedirs(AUD, exist_ok=True)
    FF = ffmpeg_bin()
    for cut, fp in got.items():
        dst = os.path.join(AUD, "cut%02d.wav" % cut)
        if os.path.abspath(fp) == os.path.abspath(dst):
            continue
        sh([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", fp,
            "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", dst])
    return len(got)


def find_bgm():
    # /content に bgm.mp3 のような名前で置いてあれば使う
    import glob
    for d in ("/content", "."):
        for fp in sorted(glob.glob(os.path.join(d, "*"))):
            n = os.path.basename(fp).lower()
            if os.path.splitext(n)[1] in AUDIO_EXT and ("bgm" in n or "music" in n):
                return fp
    return None


def mix_bgm(video, bgm, db, out):
    # 参考動画を測ると、BGM はナレーションより 8〜12dB 下だった。
    # 頭と尻を少し絞って、喋りの上に乗せる
    dur = media_seconds(video)
    fc = ("[1:a]aloop=loop=-1:size=2000000000,atrim=0:%.3f,"
          "volume=%.1fdB,afade=t=in:d=1.2,afade=t=out:st=%.3f:d=1.8[b];"
          "[0:a][b]amix=inputs=2:duration=first:normalize=0,"
          "alimiter=limit=0.95[a]" % (dur, db, max(dur - 1.8, 0.1)))
    sh([ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y",
        "-i", video, "-i", bgm, "-filter_complex", fc,
        "-map", "0:v", "-map", "[a]", "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-shortest", out])


def find_voice_files():
    # 声1.wav … と付いていれば確実。付いていなくても、置いてある音声を
    # 名前の数字順に並べて使う。スマホだと名前を直すのが一番の手間なので
    import glob
    for d in ("/content", ".", AUD, WORK):
        if not os.path.isdir(d):
            continue
        named, loose = [], []
        for fp in glob.glob(os.path.join(d, "*")):
            if os.path.splitext(fp)[1].lower() not in AUDIO_EXT:
                continue
            n = os.path.basename(fp).lower()
            if any(x in n for x in NOT_VOICE):
                continue
            if n.startswith(("声", "voice")):
                named.append(fp)
            else:
                loose.append(fp)
        hits = named or loose
        if hits:
            return sorted(set(hits), key=voice_order)
    return []


def media_seconds(path):
    if path.lower().endswith(".wav"):
        try:
            return wav_seconds(path)
        except Exception:
            pass
    out = subprocess.run([ffmpeg_bin(), "-hide_banner", "-i", path],
                         capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", out)
    if not m:
        return 0.0
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


# 参考動画を測ると、間は 0.24〜0.38秒が中央で、0.40〜0.70秒の長めが
# 1本あたり7〜23回あった。短い間だけだと切れ目が立たないので、
# ブロックの継ぎ目はその長めの帯に置く
BLOCK_GAP, TITLE_GAP = 0.45, 0.60


def voice_gaps(paths):
    # 各ファイルの後ろに入れる無音。最後の1本だけ入れない
    titled = has_title_voice(paths)
    out = []
    for i in range(len(paths)):
        if i == len(paths) - 1:
            out.append(0.0)
        elif i == 0 and titled:
            out.append(TITLE_GAP)      # タイトルのあとは長めに置く
        else:
            out.append(BLOCK_GAP)
    return out


def join_voices(paths):
    os.makedirs(WORK, exist_ok=True)
    joined = os.path.join(WORK, "narration.wav")
    FF = ffmpeg_bin()
    parts = []
    for i, (h, g) in enumerate(zip(paths, voice_gaps(paths))):
        q = os.path.join(WORK, "v%02d.wav" % i)
        sh([FF, "-hide_banner", "-loglevel", "error", "-y",
            "-i", h, "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", q])
        parts.append(q)
        if g > 0:
            z = os.path.join(WORK, "z%02d.wav" % i)
            sh([FF, "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "%.3f" % g,
                "-c:a", "pcm_s16le", z])
            parts.append(z)
    if len(parts) == 1:
        return parts[0]
    lst = os.path.join(WORK, "voices.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for q in parts:
            f.write("file '%s'\n" % q)
    sh([FF, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
    return joined


def has_title_voice(paths):
    # 先頭がタイトルの読み上げかどうか。声0.wav なら明らか。
    # 名前を直していない場合は本数で見る（ブロック数より1本多ければ先頭がタイトル）
    if not paths:
        return False
    if len(paths) == len(BLOCKS) + 1:
        return True
    m = re.search(r"(\d+)", os.path.basename(paths[0]))
    return bool(m) and int(m.group(1)) == 0


def voice_blocks(paths):
    if not has_title_voice(paths):
        return BLOCKS
    return [[0]] + [[c for c in b if c != 0] for b in BLOCKS]


# 読点の間は 0.1秒を切ることがある。取りこぼすとそのカットが合わない
MIN_PAUSE = 0.06
MIN_TELOP = 0.70      # これより短いテロップは読めない


def speech_edges(path):
    # 声の中の「間」の位置を返す。文字数で割るより、実際に息継ぎした
    # ところでテロップを変えたほうが合って聞こえる
    import numpy as np
    tmp = os.path.join(WORK, "_edge.wav")
    try:
        sh([ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y",
            "-i", path, "-ac", "1", "-ar", "8000", "-c:a", "pcm_s16le", tmp])
        w = wave.open(tmp)
        a = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
        sr = w.getframerate()
    except Exception:
        return []
    if len(a) < sr // 2:
        return []
    hop = int(sr * 0.010)
    n = len(a) // hop
    env = np.sqrt((a[:n*hop].reshape(n, hop) ** 2).mean(1) + 1e-12)
    env = np.convolve(env, np.ones(3) / 3, "same")
    thr = np.percentile(env, 90) * 0.22
    out, run = [], 0
    for i, loud in enumerate(env > thr):
        if not loud:
            run += 1
        else:
            if run * 0.010 >= MIN_PAUSE:
                # 読み終わった瞬間。無音の真ん中に置くと、
                # 読み終わってもテロップが残っていて遅れて見える
                out.append((i - run) * 0.010 + 0.04)
            run = 0
    # 最後は無音で終わることが多い。そこも切り替え先として使えるようにする
    if run * 0.010 >= MIN_PAUSE:
        out.append((len(env) - run) * 0.010 + 0.04)
    return out


def snap(targets, edges, total=None, want=None, pause_bonus=0.30):
    # 切り替え時刻を「間」に合わせる。近い順に1つずつ選ぶと、
    # 文字数の見積もりが少しずれただけで正しい間を取り逃す。
    # 全体でいちばん辻褄が合う組を選ぶ（動的計画法）
    n = len(targets)
    if not edges or not n:
        return list(targets)
    if want is None:
        want = [targets[0]] + [targets[i] - targets[i - 1] for i in range(1, n)]
    if total is None:
        total = targets[-1]
    # 間が足りないときは、文字数から出した時刻も候補に混ぜる。
    # そのままだと候補不足で合わせること自体を諦めてしまう
    cand = [(e, True) for e in edges]
    if len(edges) < n:
        cand += [(t, False) for t in targets]
    cand.sort()
    times = [c[0] for c in cand]
    is_pause = [c[1] for c in cand]
    edges = times
    m = len(edges)
    INF = float("inf")

    def cost(prev_t, t, k):
        # k番目のカットが prev_t〜t になったときの無理さ
        got = t - prev_t
        if got < MIN_TELOP:      # 読めない長さのテロップは作らせない
            return INF
        exp = max(want[k], 0.3)
        return (got - exp) ** 2 / exp

    # best[k][j] = k番目までの境界を決め、k番目が edges[j] のときの最小コスト
    best = [[INF] * m for _ in range(n)]
    back = [[-1] * m for _ in range(n)]
    def bonus(j):
        return 0.0 if is_pause[j] else pause_bonus

    for j in range(m):
        best[0][j] = cost(0.0, edges[j], 0) + bonus(j)
    for k in range(1, n):
        for j in range(m):
            for h in range(j):
                if best[k - 1][h] == INF:
                    continue
                c = best[k - 1][h] + cost(edges[h], edges[j], k) + bonus(j)
                if c < best[k][j]:
                    best[k][j], back[k][j] = c, h
    # 最後のカットの尺も評価に入れる
    end, endj = INF, -1
    for j in range(m):
        if best[n - 1][j] == INF:
            continue
        c = best[n - 1][j] + cost(edges[j], total, n)
        if c < end:
            end, endj = c, j
    if endj < 0:
        return list(targets)
    out, j = [], endj
    for k in range(n - 1, -1, -1):
        out.append(edges[j])
        j = back[k][j]
        if j < 0 and k:
            return list(targets)
    return out[::-1]


def plan_from_voices(paths, cuts_used):
    # 音声ファイルごとの実測時間で、その中のカットに時間を配る。
    # 1本まるごとで按分するとズレが最後まで積もるが、ファイル単位で
    # 区切れば、ズレてもその声が終われば必ず戻る
    blocks = voice_blocks(paths)
    if len(paths) == len(blocks):
        gaps = voice_gaps(paths)
        pairs = [(media_seconds(p) + g, b, p, 0.0)
                 for p, b, g in zip(paths, blocks, gaps)]
    else:
        # 本数が想定と違うときは、全部まとめて1本ぶんとして按分する。
        # 継ぎ目に入れる無音も足しておかないと、そのぶん丸ごとずれる
        pairs = [(sum(media_seconds(p) for p in paths) + sum(voice_gaps(paths)),
                  sorted(cuts_used), None, 0.0)]

    titled = has_title_voice(paths) and len(paths) == len(blocks)

    dur = {}
    for sec, block, src, head in pairs:
        here = [c for c in block if c in cuts_used]
        if not here:
            continue
        # 番号カードは尺を固定する。タイトルも、読み上げが無いなら固定にする。
        # 文字数で割ると、原稿の無いタイトルが一瞬で消えてしまう
        cards = {c: NUMCARD_SEC for c in here if c in SILENT_CUTS}
        if 0 in here and not titled:
            cards[0] = TITLE_SEC
        talk = [c for c in here if c not in cards]
        chars = {c: max(len(NARRATION.get(c, "")),
                        CARD_WEIGHT if c in CARD_CUTS else 1) for c in talk}
        body = max(sec - sum(cards.values()), 0.6)
        unit = body / max(sum(chars.values()), 1)
        dur.update(cards)
        for c in talk:
            dur[c] = max(chars[c] * unit, 0.7)

        # ここまでは文字数の按分。実際の息継ぎに寄せて精度を上げる
        snapped = False
        if src and len(here) > 1:
            # 声の中の時刻に、前の継ぎ目からもらった無音のぶんを足す
            edges = [e + head for e in speech_edges(src)]
            if edges:
                acc, targets = 0.0, []
                for c in here[:-1]:
                    acc += dur[c]
                    targets.append(acc)
                want = [dur[c] for c in here]
                fixed = snap(targets, edges, total=sec, want=want)
                if fixed != targets:
                    # 合わせた境界はそのまま使う。ここで下限や丸めを掛けると
                    # せっかく乗せた切れ目からずれてしまう
                    prev = 0.0
                    for c, t in zip(here[:-1], fixed):
                        dur[c] = t - prev
                        prev = t
                    dur[here[-1]] = sec - prev
                    snapped = True
        if not snapped:
            # 下限を効かせると合計が声より長くなることがある。
            # はみ出したぶんは全体を縮めて、必ず声の長さに収める
            got = sum(dur[c] for c in here)
            if got > sec + 1e-6:
                k = sec / got
                for c in here:
                    dur[c] *= k
    return dur


def make_narration(host, speaker, speed, pitch, intonation, cuts_wanted):
    os.makedirs(AUD, exist_ok=True)
    made, total = 0, 0.0
    for cut in sorted(NARRATION):
        if cuts_wanted and cut not in cuts_wanted:
            continue
        path = os.path.join(AUD, "cut%02d.wav" % cut)
        if not os.path.exists(path):
            try:
                open(path, "wb").write(
                    vv_synth(host, speaker, NARRATION[cut], speed, pitch, intonation))
                made += 1
            except Exception as e:
                print("   カット%-2d  失敗（%s）。5秒待って もう一度試します"
                      % (cut, type(e).__name__))
                if os.path.exists(path):
                    os.remove(path)
                time.sleep(5)
                try:
                    open(path, "wb").write(
                        vv_synth(host, speaker, NARRATION[cut], speed, pitch, intonation))
                    made += 1
                except Exception:
                    print("   カット%-2d  作れませんでした" % cut)
                    if os.path.exists(path):
                        os.remove(path)
                    continue
        total += wav_seconds(path)
    return made, total



# ── 足りないカットの画像を生成する ────────────────────────────────

# Imagen は有料の枠でしか動かない。無料のキーだと 429 が返るので、
# 無料でも使える gemini-2.5-flash-image に落ちられるようにしておく。
# 呼び方も返り方も違うので、方式ごと持つ
GEMINI_MODELS = [("gemini-2.5-flash-image", "generate"),
                 ("imagen-4.0-generate-001", "predict"),
                 ("imagen-3.0-generate-002", "predict")]

NEGATIVE = ("text, letters, watermark, logo, caption, cartoon, anime, "
            "3d render, distorted face, extra fingers, low resolution, blurry")


def gen_body(prompt, how, ratio=True):
    if how == "predict":
        return json.dumps({
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1, "aspectRatio": "9:16",
                           "negativePrompt": NEGATIVE},
        }).encode()
    cfg = {"responseModalities": ["IMAGE"]}
    if ratio:
        cfg["imageConfig"] = {"aspectRatio": "9:16"}
    return json.dumps({
        "contents": [{"parts": [{"text": prompt + "。避けるもの: " + NEGATIVE}]}],
        "generationConfig": cfg,
    }).encode()


def gen_read(res, how):
    if how == "predict":
        preds = res.get("predictions") or []
        if preds and preds[0].get("bytesBase64Encoded"):
            return base64.b64decode(preds[0]["bytesBase64Encoded"])
        return None
    for c in res.get("candidates") or []:
        for part in (c.get("content") or {}).get("parts") or []:
            data = (part.get("inlineData") or part.get("inline_data") or {}).get("data")
            if data:
                return base64.b64decode(data)
    return None


def quota_kind(err):
    # 429 が「1分あたり」なのか「1日ぶん使い切り」なのかを本文から見る
    try:
        body = err.read().decode("utf-8", "ignore")
    except Exception:
        return "minute"
    if re.search(r"PerDay|per day|daily", body, re.I):
        return "day"
    return "minute"


def gen_one(prompt, key):
    last = None
    for model, how in GEMINI_MODELS:
        # imageConfig を知らない版だと 400 になるので、比率なしでもう一度試す
        for ratio in ((True, False) if how == "generate" else (True,)):
            verb = "predict" if how == "predict" else "generateContent"
            url = "https://generativelanguage.googleapis.com/v1beta/models/%s:%s" % (model, verb)
            req = urllib.request.Request(url, data=gen_body(prompt, how, ratio),
                                         method="POST", headers={
                "Content-Type": "application/json", "x-goog-api-key": key,
                "User-Agent": "Mozilla/5.0"})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    img = gen_read(json.loads(r.read()), how)
                if img:
                    return img
                last = "画像が返りませんでした"
            except urllib.error.HTTPError as e:
                last = "HTTP %s" % e.code
                if e.code == 401:        # キーが違う。どのモデルでも同じ
                    raise RuntimeError("キーが違います")
                if e.code == 429:
                    detail = quota_kind(e)
                    if detail == "day":
                        raise RuntimeError("今日の無料枠を使い切りました")
                    last = "混み合っています"
                continue                 # 枠切れもモデル名違いも、次を試す
            except Exception as e:
                last = type(e).__name__
                break
    raise RuntimeError(last or "不明")


def generate_missing(key, only_n, reserve_pexels=False):
    # Pexels と手持ちで埋まらなかったカットだけ作る
    os.makedirs(GEN, exist_ok=True)
    need = []
    for row in CUTS:
        cut = int(row["cut"])
        if only_n and cut > only_n:
            break
        if cut not in PROMPTS:
            continue
        # ④が Pexels で埋めるカットは、まだ落ちていなくても作らない。
        # ここで作ると動く映像が静止画に負けるし、生成の回数も無駄になる
        if reserve_pexels and cut in SEARCH:
            continue
        r = dict(row)
        if row["cut"] in ASSET_ALIAS:
            r["asset"] = ASSET_ALIAS[row["cut"]]
        if find_asset(r, cut) is None:      # 借りる前の、素の状態で見る
            need.append(cut)
    # 番号の無い手持ち素材が空きに入る分は、作らなくてよい
    spare = len(mine_index()[1])
    if spare:
        keep = set(spread(need, spare))
        need = [c for c in need if c not in keep]
        print("     番号の無い素材が %d 点あるので、その分は作りません" % spare)
    if not need:
        print("     足りないカットはありません")
        return
    print("     %d カットを生成します: %s" % (len(need), ", ".join(map(str, need))))
    print("     無料枠は1分あたりの上限が低いので、ゆっくり進みます")
    ok, wait = 0, 6.0
    for cut in need:
        dst = os.path.join(GEN, "%02d.png" % cut)
        # 429 は1分あたりの上限。間を空けて3回まで粘る
        for attempt in range(3):
            try:
                open(dst, "wb").write(gen_one(PROMPTS[cut], key))
                ok += 1
                print("     カット%-2d  できました" % cut)
                break
            except Exception as e:
                if os.path.exists(dst):
                    os.remove(dst)
                if "今日の無料枠" in str(e):
                    print("     カット%-2d  %s" % (cut, e))
                    print("     ここで止めます。明日また押すか、④に進んでください")
                    print("     （足りないカットは近くの映像で埋まります）")
                    _PLAN_CACHE.clear()
                    print("     %d / %d 枚できました" % (ok, len(need)))
                    return
                if attempt == 2:
                    print("     カット%-2d  失敗（%s）" % (cut, e))
                else:
                    print("     カット%-2d  混み合っています。%d秒待ちます"
                          % (cut, int(wait * (attempt + 1) * 5)))
                    time.sleep(wait * (attempt + 1) * 5)
        time.sleep(wait)
    _PLAN_CACHE.clear()
    global _MINE_CACHE
    _MINE_CACHE = None          # 作った分を見直す
    print("     %d / %d 枚できました" % (ok, len(need)))


# ── テロップ ──

# 参考動画に合わせて、白→黄→赤→白。暗い海の上でいちばん飛ぶ組み合わせ
TITLE_LINES = [("今も正体が", "#FFFFFF", 0.72),
               ("分かっていない", "#FFD400", 1.00),
               ("地球の音", "#FF1F1F", 0.86),
               ("3選", "#FFFFFF", 0.34)]


def fit_font(draw, text, font_path, target_w, cap):
    # 行ごとに、目標の幅に収まる最大のサイズを探す
    from PIL import ImageFont
    lo, hi, best = 20, cap, None
    while lo <= hi:
        mid = (lo + hi) // 2
        f = ImageFont.truetype(font_path, mid)
        if draw.textlength(text, font=f) <= target_w:
            best, lo = f, mid + 1
        else:
            hi = mid - 1
    return best or ImageFont.truetype(font_path, 20)


def draw_title(font_path, out):
    # 行ごとに大きさと色を変える。1行にベタ打ちすると弱い。
    # 参考動画はどれも横幅いっぱいまで文字を使い、黒フチが芯と同じくらい太い
    from PIL import Image, ImageDraw
    tf = find_title_font() or font_path
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    fonts = []
    for text, col, k in TITLE_LINES:
        f = fit_font(d, text, tf, W * 0.90 * k, int(W * 0.34))
        fonts.append((text, col, f))
    heights = [int(f.size * 1.16) for _, _, f in fonts]
    y = (H - sum(heights)) // 2

    # 背後をうっすら暗くして、どんな素材でも文字が立つようにする
    pad = int(W * 0.05)
    d.rectangle([0, y - pad, W, y + sum(heights) + pad], fill=(0, 0, 0, 115))

    for (text, col, fnt), lh in zip(fonts, heights):
        x = (W - d.textlength(text, font=fnt)) / 2
        sw = max(int(fnt.size * 0.11), 8)          # 芯に対して十分な太さの縁
        d.text((x, y), text, font=fnt, fill=col, stroke_width=sw, stroke_fill="black")
        y += lh
    im.save(out)


def telop(row, font, out):
    from PIL import Image, ImageDraw, ImageFont
    if row["hl"] == "TITLE":
        return draw_title(font, out)
    numcard = row["hl"] == "ALL"
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    # 標準の太ゴシックだと安っぽい。見出し用の極太を本文にも使う
    face = find_title_font() or font
    cap = 96 if numcard else 78
    lines_raw = [l for l in (row["telop1"], row["telop2"]) if l]
    fnt = min((fit_font(d, l, face, W * 0.88, cap) for l in lines_raw),
              key=lambda f: f.size)
    size = fnt.size

    def split(line):
        if numcard:
            return [(line, COLORS["red"])]
        hl = row["hl"]
        if hl and hl in line:
            i = line.index(hl)
            segs = []
            if line[:i]:
                segs.append((line[:i], "#FFFFFF"))
            segs.append((hl, COLORS.get(row["hl_color"], "#FFFFFF")))
            if line[i + len(hl):]:
                segs.append((line[i + len(hl):], "#FFFFFF"))
            return segs
        return [(line, "#FFFFFF")]

    # 番号は丸で囲む。参考動画も「②」の形で出していて、そのほうが締まる
    badge = None
    if numcard and lines_raw and len(lines_raw[0]) <= 2 and lines_raw[0].isdigit():
        badge = lines_raw[0]
        lines_raw = lines_raw[1:]
        fnt = min((fit_font(d, l, face, W * 0.88, cap) for l in lines_raw),
                  key=lambda f: f.size)
        size = fnt.size

    lines = lines_raw
    lh = int(size * 1.30)
    y = int(H * .58) - (len(lines) - 1) * lh // 2
    sw = max(int(size * 0.13), 8)      # 参考動画は芯と同じくらい黒フチが太い

    # 先に影だけを別の層に描いてぼかす。フチだけだと背景に沈む
    from PIL import ImageFilter
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(shadow)
    yy = y
    for line in lines:
        segs = split(line)
        x = (W - sum(d.textlength(t, font=fnt) for t, _ in segs)) / 2
        for txt, _ in segs:
            ds.text((x, yy + size * 0.06), txt, font=fnt, fill=(0, 0, 0, 200),
                    stroke_width=sw, stroke_fill=(0, 0, 0, 200))
            x += d.textlength(txt, font=fnt)
        yy += lh
    im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(size * 0.10)))

    for line in lines:
        segs = split(line)
        x = (W - sum(d.textlength(t, font=fnt) for t, _ in segs)) / 2
        for txt, col in segs:
            d.text((x, y), txt, font=fnt, fill=col,
                   stroke_width=sw, stroke_fill="black")
            x += d.textlength(txt, font=fnt)
        y += lh

    if badge:
        from PIL import ImageFont as _IF
        bs = int(size * 0.86)
        bf = _IF.truetype(face, bs)
        r = int(bs * 0.82)
        cx, cy = W // 2, int(H * .58) - (len(lines) - 1) * lh // 2 - int(r * 1.5)
        ring = max(int(bs * 0.11), 7)
        # 黒フチ→色の順に描いて、どんな背景でも輪郭が立つようにする
        col = COLORS.get(row["hl_color"], "#FF2A2A")
        for w_, c_ in ((ring + sw, "black"), (ring, col)):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c_, width=w_)
        bw = d.textlength(badge, font=bf)
        bb = d.textbbox((0, 0), badge, font=bf)
        d.text((cx - bw / 2, cy - (bb[3] + bb[1]) / 2), badge, font=bf,
               fill=col, stroke_width=sw, stroke_fill="black")
    im.save(out)


def camera(kind, n, video=False):
    n = max(n, 2)
    # 1カット1.5秒ほどしかないので、控えめに振ると動いていないように見える。
    # 実写は素材自体も動くぶん、静止画より少し弱くする
    amp = 0.11 if video else 0.18
    zmax = 1.0 + amp
    if kind == "zoomout":
        z, x, y = "max(%f-%f*on,1.0)" % (zmax, amp / n), "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif kind == "panleft":
        z, x, y = "%f" % (zmax,), "(iw-iw/zoom)*(1-on/%d)" % n, "ih/2-(ih/zoom/2)"
    elif kind == "panright":
        z, x, y = "%f" % (zmax,), "(iw-iw/zoom)*(on/%d)" % n, "ih/2-(ih/zoom/2)"
    elif kind == "pandown":
        z, x, y = "%f" % (zmax,), "iw/2-(iw/zoom/2)", "(ih-ih/zoom)*(on/%d)" % n
    elif kind == "still":
        # 「止め」でも動かす。完全静止が1カットでも混ざると、そこで目が止まる
        z = "min(1.0+%f*on,%f)" % (amp * 0.6 / n, 1.0 + amp * 0.6)
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    else:
        z, x, y = "min(1.0+%f*on,%f)" % (amp / n, zmax), "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    # 動画は1入力フレーム=1出力フレーム。静止画は d=n で伸ばす
    d = 1 if video else n
    return ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
            "zoompan=z='%s':d=%d:x='%s':y='%s':s=%dx%d:fps=%d"
            % (W * 2, H * 2, W * 2, H * 2, z, d, x, y, W, H, FPS))


def unpack_zips():
    # /content に置かれた zip は素材として展開する。中の階層は無視して平らに置く
    import glob, zipfile
    zips = sorted(glob.glob("/content/*.zip"))
    if not zips:
        return
    os.makedirs(MINE, exist_ok=True)
    total = 0
    for z in zips:
        try:
            with zipfile.ZipFile(z) as f:
                for info in f.infolist():
                    if info.is_dir():
                        continue
                    name = os.path.basename(info.filename)
                    if not name or name.startswith("."):
                        continue
                    if os.path.splitext(name)[1].lower() not in VIDEO_EXT | {".png", ".jpg", ".jpeg", ".webp"}:
                        continue
                    dst = os.path.join(MINE, name)
                    if os.path.exists(dst):
                        continue
                    with f.open(info) as src, open(dst, "wb") as out:
                        shutil.copyfileobj(src, out)
                    total += 1
        except Exception as e:
            print("   %s は展開できませんでした（%s）" % (os.path.basename(z), type(e).__name__))
    if total:
        print("     zip から %d 点を取り出しました" % total)


MAX_CUT = max(int(r["cut"]) for r in CUTS)


def cut_of(name):
    # 名前からカット番号を読む。「cut25」「カット25」を優先し、
    # 無ければ最初の数字。番号として有り得ない値なら「番号なし」とみなす。
    # hf_20260804_183232_1.png のような生成ツールの名前を誤って拾わないため
    m = re.search(r"(?:cut|カット)[ _\-]*(\d+)", name, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)", name)
    if m and int(m.group(1)) <= MAX_CUT:
        return int(m.group(1))
    return None


def _scan_mine():
    # 手で置いた素材を1回だけ見て、番号つきと番号なしに分ける
    import glob
    numbered, spare = {}, []
    for d in (MINE, GEN, "/content/素材_画像", "/content/素材_動画"):
        if not os.path.isdir(d):
            continue
        for fp in sorted(glob.glob(os.path.join(d, "*"))):
            if os.path.splitext(fp)[1].lower() not in VIDEO_EXT | {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            name = os.path.basename(fp)
            cut = cut_of(name)
            if cut is None:
                spare.append(fp)
                continue
            # 同じカットに複数あれば、_ok つきを差し替え版として優先する
            cur = numbered.get(cut)
            if cur is None or ("_ok" in name and "_ok" not in os.path.basename(cur)):
                numbered[cut] = fp
    return numbered, spare


_MINE_CACHE = None


def mine_index():
    global _MINE_CACHE
    if _MINE_CACHE is None:
        _MINE_CACHE = _scan_mine()
    return _MINE_CACHE


def find_mine(cut):
    # 自分で用意した素材。名前の先頭にカット番号があれば拾う。
    # 4.png / 04.jpg / cut4.png / カット4_海.png / 4-2.mp4 … どれでもよい
    return mine_index()[0].get(cut)


def spread(items, n):
    # items から n 個を等間隔に選ぶ。前半に固まらせないため
    n = min(n, len(items))
    return [items[k * len(items) // n] for k in range(n)] if n else []


def find_asset(row, cut):
    mine = find_mine(cut)
    if mine:
        return mine
    for d in (IMG, VID):
        if not os.path.isdir(d):
            continue
        hits = sorted(os.path.join(d, f) for f in os.listdir(d)
                      if f.startswith(row["asset"][:3]) or f.startswith("cut%02d_" % cut))
        hits = [h for h in hits if os.path.splitext(h)[1].lower() in VIDEO_EXT | {".png", ".jpg", ".jpeg"}]
        if hits:
            ok = [h for h in hits if "_ok" in os.path.basename(h)]
            return (ok or hits)[0]
    return None


ASSET_ALIAS = {"6": "A06", "7": "A06", "32": "A26"}


ROTATE = ["zoomin", "panright", "zoomout", "panleft", "pandown"]
_PLAN_CACHE = {}


def resolve_assets(only_n):
    if only_n in _PLAN_CACHE:
        return _PLAN_CACHE[only_n]
    plan = _resolve_assets(only_n)
    _PLAN_CACHE[only_n] = plan
    return plan


def _resolve_assets(only_n):
    # 素材が無いカットは近くの映像を借りる。絵が変わらないと、
    # セリフだけ進んで「音が合っていない」ように見えてしまう
    plan, have = [], []
    for row in CUTS:
        cut = int(row["cut"])
        if only_n and cut > only_n:
            break
        r = dict(row)
        if row["cut"] in ASSET_ALIAS:
            r["asset"] = ASSET_ALIAS[row["cut"]]
        a = find_asset(r, cut)
        if a is None and cut == 0:
            a = find_asset({"asset": "A01"}, 1)
        plan.append([cut, r, a])
        if a:
            have.append((cut, a))

    # 番号が付いていない手持ちの素材は、空いているカットに散らして使う。
    # 生成ツールが付けた名前のままでも、捨てずに済ませたい
    spare = [p for p in mine_index()[1] if p not in {a for _, a in have}]
    gaps = [i for i, (_, _, a) in enumerate(plan) if not a]
    for i, sp in zip(spread(gaps, len(spare)), spare):
        plan[i][2] = sp
        have.append((plan[i][0], sp))
    if spare and gaps:
        print("     番号の無い素材 %d 点を空いているカットに入れました"
              % min(len(spare), len(gaps)))

    if not have:
        return plan

    # 図版はそのカットの説明のために描いたもの。他所で使い回すと
    # 同じ絵が何度も出てきて、見ているほうは飽きる
    pool = [(c, a) for c, a in have if not a.startswith(IMG)] or have

    used = {}
    for _, _, a in plan:
        if a:
            used[a] = used.get(a, 0) + 1

    borrowed = 0
    for i, (cut, r, a) in enumerate(plan):
        if a:
            continue
        # 前だけ見ても、次のカットが同じ絵を持っていれば並んでしまう
        prev = plan[i - 1][2] if i else None
        prev2 = plan[i - 2][2] if i > 1 else None
        nxt = plan[i + 1][2] if i + 1 < len(plan) else None
        # 近さより「使われていないもの」を優先する。近い順だけで選ぶと
        # 隣の1枚が何度も呼ばれてしまう
        cand = sorted(pool, key=lambda t: (used.get(t[1], 0),
                                           abs(t[0] - cut)))
        pick = next((p for _, p in cand
                     if p != prev and p != prev2 and p != nxt), None)
        if pick is None:
            pick = next((p for _, p in cand if p != prev and p != nxt), None)
        if pick is None:
            pick = next((p for _, p in cand if p != prev), cand[0][1])
        plan[i][2] = pick
        used[pick] = used.get(pick, 0) + 1
        # 借り物は動きを変えて、同じ絵に見えないようにする
        plan[i][1] = dict(r, camera=ROTATE[cut % len(ROTATE)], _borrowed=True)
        borrowed += 1
    if borrowed:
        print("     素材が無い %d カットは近くの映像を借ります" % borrowed)
        top = sorted(used.items(), key=lambda kv: -kv[1])[:1]
        if top and top[0][1] >= 4:
            print("     ※ %s が %d 回出ます。素材を足すと減ります"
                  % (os.path.basename(top[0][0])[:28], top[0][1]))
    return plan


def warn_low_res(plan):
    # 横素材を縦に切ると横幅の 9/16 しか残らない。元が小さいとぼやける
    FF = ffmpeg_bin()
    seen, bad = set(), []
    for cut, r, a in plan:
        if not a or a in seen or os.path.splitext(a)[1].lower() not in VIDEO_EXT:
            continue
        seen.add(a)
        out = subprocess.run([FF, "-hide_banner", "-i", a],
                             capture_output=True, text=True).stderr
        m = re.search(r"(\d{3,4})x(\d{3,4})", out)
        if not m:
            continue
        w, h = int(m.group(1)), int(m.group(2))
        keep = min(w, int(h * 9 / 16)) if w > h else w
        if keep < 600:
            bad.append((os.path.basename(a), w, h))
    if bad:
        print("     切り出すと粗くなる素材:")
        for n, w, h in bad[:6]:
            print("       %s (%dx%d)" % (n[:40], w, h))


def report_sources(plan):
    kind = {"自分で用意": 0, "Pexels": 0, "図版": 0, "借用": 0}
    for cut, r, a in plan:
        if not a:
            continue
        if r.get("_borrowed"):
            kind["借用"] += 1
        elif a.startswith(MINE) or "/content/素材" in a:
            kind["自分で用意"] += 1
        elif a.startswith(IMG):
            kind["図版"] += 1
        else:
            kind["Pexels"] += 1
    print("     素材の内訳: " + " / ".join("%s %d" % (k, v) for k, v in kind.items() if v))


def build(font, only_n, out, fixed_dur=None):
    FF = ffmpeg_bin()
    os.makedirs(TMP, exist_ok=True)
    segs = []
    elapsed = 0.0
    for i, (cut, r, asset) in enumerate(resolve_assets(only_n)):
        if asset is None:
            continue
        wav = os.path.join(AUD, "cut%02d.wav" % cut)
        wav = wav if os.path.exists(wav) else None
        if fixed_dur is not None:
            wav = None                      # 音声は最後にまとめて敷く
            dur = fixed_dur.get(cut, 2.2)
        elif r["hl"] == "TITLE":
            dur = wav_seconds(wav) if wav else 3.5
        elif r["hl"] == "ALL":
            dur = NUMCARD_SEC
        elif wav:
            dur = wav_seconds(wav)          # 声の長さがそのままカットの長さになる
        else:
            dur = 2.2
        if fixed_dur is None:
            dur += GAP_ITEM_END if r["item_end"] == "1" else GAP
        if r["hl"] == "TITLE":
            dur = max(dur, 3.2)
        use_trans = wants_trans(i, r) if dur > TRANS_SEC * 2 else ""
        tp = os.path.join(TMP, "t%02d.png" % cut)
        seg = os.path.join(TMP, "s%02d.mp4" % cut)
        telop(r, font, tp)
        # カットごとに丸めると端数が積もって、後半ほど境界がずれる。
        # 通しの時間で丸めてから差を取れば、ずれは1フレームに収まる
        frames = int(round((elapsed + dur) * FPS)) - int(round(elapsed * FPS))
        frames = max(frames, 2)
        elapsed += dur
        dur = frames / float(FPS)      # 実際に書き出す長さに合わせる
        args = [FF, "-hide_banner", "-loglevel", "error", "-y"]
        if os.path.splitext(asset)[1].lower() in VIDEO_EXT:
            # 実写にも必ず動きを足す。素材が動いていても、寄り引きが無いと単調に見える
            args += ["-stream_loop", "-1", "-i", asset]
            vf = ("fps=%d," % FPS) + camera(r["camera"], frames, video=True)
        else:
            args += ["-loop", "1", "-i", asset]
            vf = camera(r["camera"], frames)
        # 生成サービスの透かしは下端(縦 0.90 付近)に入る。実測して 88% で切る
        if asset.startswith(MINE) or "/content/素材_" in asset:
            vf = "crop=iw:ih*0.88:0:0," + vf
        # 1枚絵のまま渡すと t が進まず、fade も scale も効かない
        args += ["-loop", "1", "-framerate", str(FPS), "-i", tp]
        if wav:
            args += ["-i", wav]
            amap = "[2:a]apad[a]"
        else:
            args += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
            amap = "[2:a]anull[a]"
        args += ["-filter_complex",
                 "[0:v]%s[bg];%s;%s;%s"
                 % (vf, telop_filter(), trans_filter(use_trans, dur), amap),
                 "-map", "[vv]", "-map", "[a]", "-t", "%.3f" % dur, "-r", str(FPS),
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                 "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                 "-ar", "44100", "-ac", "2", seg]
        sh(args)
        segs.append(seg)
        print("   カット%-2d  %s" % (cut, os.path.basename(asset)[:38]))
    if not segs:
        sys.exit("素材が1つも無いので作れませんでした。")
    lst = os.path.join(TMP, "list.txt")
    with open(lst, "w") as f:
        for s in segs:
            f.write("file '%s'\n" % s)
    sh([FF, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])
    return len(segs)


def main():
    global FACE, ANIM, TRANS_MODE
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--range", type=int, default=0, help="0なら全部")
    ap.add_argument("--out", default="動画.mp4")
    ap.add_argument("--voice", default="", help="VOICEVOXの話者名。空なら声なし")
    ap.add_argument("--vv-host", default="http://127.0.0.1:50021")
    ap.add_argument("--speed", type=float, default=1.10)
    ap.add_argument("--pitch", type=float, default=-0.04)
    ap.add_argument("--intonation", type=float, default=0.95)
    ap.add_argument("--gen-images", default="", help="Geminiのキー。足りないカットを生成して終了")
    ap.add_argument("--face", default=FACE, choices=sorted(FACES), help="テロップの書体")
    ap.add_argument("--anim", default=ANIM, choices=ANIMS, help="テロップの出し方")
    ap.add_argument("--trans", default=TRANS_MODE, choices=TRANS, help="カットの切り替え")
    ap.add_argument("--bgm", default="", help="BGMのファイル。空なら /content から探す")
    ap.add_argument("--bgm-db", type=float, default=-11.0, help="ナレーションに対する音量")
    a = ap.parse_args()
    FACE = a.face
    ANIM = a.anim
    TRANS_MODE = a.trans

    os.makedirs(WORK, exist_ok=True)
    only = a.range or None

    if a.gen_images:
        print("足りないカットの画像をつくります")
        render_figures()
        unpack_zips()
        # ③は④より先に押される。Pexels をまだ落としていない状態で数えると
        # 「全部足りない」に見えるので、キーがあるなら先に落としてから数える
        real_key = a.key.strip() and a.key.strip() != "x"
        if real_key:
            wanted = {c for c in SEARCH if not only or c <= only}
            print("     先に Pexels を落とします（%dカット）" % len(wanted))
            got, _ = pexels(a.key.strip(), wanted)
            print("     %d本 取得" % got)
        else:
            print("     Pexels のキーが無いので、④が埋めるカットは作りません")
        generate_missing(a.gen_images.strip(), only, reserve_pexels=not real_key)
        return
    wanted = {c for c in SEARCH if not only or c <= only}

    print("1/4  図版をつくる")
    render_figures()
    unpack_zips()

    # 1カット1ファイルが置いてあれば、そちらが確実。推測が要らない
    per_cut = adopt_cut_voices()
    need = len([r for r in CUTS if not only or int(r["cut"]) <= only])
    if per_cut >= max(need - 2, 3):
        print("2/4  カットごとの音声を使います（%d本）" % per_cut)
        print("     1カット＝1ファイルなので、切り替えの推測はしません")
        voices, fixed, voice_file = [], None, None
        per_cut_ok = True
    else:
        per_cut_ok = False
        if per_cut:
            print("     カット別の音声が %d/%d 本しかないので、まとめて割り振ります"
                  % (per_cut, need))
        voices = find_voice_files()
        fixed, voice_file = None, None
    if voices:
        print("2/4  用意された音声を使います（%d本）" % len(voices))
        titled = has_title_voice(voices)
        for i, v in enumerate(voices):
            what = "タイトル" if (titled and i == 0) else "声%d" % (i if titled else i + 1)
            print("     %-8s %-22s %5.1f秒"
                  % (what, os.path.basename(v)[:22], media_seconds(v)))
        want = len(BLOCKS) + (1 if titled else 0)
        if len(voices) != want:
            print("     ※ %d本のはずが %d本です。台本のブロックと数が合わないので、"
                  % (want, len(voices)))
            print("       全部まとめて割り振ります（音が少しずれることがあります）")
        elif not all(os.path.basename(v).startswith(("声", "voice")) for v in voices):
            print("     ※ 名前で順番を決めました。上の並びが台本の順と違っていたら、")
            print("       声1.wav 声2.wav … と付け直してください")
    elif a.voice and not per_cut_ok:
        print("2/4  ナレーションをつくる")
        if not vv_alive(a.vv_host):
            sys.exit("VOICEVOX につながりません。エンジンを起動するか、\n"
                     "自分で作った音声を /content に「声.wav」の名前で置いてください。")
        sp = vv_find_speaker(a.vv_host, a.voice)
        if not sp:
            names = sorted({t[1] for t in vv_speakers(a.vv_host)})
            sys.exit("話者「%s」が見つかりません。使えるのは: %s" % (a.voice, "、".join(names)))
        print("     %s（%s） ID=%d" % (sp[1], sp[2], sp[0]))
        narr_cuts = {c for c in NARRATION if not only or c <= only}
        made, total = make_narration(a.vv_host, sp[0], a.speed, a.pitch, a.intonation, narr_cuts)
        print("     %d本 生成 / 発話 %.1f秒" % (made, total))
    elif not per_cut_ok:
        print("2/4  ナレーションは作りません")

    print("3/4  Pexelsから映像を落とす（%dカット）" % len(wanted))
    got, miss = pexels(a.key, wanted)
    print("     %d本 取得" % got)
    if miss:
        print("     見つからなかったカット: %s" % ", ".join(map(str, miss)))

    font = find_font()
    if not font:
        sys.exit("日本語フォントが見つかりません。")

    if voices:
        # 素材が無くて飛ばすカットに時間を配ると、その分だけ音がずれる。
        # 実際に使えるカットだけで割り振る
        have = [c for c, _, a in resolve_assets(only) if a]
        fixed = plan_from_voices(voices, set(have))
        voice_file = join_voices(voices)
        print("     使えるカット %d / 音声 %.1f秒" % (len(have), media_seconds(voice_file)))

    print("4/4  動画を組み立てる")
    _plan = resolve_assets(only)
    report_sources(_plan)
    warn_low_res(_plan)
    if fixed is None:
        n = build(font, only, a.out)
    else:
        tmp = os.path.join(WORK, "no_audio.mp4")
        n = build(font, only, tmp, fixed_dur=fixed)
        sh([ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y",
            "-i", tmp, "-i", voice_file, "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", a.out])
    bgm = a.bgm.strip() or find_bgm()
    if bgm and os.path.exists(bgm):
        tmp = os.path.join(WORK, "with_bgm.mp4")
        try:
            mix_bgm(a.out, bgm, a.bgm_db, tmp)
            shutil.move(tmp, a.out)
            print("     BGM: %s（%.0fdB）" % (os.path.basename(bgm), a.bgm_db))
        except Exception as e:
            print("     BGM を混ぜられませんでした（%s）。音声はそのままです" % e)
    elif bgm:
        print("     BGM が見つかりません: %s" % bgm)

    print("\n完成： %s（%dカット）" % (a.out, n))


if __name__ == "__main__":
    main()
