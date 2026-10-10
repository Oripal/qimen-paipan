"""格局层测试 — M3 批(第十二章正格9/辅格25/常用吉凶格15 + 时辰级三时禁)。

来源 SoT:《道家阴盘奇门遁甲》第十二章(行1327-1505);表逐字照书,断语在 facts。

真盘锚定(引擎重排盘,盘面已在开发窗逐宫手核对表):
- sample 盘 2026-07-04 15:20(阴5局,与 test_qimen_tools._sample_chart 同源);
- 书中可复排案例(mingju.py 案例复排铁证同源盘):14-1(1977-04-06 09:26 阳5局)
  /14-2(1967-06-04 15:11 阳3局)/16-3(1968-06-05 12:24 阳4局,全盘伏吟);
- 三时禁按 60 甲子历点位锚定(caster 日/时柱为 SoT)。
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from qimen_engine import (
    FU_GE,
    JI_XIONG_GE,
    PATTERN_DETECTORS,
    ZHENG_GE,
    build_chart,
    cast,
    chart_elements,
    chart_pattern_hits,
    chart_shi_jin,
    detect_flags,
    run_pattern_detectors,
)
from qimen_engine.geju import (
    JI_XING_SHI,
    LIU_YI_RU_MU_SHI,
    RU_MU_SHI,
    SAN_QI_RU_MU_SHI,
    WU_BU_YU_SHI,
    ji_xiong_ge_hits,
    palace_geju_hits,
    shi_jin_flags,
    zheng_ge_hits,
)
from qimen_engine.wuxing import STEM_WUXING, sheng_ke


def _chart(dt: datetime) -> dict:
    return build_chart(cast(dt), cast_time=dt, time_source="explicit")


def _hits(dt: datetime) -> set[tuple[int, str, str]]:
    pan = cast(dt)
    return {
        (h["gong"], h["name"], h["pair"])  # type: ignore[misc]
        for h in run_pattern_detectors(pan, detect_flags(pan))
    }


SAMPLE = datetime(2026, 7, 4, 15, 20)  # 阴5局 己卯日壬申时
CASE_14_1 = datetime(1977, 4, 6, 9, 26)  # 阳5局 癸巳日丁巳时(书案例复排)
CASE_14_2 = datetime(1967, 6, 4, 15, 11)  # 阳3局 己亥日壬申时(书案例复排)
CASE_16_3 = datetime(1968, 6, 5, 12, 24)  # 阳4局 全盘伏吟(书案例复排)


class TestGeJuTables:
    """表全量:对数/落宫组逐字照书(§1/§2/§6)。"""

    def test_zheng_ge_pair_counts(self) -> None:
        """正格9类:进5/退5/前间10/后间10/上合5/下合5/正冲4/背冲4/支破6=54对。"""
        counts = Counter(ZHENG_GE.values())
        assert counts == {
            "进格": 5, "退格": 5, "前间格": 10, "后间格": 10,
            "上合格": 5, "下合格": 5, "正冲格": 4, "背冲格": 4, "支破格": 6,
        }

    def test_chong_ge_only_four_pairs_as_written(self) -> None:
        """正冲/背冲格原文仅列 4 对——照录不补全(戊己土无冲对,书未列)。"""
        zheng = {p for p, n in ZHENG_GE.items() if n == "正冲格"}
        bei = {p for p, n in ZHENG_GE.items() if n == "背冲格"}
        assert zheng == {("庚", "甲"), ("辛", "乙"), ("壬", "丙"), ("癸", "丁")}
        assert bei == {("甲", "庚"), ("乙", "辛"), ("丙", "壬"), ("丁", "癸")}
        # 语义自证:正冲=天克地,背冲=地克天(书释义)
        for t, d in zheng:
            assert sheng_ke(STEM_WUXING[t], STEM_WUXING[d]) == "克"
        for t, d in bei:
            assert sheng_ke(STEM_WUXING[d], STEM_WUXING[t]) == "克"

    def test_zhi_po_ge_six_pairs(self) -> None:
        """支破格 6 对(六仪暗支相冲,书列对照表照录)。"""
        assert {p for p, n in ZHENG_GE.items() if n == "支破格"} == {
            ("戊", "辛"), ("己", "壬"), ("庚", "癸"),
            ("辛", "戊"), ("壬", "己"), ("癸", "庚"),
        }

    def test_fu_ge_25_names_over_8_palaces(self) -> None:
        """辅格25格:五行干对×5格名;每组覆盖全部 8 宫(无中宫组)。"""
        names = {n for group in FU_GE.values() for n in group.values()}
        assert len(names) == 25
        for pair, group in FU_GE.items():
            assert set(group) == {1, 2, 3, 4, 6, 7, 8, 9}, pair
            assert len(set(group.values())) == 5, pair

    def test_fu_ge_palace_groups_per_book(self) -> None:
        """辅格落宫组抽核(§2 逐节):专旺归本行宫,余四组照书。"""
        mu = FU_GE[frozenset({"甲", "乙"})]
        assert mu[3] == mu[4] == "曲直格" and mu[1] == "温润格"
        assert mu[2] == mu[8] == "创兴格" and mu[6] == mu[7] == "伐木格"
        assert mu[9] == "焚木格"
        huo = FU_GE[frozenset({"丙", "丁"})]
        assert huo[9] == "炎上格" and huo[1] == "减光格"
        assert huo[3] == huo[4] == "增辉格" and huo[6] == huo[7] == "门讼格"
        tu = FU_GE[frozenset({"戊", "己"})]
        assert tu[2] == tu[8] == "稼穑格" and tu[9] == "转机格" and tu[1] == "迫水格"
        jin = FU_GE[frozenset({"庚", "辛"})]
        assert jin[6] == jin[7] == "从革格" and jin[9] == "抑格" and jin[2] == "扬威格"
        shui = FU_GE[frozenset({"壬", "癸"})]
        assert shui[1] == "润下格" and shui[9] == "冲激格" and shui[6] == "津润格"

    def test_ji_xiong_ge_15_names_per_book(self) -> None:
        """吉7凶8;格名照书原字(鸟跌穴/龙返首/蛇夭矫,非通行别称)。"""
        assert len(JI_XIONG_GE) == 15
        kinds = Counter(kind for _, kind in JI_XIONG_GE.values())
        assert kinds == {"吉": 7, "凶": 8}
        assert JI_XIONG_GE[("丙", "戊")] == ("鸟跌穴", "吉")
        assert JI_XIONG_GE[("戊", "丙")] == ("龙返首", "吉")
        assert JI_XIONG_GE[("癸", "丁")] == ("蛇夭矫", "凶")
        assert JI_XIONG_GE[("丙", "庚")] == ("荧入太白", "凶")
        assert JI_XIONG_GE[("癸", "癸")] == ("天网四张", "凶")
        assert JI_XIONG_GE[("庚", "癸")] == ("大格", "凶")

    def test_registered_detectors(self) -> None:
        assert set(PATTERN_DETECTORS) == {"正格", "辅格", "常用吉凶格"}


class TestZhengGeOnRealPans:
    """正格真盘锚定(sample 盘逐宫手核)。"""

    def test_sample_pan_zheng_ge_hits(self) -> None:
        hits = _hits(SAMPLE)
        assert (2, "进格", "天庚+地辛") in hits
        assert (2, "后间格", "天庚+地戊") in hits  # 坤二寄宫双地干逐干组合
        assert (3, "上合格", "天乙+地庚") in hits
        assert (4, "支破格", "天壬+地己") in hits
        assert (8, "进格", "天丙+地丁") in hits
        assert (9, "背冲格", "天丁+地癸") in hits

    def test_qian_jian_ge_carries_middle_stem_note(self) -> None:
        """前间格解读步:书「查夹在中间的那个天干落宫寻受阻原因」→ note 带中间干。"""
        pan = cast(SAMPLE)
        hits = [
            h for h in run_pattern_detectors(pan, detect_flags(pan))
            if h["name"] == "前间格"
        ]
        assert hits and hits[0]["gong"] == 6 and hits[0]["pair"] == "天癸+地乙"
        assert "中间干为甲" in str(hits[0]["note"])

    def test_negative_no_false_positive(self) -> None:
        """负例:sample 盘 1/7 宫(辛+壬 / 己+丙)与中宫不产生任何格局。"""
        gongs = {h["gong"] for h in run_pattern_detectors(cast(SAMPLE), detect_flags(cast(SAMPLE)))}
        assert 1 not in gongs and 7 not in gongs and 5 not in gongs

    def test_unit_negative_empty_palace(self) -> None:
        assert palace_geju_hits(1, [], ["壬"]) == []
        assert palace_geju_hits(1, ["辛"], []) == []
        assert zheng_ge_hits(1, ["辛"], ["壬"]) == []


class TestFuGeOnRealPans:
    """辅格真盘锚定(含书中可复排案例 14-1/14-2)。"""

    def test_sample_pan_fu_ge(self) -> None:
        hits = _hits(SAMPLE)
        assert (2, "扬威格", "天庚+地辛") in hits  # 金对落坤(土生金旺)
        assert (8, "晦光格", "天丙+地丁") in hits  # 火对落艮(土多火晦)

    def test_case_14_2_yan_shang_and_jian_guang(self) -> None:
        """14-2 书案例盘:离九丙+丁=炎上格(火行专旺),坎一丁+丙=减光格。"""
        hits = _hits(CASE_14_2)
        assert (9, "炎上格", "天丙+地丁") in hits
        assert (1, "减光格", "天丁+地丙") in hits
        assert (9, "进格", "天丙+地丁") in hits  # 同干对正格并列,不加权不排序

    def test_case_14_1_zeng_hui_and_cong_ge(self) -> None:
        """14-1 书案例盘:震三丁+丙=增辉格,兑七辛+庚=从革格(各带同对退格)。"""
        hits = _hits(CASE_14_1)
        assert (3, "增辉格", "天丁+地丙") in hits
        assert (3, "退格", "天丁+地丙") in hits
        assert (7, "从革格", "天辛+地庚") in hits
        assert (7, "退格", "天辛+地庚") in hits


class TestJiXiongGeOnRealPans:
    """常用吉凶格真盘锚定 + 龙返首书注条件机械判。"""

    def test_case_14_1_long_fan_shou_with_zhen_gong_note(self) -> None:
        """14-1 震三宫天戊+地丙=龙返首,正落震宫→书注「忌落震宫击刑」命中。"""
        pan = cast(CASE_14_1)
        hits = [
            h for h in run_pattern_detectors(pan, detect_flags(pan))
            if h["name"] == "龙返首"
        ]
        assert len(hits) == 1 and hits[0]["gong"] == 3
        assert "忌落震宫击刑" in str(hits[0]["note"])

    def test_long_fan_shou_li_gong_note_unit(self) -> None:
        """龙返首落离宫→「忌离宫子午相冲」note;落他宫(乾六)无 note。"""
        li = ji_xiong_ge_hits(9, ["戊"], ["丙"])
        assert len(li) == 1 and "忌离宫子午相冲" in str(li[0]["note"])
        qian = ji_xiong_ge_hits(6, ["戊"], ["丙"])
        assert len(qian) == 1 and "note" not in qian[0]

    def test_case_14_1_she_yao_jiao_parallel_zheng_chong(self) -> None:
        """14-1 坤二天癸+地丁=蛇夭矫(凶)+正冲格并列;天癸+地戊=下合格。"""
        hits = _hits(CASE_14_1)
        assert (2, "蛇夭矫", "天癸+地丁") in hits
        assert (2, "正冲格", "天癸+地丁") in hits
        assert (2, "下合格", "天癸+地戊") in hits

    def test_case_14_2_da_ge_is_directional(self) -> None:
        """14-2:艮八天庚+地癸=大格+支破格;坤二天癸+地庚=只支破格(方向性)。"""
        hits = _hits(CASE_14_2)
        assert (8, "大格", "天庚+地癸") in hits
        assert (8, "支破格", "天庚+地癸") in hits
        assert (2, "支破格", "天癸+地庚") in hits
        assert (2, "大格", "天癸+地庚") not in hits

    def test_case_16_3_tian_wang_si_zhang_on_fu_yin_pan(self) -> None:
        """16-3 全盘伏吟:离九癸+癸=天网四张(同干对亦成格,照书)。"""
        pan = cast(CASE_16_3)
        flags = detect_flags(pan)
        assert flags.pan_fu_yin  # 前提:确为全盘伏吟盘
        assert (9, "天网四张", "天癸+地癸") in _hits(CASE_16_3)

    def test_kind_values_vocabulary(self) -> None:
        """hit.kind ∈ {正格,辅格,吉,凶};必备键齐全。"""
        for dt in (SAMPLE, CASE_14_1, CASE_14_2, CASE_16_3):
            pan = cast(dt)
            for h in run_pattern_detectors(pan, detect_flags(pan)):
                assert {"detector", "gong", "name", "kind", "pair"} <= set(h)
                assert h["kind"] in {"正格", "辅格", "吉", "凶"}


class TestShiJin:
    """时辰级三时禁:表全量照书(§3-5)+ 真历点锚定 + 与宫位级命名区分。"""

    def test_wu_bu_yu_shi_full_table(self) -> None:
        """五不遇时对照表 10 对全量(§3 行1451-1463)。"""
        assert WU_BU_YU_SHI == {
            "甲": "庚午", "丙": "壬辰", "戊": "甲寅", "庚": "丙子", "壬": "戊申",
            "乙": "辛巳", "丁": "癸卯", "己": "乙丑", "辛": "丁酉", "癸": "己未",
        }

    def test_wu_bu_yu_shi_semantics(self) -> None:
        """语义自证:每对均为时干克日干且同阴阳(书定义↔对照表内洽)。"""
        from qimen_engine.data_tables import GAN

        for day, hour_gz in WU_BU_YU_SHI.items():
            hour_gan = hour_gz[0]
            assert sheng_ke(STEM_WUXING[hour_gan], STEM_WUXING[day]) == "克"
            assert GAN.index(hour_gan) % 2 == GAN.index(day) % 2

    def test_ru_mu_shi_six_pillars(self) -> None:
        """入墓时=三奇(丙戌/丁丑)+六仪(戊戌/己丑/壬辰/癸未)共 6。"""
        assert SAN_QI_RU_MU_SHI == {"丙戌", "丁丑"}
        assert LIU_YI_RU_MU_SHI == {"戊戌", "己丑", "壬辰", "癸未"}
        assert RU_MU_SHI == {"丙戌", "丁丑", "戊戌", "己丑", "壬辰", "癸未"}

    def test_ji_xing_shi_four_pillars(self) -> None:
        assert JI_XING_SHI == {"己未", "庚寅", "壬辰", "癸巳"}

    def test_anchor_jia_day_geng_wu_hour(self) -> None:
        """2026-01-10 11:30=甲申日庚午时→五不遇时(甲日庚午,书表首行)。"""
        chart = _chart(datetime(2026, 1, 10, 11, 30))
        assert chart["pillars"]["day"] == "甲申" and chart["pillars"]["hour"] == "庚午"
        assert chart["shi_jin"] == {
            "wu_bu_yu_shi": True, "shi_ru_mu": False, "shi_ji_xing": False,
        }

    def test_anchor_ji_day_geng_wu_hour_is_negative(self) -> None:
        """负例:2026-01-05 11:30=己卯日庚午时——同为庚午时但日干非甲,不成禁。"""
        chart = _chart(datetime(2026, 1, 5, 11, 30))
        assert chart["pillars"]["day"] == "己卯" and chart["pillars"]["hour"] == "庚午"
        assert chart["shi_jin"] == {
            "wu_bu_yu_shi": False, "shi_ru_mu": False, "shi_ji_xing": False,
        }

    def test_anchor_bing_xu_hour_san_qi_ru_mu(self) -> None:
        """2026-01-01 20:30=乙亥日丙戌时→入墓时(三奇丙戌),余禁不中。"""
        chart = _chart(datetime(2026, 1, 1, 20, 30))
        assert chart["pillars"]["hour"] == "丙戌"
        assert chart["shi_jin"] == {
            "wu_bu_yu_shi": False, "shi_ru_mu": True, "shi_ji_xing": False,
        }

    def test_anchor_gui_day_ji_wei_hour_double(self) -> None:
        """2026-01-09 13:30=癸未日己未时→五不遇时(癸日己未)+击刑时(己未)双中。"""
        chart = _chart(datetime(2026, 1, 9, 13, 30))
        assert chart["pillars"]["day"] == "癸未" and chart["pillars"]["hour"] == "己未"
        assert chart["shi_jin"] == {
            "wu_bu_yu_shi": True, "shi_ru_mu": False, "shi_ji_xing": True,
        }

    def test_anchor_bing_day_ren_chen_hour_triple(self) -> None:
        """2026-01-02 08:30=丙子日壬辰时→三禁齐中(丙日壬辰+壬辰入墓+壬辰击刑)。"""
        chart = _chart(datetime(2026, 1, 2, 8, 30))
        assert chart["pillars"]["day"] == "丙子" and chart["pillars"]["hour"] == "壬辰"
        assert chart["shi_jin"] == {
            "wu_bu_yu_shi": True, "shi_ru_mu": True, "shi_ji_xing": True,
        }

    def test_legacy_chart_fallback_from_pillars(self) -> None:
        """旧盘(落库无 shi_jin 键)经 chart_shi_jin 从四柱现算,结果同源。"""
        chart = _chart(datetime(2026, 1, 2, 8, 30))
        stored = dict(chart["shi_jin"])
        chart.pop("shi_jin")
        assert chart_shi_jin(chart) == stored

    def test_shi_jin_flags_pure_table(self) -> None:
        assert shi_jin_flags("甲申", "庚午")["wu_bu_yu_shi"] is True
        assert shi_jin_flags("己卯", "庚午")["wu_bu_yu_shi"] is False
        assert shi_jin_flags("丙子", "壬辰") == {
            "wu_bu_yu_shi": True, "shi_ru_mu": True, "shi_ji_xing": True,
        }


class TestChartWiring:
    """chart 层接线:引擎路(Pan)与盘面路(chart dict)逐项一致;要素注入。"""

    def test_pan_vs_chart_path_parity(self) -> None:
        for dt in (SAMPLE, CASE_14_1, CASE_14_2, CASE_16_3):
            pan = cast(dt)
            chart = build_chart(pan, cast_time=dt, time_source="explicit")
            via_pan = sorted(
                (h["gong"], h["name"], h["pair"])  # type: ignore[misc]
                for h in run_pattern_detectors(pan, detect_flags(pan))
            )
            via_chart = sorted(
                (h["gong"], h["name"], h["pair"])  # type: ignore[misc]
                for g in range(1, 10)
                for h in chart_pattern_hits(chart, g)
            )
            assert via_pan == via_chart, dt

    def test_chart_elements_include_pattern_names(self) -> None:
        """格名注入命中宫要素集(verify-citation 重放命中前提);未命中宫不注入。"""
        chart = _chart(SAMPLE)
        elems9 = chart_elements(chart, 9)
        assert "朱雀投江" in elems9 and "背冲格" in elems9
        elems1 = chart_elements(chart, 1)
        assert not ({"朱雀投江", "背冲格", "进格"} & elems1)

    def test_chart_elements_include_shi_jin_all_palaces(self) -> None:
        """时禁为全局凶时→命中时注入全部九宫;未命中盘不注入。"""
        triple = _chart(datetime(2026, 1, 2, 8, 30))
        for g in range(1, 10):
            assert {"五不遇时", "入墓时", "击刑时"} <= chart_elements(triple, g)
        clean = _chart(SAMPLE)
        assert not ({"五不遇时", "入墓时", "击刑时"} & chart_elements(clean, 1))
