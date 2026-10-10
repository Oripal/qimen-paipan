#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["skyfield==1.55"]
# ///
"""节气分钟精度表扩展段生成器(2031-2050)— 天文计算,非 iqm.js 原表。

师门原表 finedate(iqm.js)只覆盖 1930-2030,范围外原引擎回退近似公式、时分归零。
本脚本用 JPL DE440s 星历补出 2031-2050 段,写成与原表同编码、同取整口径的
FINEDATE_EXT,供 qimen_engine/calendar.py 的 s_term 拼接使用;原表一字不动。

算法:太阳地心视黄经(当日真黄道,含光行差+章动)过 15° 整数倍的 TT 时刻。
民用时:北京时间 = UTC+8,UTC 按现行闰秒数外推(TAI−UTC=37s,即 TT−UTC=69.184s,
假定此后不再增减闰秒)——结果只依赖星历,不依赖 ΔT 预报。
取整:**截断到分**。这是原表口径(对账:1972-2009 段原表 = 本算法截断分),
不是紫金山年历的四舍五入口径。

对账闸(生成前必过,否则拒绝输出):
- 编码往返:encode(decode(x)) == x 对原表 2424 项全等;
- 1972-2009(闰秒制 UTC 时代,且原表编制时 ΔT 已知):本算法截断分与原表
  全部相差 ≤1 分钟,且逐项相等率 ≥97%。

Regenerate(星历文件 de440s.bsp 约 32MB,首次自动下载到 --ephemeris-dir):
  uv run tests/fixtures/gen_jieqi_ext.py > qimen_engine/jieqi_ext.py
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from skyfield import almanac
from skyfield.api import Loader
from skyfield.framelib import ecliptic_frame

EXT_FIRST_YEAR = 2031
EXT_LAST_YEAR = 2050
RECONCILE_YEARS = range(1972, 2010)
RECONCILE_MIN_EXACT = 0.97
EPHEMERIS = "de440s.bsp"
EPHEMERIS_SHA256 = "c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2"
# 小寒 = 太阳视黄经 285° = 第 19 个 15° 段的起点;规范序 n(0=小寒)= (k-19) % 24
XIAO_HAN_SEGMENT = 19
TT_MINUS_UTC_S = 69.184  # 32.184(TT−TAI)+ 37(TAI−UTC,2017-01-01 起)
BOUNDARY_SENSITIVE_S = 5.0

_DATA_TABLES = Path(__file__).resolve().parents[2] / "qimen_engine" / "data_tables.py"
_J2000_TT = datetime(2000, 1, 1, 12)


def encode(dt: datetime) -> int:
    """iqm.js finedate 编码:min|hour|day|mon|year(基年 1930)。"""
    v = (dt.year - 1930) * 12 + (dt.month - 1)
    v = v * 32 + (dt.day - 1)
    v = v * 24 + dt.hour
    return v * 60 + dt.minute


def decode(data: int) -> datetime:
    minute = data % 60
    data //= 60
    hour = data % 24
    data //= 24
    day = data % 32 + 1
    data //= 32
    return datetime(data // 12 + 1930, data % 12 + 1, day, hour, minute)


def _lineage_finedate() -> tuple[int, ...]:
    spec = importlib.util.spec_from_file_location("qimen_data_tables", _DATA_TABLES)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return tuple(mod.FINEDATE)


class TermSolver:
    def __init__(self, ephemeris_dir: Path) -> None:
        ephemeris_dir.mkdir(parents=True, exist_ok=True)
        load = Loader(str(ephemeris_dir), verbose=False)
        self.ts = load.timescale()
        eph = load(EPHEMERIS)
        digest = hashlib.sha256((ephemeris_dir / EPHEMERIS).read_bytes()).hexdigest()
        if digest != EPHEMERIS_SHA256:
            raise SystemExit(f"{EPHEMERIS} 校验和不符: {digest}")
        self.earth, self.sun = eph["earth"], eph["sun"]

    def year_terms(self, year: int) -> list[tuple[datetime, float]]:
        """某公历年 24 节气 → [(北京时间 naive 秒级, TT−UTC 秒)],按 0=小寒 排序。"""

        def segment(t):  # type: ignore[no-untyped-def]
            _, lon, _ = (
                self.earth.at(t).observe(self.sun).apparent().frame_latlon(ecliptic_frame)
            )
            return np.floor(lon.degrees / 15.0).astype(int) % 24

        segment.step_days = 5
        t0, t1 = self.ts.utc(year, 1, 1), self.ts.utc(year + 1, 1, 1)
        times, segs = almanac.find_discrete(t0, t1, segment, epsilon=0.01 / 86400)
        rows: dict[int, tuple[datetime, float]] = {}
        for t, k in zip(times, segs, strict=True):
            cst = (t.utc_datetime() + timedelta(hours=8)).replace(tzinfo=None)
            tt = _J2000_TT + timedelta(days=float(t.tt) - 2451545.0)
            tt_minus_utc = (tt - (cst - timedelta(hours=8))).total_seconds()
            rows[(int(k) - XIAO_HAN_SEGMENT) % 24] = (cst, tt_minus_utc)
        if sorted(rows) != list(range(24)):
            raise SystemExit(f"{year} 年节气不足 24 项: {sorted(rows)}")
        return [rows[n] for n in range(24)]


def _truncate(dt: datetime) -> datetime:
    return dt.replace(second=0, microsecond=0)


def reconcile(solver: TermSolver, lineage: tuple[int, ...]) -> str:
    if len(lineage) != 101 * 24:
        raise SystemExit(f"原表项数异常: {len(lineage)}")
    if any(encode(decode(x)) != x for x in lineage):
        raise SystemExit("编码往返失败:encode/decode 与原表编码不一致")
    exact = total = 0
    for year in RECONCILE_YEARS:
        for n, (moment, _) in enumerate(solver.year_terms(year)):
            tab = decode(lineage[(year - 1930) * 24 + n])
            diff_min = abs((tab - _truncate(moment)).total_seconds()) / 60
            if diff_min > 1:
                raise SystemExit(f"对账失败 {year} 节气{n}: 原表 {tab} vs 计算 {moment}")
            exact += diff_min == 0
            total += 1
    if exact / total < RECONCILE_MIN_EXACT:
        raise SystemExit(f"对账相等率过低: {exact}/{total}")
    return f"{exact}/{total}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--ephemeris-dir", type=Path, default=Path.home() / ".cache" / "skyfield",
    )
    args = parser.parse_args()

    solver = TermSolver(args.ephemeris_dir)
    lineage = _lineage_finedate()
    reconciled = reconcile(solver, lineage)

    values: list[int] = []
    sensitive = 0
    for year in range(EXT_FIRST_YEAR, EXT_LAST_YEAR + 1):
        for moment, tt_minus_utc in solver.year_terms(year):
            if abs(tt_minus_utc - TT_MINUS_UTC_S) > 1e-3:
                raise SystemExit(f"{year}: TT−UTC={tt_minus_utc},闰秒外推假设被打破")
            seconds = moment.second + moment.microsecond / 1e6
            sensitive += min(seconds, 60 - seconds) < BOUNDARY_SENSITIVE_S
            values.append(encode(_truncate(moment)))
    last_lineage, first_ext = decode(lineage[-1]), decode(values[0])
    if not timedelta(days=14) < first_ext - last_lineage < timedelta(days=16):
        raise SystemExit(f"与原表接缝异常: {last_lineage} → {first_ext}")

    out = [
        f'"""节气分钟精度表扩展段 {EXT_FIRST_YEAR}-{EXT_LAST_YEAR} — 天文计算生成,非 iqm.js 原表。',
        "",
        "GENERATED FILE — do not edit by hand.",
        "Regenerate: uv run tests/fixtures/gen_jieqi_ext.py > <this file>",
        "",
        "来源:JPL DE440s 星历(skyfield 1.55),太阳地心视黄经过 15° 整数倍的时刻。",
        "口径:北京时间 = UTC+8,UTC 按现行闰秒数外推(TT−UTC=69.184s);**截断到分**",
        "(与 data_tables.FINEDATE 原表同口径同编码,基年 1930)。",
        f"对账:1972-2009 段本算法与原表逐项相等 {reconciled},其余相差 1 分钟。",
        f"精度声明:{len(values)} 项中 {sensitive} 项的秒数距整分不足 "
        f"{BOUNDARY_SENSITIVE_S:g} 秒——届时实际 UTC",
        "(取决于地球自转与闰秒政策)若偏离本外推数秒,这些项的截断分会变动 1 分钟。",
        '"""',
        "",
        "from typing import Final",
        "",
        f"FINEDATE_EXT_FIRST_YEAR: Final[int] = {EXT_FIRST_YEAR}",
        "",
        "# 24 项/年(0=小寒 … 23=冬至),编码 min|hour|day|mon|year",
        "FINEDATE_EXT: Final[tuple[int, ...]] = (",
    ]
    for i in range(0, len(values), 24):
        out.append(f"    # {EXT_FIRST_YEAR + i // 24}")
        for j in range(i, i + 24, 8):
            out.append("    " + ", ".join(str(v) for v in values[j:j + 8]) + ",")
    out.append(")")
    sys.stdout.write("\n".join(out) + "\n")
    print(f"reconciled {reconciled}; boundary-sensitive {sensitive}/{len(values)}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
