"""LangGraph によるマーケティングAIのオーケストレーション定義。

フロー:

    research -> creative -> review --PASS--> END
                    ^                 |
                    |               REJECT
                    +-----------------+
                    (revision_count < max_revisions の間はループ)
"""

from langgraph.graph import END, StateGraph

from marketing_ai.agents.creative import creative_node
from marketing_ai.agents.research import research_node
from marketing_ai.agents.review import review_node
from marketing_ai.config import DEFAULT_MAX_REVISIONS
from marketing_ai.state import AgentState


def _route_after_review(state: AgentState) -> str:
    """レビュー結果に応じて次のノードを決める条件分岐。"""

    max_revisions = state.get("max_revisions", DEFAULT_MAX_REVISIONS)

    if state.get("review_status") == "PASS":
        return "end"

    if state.get("revision_count", 0) >= max_revisions:
        # 上限に達した場合は無限ループを避けて強制終了する
        return "end"

    return "revise"


def build_graph():
    """コンパイル済みの LangGraph アプリケーションを構築して返す。"""

    workflow = StateGraph(AgentState)

    workflow.add_node("research", research_node)
    workflow.add_node("creative", creative_node)
    workflow.add_node("review", review_node)

    workflow.set_entry_point("research")

    workflow.add_edge("research", "creative")
    workflow.add_edge("creative", "review")

    workflow.add_conditional_edges(
        "review",
        _route_after_review,
        {
            "revise": "creative",
            "end": END,
        },
    )

    return workflow.compile()
