"""节气分钟精度表(1930-2050)— 原表段 + 天文计算段的接缝、官方锚点与独立源对账。

s_term 对 1930-2009 用师门原表(iqm.js finedate),2010-2050 用计算段
jieqi_computed.py(tests/fixtures/gen_jieqi_computed.py 以 JPL DE440s 星历生成;
生成器自带对账闸:与原表 1972-2009 段逐项对账)。本套件再用**另一套独立算法**
(chinese_calendrics 的寿星算法后端)和官方年历锚点各对一遍,并锁定接缝、范围
边界、与原表的差异清单,以及「交气那一分钟」的排盘行为。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from chinese_calendrics.core import SOLAR_TERM_NAMES, solar_terms
from qimen_engine import build_chart, cast, cyclical, s_term
from qimen_engine.data_tables import FINEDATE
from qimen_engine.jieqi_computed import FINEDATE_COMPUTED, FINEDATE_COMPUTED_FIRST_YEAR

COMPUTED_YEARS = range(2010, 2051)
LINEAGE_OVERLAP_YEARS = range(2010, 2031)

# 官方年历锚点(分钟级,四舍五入口径)。来源:紫金山天文台《2025年日历资料》、
# 《2022~2026年日历资料》2026 册;2025 冬至与香港天文台 2025 年节气表同分。
OFFICIAL_ROUNDED = {
    (2025, "小寒"): datetime(2025, 1, 5, 10, 33),
    (2025, "立春"): datetime(2025, 2, 3, 22, 10),
    (2025, "雨水"): datetime(2025, 2, 18, 18, 7),
    (2025, "冬至"): datetime(2025, 12, 21, 23, 3),
    (2026, "立春"): datetime(2026, 2, 4, 4, 2),
}


def _lineage(year: int, n: int) -> datetime:
    """iqm.js 原表的值(含已不再采用的 2010-2030 段)。"""
    data = FINEDATE[(year - 1930) * 24 + n]
    minute, data = data % 60, data // 60
    hour, data = data % 24, data // 24
    day, data = data % 32 + 1, data // 32
    return datetime(data // 12 + 1930, data % 12 + 1, day, hour, minute)


class TestTableShape:
    def test_lineage_table_is_still_the_iqm_js_table(self) -> None:
        """data_tables.FINEDATE 不因校对而改动:仍是 1930-2030 共 101 年的原表。"""
        assert len(FINEDATE) == 101 * 24
        assert _lineage(2030, 23) == datetime(2030, 12, 22, 4, 9)

    def test_lineage_segment_serves_through_2009(self) -> None:
        for year in (1930, 1987, 2009):
            assert all(s_term(year, n) == _lineage(year, n) for n in range(24))

    def test_computed_segment_shape(self) -> None:
        assert FINEDATE_COMPUTED_FIRST_YEAR == 2010
        assert len(FINEDATE_COMPUTED) == len(COMPUTED_YEARS) * 24

    def test_terms_land_in_their_own_year_and_order(self) -> None:
        """全表(含 2009→2010 接缝)严格递增,相邻节气间隔 14~16.5 天。"""
        moments = [s_term(y, n) for y in range(1930, 2051) for n in range(24)]
        for y in COMPUTED_YEARS:
            assert all(s_term(y, n).year == y for n in range(24))
        for prev, cur in zip(moments, moments[1:], strict=False):
            assert timedelta(days=14) < cur - prev < timedelta(days=16, hours=12)


class TestAgainstLineageTable:
    def test_corrections_are_one_minute_and_almost_all_later(self) -> None:
        """2010-2030 与原表的差异清单:只差 1 分钟;原表 88 项偏早、1 项偏晚。

        原表 2011 起逐年偏早(2010 年代 11 项,2020 年起每年 2~11 项)——
        这是改用计算段的原因;数字变动说明生成器或原表被动过。
        """
        early = late = 0
        for y in LINEAGE_OVERLAP_YEARS:
            for n in range(24):
                diff = _lineage(y, n) - s_term(y, n)
                assert abs(diff) <= timedelta(minutes=1), (y, n)
                early += diff == timedelta(minutes=-1)
                late += diff == timedelta(minutes=1)
        assert (early, late) == (88, 1)


class TestAgainstOfficialAlmanac:
    @pytest.mark.parametrize(("key", "official"), OFFICIAL_ROUNDED.items(), ids=str)
    def test_truncated_minute_is_consistent_with_rounded_official(
        self, key: tuple[int, str], official: datetime,
    ) -> None:
        """本表截断到分,官方四舍五入:本表必须等于官方值或恰早 1 分钟。"""
        year, name = key
        ours = s_term(year, SOLAR_TERM_NAMES.index(name))
        assert timedelta(0) <= official - ours <= timedelta(minutes=1)

    def test_entries_the_lineage_table_had_early(self) -> None:
        """原表把这两项记早了 1 分钟(官方 23:03 / 04:02),计算段与官方同分。"""
        assert _lineage(2025, 23) == datetime(2025, 12, 21, 23, 2)
        assert s_term(2025, 23) == OFFICIAL_ROUNDED[(2025, "冬至")]
        assert _lineage(2026, 2) == datetime(2026, 2, 4, 4, 1)
        assert s_term(2026, 2) == OFFICIAL_ROUNDED[(2026, "立春")]


class TestIndependentSource:
    def test_computed_segment_matches_shouxing(self) -> None:
        """计算段 vs 寿星算法(截断到分):全部相差 ≤1 分钟,逐项相等率 ≥97%。

        两套算法的秒级结果差数秒属预期(寿星是级数近似,且对未来的 ΔT/闰秒外推
        假设不同)——秒数贴近整分的项会因此差 1 分钟,不可能 100% 相等。
        """
        exact = total = 0
        for y in COMPUTED_YEARS:
            for n, term in enumerate(solar_terms(y)):
                diff = abs(s_term(y, n) - term.moment.replace(second=0))
                assert diff <= timedelta(minutes=1), (y, term.name, s_term(y, n), term.moment)
                exact += diff == timedelta(0)
                total += 1
        assert total == len(COMPUTED_YEARS) * 24
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
    """交气那一分钟前后,遁/局/月柱/年柱按分钟切换。"""

    def test_lichun_2026_follows_the_corrected_minute(self) -> None:
        """原表 04:01 交立春;校对后 04:02——04:01 起局仍属乙巳年、阳2局。"""
        before, after = cast(datetime(2026, 2, 4, 4, 1)), cast(datetime(2026, 2, 4, 4, 2))
        assert (cyclical(before.year_cyl), cyclical(before.mon_cyl), before.ju) == (
            "乙巳", "己丑", 2,
        )
        assert (cyclical(after.year_cyl), cyclical(after.mon_cyl), after.ju) == (
            "丙午", "庚寅", 3,
        )

    def test_dongzhi_2026_follows_the_corrected_minute(self) -> None:
        """原表 04:49 交冬至;校对后 04:50——04:49 起局仍是阴遁。"""
        assert cast(datetime(2026, 12, 22, 4, 49)).dun == "阴"
        assert cast(datetime(2026, 12, 22, 4, 50)).dun == "阳"

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
