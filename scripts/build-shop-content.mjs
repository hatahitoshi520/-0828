// 有料納品データ（supabase/functions/ai-team-shop/content.ts）を生成する。
// 使い方: node scripts/build-shop-content.mjs <ガイド本文.md>
// ガイド本文は有料コンテンツのため、公開リポジトリには置かない。
// テンプレートの各ファイルは納品時に関数が GitHub から取得し、納品ページで表示するので、ここでは本文から外す。
import { readFileSync, writeFileSync } from "node:fs";

const guidePath = process.argv[2];
if (!guidePath) throw new Error("ガイド本文のパスを指定してください");
const guide = readFileSync(guidePath, "utf8")
  .replace(/^===== ここから有料 =====\n\n?/m, "")
  .replace(/^## 全ファイル\n[\s\S]*?(?=^## うまく動かない時)/m, "");

writeFileSync(
  "supabase/functions/ai-team-shop/content.ts",
  `// 自動生成（scripts/build-shop-content.mjs）。編集しないこと。\n` +
    `export const GUIDE_MARKDOWN = ${JSON.stringify(guide)};\n`,
);
console.log(`guide ${guide.length} chars`);
