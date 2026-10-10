"""节气分钟精度表(1930-2050)— 师门原表 + 天文计算扩展段的接缝与独立源对账。

扩展段 jieqi_ext.py 由 tests/fixtures/gen_jieqi_ext.py 用 JPL DE440s
星历生成(生成器自带对账闸:与原表 1972-2009 段逐项对账)。本套件在 CI 里用
**另一套独立算法**(chinese_calendrics 的寿星算法后端)再对一遍,并锁定接缝、
范围边界与「交气那一分钟」的排盘行为。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from chinese_calendrics.core import solar_terms
from qimen_engine import build_chart, cast, cyclical, s_term
from qimen_engine.data_tables import FINEDATE
from qimen_engine.jieqi_ext import FINEDATE_EXT, FINEDATE_EXT_FIRST_YEAR

EXT_YEARS = range(2031, 2051)


class TestTableShape:
    def test_lineage_table_untouched(self) -> None:
        """原表一字不动:1930-2030 共 101 年,末项仍是 2030 冬至原值。"""
        assert len(FINEDATE) == 101 * 24
        assert s_term(2030, 23) == datetime(2030, 12, 22, 4, 9)

    def test_extension_is_contiguous(self) -> None:
        assert FINEDATE_EXT_FIRST_YEAR == 1930 + len(FINEDATE) // 24
        assert len(FINEDATE_EXT) == len(EXT_YEARS) * 24

    def test_terms_land_in_their_own_year_and_order(self) -> None:
        """全表(含接缝)严格递增,相邻节气间隔 14~16.5 天;逐项落在本年。"""
        moments = [s_term(y, n) for y in range(1930, 2051) for n in range(24)]
        for y in EXT_YEARS:
            assert all(s_term(y, n).year == y for n in range(24))
        for prev, cur in zip(moments, moments[1:], strict=False):
            assert timedelta(days=14) < cur - prev < timedelta(days=16, hours=12)


class TestIndependentSource:
    def test_extension_matches_shouxing(self) -> None:
        """扩展段 vs 寿星算法(截断到分):全部相差 ≤1 分钟,逐项相等率 ≥97%。

        两套算法对 ΔT/闰秒外推的假设不同,秒级差数秒属预期——秒数贴近整分的
        项会因此差 1 分钟,不可能 100% 相等。
        """
        exact = total = 0
        for y in EXT_YEARS:
            for n, term in enumerate(solar_terms(y)):
                diff = abs(s_term(y, n) - term.moment.replace(second=0))
                assert diff <= timedelta(minutes=1), (y, term.name, s_term(y, n), term.moment)
                exact += diff == timedelta(0)
                total += 1
        assert total == 480
        assert exact / total >= 0.97


class TestCoverageBoundary:
    def test_minute_precision_through_2050(self) -> None:
        assert s_term(2031, 0) == datetime(2031, 1, 5, 21, 23)
        assert s_term(2050, 23) == datetime(2050, 12, 22, 0, 38)

    @pytest.mark.parametrize(("year", "n"), [(1929, 11), (2051, 0)])
    def test_out_of_table_still_falls_back_to_day_granularity(self, year: int, n: int) -> None:
        t = s_term(year, n)
        assert (t.hour, t.minute) == (0, 0)

    def test_last_castable_day_reports_next_term_to_the_minute(self) -> None:
        """农历表止于 2049:年末起局的「下一节气」落在 2050,须为分钟精度。"""
        dt = datetime(2049, 12, 31, 12, 0)
        chart = build_chart(cast(dt), cast_time=dt, time_source="explicit")
        assert chart["jieqi"]["current_at"] == "2049-12-21 18:52"
        assert chart["jieqi"]["next_at"] == "2050-01-05 12:08"


class TestTermMinuteDrivesChart:
    """交气那一分钟前后,遁/月柱/年柱按分钟切换(扩展前此段只有日粒度)。"""

    def test_xiazhi_2031_flips_yang_to_yin(self) -> None:
        t = s_term(2031, 11)
        assert t == datetime(2031, 6, 21, 21, 17)
        assert cast(t - timedelta(minutes=1)).dun == "阳"
        assert cast(t).dun == "阴"

    def test_dongzhi_2040_flips_yin_to_yang(self) -> None:
        t = s_term(2040, 23)
        assert t == datetime(2040, 12, 21, 14, 32)
        assert cast(t - timedelta(minutes=1)).dun == "阴"
        assert cast(t).dun == "阳"

    def test_lichun_2035_rolls_year_and_month_pillars(self) -> None:
        t = s_term(2035, 2)
        before, after = cast(t - timedelta(minutes=1)), cast(t)
        assert (cyclical(before.year_cyl), cyclical(before.mon_cyl)) == ("甲寅", "丁丑")
        assert (cyclical(after.year_cyl), cyclical(after.mon_cyl)) == ("乙卯", "戊寅")
