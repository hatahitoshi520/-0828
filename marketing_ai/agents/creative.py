"""クリエイティブエージェント: リサーチ結果からコンテンツ案を生成する。"""

from langchain_anthropic import ChatAnthropic

from marketing_ai.config import MAIN_MODEL
from marketing_ai.prompts import creative_prompt
from marketing_ai.state import AgentState


def creative_node(state: AgentState) -> dict:
    """リサーチ結果（と前回のレビューフィードバック）を元にコンテンツを生成する。"""

    new_revision_count = state.get("revision_count", 0) + 1

    chain = creative_prompt | ChatAnthropic(model=MAIN_MODEL, temperature=0.7)
    response = chain.invoke(
        {
            "user_task": state["user_task"],
            "research_data": state.get("research_data", ""),
            "feedback": state.get("feedback", "") or "（初回のため無し）",
        }
    )

    return {
        "draft_content": response.content,
        "revision_count": new_revision_count,
    }
