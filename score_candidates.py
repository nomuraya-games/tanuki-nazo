"""
たぬき謎 候補スコアリング

目的:
    candidates.json の各候補（問題文・答え）に Google Trends スコアを付与する。
    スコアが低い候補（一般語でない）を除外しやすくする。

スコアの意味:
    Google Trends の相対検索量（0〜100）。
    漢字表記が存在しない単語は score=0 とする。

キャッシュ:
    word_scores.json に単語→スコアを保存。再実行時は API を叩かない。

使い方:
    uv run score_candidates.py [--min-score N]
    例: uv run score_candidates.py --min-score 5
"""

import json
import sys
import time
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from pytrends.request import TrendReq

CANDIDATES_PATH = "candidates.json"
CACHE_PATH = "word_scores.json"
JMDICT_PATH = "JMdict_e"

HIRAGANA_RE = re.compile(r"^[\u3041-\u3096ー]+$")
BATCH_SIZE = 5      # pytrends は1リクエスト最大5単語
SLEEP_SEC = 1.5     # レート制限対策


def build_kana_to_kanji(jmdict_path: str) -> dict[str, str]:
    """JMdict からひらがな→漢字表記（最初の非ひらがな表記）のマッピングを構築"""
    mapping = {}
    tree = ET.parse(jmdict_path)
    root = tree.getroot()
    for entry in root.findall("entry"):
        readings = [r.text for r in entry.findall("r_ele/reb")
                    if r.text and HIRAGANA_RE.match(r.text)]
        kanjis = [k.text for k in entry.findall("k_ele/keb") if k.text]
        kanji_only = [k for k in kanjis if not HIRAGANA_RE.match(k)]
        for reading in readings:
            if reading not in mapping and kanji_only:
                mapping[reading] = kanji_only[0]
    return mapping


def fetch_scores(words: list[str], pytrends: TrendReq) -> dict[str, float]:
    """pytrends で単語リストのスコアを取得（5単語ずつバッチ処理）"""
    scores = {}
    batches = [words[i:i + BATCH_SIZE] for i in range(0, len(words), BATCH_SIZE)]

    for i, batch in enumerate(batches):
        try:
            pytrends.build_payload(batch, timeframe="today 12-m", geo="JP")
            df = pytrends.interest_over_time()
            for word in batch:
                scores[word] = float(df[word].mean()) if word in df.columns else 0.0
        except Exception as e:
            print(f"  ⚠️  バッチ{i+1}エラー ({batch}): {e}")
            for word in batch:
                scores[word] = -1.0  # エラー扱い（キャッシュに保存してスキップ）
        if i < len(batches) - 1:
            time.sleep(SLEEP_SEC)

    return scores


def main():
    min_score = 0
    args = sys.argv[1:]
    if "--min-score" in args:
        min_score = int(args[args.index("--min-score") + 1])

    # candidates.json 読み込み
    candidates = json.loads(Path(CANDIDATES_PATH).read_text(encoding="utf-8"))

    # キャッシュ読み込み
    cache_path = Path(CACHE_PATH)
    cache: dict[str, float] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        print(f"キャッシュ読み込み: {len(cache)}件")

    # JMdict でひらがな→漢字マッピング構築
    print("JMdict 読み込み中...")
    kana_to_kanji = build_kana_to_kanji(JMDICT_PATH)

    # スコアが必要な単語を収集（キャッシュ未取得のもの）
    needed_kana: set[str] = set()
    for c in candidates:
        for word in [c["question"], c["answer"]]:
            kanji = kana_to_kanji.get(word)
            if kanji and kanji not in cache:
                needed_kana.add(word)

    needed_kanji = [kana_to_kanji[w] for w in needed_kana]
    print(f"スコア取得対象: {len(needed_kanji)}件（キャッシュ済み除く）")

    # pytrends でスコア取得
    if needed_kanji:
        print("Google Trends からスコア取得中...")
        pytrends = TrendReq(hl="ja-JP", tz=540)
        new_scores = fetch_scores(needed_kanji, pytrends)

        # ひらがな→漢字→スコアの逆引きでキャッシュに追加
        kanji_to_score = new_scores
        for kana in needed_kana:
            kanji = kana_to_kanji[kana]
            if kanji in kanji_to_score:
                cache[kanji] = kanji_to_score[kanji]

        # キャッシュ保存
        cache_path.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"キャッシュ更新: {len(cache)}件 → {CACHE_PATH}")

    # candidates.json にスコアを付与
    rejected = 0
    for c in candidates:
        q_kanji = kana_to_kanji.get(c["question"])
        a_kanji = kana_to_kanji.get(c["answer"])
        q_score = cache.get(q_kanji, 0.0) if q_kanji else 0.0
        a_score = cache.get(a_kanji, 0.0) if a_kanji else 0.0
        c["score_q"] = round(q_score, 1)
        c["score_a"] = round(a_score, 1)
        c["score_min"] = round(min(q_score, a_score), 1)

        # --min-score 指定時は自動却下
        if min_score > 0 and c["status"] == "pending" and c["score_min"] < min_score:
            c["status"] = "rejected"
            rejected += 1

    # スコア順にソート（置き換え系優先、score_min 降順）
    candidates.sort(key=lambda x: (
        0 if x["type"] == "置き換え系" else 1,
        -x["score_min"],
        -len(x["question"])
    ))

    Path(CANDIDATES_PATH).write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # 結果サマリー
    print(f"\n--- スコアリング結果 ---")
    scored = [c for c in candidates if c["score_min"] > 0]
    zero = [c for c in candidates if c["score_min"] == 0]
    print(f"  スコアあり: {len(scored)}件")
    print(f"  スコア0（漢字表記なし等）: {len(zero)}件")
    if min_score > 0:
        print(f"  自動却下（score_min < {min_score}）: {rejected}件")

    print(f"\n--- 上位10件（置き換え系） ---")
    replace = [c for c in candidates if c["type"] == "置き換え系" and c["score_min"] > 0]
    for c in replace[:10]:
        print(f"  問題「{c['question']}」({c['score_q']}) [{c['rule']}] → 答え「{c['answer']}」({c['score_a']})  min={c['score_min']}")

    print(f"\n{CANDIDATES_PATH} を更新しました")


if __name__ == "__main__":
    main()
