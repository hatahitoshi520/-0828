"""LangGraph が各ノード間で受け渡す共有ステート定義。"""

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """マーケティングAIエージェント間で共有されるステート。

    total=False とすることで、各ノードは自分が更新するキーだけを
    返せば良い（LangGraph が既存ステートにマージする）。
    """

    # ユーザーが最初に与えるゴール・タスク
    user_task: str

    # リサーチノードが取得した検索の生データ（Tavily等）
    raw_search_results: str

    # リサーチノードが要約・整理した結果（Markdown）
    research_data: str

    # クリエイティブノードが生成したコンテンツ案
    draft_content: str

    # レビューノードの判定結果: "PASS" | "REJECT"
    review_status: str

    # レビューノードからの修正指示（REJECT時）
    feedback: str

    # クリエイティブ→レビューを何回繰り返したか
    revision_count: int

    # 何回REJECTされたら強制終了するか（無限ループ防止）
    max_revisions: int
