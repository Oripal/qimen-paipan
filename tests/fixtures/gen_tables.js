#!/usr/bin/env node
// Extract constant tables from the ORIGINAL iqm.js (师门可执行 SoT) and emit
// qimen_engine/data_tables.py — guarantees verbatim fidelity
// of the ported engine's data layer (no hand-transcription errors possible).
//
// Regenerate (only needed if vendor/iqm.js changes):
//   node tests/fixtures/gen_tables.js > qimen_engine/data_tables.py
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const SRC = fs.readFileSync(path.join(__dirname, 'vendor', 'iqm.js'), 'utf8');
const sandbox = {
  Date, Math,
  document: { all: { item: () => ({ value: 0 }) }, getElementById: () => null },
  window: { alert: () => {} },
  alert: () => {},
};
vm.createContext(sandbox);
vm.runInContext(SRC, sandbox);

function pyIntList(name, arr, perLine) {
  const items = Array.from(arr, (v) => String(v));
  const lines = [];
  for (let i = 0; i < items.length; i += perLine) {
    lines.push('    ' + items.slice(i, i + perLine).join(', ') + ',');
  }
  return `${name}: Final[tuple[int, ...]] = (\n${lines.join('\n')}\n)`;
}

function pyStrList(name, arr) {
  const items = Array.from(arr, (v) => JSON.stringify(String(v)));
  return `${name}: Final[tuple[str, ...]] = (${items.join(', ')})`;
}

const out = [];
out.push('"""Constant tables extracted verbatim from the lineage engine iqm.js.');
out.push('');
out.push('GENERATED FILE — do not edit by hand. Source of truth:');
out.push('tests/fixtures/vendor/iqm.js (师门可执行 SoT, Android app engine).');
out.push('Regenerate: node tests/fixtures/gen_tables.js > <this file>');
out.push('"""');
out.push('# ruff: noqa: E501 — generated data tables, verbatim fidelity beats line length');
out.push('');
out.push('from typing import Final');
out.push('');
out.push('# 农历年信息位表 1900-2049 (lunarInfo)');
out.push(pyIntList('LUNAR_INFO', sandbox.lunarInfo, 10));
out.push('');
out.push('# 节气分钟精度表 1930-2030, 24 项/年, 编码 min|hour|day|mon|year (finedate)');
out.push(pyIntList('FINEDATE', sandbox.finedate, 8));
out.push('');
out.push('# 节气近似分钟偏移 (sTermInfo, finedate 覆盖范围外的回退公式用)');
out.push(pyIntList('S_TERM_INFO', sandbox.sTermInfo, 12));
out.push('');
out.push(pyIntList('SOLAR_MONTH', sandbox.solarMonth, 12));
out.push('');
out.push(pyStrList('GAN', sandbox.Gan));
out.push(pyStrList('ZHI', sandbox.Zhi));
out.push(pyStrList('SOLAR_TERM', sandbox.solarTerm));
out.push(pyStrList('MONTH_NAME', sandbox.monthName));
out.push(pyStrList('NSTR1', sandbox.nStr1));
out.push(pyStrList('NSTR2', sandbox.nStr2));
out.push('');
out.push('# 八门/九星/八神 (index 1..8 对应转盘序; index 0 为占位)');
out.push(pyStrList('MEN', sandbox.men));
out.push(pyStrList('XING', sandbox.xing));
out.push('# 八神两套布序: SHEN=阴遁用(反序), SHEN2=阳遁用(顺布) — 师门Q1 gated,');
out.push('# 切换点在 caster.QimenOptions.shen_yin_dun_reversed (photocopy of iqm.js:666-669)');
out.push(pyStrList('SHEN', sandbox.shen));
out.push(pyStrList('SHEN2', sandbox.shen2));
out.push('');
out.push('# 宫序转换: ZHUAN[转盘位]=宫号; FZHUAN[宫号]=转盘位(中5寄坤二=6)');
out.push(pyIntList('ZHUAN', sandbox.zhuan, 10));
out.push(pyIntList('FZHUAN', sandbox.fzhuan, 10));
out.push('');
out.push('# 六仪三奇布干序 (戊己庚辛壬癸丁丙乙 的 Gan 下标)');
out.push(pyIntList('LIUYI', sandbox.liuyi, 10));
out.push('');
out.push('# 驿马地支 (按时支 %4: 申子辰→寅 巳酉丑→亥 寅午戌→申 亥卯未→巳)');
out.push(pyIntList('YIMA', sandbox.YiMa, 4));
out.push('');
out.push('# 地支→宫号');
out.push(pyIntList('ZHI2GONG', sandbox.zhi2gong, 12));
out.push('');
out.push('# 月将 (按节气 index)');
out.push(pyIntList('YUEJIANG', sandbox.yuejiang, 12));
out.push('');
process.stdout.write(out.join('\n') + '\n');
