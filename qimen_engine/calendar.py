"""历法层 — 逐函数移植自师门引擎 iqm.js(可执行 SoT)。

移植纪律:与 tests/fixtures/vendor/iqm.js 逐函数对齐,golden fixtures
由 node 执行原 JS 生成(tests/fixtures/generate_golden.js)。
所有 datetime 均为 naive 中国民用时(Asia/Shanghai);时区换算在工具层完成。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from qimen_engine.data_tables import (
    FINEDATE,
    GAN,
    LUNAR_INFO,
    S_TERM_INFO,
    ZHI,
)
from qimen_engine.jieqi_ext import FINEDATE_EXT

_SHANGHAI = ZoneInfo("Asia/Shanghai")
_LUNAR_BASE = datetime(1900, 1, 31)
# iqm.js sTerm 回退公式基点: Date.UTC(1900,0,6,2,5)
_TERM_BASE_UTC = datetime(1900, 1, 6, 2, 5, tzinfo=UTC)
_TROPICAL_YEAR_MS = 31556925974.7
# 节气分钟精度表 = 师门原表(iqm.js finedate,1930-2030)+ 天文计算扩展段
# (jieqi_ext,2031-2050;同编码同截断口径)。原表一字不动,扩展段只接在其后。
_FINE_FIRST_YEAR = 1930
_FINE_TABLE = FINEDATE + FINEDATE_EXT
_FINE_LAST_YEAR = _FINE_FIRST_YEAR + len(_FINE_TABLE) // 24 - 1


def js_round_half_up(x: float) -> int:
    """JS Math.round 语义(0.5 恒向上);Python round 是银行家舍入,不可用。"""
    import math

    return math.floor(x + 0.5)


def leap_month(y: int) -> int:
    """农历 y 年闰哪个月(1-12),无闰返回 0。(iqm.js leapMonth)"""
    return LUNAR_INFO[y - 1900] & 0xF


def leap_days(y: int) -> int:
    """农历 y 年闰月天数。(iqm.js leapDays)"""
    if leap_month(y):
        return 30 if LUNAR_INFO[y - 1900] & 0x10000 else 29
    return 0


def lunar_year_days(y: int) -> int:
    """农历 y 年总天数。(iqm.js lYearDays)"""
    total = 348
    mask = 0x8000
    while mask > 0x8:
        total += 1 if LUNAR_INFO[y - 1900] & mask else 0
        mask >>= 1
    return total + leap_days(y)


def month_days(y: int, m: int) -> int:
    """农历 y 年 m 月天数。(iqm.js monthDays)"""
    return 30 if LUNAR_INFO[y - 1900] & (0x10000 >> m) else 29


def cyclical(num: int) -> str:
    """60 甲子序号 → 干支字符串,0=甲子。(iqm.js cyclical)"""
    return GAN[num % 10] + ZHI[num % 12]


def s_term(y: int, n: int) -> datetime:
    """某年第 n 个节气的交气时刻(从 0=小寒起算),naive 中国民用时。

    (iqm.js sTerm)1930-2050 用分钟精度表:1930-2030 为 iqm.js 原表 finedate,
    2031-2050 为天文计算扩展段(原引擎此段回退近似公式,本移植不复刻);
    范围外仍回退近似公式(仅日粒度,时分归零)。
    """
    v3_ms = (
        _TROPICAL_YEAR_MS * (y - 1900) + S_TERM_INFO[n] * 60000
    )
    off_utc = _TERM_BASE_UTC + timedelta(milliseconds=v3_ms)
    off_local = off_utc.astimezone(_SHANGHAI).replace(tzinfo=None)
    ly = off_local.year
    if _FINE_FIRST_YEAR <= ly <= _FINE_LAST_YEAR:
        data = _FINE_TABLE[(ly - _FINE_FIRST_YEAR) * 24 + n]
        minute = data % 60
        data //= 60
        hour = data % 24
        data //= 24
        day = data % 32 + 1
        data //= 32
        mon = data % 12
        year = data // 12 + _FINE_FIRST_YEAR
        return datetime(year, mon + 1, day, hour, minute)
    return datetime(off_local.year, off_local.month, off_local.day)


def get_term(obj_dt: datetime) -> int:
    """某时刻所处节气:返回首个交气时刻晚于 obj_dt 的节气序号(0-24)。

    (iqm.js GetTerm)返回 24 表示已过当年冬至后段(调用方归 0)。
    """
    year = obj_dt.year
    i = 0
    while i < 24:
        if obj_dt < s_term(year, i):
            break
        i += 1
    return i


@dataclass(frozen=True)
class LunarDate:
    """农历转换结果。(iqm.js Lunar 对象)"""

    year: int
    month: int
    day: int  # 已取整的农历日
    is_leap: bool
    year_cyl: int  # 干支年序(year-1864 基,含正月界调整)
    mon_cyl: int  # 干支月序(节气界)
    day_cyl: int  # 干支日序(已取整)


def to_lunar(obj_dt: datetime) -> LunarDate:
    """公历 → 农历+三柱序。(iqm.js Lunar,逐行对齐,offset 保留小数语义)"""
    # 护栏:LUNAR_INFO 覆盖 1900-2049,基点 1900-01-31。越界原行为是
    # 静默回绕产垃圾盘(pre-1900)或裸 IndexError(≥2050)——fail-closed。
    if obj_dt < _LUNAR_BASE or obj_dt.year > 2049:
        raise ValueError(
            f"历法表仅覆盖 1900-01-31 ~ 2049 年,无法为 {obj_dt:%Y-%m-%d} 排盘/换算。"
        )
    # 与 iqm.js `(objDate-baseDate)/86400000` 对齐:JS 的 Date 差是 epoch 毫秒差,
    # 含 Asia/Shanghai 历史偏移(1900 基点 LMT +8:05:43、1986-1991 夏令时 +9)。
    # naive 日历差在夏令时段(如 1987-07 墙钟 00:00-00:54)会比 SoT 多算一天日柱。
    # 必须走 .timestamp()(epoch 差):同 tzinfo 对象的 aware datetime 直接相减,
    # CPython 按「同 tzinfo 忽略 offset」捷径退化成 naive 日历差,历史变偏移全丢。
    offset = (
        obj_dt.replace(tzinfo=_SHANGHAI).timestamp()
        - _LUNAR_BASE.replace(tzinfo=_SHANGHAI).timestamp()
    ) / 86400.0
    day_cyl = offset + 40
    mon_cyl = 14

    temp = 0
    i = 1900
    while i < 2050 and offset > 0:
        temp = lunar_year_days(i)
        offset -= temp
        mon_cyl += 12
        i += 1
    if offset < 0:
        offset += temp
        i -= 1
        mon_cyl -= 12
    year = i

    leap = leap_month(year)
    is_leap = False
    i = 1
    while i < 13 and offset > 0:
        if leap > 0 and i == leap + 1 and not is_leap:
            i -= 1
            is_leap = True
            temp = leap_days(year)
        else:
            temp = month_days(year, i)
        if is_leap and i == leap + 1:
            is_leap = False
        offset -= temp
        if not is_leap:
            mon_cyl += 1
        i += 1
    if offset == 0 and leap > 0 and i == leap + 1:
        if is_leap:
            is_leap = False
        else:
            is_leap = True
            i -= 1
            mon_cyl -= 1
    if offset < 0:
        offset += temp
        i -= 1
        mon_cyl -= 1
    month = i
    day = offset + 1

    # 干支月按「节」界重算(iqm.js Lunar 尾段)
    y = obj_dt.year
    m = obj_dt.month - 1  # JS 0-based month
    first_node = s_term(y, m * 2)
    if obj_dt >= first_node:
        mon_cyl = (y - 1900) * 12 + m + 13
    else:
        mon_cyl = (y - 1900) * 12 + m + 12

    year_cyl = y - 1864
    om = m
    olm = mon_cyl % 12
    if om < 4 and olm < 2:
        year_cyl -= 1

    return LunarDate(
        year=year,
        month=month,
        day=int(day),
        is_leap=is_leap,
        year_cyl=year_cyl,
        mon_cyl=mon_cyl,
        day_cyl=int(day_cyl),
    )
