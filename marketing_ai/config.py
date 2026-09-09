"""Configuration constants for the marketing AI multi-agent system."""

import os

# --- LLM モデル定義 ---
# メインLLM: 構成・クリエイティブ生成・リスク検証に使用
MAIN_MODEL = os.getenv("MARKETING_AI_MAIN_MODEL", "claude-3-5-sonnet-latest")
# サブLLM: リサーチ結果の要約・整理に使用（低コスト・高速）
SUB_MODEL = os.getenv("MARKETING_AI_SUB_MODEL", "claude-3-5-haiku-latest")

# --- グラフ制御 ---
# レビューが REJECT を返し続けた場合に無限ループしないための上限
DEFAULT_MAX_REVISIONS = int(os.getenv("MARKETING_AI_MAX_REVISIONS", "3"))

# --- Web検索 ---
DEFAULT_SEARCH_RESULTS = int(os.getenv("MARKETING_AI_SEARCH_RESULTS", "5"))
