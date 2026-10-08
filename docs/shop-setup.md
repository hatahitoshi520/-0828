# 自動販売の仕組み（AI Team Starter 完全導入ガイド・500円）

```
LP「500円で購入する」
  → Supabase 関数 ai-team-shop?action=buy
      （初回だけ Stripe に商品・価格・決済リンクを自動作成し、以後は同じリンクを使う）
  → Stripe の決済ページ
  → 支払い完了で ai-team-starter-thanks.html?session_id=… に自動で移動
  → 関数 ai-team-shop?action=deliver が Stripe に「支払い済みか」を確認
  → 確認できた場合だけ、ガイド本文と zip を表示
```

- Supabase プロジェクト：`beeyqtqhlhglrxppqbvb`（レジのプロジェクトとは別）
- 売上は Stripe からあなたの口座に自動で振り込まれ、売れるたびに Stripe からメールが届く

## 最初の1回だけ必要な作業

1. **Stripe アカウントを作り、本人確認を済ませる**（https://dashboard.stripe.com/register）
   - 本人確認は法律上の義務のため、代行できません。
   - サイトURLを聞かれたら、LP のURLを入力します。
2. **制限付きキーを作る**：Stripe ダッシュボード →「開発者」→「API キー」→「制限付きのキーを作成」
   - Products・Prices・Payment Links：書き込み
   - Checkout Sessions：読み取り
   - それ以外：なし
3. **キーを Supabase に登録する**：Supabase ダッシュボード → プロジェクト `beeyqtqhlhglrxppqbvb` → Edge Functions → Secrets
   - 名前 `STRIPE_SECRET_KEY`、値に 2 のキー（`rk_live_…`）を貼る
   - キーはチャットや GitHub には貼らないこと
4. **`tokushoho.html` の【要記入】3か所を埋める**（氏名・責任者・メールアドレス）
5. **PR をマージする**（GitHub Pages で LP・納品ページ・特商法ページが公開される）

ここまで終われば、以降の販売・決済・納品・入金はすべて自動です。

## ガイド本文を更新する時

ガイド本文は有料コンテンツなので、公開リポジトリには入れていません。

```bash
node scripts/build-shop-content.mjs <ガイド本文.md>   # content.ts を生成（.gitignore 済み）
# その後 supabase/functions/ai-team-shop を再デプロイ
```

テンプレート（`templates/ai-team-starter/`）を変更した場合も、同じ手順で再デプロイすると zip に反映されます。
