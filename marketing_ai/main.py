"""自律型マーケティングAIのCLIエントリーポイント。

使い方:
    python -m marketing_ai.main "30代女性向け時短スキンケア商品のLP用SNS投稿を作って"
"""

import argparse
import sys

from dotenv import load_dotenv

from marketing_ai.config import DEFAULT_MAX_REVISIONS
from marketing_ai.graph import build_graph


def run(user_task: str, max_revisions: int = DEFAULT_MAX_REVISIONS) -> dict:
    """グラフを構築し、初期ステートを与えて実行する。"""

    graph = build_graph()

    initial_state = {
        "user_task": user_task,
        "revision_count": 0,
        "max_revisions": max_revisions,
    }

    return graph.invoke(initial_state)


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="リサーチ→コンテンツ作成→リスク検証を自律的に行うマーケティングAI"
    )
    parser.add_argument("user_task", help="達成したいマーケティングタスクの説明")
    parser.add_argument(
        "--max-revisions",
        type=int,
        default=DEFAULT_MAX_REVISIONS,
        help="レビューREJECT時に再生成を繰り返す最大回数",
    )
    args = parser.parse_args()

    final_state = run(args.user_task, max_revisions=args.max_revisions)

    print("\n===== リサーチ結果 =====")
    print(final_state.get("research_data", ""))

    print("\n===== 最終コンテンツ =====")
    print(final_state.get("draft_content", ""))

    print("\n===== 審査結果 =====")
    print(f"status: {final_state.get('review_status')}")
    print(f"revision_count: {final_state.get('revision_count')}")
    if final_state.get("review_status") != "PASS":
        print(f"feedback: {final_state.get('feedback')}")
        print(
            "\n[注意] 最大修正回数に達したため REJECT のまま終了しました。"
            " 出力内容は人手でのレビューを推奨します。",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
