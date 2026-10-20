// The hero photo is the page's largest element (Cloudflare's LCP report): it
// must be preloaded, fetched first and never lazy-loaded, with a smaller file
// on phones. Run: node test/hero.test.mjs
import { readFileSync, statSync } from 'node:fs';

const root = new URL('../', import.meta.url);
const html = readFileSync(new URL('index.html', root), 'utf8');
const head = html.slice(0, html.indexOf('</head>'));
let failed = 0;
const ok = (name, cond, detail) => {
  console.log((cond ? 'PASS  ' : 'FAIL  ') + name);
  if (!cond) { failed++; if (detail) console.log('        ' + detail); }
};
const size = f => statSync(new URL(f, root)).size;
// Width and height from the image header (AVIF ispe box, WebP VP8/VP8L/VP8X).
function dims(f) {
  const b = readFileSync(new URL(f, root));
  if (f.endsWith('.avif')) { const i = b.indexOf('ispe'); return [b.readUInt32BE(i + 8), b.readUInt32BE(i + 12)]; }
  const c = b.toString('ascii', 12, 16);
  if (c === 'VP8X') return [1 + b.readUIntLE(24, 3), 1 + b.readUIntLE(27, 3)];
  if (c === 'VP8 ') return [b.readUInt16LE(26) & 0x3fff, b.readUInt16LE(28) & 0x3fff];
  const v = b.readUInt32LE(21); return [(v & 0x3fff) + 1, ((v >> 14) & 0x3fff) + 1];
}

// ── 1. Preloaded in <head>, one per breakpoint, matching the <picture> ──
const preloads = [...head.matchAll(/<link rel="preload" as="image"[^>]*>/g)].map(m => m[0]);
ok('head: two image preloads', preloads.length === 2, preloads.join('\n'));
ok('head: phones preload the 640px AVIF', preloads.some(p => /href="lebron-hero-640\.avif"/.test(p) && /media="\(max-width: 640px\)"/.test(p) && /type="image\/avif"/.test(p) && /fetchpriority="high"/.test(p)));
ok('head: wider screens preload the 820px AVIF', preloads.some(p => /href="lebron-hero\.avif"/.test(p) && /media="\(min-width: 641px\)"/.test(p) && /type="image\/avif"/.test(p) && /fetchpriority="high"/.test(p)));
ok('head: preloads come before the stylesheets', head.indexOf('rel="preload"') < head.indexOf('rel="stylesheet"'));
ok('head: the phone breakpoint is the CSS one', /@media \(max-width: 640px\)[\s\S]*?\.heroimg \{/.test(html));

// ── 2. The <picture>: phone sources first, AVIF before WebP, JPG fallback ──
const pic = (html.match(/<picture>[\s\S]*?<\/picture>/) || [''])[0];
const sources = [...pic.matchAll(/<source ([^>]*)>/g)].map(m => m[1]);
ok('picture: four sources in order', JSON.stringify(sources.map(s => [(s.match(/media="([^"]*)"/) || [, ''])[1], s.match(/srcset="([^"]*)"/)[1]])) === JSON.stringify([
  ['(max-width: 640px)', 'lebron-hero-640.avif'], ['(max-width: 640px)', 'lebron-hero-640.webp'], ['', 'lebron-hero.avif'], ['', 'lebron-hero.webp']]), JSON.stringify(sources));
ok('picture: every source declares its type', sources.every(s => /type="image\/(avif|webp)"/.test(s)));
const img = (pic.match(/<img [^>]*>/) || [''])[0];
ok('img: same class and selector as before', /class="heroimg"/.test(img) && /<section class="screen on" id="sIntro">\s*<div class="hero">\s*<picture>/.test(html));
ok('img: JPG fallback and alt text kept', /src="lebron-hero\.jpg"/.test(img) && /alt="LeBron James"/.test(img));
ok('img: fixed width and height (820x1139)', /width="820"/.test(img) && /height="1139"/.test(img));
ok('img: fetchpriority high, eager, never lazy', /fetchpriority="high"/.test(img) && /loading="eager"/.test(img) && !/lazy/.test(pic));

// ── 3. The files: right sizes, and smaller than what browsers used before ──
for (const f of ['lebron-hero.jpg', 'lebron-hero.webp', 'lebron-hero.avif', 'lebron-hero-640.avif', 'lebron-hero-640.webp']) ok(`file: ${f} exists`, size(f) > 1000);
ok('file: 820px AVIF is 820x1139', JSON.stringify(dims('lebron-hero.avif')) === '[820,1139]', JSON.stringify(dims('lebron-hero.avif')));
ok('file: phone AVIF is 640x889', JSON.stringify(dims('lebron-hero-640.avif')) === '[640,889]', JSON.stringify(dims('lebron-hero-640.avif')));
ok('file: phone WebP is 640x889', JSON.stringify(dims('lebron-hero-640.webp')) === '[640,889]', JSON.stringify(dims('lebron-hero-640.webp')));
ok('file: 820px WebP still 820x1139', JSON.stringify(dims('lebron-hero.webp')) === '[820,1139]', JSON.stringify(dims('lebron-hero.webp')));
ok('file: every new file is smaller than the 820px WebP browsers used before', ['lebron-hero.avif', 'lebron-hero-640.avif', 'lebron-hero-640.webp'].every(f => size(f) < size('lebron-hero.webp')));

console.log(failed ? `\n${failed} test(s) FAILED` : '\nall tests passed');
process.exit(failed ? 1 : 0);
