// usage: node render_clip.mjs <url-base> <outdir>  → poster.jpg (1280x720) + frames/f%04d.png (960x540) along the path
import puppeteer from 'puppeteer-core';
import fs from 'fs';
const [base, out] = process.argv.slice(2);
fs.mkdirSync(`${out}/frames`, { recursive: true });
const b = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: 'new', args: ['--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist'] });
const p = await b.newPage();
p.on('pageerror', e => console.error('pageerror', e.message));
await p.setViewport({ width: 1280, height: 720 });
await p.goto(`${base}/index.html?shot=0`, { waitUntil: 'networkidle0' });
await p.waitForFunction('window.__ready === true', { timeout: 120000 });
await p.screenshot({ path: `${out}/poster.jpg`, type: 'jpeg', quality: 82 });
await p.setViewport({ width: 960, height: 540 });
const N = 150;
for (let i = 0; i < N; i++) {
  await p.evaluate((s, w) => window.__shot(s, 0, 0, w), i / (N - 1), i === 0 ? 45 : 4);
  await p.screenshot({ path: `${out}/frames/f${String(i).padStart(4, '0')}.png` });
}
await b.close(); console.log('frames', N);
