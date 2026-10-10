"""四害规格补齐项与旺衰规则测试 — D2 移植层补齐,单独标注(设计 §3.1 移植纪律)。

golden 对比覆盖不了的部分在此测:
- D2 补齐「日空并标」(原 iqm.js 只标时旬空,无日空层)
- D1 天禽随天芮 co_star(Chart JSON 结构化承载)
- 伏吟/反吟标记(detect-patterns 缩窄方案的盘级/宫级标记)
- wangshui-calc 旺相休囚死死规则
- Chart JSON v1 契约(schema/流派声明/结构化 flags)
"""

from __future__ import annotations

from datetime import datetime

from qimen_engine import (
    build_chart,
    cast,
    chart_elements,
    detect_flags,
    element_of,
    sheng_ke,
    wang_shuai,
)
from qimen_engine.data_tables import ZHI
from qimen_engine.sihai import JI_XING, MEN_PO, RU_MU, stem_flags_for


class TestSihaiSpecTables:
    """《四害判定规格》表项(D2):门迫13/击刑6/入墓十干。"""

    def test_men_po_is_13_items(self) -> None:
        assert sum(len(v) for v in MEN_PO.values()) == 13
        assert "休" in MEN_PO[9]  # 默认:休门落离算迫

    def test_ji_xing_is_6_items(self) -> None:
        assert len(JI_XING) == 6
        assert JI_XING == {"戊": 3, "己": 2, "庚": 8, "辛": 9, "壬": 4, "癸": 4}

    def test_ru_mu_covers_nine_stems_own_tombs(self) -> None:
        """入墓四维宫本墓表:乾乙丙戊/艮丁己庚/巽辛壬/坤癸(九干各本墓)。

        原 App 第十干「甲」由旬首仪转承(旬首仪落坤=甲墓)——**师门 2026-07-06
        定不用**(师傅:庚在未不入墓、在坤二宫不入墓),缺省关;vendor 保真闸
        (jia_mu_xun_yi_at_kun=True)保留原行为供 golden 锚定。"""
        listed = set().union(*RU_MU.values())
        assert listed == {"乙", "丙", "戊", "丁", "己", "庚", "辛", "壬", "癸"}
        # 师门缺省:旬首仪落坤二不标墓
        assert stem_flags_for("戊", 2, "戊") == ()  # 甲子旬仪戊落坤,不墓
        assert stem_flags_for("庚", 2, "庚") == ()  # 甲申旬仪庚落坤,不墓(师傅点名)
        # vendor 保真闸:原 App 行为可复现
        assert stem_flags_for("戊", 2, "戊", jia_mu_xun_yi_at_kun=True) == ("入墓",)
        assert stem_flags_for("戊", 2, "己", jia_mu_xun_yi_at_kun=True) == ()

    def test_ren_at_xun_is_both_xing_and_mu(self) -> None:
        """壬落巽四 = 击刑+入墓 双标(iqm.js 【刑墓】#EE00EE 语义)。"""
        assert set(stem_flags_for("壬", 4, "戊")) == {"击刑", "入墓"}

    def test_gui_at_xun_is_xing_only(self) -> None:
        """癸落巽四 = 击刑(癸墓在坤,不在巽)。"""
        assert stem_flags_for("癸", 4, "戊") == ("击刑",)


class TestRiKongLayerRevoked:
    """日空层已撤(Q21 师门裁定,2026-07-06 师傅盘面纠偏「去掉日空」):
    门内空亡唯一基准=时旬空;App/精微录/宝典均无日空层——原 D2「日空并标」
    系开发期无师门依据的自加层。本类钉死:引擎/契约不再产出任何日空字段。"""

    def test_pan_has_no_ri_kong_layer(self) -> None:
        pan = cast(datetime(2026, 7, 4, 15, 20))
        assert not hasattr(pan, "ri_kong_zhi")
        assert not hasattr(pan, "ri_kong_gongs")

    def test_palace_flags_kong_is_shi_only(self) -> None:
        pan = cast(datetime(2026, 7, 4, 15, 20))
        flags = detect_flags(pan)
        for gong in range(1, 10):
            pf = flags.palaces[gong]
            assert pf.kong_shi == (gong in pan.kong_gongs)
            assert not hasattr(pf, "kong_ri")
            # si_hai 的空亡只由时空驱动
            assert ("空亡" in pf.si_hai) == pf.kong_shi

    def test_chart_json_has_no_ri_kong_keys(self) -> None:
        pan = cast(datetime(2026, 7, 4, 15, 20))
        chart = build_chart(
            pan, cast_time=datetime(2026, 7, 4, 15, 20), time_source="auto"
        )
        assert chart["xun"]["kong_zhi"] == [ZHI[z] for z in pan.xun_kong_zhi]
        assert "ri_kong_zhi" not in chart["xun"]
        assert "ri_kong_gong" not in chart["xun"]
        assert "kong_ri" not in chart["palaces"]["2"]["flags"]


class TestCoStar:
    """D1 天禽随天芮(co_star)结构化承载。"""

    def test_rui_palace_carries_qin(self) -> None:
        pan = cast(datetime(2026, 7, 4, 15, 20))
        chart = build_chart(
            pan, cast_time=datetime(2026, 7, 4, 15, 20), time_source="auto"
        )
        rui_palaces = [
            p for p in chart["palaces"].values() if "天芮" in p["stars"]
        ]
        assert len(rui_palaces) == 1
        assert rui_palaces[0]["stars"] == ["天芮", "天禽"]
        # 芮宫天盘携双干(本宫干+中宫寄干)
        assert len(rui_palaces[0]["heaven_stems"]) == 2

    def test_kun_hosts_ji_gong(self) -> None:
        """坤二承寄:地盘双干,中五保留本干(§3.8-2 双位呈现)。"""
        pan = cast(datetime(2026, 7, 4, 15, 20))
        chart = build_chart(
            pan, cast_time=datetime(2026, 7, 4, 15, 20), time_source="auto"
        )
        assert chart["palaces"]["2"]["is_ji_gong_host"] is True
        assert len(chart["palaces"]["2"]["earth_stems"]) == 2
        assert len(chart["palaces"]["5"]["earth_stems"]) == 1
        assert chart["palaces"]["2"]["earth_stems"][1] == (
            chart["palaces"]["5"]["earth_stems"][0]
        )


class TestJiaMuTransferRevoked:
    """师门 2026-07-06 定:旬首仪落坤不按「甲墓」标墓(师傅:庚在未不入墓、
    在坤二宫不入墓)。原 App 转承(iqm.js:917/974)只在 vendor 保真闸下存活。

    锚定盘 = 师傅点名的实弹盘 2026-07-06 10:18(阴遁4局,甲申旬,地盘庚落坤二)。
    """

    def test_yi_at_kun_not_mu_by_default(self) -> None:
        pan = cast(datetime(2026, 7, 6, 10, 18))
        assert pan.xun_shou == 20  # 甲申旬(仪=庚)
        flags = detect_flags(pan)
        kun2 = {
            (sf.stem, sf.layer): sf.flags for sf in flags.palaces[2].stem_flags
        }
        assert ("庚", "地") not in kun2  # 庚落坤二:无任何标(不击刑不入墓)
        assert kun2.get(("癸", "天")) == ("入墓",)  # 癸本墓在坤,不受撤销影响

    def test_vendor_gate_reproduces_app_behavior(self) -> None:
        """vendor 保真闸(golden 专用)仍复现原 App 的甲墓标——移植保真不丢。"""
        pan = cast(datetime(2026, 7, 6, 10, 18))
        flags = detect_flags(pan, jia_mu_xun_yi_at_kun=True)
        kun2 = {
            (sf.stem, sf.layer): sf.flags for sf in flags.palaces[2].stem_flags
        }
        assert kun2.get(("庚", "地")) == ("入墓",)

    def test_yi_with_own_jixing_keeps_jixing_only(self) -> None:
        """甲戌旬仪己落坤二:己自击刑(己→坤2)保留,甲墓撤后不再刑墓并。"""
        pan = cast(datetime(2026, 1, 1, 0, 30))
        flags = detect_flags(pan)
        kun2 = {
            (sf.stem, sf.layer): sf.flags for sf in flags.palaces[2].stem_flags
        }
        assert kun2.get(("己", "天")) == ("击刑",)
        assert kun2.get(("己", "地")) == ("击刑",)


class TestFuYinFanYin:
    """伏吟/反吟标记(detect-patterns 缩窄方案;格局层留扩展点,师门Q3)。"""

    def test_jia_hour_pan_is_fu_yin(self) -> None:
        """甲时值符值使归位 → 全盘伏吟(星皆居本宫)。"""
        # fuyin fixture 案例之一: 2026-01-05 00:10(甲子时)
        pan = cast(datetime(2026, 1, 5, 0, 10))
        assert pan.hour_cyl % 10 == 0  # 甲时
        flags = detect_flags(pan)
        # 硬断言(review R4-F4):此前条件守卫包住全部伏吟断言——caster 若回归
        # 使该日期 sgg≠dgg,测试体静默跳过而非失败。前提就是结论的一部分。
        assert pan.sgg == pan.dgg and pan.mgg == pan.dgg
        assert flags.pan_fu_yin
        for gong in range(1, 10):
            if gong != 5:
                assert flags.palaces[gong].xing_fu_yin
                assert flags.palaces[gong].gan_fu_yin

    def test_pan_fan_yin_full_chain(self) -> None:
        """全盘反吟 True 路径(review R4-F3:此前反吟零覆盖——OPPOSITE 表写错
        一个键,九步 SOP Step 0 风向标整体翻转而测试全绿)。

        2026-01-01 07:30(庚辰时)实证为全盘反吟盘:九星皆居对宫。
        干反吟(R2-F1 补层,精微录:干反吟影响大)同链断言。
        """
        pan = cast(datetime(2026, 1, 1, 7, 30))
        flags = detect_flags(pan)
        assert flags.pan_fan_yin
        assert not flags.pan_fu_yin
        for gong in range(1, 10):
            if gong != 5:
                assert flags.palaces[gong].xing_fan_yin
                assert flags.palaces[gong].gan_fan_yin

    def test_normal_pan_not_fu_yin(self) -> None:
        pan = cast(datetime(2026, 7, 4, 15, 20))
        flags = detect_flags(pan)
        assert not flags.pan_fu_yin
        assert not flags.pan_fan_yin
        assert not any(
            flags.palaces[g].gan_fan_yin for g in range(1, 10) if g != 5
        )

    def test_pattern_detectors_registered_by_geju(self) -> None:
        """M3 格局批:geju.py import 即注册三组检测器(正格/辅格/常用吉凶格)。

        (v1 时此测断言扩展点为空;格局层落地后翻转——详测 test_qimen_geju.py)"""
        from qimen_engine import (
            PATTERN_DETECTORS,
            run_pattern_detectors,
        )

        assert set(PATTERN_DETECTORS) == {"正格", "辅格", "常用吉凶格"}
        pan = cast(datetime(2026, 7, 4, 15, 20))
        hits = run_pattern_detectors(pan, detect_flags(pan))
        assert hits and all(
            {"detector", "gong", "name", "kind", "pair"} <= set(h) for h in hits
        )


class TestWangShui:
    """wangshui-calc 死规则:当令旺/令生相/生令休/克令囚/令克死。"""

    def test_summer_fire_month(self) -> None:
        # 午月(火令): 火旺 土相 木休 水囚 金死
        assert wang_shuai("火", "午") == "旺"
        assert wang_shuai("土", "午") == "相"
        assert wang_shuai("木", "午") == "休"
        assert wang_shuai("水", "午") == "囚"
        assert wang_shuai("金", "午") == "死"

    def test_earth_months(self) -> None:
        for branch in ("辰", "未", "戌", "丑"):
            assert wang_shuai("土", branch) == "旺"
            assert wang_shuai("金", branch) == "相"

    def test_element_of_symbols(self) -> None:
        assert element_of("天蓬") == "水"
        assert element_of("蓬") == "水"
        assert element_of("休门") == "水"
        assert element_of("值符") == "土"
        assert element_of("庚") == "金"
        assert element_of("天禽") == "土"
        assert element_of("不存在") is None

    def test_sheng_ke(self) -> None:
        assert sheng_ke("木", "火") == "生"
        assert sheng_ke("木", "土") == "克"
        assert sheng_ke("木", "水") == "被生"
        assert sheng_ke("木", "金") == "被克"
        assert sheng_ke("木", "木") == "比和"


class TestChartContract:
    """Chart JSON v1 契约。"""

    def test_schema_and_school_line(self) -> None:
        pan = cast(datetime(2026, 7, 4, 15, 20))
        chart = build_chart(
            pan, cast_time=datetime(2026, 7, 4, 15, 20), time_source="auto"
        )
        assert chart["schema"] == "qimen_chart_v1"
        assert chart["school"].startswith("阴盘奇门")  # §3.8-5 多流派歧义防御
        assert chart["input"]["true_solar_corrected"] is False  # O-3 缺省

    def test_chart_is_json_serializable(self) -> None:
        import json

        pan = cast(datetime(2026, 7, 4, 15, 20))
        chart = build_chart(
            pan, cast_time=datetime(2026, 7, 4, 15, 20), time_source="auto"
        )
        json.dumps(chart, ensure_ascii=False)

    def test_chart_elements_for_citation(self) -> None:
        """verify-citation 回查用要素集:神/星/门/三层干/四害。"""
        pan = cast(datetime(2026, 7, 4, 15, 20))
        chart = build_chart(
            pan, cast_time=datetime(2026, 7, 4, 15, 20), time_source="auto"
        )
        for gong in range(1, 10):
            elems = chart_elements(chart, gong)
            p = chart["palaces"][str(gong)]
            if gong != 5:
                assert p["god"] in elems
                assert p["door"] in elems
            for s in p["earth_stems"]:
                assert s in elems

    def test_zixuan_ju_flagged(self) -> None:
        pan = cast(datetime(2026, 7, 4, 15, 20), ju_override=("阴", 3))
        assert pan.zixuan and pan.dun == "阴" and pan.ju == 3
