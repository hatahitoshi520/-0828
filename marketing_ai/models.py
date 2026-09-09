"""構造化出力用の Pydantic モデル。"""

from pydantic import BaseModel, Field


class ReviewOutput(BaseModel):
    """レビューエージェントの審査結果。"""

    review_status: str = Field(
        description="合格の場合は 'PASS'、修正が必要な場合は 'REJECT'"
    )
    feedback: str = Field(
        default="",
        description="REJECTの場合、具体的な修正指示。PASSの場合は空文字。",
    )
