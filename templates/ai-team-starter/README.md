# AI Team Starter（無料テンプレート）

Claude Code を「1人のAI」から「役割分担したAIチーム」に組み替えるためのテンプレートです。

```
司令塔   メインセッション   Opus / effort high     計画・分解・統合・最終判断
  ↓
実働     explorer          Sonnet / medium        コードを読む
         worker            Sonnet / medium        編集・テスト
         researcher        Sonnet / medium        ドキュメント調査
  ↓
監査     advisor           Fable                  計画前・エラー反復時・完了直前の3回だけ
         （auditor）        Fable / high           advisor が使えない環境での代わり
  ↓
仕分け   router            Haiku / low            見るファイル・再試行か停止か、など小さな判断
```

## 中身

| ファイル | 内容 |
|---|---|
| `agents/explorer.md` | 読む担当（編集はしない） |
| `agents/worker.md` | 編集・テスト担当。同じエラーが2回続いたら止まって報告 |
| `agents/researcher.md` | ドキュメント調査担当。出典必須、推測で埋めない |
| `agents/router.md` | 小さな判断を速く返す仕分け担当 |
| `agents/auditor.md` | advisor が使えない時の監査役 |
| `CLAUDE.md.snippet` | 役割分担と「advisor に相談する3つのタイミング」のルール |
| `settings.example.json` | `effortLevel: high` と `advisorModel: fable` の設定例 |
| `setup-prompt.md` | Claude Code に貼るだけのセットアップ用プロンプト（diff 提示 → 「go」で適用） |
| `check-env.sh` | 4層構成を邪魔する設定がないか確認するスクリプト（何も変更しない） |

## 使い方（おすすめ：Claude Code に任せる）

1. このフォルダを、作業しているプロジェクトの中か手元の好きな場所に置く
2. 確認だけのスクリプトを実行する
   ```bash
   bash check-env.sh
   ```
3. Claude Code を起動し、`setup-prompt.md` の枠内を貼り付ける
4. 出てきた diff を読み、納得したら `go` と返す
5. `/agents` で5つのエージェントが見えること、`/advisor` で監査役が設定されていることを確認する

## 使い方（手動）

```bash
# 全プロジェクト共通で使う場合
mkdir -p ~/.claude/agents
cp -n agents/*.md ~/.claude/agents/     # -n: 同名ファイルがあれば上書きしない

# このプロジェクトだけで使う場合
mkdir -p .claude/agents
cp -n agents/*.md .claude/agents/
```

- `settings.example.json` の2行を `~/.claude/settings.json` に手で追加します（ファイルごと上書きしないでください）。
- `CLAUDE.md.snippet` の中身を `~/.claude/CLAUDE.md` の末尾に追記します。

## 注意

- advisor（`/advisor`・`advisorModel`）はプランやメインのモデルによって使えない場合があります。その時は `auditor` エージェントが同じ役割を担います。
- Fable はモデルとして利用できるプランが限られます。使えない場合は `auditor.md` の `model:` を `opus` に変えてください。
- Claude Code v2.1.289 で設定名を確認しています。仕様は更新されることがあるので、うまく動かない時は公式ドキュメントを確認してください。
- 元の投稿などで紹介されている「Jev」は、公式の機能として確認できませんでした。このテンプレートでは、同じ役割を Haiku の `router` エージェントで作っています。

---

AI Team Studio（仮称）／ Anthropic社とは関係のない、独立したサービスです。
Claude、Claude Code は Anthropic, PBC の商標です。
自分の環境に合わせた構築や、チームへの導入を手伝ってほしい場合は、無料診断（30分）をご利用ください。
