#!/usr/bin/env node
// Golden fixture generator — executes the ORIGINAL, UNMODIFIED iqm.js
// (师门可执行 SoT) in a Node VM and captures structured chart state.
// Cross-language fixtures MUST come from the real counterpart output
// (platform lesson: feedback_cross_language_test_fixtures_must_be_real).
//
// Regenerate:
//   TZ=Asia/Shanghai node tests/fixtures/generate_golden.js \
//     > tests/fixtures/golden_charts.json
//
// TZ is load-bearing: iqm.js computes in local civil time; the engine's
// semantics are Chinese civil time (Asia/Shanghai). The generator refuses
// to run under any other TZ.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

if (process.env.TZ !== 'Asia/Shanghai') {
  console.error('ERROR: run with TZ=Asia/Shanghai');
  process.exit(1);
}

const SRC = fs.readFileSync(path.join(__dirname, 'vendor', 'iqm.js'), 'utf8');
const STEMS = '甲乙丙丁戊己庚辛壬癸';

function newEngine() {
  const values = { years: 2026, months: 7, days: 4, hours: 12, mins: 0, zxj: -1 };
  const sandbox = {
    Date, Math,
    document: {
      all: { item: (k) => ({ get value() { return values[k]; } }) },
      getElementById: () => null,
    },
    window: { alert: () => {} },
    alert: () => {},
  };
  vm.createContext(sandbox);
  vm.runInContext(SRC, sandbox);
  return { sandbox, values };
}

// Parse a decorated cell string into [{ch, colors: [..], italic: bool}, ...]
// Handles nested <FONT color=#XXXXXX> wrapping and <i> tags.
function parseDecorated(str) {
  const out = [];
  const colorStack = [];
  let italic = 0;
  let i = 0;
  const s = String(str == null ? '' : str);
  while (i < s.length) {
    if (s[i] === '<') {
      const close = s.indexOf('>', i);
      if (close === -1) break;
      const tag = s.slice(i, close + 1);
      const m = tag.match(/^<FONT color=#([0-9A-Fa-f]{6})>$/i);
      if (m) colorStack.push(m[1].toUpperCase());
      else if (/^<\/FONT>$/i.test(tag)) colorStack.pop();
      else if (/^<i>$/i.test(tag)) italic++;
      else if (/^<\/i>$/i.test(tag)) italic = Math.max(0, italic - 1);
      i = close + 1;
      continue;
    }
    const ch = s[i];
    out.push({ ch, colors: colorStack.slice(), italic: italic > 0 });
    i++;
  }
  return out;
}

function stemsOf(str) {
  return parseDecorated(str)
    .filter((t) => STEMS.includes(t.ch))
    .map((t) => t.ch);
}

// Map iqm.js decoration colors -> structural sihai flags per stem.
// Legend (iqm.js:635-638): 刑=#6F00D2 · 墓=#009100 · 迫=#FF0000 italic ·
// 刑墓=#EE00EE · 空=#000080. #EA0000 appears only on 壬@巽4 first-stem
// (pass-2 re-wrap of an already 刑墓-marked stem) — treated as 刑墓.
function colorsToFlags(colors) {
  const flags = new Set();
  for (const c of colors) {
    if (c === '6F00D2') flags.add('击刑');
    else if (c === '009100') flags.add('入墓');
    else if (c === 'EE00EE') { flags.add('击刑'); flags.add('入墓'); }
    else if (c === 'EA0000') { flags.add('击刑'); flags.add('入墓'); }
  }
  return [...flags].sort();
}

function decoratedStemFlags(str) {
  const out = [];
  for (const t of parseDecorated(str)) {
    if (!STEMS.includes(t.ch)) continue;
    out.push({ stem: t.ch, flags: colorsToFlags(t.colors) });
  }
  return out;
}

function runCase(input) {
  const { sandbox, values } = newEngine();
  values.years = input.y; values.months = input.m; values.days = input.d;
  values.hours = input.h; values.mins = input.min;
  values.zxj = input.zxj == null ? -1 : input.zxj;
  vm.runInContext(`paipan(${input.zxj == null ? 'false' : 'true'})`, sandbox);

  const g = sandbox;
  const header = String(g.s);
  const zhifuMatch = header.match(/值符:天(.)星落(\d)宫 值使:(.)门落(\d)宫/);
  if (!zhifuMatch) throw new Error('header parse failed: ' + header);

  const palaces = {};
  for (let i = 1; i <= 9; i++) {
    palaces[i] = {
      shen: i === 5 ? '' : String(g.sshenpan[i] || '').trim(),
      xing: i === 5 ? '' : String(g.sxinpan[i] || '').trim(),
      men: i === 5 ? '' : String(g.smenpan[i] || '').trim(),
      tian: i === 5 ? [] : stemsOf(g.stiangan[i]),
      di: stemsOf(g.sdigan[i]),
      an: i === 5 ? [] : stemsOf(g.sangan[i]),
      kong: String(g.kong[i] || '').startsWith('<'),
      // sihai flags decoded from DrawPaipan color decoration (原引擎语义)
      tian_flags: i === 5 ? [] : decoratedStemFlags(g.tiangan[i]),
      di_flags: decoratedStemFlags(g.digan[i]),
      men_po: String(g.menpan[i] || '').startsWith('<i>'),
    };
  }
  const maGong = [];
  for (let b = 0; b < 12; b++) {
    if (String(g.maw[b] || '').includes('马')) maGong.push(b);
  }

  return {
    input,
    dun: String(g.yy),
    ju: Number(g.ju),
    zhifu_star: zhifuMatch[1],
    zhifu_gong: Number(zhifuMatch[2]),
    zhishi_men: zhifuMatch[3],
    zhishi_gong: Number(zhifuMatch[4]),
    lunar: {
      year: Number(g.lY), month: Number(g.lM), day: Number(g.lD),
      is_leap: Boolean(g.lL),
    },
    pillars: {
      year: vm.runInContext('cyclical(cY)', sandbox),
      month: vm.runInContext('cyclical(cM)', sandbox),
      day: vm.runInContext('cyclical(cD)', sandbox),
      hour: vm.runInContext('cyclical(hCyl)', sandbox),
    },
    h_cyl: Number(g.hCyl),
    xun_shou: vm.runInContext('cyclical(xunshou)', sandbox),
    kong_zhi: [g.Zhi[g.xunkong1], g.Zhi[g.xunkong2]],
    ma_zhi: g.Zhi[g.maxing],
    ma_gong_branches: maGong,
    jiang: Number(g.jiang),
    dgg: Number(g.dgg),
    mgg: Number(g.mgg),
    palaces,
  };
}

// Probe without capture (for scanning): returns minimal info.
function probe(input) {
  try { return runCase(input); } catch (e) { return null; }
}

// Exact solar-term time via the original engine's sTerm.
function termTime(y, n) {
  const { sandbox } = newEngine();
  const d = vm.runInContext(`sTerm(${y}, ${n})`, sandbox);
  return new Date(d.getTime());
}

const cases = [];
function add(id, category, input, note) {
  const r = runCase(input);
  cases.push({ id, category, note: note || '', ...r });
}

// ---- 1. 阴阳遁常规局 (spread across seasons/years) ----
add('yang-01', 'normal', { y: 2026, m: 1, d: 15, h: 10, min: 30 });
add('yang-02', 'normal', { y: 2026, m: 3, d: 8, h: 14, min: 5 });
add('yang-03', 'normal', { y: 2025, m: 4, d: 21, h: 6, min: 45 });
add('yang-04', 'normal', { y: 2024, m: 2, d: 29, h: 20, min: 0 }, '闰年2月29');
add('yang-05', 'normal', { y: 1988, m: 5, d: 30, h: 9, min: 12 });
add('yin-01', 'normal', { y: 2026, m: 7, d: 4, h: 15, min: 20 });
add('yin-02', 'normal', { y: 2026, m: 9, d: 30, h: 11, min: 59 });
add('yin-03', 'normal', { y: 2025, m: 8, d: 7, h: 17, min: 33 });
add('yin-04', 'normal', { y: 2024, m: 11, d: 15, h: 13, min: 7 });
add('yin-05', 'normal', { y: 1999, m: 10, d: 1, h: 8, min: 0 });

// ---- 2. 节气边界 (minute precision; finedate 覆盖 1930-2030) ----
// 夏至/冬至 = 阴阳遁翻转; 立春/小寒 = 月柱/年柱边界。
for (const [y, n, label] of [
  [2026, 11, 'xiazhi'],   // 夏至: 阳→阴
  [2025, 23, 'dongzhi'],  // 冬至 2025 23:02 落子时区 → 与子时换日交互(全阳,保留为金例)
  [2026, 23, 'dongzhi26'], // 冬至 2026: 干净的阴→阳翻转
  [2026, 2, 'lichun'],    // 立春
  [2026, 0, 'xiaohan'],   // 小寒 (年初跨年节气)
]) {
  const t = termTime(y, n);
  for (const [off, tag] of [[-1, 'before'], [0, 'at'], [1, 'after']]) {
    const d = new Date(t.getTime() + off * 60000);
    add(`term-${label}-${tag}`, 'term-boundary', {
      y: d.getFullYear(), m: d.getMonth() + 1, d: d.getDate(),
      h: d.getHours(), min: d.getMinutes(),
    }, `${label} ${y} exact=${t.toISOString()} offset=${off}min`);
  }
}

// ---- 3. 子时换日 ----
add('zishi-2300', 'zishi', { y: 2026, m: 7, d: 3, h: 23, min: 0 }, '晚子时按次日');
add('zishi-2359', 'zishi', { y: 2026, m: 7, d: 3, h: 23, min: 59 });
add('zishi-0000', 'zishi', { y: 2026, m: 7, d: 4, h: 0, min: 0 }, '早子时');
add('zishi-0059', 'zishi', { y: 2026, m: 12, d: 31, h: 23, min: 30 }, '跨年晚子时');

// ---- 4. 闰月 ----
add('leap-2025a', 'leap-month', { y: 2025, m: 7, d: 30, h: 10, min: 0 }, '2025闰六月内');
add('leap-2025b', 'leap-month', { y: 2025, m: 8, d: 15, h: 16, min: 40 }, '2025闰六月内');
add('leap-2028', 'leap-month', { y: 2028, m: 6, d: 20, h: 12, min: 0 }, '2028闰五月内');

// ---- 5. 自选局 (zxj: 0=阴9 … 8=阴1, 9=阳1 … 17=阳9) ----
add('zxj-yin9', 'zixuan', { y: 2026, m: 7, d: 4, h: 15, min: 20, zxj: 0 });
add('zxj-yin1', 'zixuan', { y: 2026, m: 7, d: 4, h: 15, min: 20, zxj: 8 });
add('zxj-yang1', 'zixuan', { y: 2026, m: 7, d: 4, h: 15, min: 20, zxj: 9 });
add('zxj-yang9', 'zixuan', { y: 2026, m: 1, d: 15, h: 10, min: 30, zxj: 17 });

// ---- 6. 全伏吟 (甲时: 时干为甲 → 暗干特例重排; iqm.js:682) ----
// Scan 甲-hour datetimes; categorize single vs double rearrangement.
// Expected first-pass angan (replicated from iqm.js:683-695) — used ONLY to
// detect whether the second rearrangement (还是伏吟, iqm.js:697) fired.
function firstPassAngan(g) {
  const hCyl = Number(g.hCyl);
  const yy = String(g.yy);
  const liuyi = g.liuyi, Gan = g.Gan;
  let v;
  if (hCyl % 10 === 0) v = liuyi[Math.floor(hCyl / 10) + 1];
  else v = hCyl % 10;
  let j;
  for (j = 1; j < 10; j++) if (v === liuyi[j]) break;
  v = yy === '阳' ? j - 4 : j + 4;
  const an = {};
  for (let i = 1; i < 10; i++) {
    let gg = yy === '阳' ? v + i - 1 : v - i + 1;
    if (gg < 1) gg += 9;
    if (gg > 9) gg -= 9;
    an[i] = Gan[liuyi[gg]];
  }
  return an;
}

const fuyinQuota = {
  '阳-single': 2, '阴-single': 2, '阳-double': 2, '阴-double': 2,
};
const fuyinFound = { '阳-single': 0, '阴-single': 0, '阳-double': 0, '阴-double': 0 };
outer:
for (let dayOff = 0; dayOff < 720; dayOff += 1) {
  const base = new Date(2026, 0, 5);
  const d = new Date(base.getTime() + dayOff * 86400000);
  for (const h of [0, 15, 5, 19, 9, 11, 21, 7, 17, 13]) {
    const input = { y: d.getFullYear(), m: d.getMonth() + 1, d: d.getDate(), h, min: 10 };
    const { sandbox: sb, values } = newEngine();
    values.years = input.y; values.months = input.m; values.days = input.d;
    values.hours = input.h; values.mins = input.min; values.zxj = -1;
    vm.runInContext('paipan(false)', sb);
    if (Number(sb.hCyl) % 10 !== 0) continue; // not a 甲 hour
    // 全伏吟特例 fired iff 值符/值使 both at 旬首宫 → angan was rearranged
    const r = runCase(input);
    if (r.zhifu_gong !== r.dgg || r.mgg !== r.dgg) continue;
    const fp = firstPassAngan(sb);
    const secondFired = String(sb.sangan[1] || '').slice(0, 1) !== fp[1];
    const key = `${r.dun}-${secondFired ? 'double' : 'single'}`;
    if (fuyinFound[key] >= fuyinQuota[key]) continue;
    fuyinFound[key]++;
    add(`fuyin-${r.dun === '阳' ? 'yang' : 'yin'}-${secondFired ? 'double' : 'single'}-${fuyinFound[key]}`,
      'fuyin-special', input,
      `全伏吟${secondFired ? '二次重排(还是伏吟分支)' : '一次重排'} dun=${r.dun}`);
    if (Object.keys(fuyinQuota).every((k) => fuyinFound[k] >= fuyinQuota[k])) break outer;
  }
}
console.error('fuyin coverage:', JSON.stringify(fuyinFound));
if (fuyinFound['阳-single'] < 1 || fuyinFound['阴-single'] < 1) {
  throw new Error('fuyin scan missing single-rearrange coverage for a dun');
}

// ---- 7. 值符=禽 (旬首仪落中宫 dgg=5) ----
let qinFound = 0;
for (let dayOff = 0; dayOff < 500 && qinFound < 2; dayOff += 1) {
  const base = new Date(2026, 0, 2);
  const d = new Date(base.getTime() + dayOff * 86400000);
  for (const h of [3, 11, 21]) {
    const input = { y: d.getFullYear(), m: d.getMonth() + 1, d: d.getDate(), h, min: 25 };
    const r = probe(input);
    if (r && r.dgg === 5) {
      qinFound++;
      add(`qin-zhifu-${qinFound}`, 'qin-zhifu', input, '旬首仪落中宫 值符=禽');
      break;
    }
  }
}
if (qinFound < 1) throw new Error('qin-zhifu scan found no case');

process.stdout.write(JSON.stringify({
  generator: 'generate_golden.js',
  source: 'vendor/iqm.js (师门可执行 SoT)',
  tz: 'Asia/Shanghai',
  advance_minutes: 0,
  cases,
}, null, 1) + '\n');
