// AI Team Starter 自動販売：購入リンクへの誘導と、支払い確認つきの自動納品。
//   GET ?action=buy                      → Stripe の決済ページへ転送（商品と決済リンクは初回に自動作成）
//   GET ?action=deliver&session_id=cs_…  → 支払い済みなら納品データ（ガイド＋全ファイル）を返す
// 必要なシークレット：STRIPE_SECRET_KEY（制限付きキー可：Products / Prices / Payment Links の書き込み、Checkout Sessions の読み取り）
import { GUIDE_MARKDOWN } from "./content.ts";

const APP = "ai-team-starter";
const PRICE_JPY = 500;
const THANKS_URL = Deno.env.get("THANKS_URL") ??
  "https://hatahitoshi520.github.io/-0828/ai-team-starter-thanks.html";

// テンプレート本体は公開リポジトリにあるので、納品時に GitHub から取得する（有料なのはガイド本文のみ）。
const TEMPLATE_REPO = "hatahitoshi520/-0828";
const TEMPLATE_REF = Deno.env.get("TEMPLATE_REF") ?? "main";
const TEMPLATE_FILES = [
  "README.md", "CLAUDE.md.snippet", "settings.example.json", "setup-prompt.md", "check-env.sh",
  "agents/explorer.md", "agents/worker.md", "agents/researcher.md", "agents/router.md", "agents/auditor.md",
];
let filesCache: { at: number; files: Record<string, string> } | null = null;

async function loadTemplateFiles(): Promise<Record<string, string>> {
  if (filesCache && Date.now() - filesCache.at < 10 * 60_000) return filesCache.files;
  const entries = await Promise.all(TEMPLATE_FILES.map(async (f) => {
    const res = await fetch(
      `https://raw.githubusercontent.com/${TEMPLATE_REPO}/${TEMPLATE_REF}/templates/ai-team-starter/${f}`,
    );
    if (!res.ok) throw new Error(`template ${f}: ${res.status}`);
    return [f, await res.text()] as const;
  }));
  filesCache = { at: Date.now(), files: Object.fromEntries(entries) };
  return filesCache.files;
}

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...cors, "Content-Type": "application/json; charset=utf-8" },
  });
}

async function stripe(path: string, init: { method?: string; form?: Record<string, string> } = {}) {
  const key = Deno.env.get("STRIPE_SECRET_KEY");
  if (!key) throw new Error("STRIPE_SECRET_KEY is not set");
  const res = await fetch(`https://api.stripe.com/v1/${path}`, {
    method: init.method ?? "GET",
    headers: {
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: init.form ? new URLSearchParams(init.form) : undefined,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(`Stripe ${path}: ${data?.error?.message ?? res.status}`);
  return data;
}

// 商品・価格・決済リンクを一度だけ作り、リンクの URL を商品の metadata に保存して再利用する。
async function getPaymentLinkUrl(): Promise<string> {
  const found = await stripe(
    `products/search?query=${encodeURIComponent(`metadata['app']:'${APP}' AND active:'true'`)}`,
  );
  const existing = found.data?.[0];
  if (existing?.metadata?.payment_link_url) return existing.metadata.payment_link_url;

  const product = existing ?? await stripe("products", {
    method: "POST",
    form: {
      name: "AI Team Starter 完全導入ガイド",
      description: "Claude Code を4層のAIチームに組み替える導入ガイドと設定ファイル一式（デジタル納品）",
      "metadata[app]": APP,
    },
  });
  const price = await stripe("prices", {
    method: "POST",
    form: { product: product.id, currency: "jpy", unit_amount: String(PRICE_JPY) },
  });
  const link = await stripe("payment_links", {
    method: "POST",
    form: {
      "line_items[0][price]": price.id,
      "line_items[0][quantity]": "1",
      "after_completion[type]": "redirect",
      "after_completion[redirect][url]": `${THANKS_URL}?session_id={CHECKOUT_SESSION_ID}`,
      "metadata[app]": APP,
    },
  });
  await stripe(`products/${product.id}`, {
    method: "POST",
    form: { "metadata[payment_link_url]": link.url },
  });
  return link.url;
}

async function isPaidForThisProduct(sessionId: string): Promise<boolean> {
  if (!/^cs_(live|test)_[A-Za-z0-9]+$/.test(sessionId)) return false;
  const s = await stripe(
    `checkout/sessions/${sessionId}?expand[]=line_items.data.price.product`,
  );
  if (s.payment_status !== "paid") return false;
  return (s.line_items?.data ?? []).some(
    (li: { price?: { product?: { metadata?: Record<string, string> } } }) =>
      li.price?.product?.metadata?.app === APP,
  );
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: cors });
  const url = new URL(req.url);
  const action = url.searchParams.get("action");
  try {
    if (action === "buy") {
      return new Response(null, { status: 302, headers: { ...cors, Location: await getPaymentLinkUrl() } });
    }
    if (action === "deliver") {
      const ok = await isPaidForThisProduct(url.searchParams.get("session_id") ?? "");
      if (!ok) return json({ error: "支払いを確認できませんでした。" }, 402);
      return json({ guide: GUIDE_MARKDOWN, files: await loadTemplateFiles() });
    }
    return json({ error: "unknown action" }, 400);
  } catch (e) {
    console.error(e);
    return json({ error: "一時的なエラーです。少し待ってから再読み込みしてください。" }, 500);
  }
});
