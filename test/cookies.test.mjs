// Beat LeBron no longer sets cookies (Oct 2026). Old cookies (device id,
// name/handle, best score) are copied into localStorage when it lacks them
// and then expired, so players keep their id, name, handle and best.
// Run: node test/cookies.test.mjs (needs Playwright and Chromium; skips without)
import { readFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { createRequire } from 'node:module';

const root = new URL('../', import.meta.url);
const html = readFileSync(new URL('index.html', root), 'utf8');
let failed = 0;
const ok = (name, cond, detail) => {
  console.log((cond ? 'PASS  ' : 'FAIL  ') + name);
  if (!cond) { failed++; if (detail) console.log('        ' + detail); }
};

// ── 1. Source: no cookie is ever written with a value ──
const writes = [...html.matchAll(/document\.cookie\s*=\s*([^;]+);/g)].map(m => m[1]);
ok('source: the only cookie write expires one', writes.length === 1 && /'=;max-age=0/.test(html), writes.join(' | '));
ok('source: no ckSet left', !/ckSet\(/.test(html));

// ── 2. Browser: migration ──
let chromium;
try { chromium = createRequire(import.meta.url)('playwright').chromium; } catch (e) {}
if (!chromium) { console.log('SKIP  browser checks: needs Playwright and Chromium'); process.exit(failed ? 1 : 0); }

const types = { html: 'text/html', js: 'text/javascript', webp: 'image/webp', avif: 'image/avif', png: 'image/png', jpg: 'image/jpeg' };
const srv = createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname.replace(/^\/beat-lebron/, '')) || '/';
  if (p.endsWith('/')) p += 'index.html';
  try { const b = readFileSync(new URL('.' + p, root)); res.writeHead(200, { 'content-type': types[p.split('.').pop()] || 'application/octet-stream' }); res.end(b); }
  catch (e) { res.writeHead(404); res.end(); }
});
await new Promise(r => srv.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${srv.address().port}`;
const browser = await chromium.launch();

async function visit(cookies, ls) {
  const ctx = await browser.newContext();
  await ctx.route(u => !u.href.startsWith(base), r => r.abort());   // no network beyond the page
  if (cookies.length) await ctx.addCookies(cookies.map(([name, value]) => ({ name, value: encodeURIComponent(value), url: base + '/' })));
  const page = await ctx.newPage();
  if (ls) { await page.goto(base + '/robots-none'); await page.evaluate(o => { for (const k in o) localStorage.setItem(k, o[k]); }, ls); }
  await page.goto(base + '/beat-lebron/');
  await page.waitForTimeout(300);
  const out = await page.evaluate(() => ({
    ls: { id: localStorage.getItem('hm_beat_lebron_id'), name: localStorage.getItem('hm_beat_lebron_name'), best: localStorage.getItem('hm_beat_lebron_best') },
    intro: document.getElementById('introBest').textContent,
  }));
  out.cookies = (await ctx.cookies()).map(c => c.name);
  await ctx.close();
  return out;
}

const NAME = JSON.stringify({ name: 'Old Player', handle: '@old' });
let r = await visit([['hm_beat_lebron_id', 'abcdef0123456789abcdef01'], ['hm_beat_lebron_name', NAME], ['hm_beat_lebron_best', '1234']]);
ok('cookies only: id copied to localStorage', r.ls.id === 'abcdef0123456789abcdef01', JSON.stringify(r.ls));
ok('cookies only: name and handle copied', r.ls.name === NAME, r.ls.name);
ok('cookies only: best copied and shown', r.ls.best === '1234' && /1,234/.test(r.intro), r.ls.best + ' / ' + r.intro);
ok('cookies only: all three cookies expired', !r.cookies.some(c => c.startsWith('hm_beat_lebron')), r.cookies.join());

r = await visit([['hm_beat_lebron_id', 'cookieid0000000000000000'], ['hm_beat_lebron_best', '900'], ['other_cookie', 'x']],
  { hm_beat_lebron_id: 'lsid000000000000000000aa', hm_beat_lebron_best: '500' });
ok('both: localStorage id wins (as before)', r.ls.id === 'lsid000000000000000000aa', r.ls.id);
ok('both: the higher best wins', r.ls.best === '900', r.ls.best);
ok('both: our cookies expired, others left alone', !r.cookies.some(c => c.startsWith('hm_beat_lebron')) && r.cookies.includes('other_cookie'), r.cookies.join());

r = await visit([]);
ok('new player: no cookie set, nothing invented', !r.cookies.length && r.ls.best === null && /No score yet/.test(r.intro), JSON.stringify(r));

await browser.close(); srv.close();
console.log(failed ? `\n${failed} failed` : '\nall tests passed');
process.exit(failed ? 1 : 0);
