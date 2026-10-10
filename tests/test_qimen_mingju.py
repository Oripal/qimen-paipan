"""命局定宫 golden 测试(2026-07-06 著作批定参,取代 fail-closed scaffold 测试)。

定参依据+复排铁证见 mingju.py docstring。golden 锚=《道家阴盘奇门遁甲》
第十四/十六章四案例。⚠️ 书 md 案例**宫名**被转换系统性损坏(如 14-1 平台
「巽四」/16-3 命宫「离九」),宫位断言一律以引擎复排+书中**符号叙述**交叉
验证为准(символ链见各断言注释)——few-shot 提取同理,勿直信书文宫名。
"""

from __future__ import annotations

from datetime import datetime

import pytest
from qimen_engine import cast
from qimen_engine.calendar import cyclical
from qimen_engine.data_tables import ZHI2GONG
from qimen_engine.mingju import (
    anchor_stem_gong,
    da_yun_at,
    da_yun_forward,
    da_yun_label,
    da_yun_sequence,
    find_stem_gong,
    liu_nian_gong,
    ming_gong,
    ping_tai_gong,
    qi_yun_age,
)

# 四案例出生时刻(书中「基础信息」;四柱/遁局引擎复排与书头全等,
# 14-2 书头「阴3」/14-3 书头日柱「丙子」为转录误,均被书头自身的
# 值符值使宫/空亡字段反证——详 mingju.py docstring)
CASE_14_1 = datetime(1977, 4, 6, 9, 26)  # 丁巳 甲辰 癸巳 丁巳 阳5局(男,阴年逆排)
CASE_14_2 = datetime(1967, 6, 4, 15, 11)  # 丁未 乙巳 己亥 壬申 阳3局
CASE_14_3 = datetime(2006, 5, 7, 5, 49)  # 丙戌 癸巳 丙申 辛卯 阳2局(阳年顺排)
CASE_16_3 = datetime(1968, 6, 5, 12, 24)  # 戊申 丁巳 丙午 甲午 阳4局(男,书中明说)


class TestMingGongPingTai:
    """Q17:命宫=日干天盘落宫/平台=时干天盘落宫(第十三章书证)。"""

    def test_14_1_ming_gong_kun2(self) -> None:
        """14-1 癸@坤二:书文+书盘双证(值符+天蓬+伤门迫+地戊+癸墓五符号)。"""
        pan = cast(CASE_14_1)
        assert ming_gong(pan) == 2
        assert pan.shenpan[2] == "符" and pan.xinpan[2] == "蓬" and pan.menpan[2] == "伤"

    def test_14_1_ping_tai_zhen3(self) -> None:
        """14-1 丁@震三:书文宫名「巽四」已损,符号(开门+玄武+天芮)全指震三。"""
        pan = cast(CASE_14_1)
        assert ping_tai_gong(pan) == 3
        assert pan.menpan[3] == "开" and pan.shenpan[3] == "玄" and pan.xinpan[3] == "芮"

    def test_14_2_ming_gong_qian6(self) -> None:
        """14-2 己@乾六:腾蛇+景门+空亡+地辛四符号(书文宫名此例未损)。"""
        pan = cast(CASE_14_2)
        assert ming_gong(pan) == 6
        assert pan.shenpan[6] == "蛇" and pan.menpan[6] == "景"
        assert 6 in pan.kong_gongs and "辛" in pan.digan[6]

    def test_14_3_ming_gong_dui7(self) -> None:
        """14-3 丙@兑七:腾蛇(聪明/走神)+景门(学习能力)。"""
        pan = cast(CASE_14_3)
        assert ming_gong(pan) == 7
        assert pan.shenpan[7] == "蛇" and pan.menpan[7] == "景"

    def test_16_3_ming_gong_kun2(self) -> None:
        """16-3 丙@坤二:九天+天芮(善管理)+马星(闲不住)三符号全中。"""
        pan = cast(CASE_16_3)
        assert ming_gong(pan) == 2
        assert pan.shenpan[2] == "天" and pan.xinpan[2] == "芮" and pan.ma_gong == 2


class TestJiaAnchor:
    """锚干为甲 → 以戊(甲子戊)落宫(16-1 书注;非本柱旬遁)。"""

    def test_16_3_hour_jia_falls_with_wu(self) -> None:
        """16-3 时柱甲午:平台=戊@巽四——玄武+空亡两符号中(书文「乾六」已损)。
        若按本柱旬遁(甲午→辛)会落兑七,符号全不匹配。"""
        pan = cast(CASE_16_3)
        assert ping_tai_gong(pan) == 4
        assert pan.shenpan[4] == "玄" and 4 in pan.kong_gongs
        assert ping_tai_gong(pan) == anchor_stem_gong(pan, "戊")

    def test_day_stem_jia(self) -> None:
        """甲日干(1977-04-07=甲午日)命宫=天盘戊宫。"""
        pan = cast(datetime(1977, 4, 7, 9, 26))
        assert cyclical(pan.day_cyl) == "甲午"
        assert ming_gong(pan) == find_stem_gong(pan, "戊", layer="天") == 7

    def test_unknown_stem_raises(self) -> None:
        pan = cast(CASE_14_1)
        with pytest.raises(ValueError, match="未知天干"):
            anchor_stem_gong(pan, "子")


class TestQiYunAge:
    """起运岁=距相邻节天数÷3(真算,非固定值)——四案例核算。"""

    def test_14_1_reverse_to_qingming(self) -> None:
        raw, rounded = qi_yun_age(CASE_14_1, forward=False)  # 逆数至清明 04-05 05:45
        assert raw == pytest.approx(0.384, abs=0.01)
        assert rounded == 0

    def test_14_2_reverse_to_lixia(self) -> None:
        raw, rounded = qi_yun_age(CASE_14_2, forward=False)  # 逆数至立夏 05-06 13:17
        assert raw == pytest.approx(9.69, abs=0.01)
        assert rounded == 10

    def test_14_3_forward_to_mangzhong(self) -> None:
        raw, rounded = qi_yun_age(CASE_14_3, forward=True)  # 顺数至芒种 06-06 03:36
        assert raw == pytest.approx(9.97, abs=0.01)
        assert rounded == 10

    def test_16_3_forward_born_hours_before_jie(self) -> None:
        raw, rounded = qi_yun_age(CASE_16_3, forward=True)  # 芒种 06-05 23:19 同日
        assert raw == pytest.approx(0.15, abs=0.01)
        assert rounded == 0


class TestDaYunDirection:
    """阳年干+男/阴年干+女=顺;反之逆(阴年女顺排=通行规则,师门清单挂验证勾)。"""

    def test_yin_year_male_reverse(self) -> None:
        assert da_yun_forward(cast(CASE_14_1), "male") is False  # 丁巳阴年男

    def test_yang_year_male_forward(self) -> None:
        assert da_yun_forward(cast(CASE_14_3), "male") is True  # 丙戌阳年男
        assert da_yun_forward(cast(CASE_16_3), "male") is True  # 戊申阳年男(书明说男)

    def test_gender_flips(self) -> None:
        assert da_yun_forward(cast(CASE_14_1), "female") is True
        assert da_yun_forward(cast(CASE_14_3), "female") is False

    def test_bad_gender_raises(self) -> None:
        with pytest.raises(ValueError, match="gender"):
            da_yun_forward(cast(CASE_14_1), "other")  # type: ignore[arg-type]


class TestDaYunCase141:
    """golden 最强锚:书中六运全列(干序+岁段)+逐运落宫符号链。"""

    def test_six_yun_full_sequence(self) -> None:
        pan = cast(CASE_14_1)
        seq = da_yun_sequence(pan, CASE_14_1, "male", count=6)
        assert [cyclical(y.cyl) for y in seq] == ["癸卯", "壬寅", "辛丑", "庚子", "己亥", "戊戌"]
        assert [y.start_age for y in seq] == [0, 10, 20, 30, 40, 50]
        assert [y.end_age for y in seq] == [9, 19, 29, 39, 49, 59]
        assert [y.start_year for y in seq] == [1977, 1987, 1997, 2007, 2017, 2027]

    def test_yun_gongs_symbol_chain(self) -> None:
        """癸→坤二(墓)/壬→艮八(空亡)/辛→兑七(蛇+杜)/庚→巽四(休门=值使宫)/
        己→离九(生门+九天,书文宫名「离九」此处未损,直证)/戊→震三(开门事业)。"""
        pan = cast(CASE_14_1)
        seq = da_yun_sequence(pan, CASE_14_1, "male", count=6)
        assert [y.gong for y in seq] == [2, 8, 7, 4, 9, 3]
        assert seq[1].gong in pan.kong_gongs  # 壬运「逢空亡」
        assert pan.shenpan[seq[2].gong] == "蛇" and pan.menpan[seq[2].gong] == "杜"  # 辛运
        assert pan.menpan[seq[3].gong] == "休" and seq[3].gong == pan.mgg  # 庚运「休门」
        assert pan.menpan[seq[4].gong] == "生" and pan.shenpan[seq[4].gong] == "天"  # 己运
        assert pan.menpan[seq[5].gong] == "开"  # 戊运「走事业运」

    def test_da_yun_at_and_label(self) -> None:
        pan = cast(CASE_14_1)
        seq = da_yun_sequence(pan, CASE_14_1, "male", count=6)
        hit = da_yun_at(seq, 45)
        assert hit is not None and hit.gan == "己" and hit.gong == 9
        assert da_yun_at(seq, 60) is None  # 超出序列
        assert da_yun_label(seq[0]) == "癸卯运(0-9 岁,1977-1986)"


class TestDaYunCase142:
    """起运 10 岁;庚子运 50-59=2017-2026(书:咨询期「正走庚运」)。"""

    def test_geng_yun_window_and_gong(self) -> None:
        pan = cast(CASE_14_2)
        seq = da_yun_sequence(pan, CASE_14_2, "male", count=6)
        assert [cyclical(y.cyl) for y in seq] == ["甲辰", "癸卯", "壬寅", "辛丑", "庚子", "己亥"]
        geng = seq[4]
        assert (geng.start_age, geng.end_age, geng.start_year) == (50, 59, 2017)
        # 庚@艮八:击刑+入墓+天芮「病星浮现」(书文宫名「巽」已损,符号指艮八)
        assert geng.gong == 8 and pan.xinpan[8] == "芮"

    def test_before_qiyun_returns_none(self) -> None:
        pan = cast(CASE_14_2)
        seq = da_yun_sequence(pan, CASE_14_2, "male")
        assert da_yun_at(seq, 5) is None  # 起运 10 岁前=幼运期,如实为 None

    def test_jia_yun_first(self) -> None:
        """首运甲辰→戊@兑七(甲→戊落宫在大运轴同样生效)。"""
        pan = cast(CASE_14_2)
        seq = da_yun_sequence(pan, CASE_14_2, "male")
        assert seq[0].gan == "甲" and seq[0].gong == find_stem_gong(pan, "戊", layer="天") == 7


class TestDaYunCase143:
    """「19 岁之前」精确命中=起运岁真算的书面实证;平台大运同宫扶文昌。"""

    def test_jia_yun_10_19_with_platform(self) -> None:
        pan = cast(CASE_14_3)
        seq = da_yun_sequence(pan, CASE_14_3, "male", count=2)
        jia = seq[0]
        assert cyclical(jia.cyl) == "甲午"
        assert (jia.start_age, jia.end_age) == (10, 19)  # 书:「19 岁之前」
        # 大运甲(→戊)与平台辛同落乾六(天盘戊辛双干宫=芮宫,芮=文昌)
        assert jia.gong == ping_tai_gong(pan) == 6
        assert pan.xinpan[6] == "芮"

    def test_yi_yun_next(self) -> None:
        pan = cast(CASE_14_3)
        seq = da_yun_sequence(pan, CASE_14_3, "male", count=2)
        assert seq[1].gan == "乙" and (seq[1].start_age, seq[1].end_age) == (20, 29)


class TestDaYunCase163:
    """起运 0 岁(生于芒种前 11 小时);2019 年(51 岁)「大运走癸运」。"""

    def test_gui_yun_at_51(self) -> None:
        pan = cast(CASE_16_3)
        seq = da_yun_sequence(pan, CASE_16_3, "male")
        want = ["戊午", "己未", "庚申", "辛酉", "壬戌", "癸亥"]
        assert [cyclical(y.cyl) for y in seq[:6]] == want
        hit = da_yun_at(seq, 51)
        assert hit is not None and hit.gan == "癸" and hit.start_age == 50
        assert hit.start_year == 2018  # 2018-2027 覆盖 2019 咨询年


class TestLiuNianBenwei:
    """流年=年支九宫本位(Q19,gated 待师门打勾;精微录两处+社区形态互证)。"""

    def test_full_branch_table(self) -> None:
        # 子坎1 丑寅艮8 卯震3 辰巳巽4 午离9 未申坤2 酉兑7 戌亥乾6
        want = {0: 1, 1: 8, 2: 8, 3: 3, 4: 4, 5: 4, 6: 9, 7: 2, 8: 2, 9: 7, 10: 6, 11: 6}
        assert {z: liu_nian_gong(z) for z in range(12)} == want

    def test_jingweilu_anchor_cases(self) -> None:
        """精微录互证例:2021辛丑/2022壬寅→艮宫;子年→坎宫。"""
        assert liu_nian_gong(1) == 8 and liu_nian_gong(2) == 8  # 丑/寅=艮
        assert liu_nian_gong(0) == 1  # 子=坎

    def test_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            liu_nian_gong(12)

    def test_liu_nian_vs_zhi2gong_consistency(self) -> None:
        for z in range(12):
            assert liu_nian_gong(z) == ZHI2GONG[z]


class TestFindStemGong:
    def test_layers(self) -> None:
        pan = cast(datetime(2026, 7, 5, 23, 42))
        # 该盘天盘庚在艮八、地盘庚在乾六(dogfood 锚定盘)
        assert find_stem_gong(pan, "庚", layer="天") == 8
        assert find_stem_gong(pan, "庚", layer="地") == 6
        assert find_stem_gong(pan, "甲", layer="天") == 0  # 甲遁不现(裸查层)
