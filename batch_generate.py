"""
たぬき謎 一括策問ジェネレータ

目的:
    辞書内の全単語にルールを逆適用し、成立する問題文候補を
    candidates.json に保存する。レビュー→承認→投稿のフロー起点。

使い方:
    uv run batch_generate.py [--min-len N] [--max-answer-len N]
"""

import json
import sys
from pathlib import Path
from generator import load_dict, apply_single_rule

DICT_PATH = "kana_words.txt"
OUTPUT_PATH = "candidates.json"


def main():
    min_len = 5
    max_answer_len = 6

    args = sys.argv[1:]
    if "--min-len" in args:
        min_len = int(args[args.index("--min-len") + 1])
    if "--max-answer-len" in args:
        max_answer_len = int(args[args.index("--max-answer-len") + 1])

    dictionary = load_dict(DICT_PATH)
    target_answers = [w for w in dictionary if 3 <= len(w) <= max_answer_len]

    print(f"対象答え候補: {len(target_answers):,}件")
    print(f"問題文最小文字数: {min_len}")

    seen = set()
    candidates = []

    for answer in target_answers:
        for question, rule, kind in apply_single_rule(answer):
            if question in dictionary and len(question) >= min_len and question != answer:
                key = (question, rule, answer)
                if key not in seen:
                    seen.add(key)
                    candidates.append({
                        "question": question,
                        "rule": rule,
                        "answer": answer,
                        "type": kind,
                        "status": "pending",  # pending / approved / rejected
                    })

    # 置き換え系を先頭に、次に問題文の長い順
    candidates.sort(key=lambda x: (0 if x["type"] == "置き換え系" else 1, -len(x["question"])))

    Path(OUTPUT_PATH).write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    replace_count = sum(1 for c in candidates if c["type"] == "置き換え系")
    delete_count = sum(1 for c in candidates if c["type"] == "削除系")

    print(f"\n生成完了: {len(candidates):,}件")
    print(f"  置き換え系: {replace_count:,}件")
    print(f"  削除系:     {delete_count:,}件")
    print(f"\n{OUTPUT_PATH} に保存しました")


if __name__ == "__main__":
    main()
