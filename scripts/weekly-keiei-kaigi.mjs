/* ============================================================
   経営会議・週次自動実行スクリプト（GitHub Actionsから実行）
   ------------------------------------------------------------
   毎週決まった曜日・時間に、人が何も操作しなくても：
     ① POSの売上・経費データを読む（読み取り専用）
     ② 事務AI・マーケティングAIが今週の分析報告を作る
     ③ 経営会議ページ（keiei-kaigi.html）と同じ場所に会議として保存する
        （オーナーが後からページを開けば、続きの会話ができる）
     ④ LINE公式アカウントから要約を自動送信する
   を行う。ブラウザ側（keiei-kaigi.html）のロジックと食い違わないよう、
   データの形・保存先・週の判定ルールは同じものを使っている。
   ============================================================ */

const SUPABASE_URL = "https://txfzylywpdrcpashiwae.supabase.co";
const SUPABASE_ANON_KEY = "sb_publishable_YqEkc-SyynhhH3GttVqq6Q_Uf9PeuVr";
const POS_DATA_ROW_ID = "kissa-suzu-pos-store";
const MEETING_ROW_ID = "kissa-suzu-keiei-kaigi";
const KEIEI_PAGE_URL = "https://hatahitoshi520.github.io/-0828/keiei-kaigi.html";

const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY || "";
const LINE_CHANNEL_ACCESS_TOKEN = process.env.LINE_CHANNEL_ACCESS_TOKEN || "";

async function sbFetchRow(id) {
  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/app_state?id=eq.${encodeURIComponent(id)}&select=data,updated_at`,
    { headers: { apikey: SUPABASE_ANON_KEY, Authorization: `Bearer ${SUPABASE_ANON_KEY}` } }
  );
  if (!res.ok) throw new Error(`supabase fetch failed: ${res.status}`);
  const rows = await res.json();
  return rows && rows[0] ? rows[0] : null;
}
async function sbUpsertRow(id, dataObj) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/app_state?on_conflict=id`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_ANON_KEY,
      Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
      "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates,return=minimal",
    },
    body: JSON.stringify({ id, data: dataObj, updated_at: new Date().toISOString() }),
  });
  if (!res.ok) throw new Error(`supabase upsert failed: ${res.status}`);
}

async function callAnthropicMessages(body) {
  if (!ANTHROPIC_API_KEY) {
    const err = new Error("NO_API_KEY");
    err.code = "NO_API_KEY";
    throw err;
  }
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Anthropic API error ${res.status}: ${text.slice(0, 300)}`);
  }
  return res.json();
}
function extractText(data) {
  return (data.content || []).map((b) => (b.type === "text" ? b.text : "")).filter(Boolean).join("\n").trim();
}

const PERSONAS = {
  jimu: {
    name: "事務AI",
    icon: "💼",
    role: "あなたは喫茶すず〜の事務担当のAI社員です。経費・コスト・業務効率化・キャッシュフローの視点から発言します。",
  },
  marketing: {
    name: "マーケティングAI",
    icon: "📈",
    role: "あなたは喫茶すず〜のマーケティング担当のAI社員です。集客・SNS・販促・客単価アップなど、売上を伸ばす施策の視点から発言します。",
  },
};

function mondayStartOf(d) {
  const date = new Date(d);
  const day = date.getDay();
  const diff = (day === 0 ? -6 : 1) - day;
  date.setDate(date.getDate() + diff);
  date.setHours(0, 0, 0, 0);
  return date;
}
function addDays(d, n) {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
}
function ymdLabel(d) {
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

// ブラウザ側 (keiei-kaigi.html) の buildDataSummary と同じロジック。
function buildDataSummary(posData) {
  if (!posData) return "（売上データを取得できませんでした。最新の数字が無い前提で話してください）";
  const orders = posData.orders || [];
  const expenses = posData.expenses || [];
  const now = new Date();
  const thisMonday = mondayStartOf(now);
  const lastMonday = addDays(thisMonday, -7);
  const nextMonday = addDays(thisMonday, 7);
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);

  const thisWeekOrders = orders.filter((o) => o.time >= thisMonday.getTime() && o.time < nextMonday.getTime());
  const lastWeekOrders = orders.filter((o) => o.time >= lastMonday.getTime() && o.time < thisMonday.getTime());
  const monthOrders = orders.filter((o) => o.time >= monthStart.getTime());

  const sum = (arr) => arr.reduce((s, o) => s + (o.total || 0), 0);
  const thisWeekTotal = sum(thisWeekOrders);
  const lastWeekTotal = sum(lastWeekOrders);
  const monthTotal = sum(monthOrders);

  const itemCount = {};
  thisWeekOrders.forEach((o) => {
    (o.lines || []).forEach((l) => {
      itemCount[l.name] = (itemCount[l.name] || 0) + (l.qty || 0);
    });
  });
  const topItems =
    Object.entries(itemCount).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([n, q]) => `${n}(${q}点)`).join("、") ||
    "（今週はまだ注文データなし）";

  const monthKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const monthExpenses = expenses.filter((e) => (e.date || "").startsWith(monthKey));
  const expByCat = {};
  monthExpenses.forEach((e) => {
    expByCat[e.cat] = (expByCat[e.cat] || 0) + (Number(e.amount) || 0);
  });
  const expLines =
    Object.entries(expByCat).map(([c, v]) => `${c} ¥${v.toLocaleString()}`).join("、") || "（今月の経費データなし）";
  const expTotal = Object.values(expByCat).reduce((s, v) => s + v, 0);

  return [
    `【今週(${ymdLabel(thisMonday)}〜) の売上】¥${thisWeekTotal.toLocaleString()}（${thisWeekOrders.length}件）`,
    `【先週の売上】¥${lastWeekTotal.toLocaleString()}（${lastWeekOrders.length}件）`,
    `【今月(${now.getMonth() + 1}月)の売上合計】¥${monthTotal.toLocaleString()}`,
    `【今週よく出たメニュー】${topItems}`,
    `【今月の経費内訳】${expLines}（合計 ¥${expTotal.toLocaleString()}）`,
  ].join("\n");
}

async function askPersonaOpeningReport(personaKey, dataSummary) {
  const persona = PERSONAS[personaKey];
  const system = `${persona.role}

${dataSummary}

これは週に一度の経営会議の冒頭です。オーナーはまだ何も発言していません。オーナーの発言を待たず、あなた（${persona.name}）から能動的に「今週の分析報告」を行ってください。実際のデータに基づいた具体的な気づき・気になる点・提案を含め、3〜5文程度で簡潔に述べてください。前置きや名乗りは不要で、報告の本文だけを書いてください。`;
  const data = await callAnthropicMessages({
    model: "claude-sonnet-5",
    max_tokens: 350,
    system,
    messages: [{ role: "user", content: "今週の分析報告をお願いします。" }],
  });
  return extractText(data);
}

// ブラウザ側と同じ「7日経過judge」。ブラウザ側が先に今週分を開始済みなら、
// 重複して2通目を作らないようにする（どちらが先に動いても1回だけになる）。
function isWeeklyMeetingDue(meetings) {
  const active = meetings.find((m) => !m.endedAt);
  if (active) return false;
  if (meetings.length === 0) return true;
  const last = meetings.reduce((a, b) => (new Date(a.startedAt) > new Date(b.startedAt) ? a : b));
  const daysSince = (Date.now() - new Date(last.startedAt).getTime()) / 86400000;
  return daysSince >= 7;
}

function truncate(text, max) {
  if (!text) return "";
  return text.length > max ? text.slice(0, max) + "…" : text;
}

async function sendLineBroadcast(text) {
  if (!LINE_CHANNEL_ACCESS_TOKEN) {
    console.warn("LINE_CHANNEL_ACCESS_TOKEN が未設定のため、LINE送信をスキップしました。");
    return;
  }
  const res = await fetch("https://api.line.me/v2/bot/message/broadcast", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${LINE_CHANNEL_ACCESS_TOKEN}`,
    },
    body: JSON.stringify({ messages: [{ type: "text", text }] }),
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`LINE broadcast failed: ${res.status} ${body.slice(0, 300)}`);
  }
}

async function main() {
  console.log("=== 経営会議 週次自動実行 開始 ===", new Date().toISOString());

  const [posRow, meetingRow] = await Promise.all([sbFetchRow(POS_DATA_ROW_ID), sbFetchRow(MEETING_ROW_ID)]);
  const posData = posRow ? posRow.data : null;
  const meetings = meetingRow && meetingRow.data && meetingRow.data.meetings ? meetingRow.data.meetings : [];

  if (!isWeeklyMeetingDue(meetings)) {
    console.log("今週分の会議はすでに開始済み（または進行中）のため、今回はスキップします。");
    return;
  }

  const dataSummary = buildDataSummary(posData);
  console.log("--- 参考データ ---\n" + dataSummary);

  const messages = [];
  for (const personaKey of ["jimu", "marketing"]) {
    console.log(`${PERSONAS[personaKey].name} の分析報告を生成中...`);
    const text = await askPersonaOpeningReport(personaKey, dataSummary);
    messages.push({ speaker: personaKey, text: text || "（分析を生成できませんでした）", time: new Date().toISOString() });
  }

  const meeting = {
    id: "m" + Date.now().toString(36),
    startedAt: new Date().toISOString(),
    endedAt: null,
    messages,
    summary: "",
    auto: true,
    source: "scheduled",
  };
  await sbUpsertRow(MEETING_ROW_ID, { meetings: [...meetings, meeting] });
  console.log("会議データを保存しました。");

  const lineText = [
    "【喫茶すず〜 経営会議】週次自動報告",
    "",
    `💼事務AI\n${truncate(messages[0].text, 300)}`,
    "",
    `📈マーケティングAI\n${truncate(messages[1].text, 300)}`,
    "",
    `続きの会話・詳細はこちら\n${KEIEI_PAGE_URL}`,
  ].join("\n");

  await sendLineBroadcast(lineText);
  console.log("LINEへ送信しました。");
  console.log("=== 経営会議 週次自動実行 完了 ===");
}

main().catch((e) => {
  console.error("週次自動実行でエラーが発生しました:", e.message || e);
  process.exitCode = 1;
});
