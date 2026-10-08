# セットアップ用プロンプト

Claude Code に下の枠内をそのまま貼り付けてください。
**diff を見て納得してから「go」と返す**のが、このテンプレートの使い方です。

---

```
このフォルダにある AI Team Starter テンプレートを使って、私の Claude Code を4層構成に組み替えたいです。
次の順番で進めてください。

1. ~/.claude/agents と .claude/agents を読み、既存のサブエージェントを一覧にしてください。
   それぞれが explorer（読む）・worker（編集・テスト）・researcher（調査）・router（小さな判断）・auditor（監査）のどれに当たるか、当たらないかを表にしてください。

2. 役割が足りないものだけ、テンプレートの agents/ から追加する案を作ってください。
   - 既存のエージェントで役割が同じものがあれば、新規追加ではなく既存を使う案にしてください。
   - すでに model が明示されているエージェントは変更せず、一覧にだけ載せてください。

3. ~/.claude/settings.json を読み、settings.example.json の内容（effortLevel: high、advisorModel: fable）を取り込む変更案を作ってください。
   既存の設定は消さずに残してください。

4. 次の設定・環境変数が、上の設定を無効化または上書きしていないか探して、報告だけしてください（変更はしない）。
   - CLAUDE_CODE_DISABLE_ADVISOR_TOOL
   - CLAUDE_CODE_EFFORT_LEVEL
   - DISABLE_TELEMETRY・DO_NOT_TRACK
   - feature flag の取得を止める設定
   探す場所：~/.claude/settings.json、.claude/settings.json、.claude/settings.local.json、シェルの設定ファイル（~/.bashrc、~/.zshrc など）、現在の環境変数

5. ~/.claude/CLAUDE.md に CLAUDE.md.snippet の内容を追記する案を作ってください。
   すでに似たルールがあれば、重複しないようにまとめる案にしてください。

6. 2・3・5 のすべての変更を、最初に diff 形式で見せてください。
   私が「go」と言うまで、どのファイルも編集しないでください。
```
