"""各エージェント用のプロンプトテンプレート定義。"""

from langchain_core.prompts import ChatPromptTemplate

# 1. リサーチエージェント用プロンプト
research_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "あなたは優秀なデータアナリストAIです。ユーザーのタスクを達成するために、"
            "ターゲットのインサイト、最新トレンド、アピールすべき差別化ポイントを"
            "整理して出力してください。",
        ),
        (
            "user",
            "【タスク】\n{user_task}\n\n"
            "【検索結果・生データ】\n{raw_search_results}\n\n"
            "これらの情報を統合し、クリエイターがコンテンツを作りやすいように"
            "「ターゲットの悩み」「トレンド」「差別化の切り口」をマークダウンで"
            "まとめてください。",
        ),
    ]
)

# 2. クリエイティブエージェント用プロンプト
creative_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "あなたはCVRを最大化するプロのWebコピーライターAIです。"
            "リサーチ結果を元に、魅力的なコンテンツを作成してください。",
        ),
        (
            "user",
            "【タスク】\n{user_task}\n\n"
            "【リサーチ結果】\n{research_data}\n\n"
            "【前回のフィードバック(修正時)】\n{feedback}\n\n"
            "【指示】\n最初の1行で目を引くフック、共感を呼ぶ本文、行動を促す"
            "CTA（Call to Action）を含む構成で作成してください。",
        ),
    ]
)

# 3. レビューエージェント用プロンプト（JSON構造化出力）
review_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "あなたは厳格なコンプライアンス兼校正エージェントです。"
            "コンテンツに誇大表現や炎上リスクがないか、タスクの意図を満たしているかを"
            "審査します。合否は review_status に 'PASS' または 'REJECT' として、"
            "REJECTの場合は feedback に具体的な修正指示を日本語で出力してください。",
        ),
        (
            "user",
            "【タスク要件】\n{user_task}\n\n【審査対象コンテンツ】\n{draft_content}",
        ),
    ]
)
