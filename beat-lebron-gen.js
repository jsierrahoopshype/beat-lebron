// beat-lebron-gen.js — the Beat LeBron question generator, shared VERBATIM by the game page
// (index.html loads it with a <script> tag) and the leaderboard Worker (imports it to replay a
// game from its seed and verify the picks). Any change here must ship to both, and GEN_VERSION
// must be bumped so a client/server mismatch is detected instead of failing verification.
//
// Every question: A (biggest value) + B beats LeBron narrowly; the four fillers all sit below
// (LeBron - A), which guarantees no other pair among the six can reach LeBron's mark.
(function (root) {
  'use strict';
  const GEN_VERSION = 1;
  const DEFAULTS = {
    minAllStar: 2,      // only players with this many All-Star nods enter the pool
    fameExp: 4,         // steeper = more Jordan/Kobe/Curry, fewer one-time All-Stars
    upMargin: 0.10,     // winning duo may beat LeBron by at most this share of his mark (min +1)
    closeBand: 0.15,    // fillers are preferred within this share of LeBron's mark below the cut
    recentPlayers: 12,  // avoid reusing a player within this many recent picks
    recentMetrics: 6,   // avoid reusing a metric within this many questions
    metricMinA: 4       // metrics with fewer viable "big" players get weighted down
  };

  function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  function hashSeed(str) { let h = 2166136261; for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }

  // Returns a generator bound to one data file and one seed. Calling gen.generate() repeatedly
  // yields the exact same sequence of questions for the same (DATA.generated, seed, GEN_VERSION).
  function create(DATA, seed, opts) {
    const CFG = Object.assign({}, DEFAULTS, opts || {});
    const METRICS = DATA.metrics, LB = DATA.lebron;
    const asgIdx = METRICS.findIndex(m => m.k === 'asg');
    const POOL = DATA.players.filter(p => p.v[asgIdx] >= CFG.minAllStar);
    const metricWeight = METRICS.map((m, mi) => {
      const L = LB.v[mi];
      if (L <= 0) return 0;
      const bigs = POOL.filter(p => p.v[mi] < L && p.v[mi] * 2 > L).length;
      return bigs === 0 ? 0 : Math.min(1, bigs / CFG.metricMinA);
    });
    const rng = mulberry32(hashSeed(String(seed) + '|' + DATA.generated));
    const rnd = () => rng();
    function pickWeighted(arr, wfn) {
      let tot = 0; const w = arr.map(x => { const v = Math.max(0, wfn(x)); tot += v; return v; });
      let r = rnd() * tot;
      for (let i = 0; i < arr.length; i++) { r -= w[i]; if (r <= 0) return arr[i]; }
      return arr[arr.length - 1];
    }
    const fame = p => Math.pow(p.f + 2, CFG.fameExp);
    function shuffle(a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
    const recentP = [], recentM = [];
    function markRecent(list, item, cap) { list.push(item); while (list.length > cap) list.shift(); }
    function generate() {
      for (let attempt = 0; attempt < 60; attempt++) {
        const mi = pickWeighted(METRICS.map((m, i) => i), i => recentM.includes(i) ? 0 : metricWeight[i]);
        const q = buildFor(mi, attempt < 40);
        if (q) { markRecent(recentM, mi, CFG.recentMetrics); q.players.forEach(p => markRecent(recentP, p.n, CFG.recentPlayers)); return q; }
      }
      recentP.length = 0; recentM.length = 0;
      return generate();
    }
    function buildFor(mi, respectRecent) {
      const L = LB.v[mi];
      if (L <= 0 || metricWeight[mi] === 0) return null;
      const up = Math.max(1, Math.ceil(L * CFG.upMargin));
      const fresh = p => !respectRecent || !recentP.includes(p.n);
      const elig = POOL.filter(p => p.v[mi] < L);
      const As = elig.filter(p => p.v[mi] * 2 > L && fresh(p));
      if (!As.length) return null;
      for (let t = 0; t < 30; t++) {
        const A = pickWeighted(As, fame);
        const a = A.v[mi];
        const Bs = elig.filter(p => p !== A && fresh(p) && p.v[mi] > L - a && p.v[mi] <= a && a + p.v[mi] <= L + up);
        if (!Bs.length) continue;
        const B = pickWeighted(Bs, fame);
        const cut = L - a;
        const lo = Math.max(0, cut - Math.max(1, Math.ceil(L * CFG.closeBand)));
        let Fs = elig.filter(p => p !== A && p !== B && fresh(p) && p.v[mi] < cut && p.v[mi] >= lo);
        if (Fs.length < 4) Fs = elig.filter(p => p !== A && p !== B && fresh(p) && p.v[mi] < cut);
        if (Fs.length < 4) continue;
        const fill = [];
        const takeFrom = (arr) => { const p = pickWeighted(arr, x => fame(x) * (0.3 + (x.v[mi] + 1) / (cut + 1))); fill.push(p); Fs = Fs.filter(x => x !== p); return p; };
        let nearPool = Fs.filter(p => p.v[mi] >= Math.ceil((cut - 1) / 2));
        for (let i = 0; i < 2 && nearPool.length; i++) { const p = takeFrom(nearPool); nearPool = nearPool.filter(x => x !== p); }
        while (fill.length < 4 && Fs.length) takeFrom(Fs);
        if (fill.length < 4) continue;
        const players = shuffle([A, B].concat(fill));
        let beats = 0, tie = 0;
        for (let i = 0; i < 6; i++) for (let j = i + 1; j < 6; j++) {
          const s = players[i].v[mi] + players[j].v[mi];
          if (s > L) beats++; else if (s === L) tie++;
        }
        if (beats !== 1 || tie) continue;
        return { mi, metric: METRICS[mi], L, players, win: [A, B], sum: a + B.v[mi] };
      }
      return null;
    }
    return { generate, POOL, METRICS, LB, CFG, seed: String(seed) };
  }

  root.BeatLebronGen = { create, hashSeed, mulberry32, GEN_VERSION, DEFAULTS };
})(typeof globalThis !== 'undefined' ? globalThis : this);
