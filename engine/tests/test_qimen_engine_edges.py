"""引擎边界回归测试 — 2026-07-05 review R1 四项修复的钉子。

期望值全部为 JS SoT 亲跑结果(vendor iqm.js,TZ=Asia/Shanghai node 复核),
不是 Python 自身输出的回写——见各断言注释。
"""

from __future__ import annotations

from datetime import datetime

import pytest
from qimen_engine import build_chart, cast, cyclical
from qimen_engine.caster import QimenOptions


class TestYearGuard:
    """R1-F1:历法表(LUNAR_INFO)覆盖 1900-2049;越界必须 fail-closed。

    原行为:pre-1900 静默回绕产垃圾盘(1890 → 农历 0 月 -3529 日照常出图),
    ≥2050 裸 IndexError。垃圾盘以权威交付物出厂比崩溃更糟。
    """

    @pytest.mark.parametrize("y", [1890, 1899, 2050, 2055])
    def test_out_of_range_raises(self, y: int) -> None:
        with pytest.raises(ValueError, match="1900-01-31 ~ 2049"):
            cast(datetime(y, 6, 1, 12, 0))

    def test_range_edges_ok(self) -> None:
        assert cast(datetime(1900, 2, 1, 12, 0)).lunar.year == 1900
        assert cast(datetime(2049, 6, 1, 12, 0)).lunar.year == 2049


class TestAdvanceMinutesRollover:
    """R1-F2:提前入局分钟进位撞 23 时,setHours(24) 是绝对置位(次日 00:MM)。

    JS SoT(vendor iqm.js 旋钮 +0→+5 亲跑):2026-07-04 22:56 +5min
    → 阴7局 庚辰日 丙子时 旬仪落6宫 值符落9 值使落4。
    修前 Python(相对 +1h)错出:阴6局 己卯日(换日丢失)。
    """

    def test_advance_overflow_crosses_day_like_js(self) -> None:
        pan = cast(
            datetime(2026, 7, 4, 22, 56),
            options=QimenOptions(advance_minutes=5),
        )
        assert (pan.dun, pan.ju) == ("阴", 7)
        assert cyclical(pan.day_cyl) == "庚辰"
        assert cyclical(pan.hour_cyl) == "丙子"
        assert (pan.dgg, pan.sgg, pan.mgg) == (6, 9, 4)

    def test_plain_zishi_rollover_unchanged(self) -> None:
        """原始 23 时路径(golden 已覆盖)不受修复影响:两种写法此处等价。"""
        pan = cast(datetime(2026, 7, 5, 23, 42))
        assert (pan.dun, pan.ju) == ("阴", 8)
        assert pan.effective_dt == datetime(2026, 7, 6, 0, 42)


class TestJieqiYearAtZishiWindow:
    """R1-F3:23:5x 起局撞交气窗口,交气时刻年份曾回退一整年。

    2025 冬至交气 = 2025-12-21 23:03(引擎 s_term)。23:00 起局换日到
    12-22,term=冬至;修前用换日前 cast_time 作参考 → 错报 2024-12-21。
    """

    def test_current_term_year_not_rolled_back(self) -> None:
        dt = datetime(2025, 12, 21, 23, 0)
        chart = build_chart(cast(dt), cast_time=dt, time_source="explicit")
        assert chart["jieqi"]["current"] == "冬至"
        assert chart["jieqi"]["current_at"].startswith("2025-12-21")
        assert chart["jieqi"]["next"] == "小寒"
        assert chart["jieqi"]["next_at"].startswith("2026-01-05")


class TestHistoricalDstDayCyl:
    """R1-F5:日柱序须按 epoch 差(JS Date 语义),含沪历史偏移。

    1986-1991 夏令时(+9)与 1900 基点 LMT(+8:05:43)使 JS offset 比 naive
    日历差小 54min17s——墙钟 00:00-00:54 的历史起局差一天日柱。
    JS SoT:1987-07-15 00:30 → dayCyl 31980(甲子日);naive 差错出 31981。
    另:同 tzinfo 对象的 aware datetime 直接相减,CPython 按「同 tzinfo 忽略
    offset」捷径退化为 naive 差——必须走 .timestamp()。
    """

    def test_dst_window_day_pillar_matches_js(self) -> None:
        pan = cast(datetime(1987, 7, 15, 0, 30))
        assert pan.lunar.day_cyl == 31980
        assert cyclical(pan.day_cyl) == "甲子"

    def test_modern_dates_unaffected(self) -> None:
        """现代日期(+8 恒定)不受 epoch 化影响——dogfood 锚定盘。"""
        pan = cast(datetime(2026, 7, 5, 23, 42))
        assert cyclical(pan.day_cyl) == "辛巳"
        assert (pan.sgg, pan.mgg) == (8, 2)
