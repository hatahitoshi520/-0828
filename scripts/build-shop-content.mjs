// 有料納品データ（supabase/functions/ai-team-shop/content.ts）を生成する。
// 使い方: node scripts/build-shop-content.mjs <ガイド本文.md>
// ガイド本文は有料コンテンツのため、公開リポジトリには置かない。
import { readFileSync, writeFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const guidePath = process.argv[2];
if (!guidePath) throw new Error("ガイド本文のパスを指定してください");
const guide = readFileSync(guidePath, "utf8").replace(/^===== ここから有料 =====\n\n?/m, "");

const root = "templates/ai-team-starter";
const files = {};
const walk = (dir) => {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else files[relative(root, p)] = readFileSync(p, "utf8");
  }
};
walk(root);

writeFileSync(
  "supabase/functions/ai-team-shop/content.ts",
  `// 自動生成（scripts/build-shop-content.mjs）。編集しないこと。\n` +
    `export const GUIDE_MARKDOWN = ${JSON.stringify(guide)};\n` +
    `export const FILES: Record<string, string> = ${JSON.stringify(files, null, 2)};\n`,
);
console.log(`guide ${guide.length} chars, ${Object.keys(files).length} files`);
