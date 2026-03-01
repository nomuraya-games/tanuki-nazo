"""
たぬき謎 策問ジェネレータ

目的:
    答えを入力すると、ルールを逆適用して問題文候補を自動生成する。
    問題文・答えともに辞書に存在する組み合わせのみ出力する。
    --min-len で問題文の最小文字数を指定可能（デフォルト7）。
    複数ルールの同時適用（2ルール以上）にも対応。

使い方:
    uv run generator.py <答え> [--min-len N]
    例: uv run generator.py かな
    例: uv run generator.py かな --min-len 7
"""

import sys
from itertools import combinations

DICT_PATH = "kana_words.txt"

# 削除系ルール: (ルール名, 削除する文字列)
DELETE_RULES = [
    ("たぬき", "た"),
    ("こけし", "こ"),
    ("けしごむ", "ごむ"),
    ("ちりとり", "ちり"),
    ("とりい", "い"),
    ("おとしあな", "あな"),
    ("ひきだし", "だし"),
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
    """置き換え系の逆適用: answerの「after」を全て「before」に戻した候補を返す"""
    if after not in answer:
        return []
    return [answer.replace(after, before)]


def verify(question: str, rule_name: str, expected_answer: str) -> bool:
    """問題文にルールを正方向適用して、期待する答えと一致するか検証"""
    for name, rule_char in DELETE_RULES:
        if name == rule_name:
            return question.replace(rule_char, "") == expected_answer
    for name, before, after in REPLACE_RULES:
        if name == rule_name:
            return question.replace(before, after) == expected_answer
    return False


def _get_rule_ops(rule_name: str) -> tuple[str, str, str] | None:
    """ルール名から (種別, from_str, to_str) を返す。削除系は to_str = ""。"""
    for name, rule_char in DELETE_RULES:
        if name == rule_name:
            return ("削除系", rule_char, "")
    for name, before, after in REPLACE_RULES:
        if name == rule_name:
            return ("置き換え系", before, after)
    return None


def verify_multi(question: str, rule_names: list[str], expected_answer: str) -> bool:
    """複数ルールを同時適用して期待する答えと一致するか検証。
    全ルールのfrom_strが重複しない場合のみ有効。
    """
    result = question
    for rule_name in rule_names:
        op = _get_rule_ops(rule_name)
        if op is None:
            return False
        _, from_str, to_str = op
        result = result.replace(from_str, to_str)
    return result == expected_answer


def _insert_all(word: str, insert: str) -> list[str]:
    """wordの全挿入位置にinsertを挿入した文字列のリストを返す"""
    return [word[:pos] + insert + word[pos:] for pos in range(len(word) + 1)]


def generate_multi_delete_candidates(answer: str, rule_chars: list[str]) -> list[str]:
    """削除系複数ルールの逆適用: 答えにrule_charsを全挿入位置の組み合わせで挿入。
    rule_chars = [ルール1の削除文字, ルール2の削除文字, ...]
    """
    candidates = [answer]
    for rc in rule_chars:
        next_candidates = []
        for base in candidates:
            next_candidates.extend(_insert_all(base, rc))
        candidates = next_candidates
    return candidates


def apply_multi_rules(answer: str) -> list[tuple[str, list[str], str]]:
    """複数ルール同時適用の逆適用。
    削除系2ルール以上、または削除系+置き換え系の組み合わせ。
    対象文字(from_str)が重複しないペアのみ対象。
    戻り値: (問題文候補, [ルール名リスト], 種別文字列) のリスト
    """
    results = []

    # 削除系ルールのみから2ルール以上の組み合わせ
    delete_rule_names = [name for name, _ in DELETE_RULES]
    for r in range(2, min(4, len(delete_rule_names) + 1)):  # 2〜3ルール
        for rule_combo in combinations(delete_rule_names, r):
            # 対象文字が重複しないか確認
            ops = [_get_rule_ops(n) for n in rule_combo]
            from_strs = [op[1] for op in ops]
            # 文字レベルの重複チェック: 各from_strに使われる文字が被らないか
            all_chars = "".join(from_strs)
            if len(all_chars) != len(set(all_chars)):
                continue

            rule_chars = from_strs
            for q in generate_multi_delete_candidates(answer, rule_chars):
                if q != answer:
                    results.append((q, list(rule_combo), "削除系×" + str(r)))

    # 置き換え系1 + 削除系1の組み合わせ
    for rep_name, before, after in REPLACE_RULES:
        for del_name, del_char in DELETE_RULES:
            # 対象文字が重複しないか確認
            all_chars = before + del_char
            if len(all_chars) != len(set(all_chars)):
                continue

            # 逆適用: answerの「after」を「before」に戻し、さらにdel_charを挿入
            if after not in answer:
                continue
            base = answer.replace(after, before)
            for q in _insert_all(base, del_char):
                if q != answer:
                    results.append((q, [rep_name, del_name], "置き換え系+削除系"))

    return results


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
    """答えからルールを逆適用して問題文候補を生成（1ルール・複数ルール同時適用）"""
    results = []
    seen = set()

    # 1ルール適用
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

    # 複数ルール同時適用
    for question, rule_list, kind in apply_multi_rules(answer):
        if question in dictionary and len(question) >= min_len and question != answer:
            rules_str = " + ".join(rule_list)
            if verify_multi(question, rule_list, answer):
                key = (question, rules_str)
                if key not in seen:
                    seen.add(key)
                    results.append({
                        "rules": rules_str,
                        "question": question,
                        "answer": answer,
                        "type": kind,
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
