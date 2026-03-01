"""
たぬき謎 レビューCLI

目的:
    candidates.json の pending 候補を1件ずつ表示し、
    承認(a) / 却下(r) / 保留(s) / 終了(q) で仕分けする。

使い方:
    uv run review.py [--type 置き換え系|削除系]
"""

import json
import sys
from pathlib import Path

CANDIDATES_PATH = "candidates.json"


def main():
    filter_type = None
    args = sys.argv[1:]
    if "--type" in args:
        filter_type = args[args.index("--type") + 1]

    path = Path(CANDIDATES_PATH)
    candidates = json.loads(path.read_text(encoding="utf-8"))

    targets = [
        (i, c) for i, c in enumerate(candidates)
        if c["status"] == "pending"
        and (filter_type is None or c["type"] == filter_type)
    ]

    if not targets:
        print("レビュー対象なし（全て処理済み）")
        return

    approved = rejected = skipped = 0
    print(f"レビュー対象: {len(targets)}件")
    print("操作: [a]承認 [r]却下 [s]保留 [q]終了\n")

    for i, (idx, c) in enumerate(targets):
        print(f"[{i+1}/{len(targets)}] {c['type']}")
        print(f"  問題: 「{c['question']}」に「{c['rule']}」を適用すると？")
        print(f"  答え: 「{c['answer']}」")
        print()

        while True:
            key = input("  > ").strip().lower()
            if key in ("a", "r", "s", "q"):
                break
            print("  a/r/s/q で入力してください")

        if key == "q":
            break
        elif key == "a":
            candidates[idx]["status"] = "approved"
            approved += 1
        elif key == "r":
            candidates[idx]["status"] = "rejected"
            rejected += 1
        elif key == "s":
            skipped += 1

        print()

    path.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    approved_total = sum(1 for c in candidates if c["status"] == "approved")
    print(f"\n--- 結果 ---")
    print(f"  今回: 承認 {approved} / 却下 {rejected} / 保留 {skipped}")
    print(f"  累計承認数: {approved_total}")
    print(f"\n{CANDIDATES_PATH} を更新しました")


if __name__ == "__main__":
    main()
