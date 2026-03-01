"""
たぬき謎 策問ジェネレータ

目的:
    答えを入力すると、ルールを逆適用して問題文候補を自動生成する。
    問題文・答えともに辞書に存在する組み合わせのみ出力する。
    --min-len で問題文の最小文字数を指定可能（デフォルト7）。
    複数ルールの組み合わせ（2段階）にも対応。

使い方:
    uv run generator.py <答え> [--min-len N]
    例: uv run generator.py かな
    例: uv run generator.py かな --min-len 7
"""

import sys
from itertools import product, combinations

DICT_PATH = "kana_words.txt"

# 削除系ルール: (ルール名, 削除する文字列)
DELETE_RULES = [
    ("たぬき", "た"),
    ("こけし", "こ"),
    ("けしごむ", "ごむ"),
    ("ちりとり", "ちり"),
    ("とりい", "い"),
    ("おとしあな", "おとし"),
    ("ひきだし", "ひき"),
]

# 置き換え系ルール: (ルール名, 問題文の文字, 答えの文字)
# 問題文の「before」を答えの「after」に置換すると答えになる
REPLACE_RULES = [
    ("めがね", "め", "ね"),
    ("かがみ", "か", "み"),
    ("うがい", "う", "い"),
    ("はがき", "は", "き"),
    ("まがお", "ま", "お"),
    ("えがお", "え", "お"),
    ("ぞうきんがけ", "ぞうきん", "け"),
    ("うらがえし", "うら", "えし"),
    ("あまがさ", "あま", "さ"),
]


def load_dict(path: str) -> set[str]:
    with open(path, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def insert_at(word: str, insert: str, pos: int) -> str:
    """word の pos 番目に insert を挿入する"""
    return word[:pos] + insert + word[pos:]


def generate_delete_candidates(answer: str, rule_char: str) -> list[str]:
    """削除系の逆適用: answerのどこかにrule_charを挿入した候補を列挙"""
    candidates = []
    for pos in range(len(answer) + 1):
        candidates.append(insert_at(answer, rule_char, pos))
    return candidates


def generate_replace_candidates(answer: str, before: str, after: str) -> list[str]:
    """置き換え系の逆適用: answerの「after」を「before」に戻した候補を列挙"""
    candidates = []
    start = 0
    while True:
        idx = answer.find(after, start)
        if idx == -1:
            break
        candidate = answer[:idx] + before + answer[idx + len(after):]
        candidates.append(candidate)
        start = idx + 1
    return candidates


def apply_single_rule(answer: str) -> list[tuple[str, str, str]]:
    """1ルールを逆適用した (問題文候補, ルール名, 種別) のリストを返す"""
    results = []

    for rule_name, rule_char in DELETE_RULES:
        for q in generate_delete_candidates(answer, rule_char):
            if q != answer:
                results.append((q, rule_name, "削除系"))

    for rule_name, before, after in REPLACE_RULES:
        for q in generate_replace_candidates(answer, before, after):
            if q != answer:
                results.append((q, rule_name, "置き換え系"))

    return results


def generate(answer: str, dictionary: set[str], min_len: int = 5) -> list[dict]:
    """答えからルールを逆適用して問題文候補を生成（1段階・2段階）"""
    results = []
    seen = set()

    # 1段階: 1ルール適用
    for question, rule_name, kind in apply_single_rule(answer):
        if question in dictionary and len(question) >= min_len:
            key = (question, rule_name)
            if key not in seen:
                seen.add(key)
                results.append({
                    "rules": rule_name,
                    "question": question,
                    "answer": answer,
                    "type": kind,
                })

    # 2段階: 2ルール組み合わせ
    # 中間語は辞書不要（問題文と答えだけ辞書ヒットを要求）
    stage1 = apply_single_rule(answer)
    for mid, rule1, kind1 in stage1:
        for question, rule2, kind2 in apply_single_rule(mid):
            if question in dictionary and len(question) >= min_len and question != answer:
                combined_rules = f"{rule1} + {rule2}"
                key = (question, combined_rules)
                if key not in seen:
                    seen.add(key)
                    results.append({
                        "rules": combined_rules,
                        "question": question,
                        "answer": answer,
                        "type": f"{kind1} + {kind2}",
                    })

    return results


def main():
    if len(sys.argv) < 2:
        print("使い方: uv run generator.py <答え> [--min-len N]")
        print("例: uv run generator.py かな --min-len 7")
        sys.exit(1)

    answer = sys.argv[1]
    min_len = 5
    if "--min-len" in sys.argv:
        idx = sys.argv.index("--min-len")
        min_len = int(sys.argv[idx + 1])

    dictionary = load_dict(DICT_PATH)

    if answer not in dictionary:
        print(f"⚠️  「{answer}」は辞書に存在しません")

    results = generate(answer, dictionary, min_len=min_len)

    if not results:
        print(f"「{answer}」に対する問題文候補が見つかりませんでした（最小{min_len}文字）")
        return

    print(f"\n「{answer}」の策問候補 ({len(results)}件、{min_len}文字以上)\n")
    print(f"{'種別':<16} {'ルール':<24} {'問題文':<16} {'答え'}")
    print("-" * 72)
    for r in results:
        print(f"{r['type']:<16} {r['rules']:<24} {r['question']:<16} {r['answer']}")


if __name__ == "__main__":
    main()
