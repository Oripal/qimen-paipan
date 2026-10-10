"""奇门引擎 golden 对比测试 — Python 移植 vs 原 iqm.js(师门可执行 SoT)。

fixtures 由 node 执行原 JS 生成(tests/fixtures/generate_golden.js,
TZ=Asia/Shanghai),覆盖:阴阳遁常规/节气分钟边界/子时换日/闰月/自选局/
全伏吟暗干特例(含二次重排)/值符=禽(旬首落中宫)。46 例逐宫逐层断言。

四害断言来自 DrawPaipan 配色解码(刑=#6F00D2 墓=#009100 刑墓=#EE00EE/#EA0000
门迫=<i> 空=◎),与《四害判定规格》的击刑/入墓/门迫/时空映射逐项对照。
「日空并标」为 D2 补齐项(原引擎无此层),在 test_qimen_sihai.py 单独测试。

节气表:本套件测的是**移植保真度**,所以整个模块把节气表换回 iqm.js 原表再比
(见 _lineage_jieqi_table)。引擎实际采用的表在 2010 年后做过校对,有意与 iqm.js
相差 1 分钟的条目(如 2026 立春)由 test_qimen_jieqi_table.py 单独覆盖。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from qimen_engine import calendar as qimen_calendar
from qimen_engine import cast, cyclical, detect_flags
from qimen_engine.data_tables import FINEDATE, ZHI

FIXTURE = Path(__file__).parent / "fixtures" / "golden_charts.json"


def _load_cases() -> list[dict[str, Any]]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert data["tz"] == "Asia/Shanghai"
    assert data["advance_minutes"] == 0
    return list(data["cases"])


CASES = _load_cases()


@pytest.fixture(autouse=True)
def _lineage_jieqi_table(monkeypatch: pytest.MonkeyPatch) -> None:
    """节气表换回 iqm.js 原表(1930-2030)——golden 由原引擎用它自己的表生成。"""
    monkeypatch.setattr(qimen_calendar, "_FINE_TABLE", FINEDATE)
    monkeypatch.setattr(qimen_calendar, "_FINE_LAST_YEAR", 2030)


def _ju_override(zxj: int | None) -> tuple[str, int] | None:
    """fixture 的 zxj 下标 → (遁, 局)。(iqm.js:551-558 语义)"""
    if zxj is None or zxj == -1:
        return None
    if zxj < 9:
        return ("阴", 9 - zxj)
    return ("阳", zxj - 8)


def _cast_case(case: dict[str, Any]):
    inp = case["input"]
    dt = datetime(inp["y"], inp["m"], inp["d"], inp["h"], inp["min"])
    return cast(dt, ju_override=_ju_override(inp.get("zxj")))


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_golden_header(case: dict[str, Any]) -> None:
    """局数/遁/四柱/农历/旬空/马星/值符值使 与原引擎一致。"""
    pan = _cast_case(case)
    assert pan.dun == case["dun"]
    assert pan.ju == case["ju"]
    assert pan.hour_cyl == case["h_cyl"]
    assert cyclical(pan.year_cyl) == case["pillars"]["year"]
    assert cyclical(pan.mon_cyl) == case["pillars"]["month"]
    assert cyclical(pan.day_cyl) == case["pillars"]["day"]
    assert cyclical(pan.hour_cyl) == case["pillars"]["hour"]
    assert pan.lunar.year == case["lunar"]["year"]
    assert pan.lunar.month == case["lunar"]["month"]
    assert pan.lunar.day == case["lunar"]["day"]
    assert pan.lunar.is_leap == case["lunar"]["is_leap"]
    assert cyclical(pan.xun_shou) == case["xun_shou"]
    assert [ZHI[z] for z in pan.xun_kong_zhi] == case["kong_zhi"]
    assert ZHI[pan.ma_zhi] == case["ma_zhi"]
    # 马星标位(review R4-F5:fixture 的 ma_gong_branches 此前 46 例全存零断言):
    # 原引擎 maw[b] 按支位 b 画「马」——JS 实画的支位必须恰等于引擎 ma_zhi,
    # 钉住「驿马表 → 标记支位」这条渲染前链路与 SoT 的一致性。
    assert set(case["ma_gong_branches"]) == {pan.ma_zhi}
    assert pan.jiang == case["jiang"]
    assert pan.dgg == case["dgg"]
    assert pan.mgg == case["mgg"]
    assert pan.zhifu_star == case["zhifu_star"]
    assert pan.sgg == case["zhifu_gong"]
    assert pan.zhishi_men == case["zhishi_men"]
    assert pan.mgg == case["zhishi_gong"]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_golden_palaces(case: dict[str, Any]) -> None:
    """九宫全六层(神/星/门/天盘干/地盘干/暗干)+ 时空亡 逐宫一致。"""
    pan = _cast_case(case)
    for gong_str, exp in case["palaces"].items():
        gong = int(gong_str)
        if gong == 5:
            assert pan.digan[5] == exp["di"], f"宫5地盘 {case['id']}"
            continue
        assert pan.shenpan[gong] == exp["shen"], f"宫{gong}神 {case['id']}"
        assert pan.xinpan[gong] == exp["xing"], f"宫{gong}星 {case['id']}"
        assert pan.menpan[gong] == exp["men"], f"宫{gong}门 {case['id']}"
        assert pan.tiangan[gong] == exp["tian"], f"宫{gong}天盘 {case['id']}"
        assert pan.digan[gong] == exp["di"], f"宫{gong}地盘 {case['id']}"
        assert pan.angan[gong] == exp["an"], f"宫{gong}暗干 {case['id']}"
        assert (gong in pan.kong_gongs) == exp["kong"], f"宫{gong}时空 {case['id']}"


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_golden_sihai(case: dict[str, Any]) -> None:
    """四害(击刑/入墓/门迫)与原引擎 DrawPaipan 配色语义逐干一致。

    jia_mu_xun_yi_at_kun=True = **vendor 保真闸**:fixture 由原 App 生成,
    含「旬首仪落坤=甲墓」标记(19/46 例命中)。师门 2026-07-06 已定生产不用
    该转承(缺省 False,见 test_qimen_sihai 的师门缺省测试)——此处开启仅为
    锚定移植保真,勿改回缺省。
    """
    pan = _cast_case(case)
    flags = detect_flags(pan, jia_mu_xun_yi_at_kun=True)
    for gong_str, exp in case["palaces"].items():
        gong = int(gong_str)
        pf = flags.palaces[gong]
        if gong != 5:
            assert pf.men_po == exp["men_po"], f"宫{gong}门迫 {case['id']}"
        # 逐层逐干对齐(fixture 的 flags 由配色解码;engine 的按规格判定)
        for layer, key in (("天", "tian_flags"), ("地", "di_flags")):
            if gong == 5 and key == "tian_flags":
                continue
            got = {
                (sf.stem, tuple(sorted(sf.flags)))
                for sf in pf.stem_flags
                if sf.layer == layer
            }
            want = {
                (e["stem"], tuple(sorted(e["flags"])))
                for e in exp[key]
                if e["flags"]
            }
            assert got == want, f"宫{gong}{layer}盘四害 {case['id']}: {got} != {want}"


def test_fixture_coverage() -> None:
    """fixture 类别覆盖完整(防基准文件被误删减)。"""
    cats = {c["category"] for c in CASES}
    assert {
        "normal", "term-boundary", "zishi", "leap-month",
        "zixuan", "fuyin-special", "qin-zhifu",
    } <= cats
    fuyin = [c for c in CASES if c["category"] == "fuyin-special"]
    assert {(c["dun"], "double" in c["id"]) for c in fuyin} == {
        ("阳", False), ("阳", True), ("阴", False), ("阴", True),
    }


def test_fuyin_special_flags_recorded() -> None:
    """全伏吟特例分支在 Pan 上留痕(双 Vobor 哨兵与 detect-patterns 消费)。"""
    for case in CASES:
        if case["category"] != "fuyin-special":
            continue
        pan = _cast_case(case)
        assert pan.fuyin_special, case["id"]
        assert pan.fuyin_double == ("double" in case["id"]), case["id"]
