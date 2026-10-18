// 用 KaTeX（VS Code 顯示公式用的引擎）檢查每一條公式都能解析。
//   npm install --no-save --prefix tools/ci katex@0.16.11
//   node tools/ci/check_math.js math.json
const katex = require("katex");
const items = JSON.parse(require("fs").readFileSync(process.argv[2], "utf8").replace(/^﻿/, ""));
let bad = 0;
for (const it of items) {
  try {
    katex.renderToString(it.tex, { displayMode: it.display, throwOnError: true, strict: "ignore" });
  } catch (e) {
    bad++;
    console.log(`✗ ${it.where}: ${it.tex.trim().slice(0, 80)}\n    ${e.message.split("\n")[0]}`);
  }
}
console.log(`${items.length} 條公式，${bad} 條 KaTeX 無法解析`);
process.exit(bad ? 1 : 0);
