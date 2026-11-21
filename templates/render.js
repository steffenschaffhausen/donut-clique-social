// Renders every post in posts.json to posts/<id>/post.png (1080x1350) and posts/<id>/caption.md.
// Usage: node templates/render.js [id ...]   (no id: all posts). Needs Playwright with Chromium.
// PNGs from a browser screenshot carry no EXIF data.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const data = JSON.parse(fs.readFileSync(path.join(root, 'posts.json'), 'utf8'));
const only = process.argv.slice(2);

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('file://' + path.join(__dirname, 'render.html'));
  await page.evaluate(([P, S, series]) => { window.P = P; window.S = S; window.SERIES = series; }, [
    JSON.parse(fs.readFileSync(path.join(__dirname, 'portraits.json'), 'utf8')),
    JSON.parse(fs.readFileSync(path.join(__dirname, 'scenes.json'), 'utf8')),
    data.series,
  ]);
  const total = data.posts.length;
  for (const [i, post] of data.posts.entries()) {
    if (only.length && !only.includes(post.id)) continue;
    await page.evaluate(([p, n, t]) => window.renderPost(p, n, t), [post, i + 1, total]);
    const dir = path.join(root, 'posts', post.id);
    fs.mkdirSync(dir, { recursive: true });
    await page.screenshot({ path: path.join(dir, 'post.png') });
    fs.writeFileSync(path.join(dir, 'caption.md'), post.caption + '\n\n' + data.hashtags + '\n');
    console.log('ok', post.id);
  }
  if (errors.length) console.error(errors);
  await browser.close();
})();
