// Render splat views with the local viewer in headless Chrome (WebGL via Metal).
// usage: node tools/render_eval.mjs <ply> <outdir> <shots.json>
// shots.json: [{"name": "eval_f0010", "pose": 10, "off": [0,0,0], "yaw": 0}, ...]
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';

const [ply, outdir, shotsFile, bg = '', spark = ''] = process.argv.slice(2);
const shots = JSON.parse(fs.readFileSync(shotsFile, 'utf8'));
fs.mkdirSync(outdir, { recursive: true });

const browser = await puppeteer.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: 'new',
  args: ['--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader=false'],
  defaultViewport: { width: 1920, height: 1080, deviceScaleFactor: 1 },
  protocolTimeout: 600000,
});
const page = await browser.newPage();
page.on('pageerror', e => console.error('pageerror', e.message));
const t0 = Date.now();
await page.goto(`http://127.0.0.1:8765/?ply=${encodeURIComponent(ply)}&pose=0${bg ? '&bg=' + bg : ''}${spark ? '&spark=' + encodeURIComponent(spark) : ''}`, { waitUntil: 'load', timeout: 120000 });
await page.waitForFunction('window.__ready === true', { timeout: 300000, polling: 500 });
console.log(`loaded ${ply} in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
for (const s of shots) {
  await page.evaluate(s => window.__shot(s.pose, s.off || [0, 0, 0], s.yaw || 0), s);
  await page.screenshot({ path: `${outdir}/${s.name}.png` });
}
console.log(`rendered ${shots.length} shots in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
await browser.close();
