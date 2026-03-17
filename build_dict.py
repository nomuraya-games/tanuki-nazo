"""
JMdict_e から優先読みのひらがな単語セットを抽出して kana_words.txt に保存する。

目的:
    策問ジェネレータで「この文字列は日本語として存在するか」を
    辞書引きで判定するためのデータを準備する。

優先読みの条件:
    re_pri タグに ichi1 / news1 / nf** のいずれかを持つ読みのみ採用。
    これにより「きんしょく」（金色の非一般読み）等を除外できる。
"""

import re
import xml.etree.ElementTree as ET

JMDICT_PATH = "JMdict_e"
OUTPUT_PATH = "kana_words.txt"

# ひらがなのみで構成された文字列か判定
HIRAGANA_RE = re.compile(r"^[\u3041-\u3096ー]+$")

# 優先度タグ: ichi1=一般語, news1=ニュース頻出, spec1/2=特殊一般語, nf**=頻度ランク
PRIORITY_RE = re.compile(r"^(ichi1|ichi2|news1|news2|spec1|spec2|nf\d+)$")


def extract_kana_words(jmdict_path: str) -> set[str]:
    words = set()
    tree = ET.parse(jmdict_path)
    root = tree.getroot()

    for entry in root.findall("entry"):
        for r_ele in entry.findall("r_ele"):
            reb = r_ele.find("reb")
            if reb is None or not reb.text:
                continue
            text = reb.text
            if not HIRAGANA_RE.match(text):
                continue
            # re_pri タグが1つでも優先タグを持つ読みのみ採用
            pri_tags = [p.text for p in r_ele.findall("re_pri") if p.text]
            if any(PRIORITY_RE.match(t) for t in pri_tags):
                words.add(text)

    return words


if __name__ == "__main__":
    print("JMdict を解析中...")
    words = extract_kana_words(JMDICT_PATH)
    print(f"{len(words):,} 件のひらがな単語を抽出")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for word in sorted(words):
            f.write(word + "\n")

    print(f"{OUTPUT_PATH} に保存しました")
