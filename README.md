# 自律型マーケティングAI（マルチエージェント / LangGraph）

ユーザーが与えたゴールから「リサーチ」「コンテンツ作成」「リスク検証」を自律的に
繰り返すマーケティングAIです。エージェントのオーケストレーションには
[LangGraph](https://langchain-ai.github.io/langgraph/) を使用しています。

## アーキテクチャ

```
        ┌───────────┐     ┌───────────┐     ┌───────────┐
 START →│ research  │───▶│ creative  │───▶│  review   │
        └───────────┘     └───────────┘     └─────┬─────┘
                                 ▲                  │
                                 │   REJECT かつ     │
                                 │ revision_count <  │
                                 │  max_revisions    │
                                 └──────────────────┘
                                                     │ PASS もしくは
                                                     │ revision_count >= max_revisions
                                                     ▼
                                                    END
```

| エージェント | 役割 | 使用モデル |
| --- | --- | --- |
| リサーチ (`research_node`) | Tavilyで検索し、ターゲットの悩み・トレンド・差別化の切り口を整理 | `claude-3-5-haiku-latest`（サブLLM） |
| クリエイティブ (`creative_node`) | リサーチ結果（と直前のフィードバック）を元にフック・本文・CTAを含む文章を生成 | `claude-3-5-sonnet-latest`（メインLLM） |
| レビュー (`review_node`) | 誇大表現・炎上リスク・タスク充足度を審査し `PASS`/`REJECT` をJSONで返す | `claude-3-5-sonnet-latest`（メインLLM） |

レビューが `REJECT` の場合、`feedback` を添えて `creative` ノードに差し戻し
再生成します。`max_revisions`（デフォルト3回）に達すると無限ループを避けて
強制終了します。

## ディレクトリ構成

```
marketing_ai/
├── main.py            # CLIエントリーポイント
├── graph.py            # LangGraph の StateGraph 定義（配線・条件分岐）
├── state.py            # 共有ステート (AgentState) の型定義
├── prompts.py          # 各エージェントのプロンプトテンプレート
├── models.py            # レビュー結果の構造化出力用 Pydantic モデル
├── config.py            # モデル名・上限回数などの設定
├── agents/
│   ├── research.py     # リサーチエージェント
│   ├── creative.py     # クリエイティブエージェント
│   └── review.py       # レビューエージェント
├── tools/
│   └── search.py        # Tavily Web検索ラッパー
└── tests/
    └── test_graph.py    # LLM/検索をモックしたグラフ配線のテスト
```

## セットアップ

Python 3.11 以降が必要です。

```bash
pip install -r requirements.txt
cp .env.example .env
# .env を編集して ANTHROPIC_API_KEY / TAVILY_API_KEY を設定
```

## 実行

```bash
python -m marketing_ai.main "30代女性向け時短スキンケア商品のInstagram投稿文を作って"
```

修正ループの最大回数を変えたい場合:

```bash
python -m marketing_ai.main "..." --max-revisions 5
```

## テスト

実際のAPIキーがなくても、ChatAnthropic / Web検索をモックした配線テストを
実行できます。

```bash
pytest marketing_ai/tests -v
```

## 備考

- `TAVILY_API_KEY` が未設定の場合、`web_search` はエラーにせず警告文を返し、
  リサーチエージェントは一般知識のみで応答します（開発時の動作確認用）。
- レビューエージェントは `with_structured_output` を用いてツール呼び出し経由で
  確実にスキーマ通りのJSON（`ReviewOutput`）を取得しています。
