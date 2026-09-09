"""リサーチエージェント: Web検索結果を要約し、示唆を整理する。"""

from langchain_anthropic import ChatAnthropic

from marketing_ai.config import SUB_MODEL
from marketing_ai.prompts import research_prompt
from marketing_ai.state import AgentState
from marketing_ai.tools.search import web_search


def research_node(state: AgentState) -> dict:
    """ユーザーのタスクに基づきWeb検索を行い、サブLLMで要点を整理する。"""

    user_task = state["user_task"]

    raw_search_results = web_search(user_task)

    chain = research_prompt | ChatAnthropic(model=SUB_MODEL, temperature=0)
    response = chain.invoke(
        {
            "user_task": user_task,
            "raw_search_results": raw_search_results,
        }
    )

    return {
        "raw_search_results": raw_search_results,
        "research_data": response.content,
    }
