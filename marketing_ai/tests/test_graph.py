"""LangGraph配線の単体テスト。

実際のAnthropic/Tavily APIは呼ばず、ChatAnthropic と web_search をモックして
グラフのルーティング（PASSでの終了、REJECTでのループと上限打ち切り）だけを検証する。
"""

from langchain_core.runnables import Runnable

import marketing_ai.agents.creative as creative_module
import marketing_ai.agents.research as research_module
import marketing_ai.agents.review as review_module
from marketing_ai.graph import build_graph
from marketing_ai.models import ReviewOutput


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeStructuredRunnable(Runnable):
    """`llm.with_structured_output(...)` が返すダミーの Runnable。"""

    def __init__(self, results):
        # 呼ばれるたびに1つずつ消費する結果のリスト（最後の要素は使い回す）
        self._results = list(results)

    def invoke(self, input, config=None, **kwargs):
        if len(self._results) > 1:
            return self._results.pop(0)
        return self._results[0]


class _FakeChatAnthropic(Runnable):
    """`ChatAnthropic(model=..., temperature=...)` の代わりに使うダミー実装。"""

    def __init__(self, content="fake content", structured_results=None, **kwargs):
        self._content = content
        self._structured_results = structured_results

    def invoke(self, input, config=None, **kwargs):
        return _FakeMessage(self._content)

    def with_structured_output(self, schema):
        return _FakeStructuredRunnable(self._structured_results)


def test_graph_ends_on_pass(monkeypatch):
    monkeypatch.setattr(research_module, "web_search", lambda query, **kw: "raw data")
    monkeypatch.setattr(
        research_module, "ChatAnthropic", lambda **kw: _FakeChatAnthropic("research summary")
    )
    monkeypatch.setattr(
        creative_module, "ChatAnthropic", lambda **kw: _FakeChatAnthropic("draft v1")
    )
    monkeypatch.setattr(
        review_module,
        "ChatAnthropic",
        lambda **kw: _FakeChatAnthropic(
            structured_results=[ReviewOutput(review_status="PASS", feedback="")]
        ),
    )

    graph = build_graph()
    result = graph.invoke(
        {"user_task": "テストタスク", "revision_count": 0, "max_revisions": 3}
    )

    assert result["review_status"] == "PASS"
    assert result["revision_count"] == 1
    assert result["draft_content"] == "draft v1"


def test_graph_stops_at_max_revisions_on_repeated_reject(monkeypatch):
    monkeypatch.setattr(research_module, "web_search", lambda query, **kw: "raw data")
    monkeypatch.setattr(
        research_module, "ChatAnthropic", lambda **kw: _FakeChatAnthropic("research summary")
    )
    monkeypatch.setattr(
        creative_module, "ChatAnthropic", lambda **kw: _FakeChatAnthropic("draft")
    )
    monkeypatch.setattr(
        review_module,
        "ChatAnthropic",
        lambda **kw: _FakeChatAnthropic(
            structured_results=[
                ReviewOutput(review_status="REJECT", feedback="もっと簡潔に")
            ]
        ),
    )

    graph = build_graph()
    result = graph.invoke(
        {"user_task": "テストタスク", "revision_count": 0, "max_revisions": 2}
    )

    assert result["review_status"] == "REJECT"
    assert result["revision_count"] == 2
