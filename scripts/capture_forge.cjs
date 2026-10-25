// Capture the forge on art3m1s.me for the Shipped journal's prints (local only; never in CI).
//
// The forge's objects ride a ring that turns, so this takes a run of screenshots of the forge
// hold with no overlays, one every 1.5 s. Pick one frame per object where it faces the camera,
// set its "capture" file and "box" in scripts/data/journal/prints.json, then run
//   python scripts/generate_prints.py cut --cap <out dir>
//   python scripts/generate_prints.py
//   python scripts/render_hacklog.py
// Needs Node and playwright-core (PLAYWRIGHT_CORE=<path to its folder>, else the global npm
// install). It only reads the public site. Check the GPU line it prints: a software renderer
// draws a different scene.
//
//   node scripts/capture_forge.cjs <out dir> [shots=22] [gap ms=1500]

const path = require("path");
const fs = require("fs");
const corePath = process.env.PLAYWRIGHT_CORE ||
  path.join(process.env.APPDATA || "", "npm", "node_modules", "playwright-core");
const { chromium } = require(corePath);

const [outDir, shots = "22", gap = "1500"] = process.argv.slice(2);
if (!outDir) {
  console.error("usage: node scripts/capture_forge.cjs <out dir> [shots] [gap ms]");
  process.exit(2);
}
const URL = "https://art3m1s.me/?frame=352&ui=0&tier=high";   // stop 03, the forge, no overlays
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({
    headless: true, args: ["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"],
  });
  const ctx = await browser.newContext({ viewport: { width: 2560, height: 1600 }, deviceScaleFactor: 1.5 });
  const page = await ctx.newPage();
  await page.goto(URL, { waitUntil: "domcontentloaded" });
  try { await page.waitForSelector("body[data-sect-ready]", { timeout: 150000 }); } catch (e) { console.log("no ready flag"); }
  await sleep(7000);
  const gpu = await page.evaluate(() => {
    const c = document.createElement("canvas").getContext("webgl2");
    const d = c && c.getExtension("WEBGL_debug_renderer_info");
    return d ? c.getParameter(d.UNMASKED_RENDERER_WEBGL) : "unknown";
  });
  console.log("GPU:", gpu);
  for (let i = 0; i < +shots; i++) {
    const file = path.join(outDir, `loop_f352_${i}.png`);
    try { await page.screenshot({ path: file, timeout: 90000 }); console.log(file); } catch (e) { console.log("missed", i); }
    await sleep(+gap);
  }
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
