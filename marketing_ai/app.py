"""自律型マーケティングAIの Streamlit UI。

実行:
    streamlit run marketing_ai/app.py
"""

import os

import streamlit as st
from dotenv import load_dotenv

from marketing_ai.config import DEFAULT_MAX_REVISIONS
from marketing_ai.graph import build_graph

load_dotenv()

st.set_page_config(page_title="自律型マーケティングAI", page_icon="🚀", layout="wide")

st.title("🚀 自律型マーケティングAI")
st.caption(
    "リサーチ → コンテンツ作成 → リスク検証 を自律的に繰り返すマルチエージェントAI"
    "（LangGraph / Claude）"
)

# --- サイドバー: 設定 ---
with st.sidebar:
    st.header("設定")

    anthropic_key_input = st.text_input(
        "ANTHROPIC_API_KEY",
        value=os.getenv("ANTHROPIC_API_KEY", ""),
        type="password",
        help="メイン/サブLLM(Claude)の呼び出しに使用します。",
    )
    tavily_key_input = st.text_input(
        "TAVILY_API_KEY",
        value=os.getenv("TAVILY_API_KEY", ""),
        type="password",
        help="未入力の場合、Web検索はスキップされ一般知識のみで動作します。",
    )
    max_revisions = st.slider(
        "最大修正回数",
        min_value=1,
        max_value=10,
        value=DEFAULT_MAX_REVISIONS,
        help="レビューがREJECTを返し続けた場合に強制終了するまでの回数。",
    )

    st.divider()
    st.caption("APIキーはこのセッション内でのみ環境変数として保持され、保存されません。")

if anthropic_key_input:
    os.environ["ANTHROPIC_API_KEY"] = anthropic_key_input
if tavily_key_input:
    os.environ["TAVILY_API_KEY"] = tavily_key_input

# --- メイン: タスク入力 ---
user_task = st.text_area(
    "マーケティングタスクを入力してください",
    placeholder="例）30代女性向け時短スキンケア商品のInstagram投稿文を作って",
    height=100,
)

run_clicked = st.button("実行する", type="primary", disabled=not user_task.strip())

if "history" not in st.session_state:
    st.session_state.history = []


def _run_agent(task: str, max_rev: int) -> dict:
    """グラフを実行しながら進捗をUIに逐次反映し、最終ステートを返す。"""

    graph = build_graph()
    initial_state = {"user_task": task, "revision_count": 0, "max_revisions": max_rev}

    status = st.status("エージェントを実行中...", expanded=True)
    revisions: list[dict] = []
    final_state: dict = {}

    for update in graph.stream(initial_state, stream_mode="updates"):
        for node_name, node_output in update.items():
            final_state.update(node_output)

            if node_name == "research":
                status.write("🔍 リサーチ完了")
                with status.expander("リサーチ結果を見る", expanded=False):
                    st.markdown(node_output.get("research_data", ""))

            elif node_name == "creative":
                rc = node_output.get("revision_count")
                status.write(f"✍️ クリエイティブ生成中（第{rc}稿）")
                revisions.append(
                    {"revision": rc, "draft": node_output.get("draft_content", "")}
                )

            elif node_name == "review":
                verdict = node_output.get("review_status")
                icon = "✅" if verdict == "PASS" else "⚠️"
                status.write(f"{icon} レビュー結果: {verdict}")
                if revisions:
                    revisions[-1]["review_status"] = verdict
                    revisions[-1]["feedback"] = node_output.get("feedback", "")

    if final_state.get("review_status") == "PASS":
        status.update(label="完了（PASS）", state="complete")
    else:
        status.update(label="完了（最大修正回数に到達）", state="complete")

    return {"user_task": task, "revisions": revisions, "final_state": final_state}


if run_clicked:
    if not os.getenv("ANTHROPIC_API_KEY"):
        st.error(
            "ANTHROPIC_API_KEY が設定されていません。サイドバーで入力するか "
            ".env に設定してください。"
        )
        st.stop()

    try:
        result = _run_agent(user_task, max_revisions)
    except Exception as exc:  # noqa: BLE001 - UIでそのままエラー内容を見せる
        st.error("エージェント実行中にエラーが発生しました。")
        st.exception(exc)
        st.stop()

    st.session_state.history.insert(0, result)

# --- 結果表示 ---
if st.session_state.history:
    latest = st.session_state.history[0]
    final_state = latest["final_state"]

    st.subheader("最終結果")
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("#### 最終コンテンツ")
        st.markdown(final_state.get("draft_content", "（コンテンツなし）"))

    with col2:
        status_value = final_state.get("review_status", "-")
        st.metric("審査結果", status_value)
        st.metric("修正回数", final_state.get("revision_count", 0))
        if status_value != "PASS":
            st.warning(
                "最大修正回数に達したため REJECT のまま終了しました。"
                "人手でのレビューを推奨します。"
            )
            if final_state.get("feedback"):
                st.write("**最終フィードバック:**")
                st.write(final_state["feedback"])

    if latest["revisions"]:
        st.markdown("#### 修正履歴")
        for rev in latest["revisions"]:
            label = f"第{rev['revision']}稿 - {rev.get('review_status', '審査中')}"
            with st.expander(label):
                st.markdown(rev["draft"])
                if rev.get("feedback"):
                    st.info(f"フィードバック: {rev['feedback']}")

    if final_state.get("research_data"):
        with st.expander("リサーチ結果（全文）"):
            st.markdown(final_state["research_data"])

    if len(st.session_state.history) > 1:
        st.divider()
        st.subheader("過去の実行履歴")
        for i, item in enumerate(st.session_state.history[1:], start=1):
            title = item["user_task"][:60]
            with st.expander(f"{i}. {title}"):
                st.write(item["final_state"].get("draft_content", ""))
else:
    st.info("タスクを入力して「実行する」を押すと、エージェントが動き始めます。")
