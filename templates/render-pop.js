// Renders the posts in posts.json with templates/pop.html.
//   carousel/single -> posts/<id>/slide-N.png (1080x1350)
//   reel            -> posts/<id>/reel.mp4 (1080x1920, 30 fps, silent audio track) and posts/<id>/cover.png
// Usage: node templates/render-pop.js [id ...] [--sheet]   (no id: all posts). Needs Playwright (Chromium) and ffmpeg.
// Browser screenshots carry no EXIF data.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const root = path.resolve(__dirname, '..');
const data = JSON.parse(fs.readFileSync(path.join(root, 'posts.json'), 'utf8'));
const args = process.argv.slice(2);
const only = args.filter((a) => !a.startsWith('--'));
const FPS = 30;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('file://' + path.join(__dirname, 'pop.html'));
  await page.evaluate(([P, S]) => { window.P = P; window.S = S; }, [
    JSON.parse(fs.readFileSync(path.join(__dirname, 'portraits.json'), 'utf8')),
    JSON.parse(fs.readFileSync(path.join(__dirname, 'scenes.json'), 'utf8')),
  ]);
  const el = await page.$('#root');
  for (const post of data.posts) {
    if (only.length && !only.includes(post.id)) continue;
    const dir = path.join(root, 'posts', post.id);
    fs.rmSync(dir, { recursive: true, force: true });
    fs.mkdirSync(dir, { recursive: true });
    if (post.format === 'reel') {
      const frames = path.join(dir, 'frames');
      fs.mkdirSync(frames);
      await page.evaluate((shots) => window.loadReel(shots), post.shots);
      const ms = await page.evaluate(() => window.reelDuration());
      const n = Math.round((ms / 1000) * FPS);
      for (let f = 0; f < n; f++) {
        await page.evaluate((t) => window.reelFrame(t), (f * 1000) / FPS);
        await el.screenshot({ path: path.join(frames, String(f).padStart(4, '0') + '.jpg'), type: 'jpeg', quality: 92 });
      }
      await page.evaluate((t) => window.reelFrame(t), post.cover || ms - 500);
      await el.screenshot({ path: path.join(dir, 'cover.png') });
      execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(FPS), '-i', path.join(frames, '%04d.jpg'),
        '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100', '-shortest',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-c:a', 'aac', '-b:a', '128k',
        '-movflags', '+faststart', path.join(dir, 'reel.mp4')]);
      fs.rmSync(frames, { recursive: true, force: true });
      console.log('reel', post.id, (ms / 1000).toFixed(1) + ' s');
    } else {
      await page.setViewportSize({ width: 1080, height: 1350 });
      for (const [i, s] of post.slides.entries()) {
        await page.evaluate(([sl, k, t]) => window.renderSlide(sl, k, t), [s, i + 1, post.slides.length]);
        await el.screenshot({ path: path.join(dir, 'slide-' + (i + 1) + '.png') });
      }
      await page.setViewportSize({ width: 1080, height: 1920 });
      console.log('slides', post.id, post.slides.length);
    }
    fs.writeFileSync(path.join(dir, 'caption.md'), post.caption + '\n\n' + (post.tags ? post.tags + ' ' : '') + data.hashtags + '\n');
  }
  if (errors.length) console.error('page errors:', errors);
  await browser.close();
})();
