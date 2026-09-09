"""レビューエージェント: 誇大表現・炎上リスク・タスク充足度を審査する。"""

from langchain_anthropic import ChatAnthropic

from marketing_ai.config import MAIN_MODEL
from marketing_ai.models import ReviewOutput
from marketing_ai.prompts import review_prompt
from marketing_ai.state import AgentState


def review_node(state: AgentState) -> dict:
    """コンテンツ案を審査し、PASS/REJECTとフィードバックを返す。

    ChatAnthropic はツール呼び出しを利用した `with_structured_output` で
    確実にスキーマ通りのJSON（Pydanticモデル）を取得する。
    """

    llm = ChatAnthropic(model=MAIN_MODEL, temperature=0)
    chain = review_prompt | llm.with_structured_output(ReviewOutput)

    result: ReviewOutput = chain.invoke(
        {
            "user_task": state["user_task"],
            "draft_content": state["draft_content"],
        }
    )

    return {
        "review_status": result.review_status,
        "feedback": result.feedback,
    }
