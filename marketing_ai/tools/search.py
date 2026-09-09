"""Tavily を用いた Web 検索ツール。"""

import os

from marketing_ai.config import DEFAULT_SEARCH_RESULTS


def web_search(query: str, max_results: int = DEFAULT_SEARCH_RESULTS) -> str:
    """Tavily API でWeb検索を行い、リサーチノードが読みやすいテキストに整形する。

    TAVILY_API_KEY が未設定の場合は例外を投げず、その旨を示す文字列を返す。
    これにより APIキー未設定の環境でもグラフ全体の配線を確認できる。
    """

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return (
            "[警告] TAVILY_API_KEY が設定されていないため、Web検索はスキップされました。"
            "リサーチエージェントは一般的な知識のみに基づいて回答します。"
        )

    try:
        from tavily import TavilyClient
    except ImportError as exc:  # pragma: no cover - 依存未インストール時の保護
        raise RuntimeError(
            "tavily-python がインストールされていません。`pip install tavily-python` "
            "を実行してください。"
        ) from exc

    client = TavilyClient(api_key=api_key)
    response = client.search(
        query=query,
        max_results=max_results,
        search_depth="advanced",
    )

    results = response.get("results", [])
    if not results:
        return f"「{query}」に関する検索結果は見つかりませんでした。"

    formatted = []
    for i, item in enumerate(results, start=1):
        title = item.get("title", "(タイトルなし)")
        url = item.get("url", "")
        content = item.get("content", "")
        formatted.append(f"{i}. {title}\n   URL: {url}\n   概要: {content}")

    return "\n\n".join(formatted)
