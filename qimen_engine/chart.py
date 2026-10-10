"""Chart JSON v1 组装 — 排盘结果的对外数据契约(m-drive 落库形态)。

字段完备性参照设计 §3.8「Chart JSON 字段 checklist」(3meta Palace 类型对照):
神/星/门/天地盘干/暗干/寄宫/值符值使/四害/旬空/马星/四柱/节气。
全部标注由结构化字段驱动(确定性代码产 flags,LLM 只搬运),
排盘图模板与 facts-query 均纯消费本结构。

命名:对外一律全名(值符/腾蛇/天蓬/休门),与 facts 词表 canonical 对齐;
内部短名(iqm.js 位序形态)只存在于 caster/golden 对比层。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from qimen_engine.calendar import cyclical, s_term
from qimen_engine.caster import Pan
from qimen_engine.data_tables import SOLAR_TERM, ZHI
from qimen_engine.geju import (
    palace_geju_hits,
    shi_jin_flags,
    shi_jin_from_pan,
)
from qimen_engine.mingju import (
    da_yun_forward,
    da_yun_sequence,
    ming_gong,
    ping_tai_gong,
    qi_yun_age,
)
from qimen_engine.sihai import ChartFlags, detect_flags

CHART_SCHEMA = "qimen_chart_v1"
SCHOOL_LINE = "阴盘奇门 · 时家 · 转盘"

GONG_NAMES = {
    1: "坎一", 2: "坤二", 3: "震三", 4: "巽四", 5: "中五",
    6: "乾六", 7: "兑七", 8: "艮八", 9: "离九",
}
# facts 键词汇的宫位形态(宝典按修订约定统一写「X宫」;中宫寄坤,facts 无中宫键)
GONG_KEY_NAMES = {
    1: "坎宫", 2: "坤宫", 3: "震宫", 4: "巽宫",
    6: "乾宫", 7: "兑宫", 8: "艮宫", 9: "离宫",
}

# ── 九宫名归一(F2b,QM-EV2)──────────────────────────────────────────────
# 断语引用/宫名对账时,agent 写宫名的形态五花八门:宫名+数字(震三)/宫名+数字
# +宫(震三宫)/裸卦名(震)/数字+宫(三宫)/已 canonical 的 GONG_KEY 形(震宫)。
# 全部归一到 chart_elements 落的宫名形态 GONG_KEY_NAMES(「X宫」),否则师门断语的
# 落宫回查在 elements 路径恒不命中(QM-EV2 dogfood 7db6736e:「震三宫」不在 3 宫
# 实况)。**中五寄坤二**(GONG_KEY_NAMES 无 5 键、facts 无中宫键)→ 中宫一族别名
# 一律归坤宫。verify-citation 与任何宫名对账处共用此归一。
_GONG_TRIGRAM = {1: "坎", 2: "坤", 3: "震", 4: "巽", 5: "中",
                 6: "乾", 7: "兑", 8: "艮", 9: "离"}
_GONG_NUMERAL = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五",
                 6: "六", 7: "七", 8: "八", 9: "九"}


def _build_gong_name_aliases() -> dict[str, str]:
    """九宫全别名 → GONG_KEY_NAMES 宫名形态(中五寄坤宫)。"""
    aliases: dict[str, str] = {}
    for g in range(1, 10):
        canon = GONG_KEY_NAMES.get(g) or GONG_KEY_NAMES[2]  # 中五(g=5)寄坤宫
        tri, num, full = _GONG_TRIGRAM[g], _GONG_NUMERAL[g], GONG_NAMES[g]
        for form in (tri, f"{tri}宫", full, f"{full}宫", f"{num}宫",
                     f"{tri}{num}", f"{tri}{num}宫"):
            aliases[form] = canon
    for form in ("中宫", "中五宫"):  # 中宫特称(寄坤二)
        aliases[form] = GONG_KEY_NAMES[2]
    return aliases


PALACE_NAME_ALIASES: dict[str, str] = _build_gong_name_aliases()


def normalize_gong_name(raw: str) -> str:
    """九宫别名归一到 chart_elements 宫名形态(GONG_KEY_NAMES「X宫」;中五寄坤宫)。
    非宫名字符串原样返回(strip 后)。"""
    s = raw.strip()
    return PALACE_NAME_ALIASES.get(s, s)

GOD_FULL = {
    "符": "值符", "蛇": "腾蛇", "阴": "太阴", "六": "六合",
    "白": "白虎", "玄": "玄武", "地": "九地", "天": "九天",
}
STAR_FULL = {
    "蓬": "天蓬", "任": "天任", "冲": "天冲", "辅": "天辅", "英": "天英",
    "芮": "天芮", "柱": "天柱", "心": "天心", "禽": "天禽",
}
DOOR_FULL = {
    "休": "休门", "生": "生门", "伤": "伤门", "杜": "杜门",
    "景": "景门", "死": "死门", "惊": "惊门", "开": "开门",
}


def _term_time_str(year: int, term_idx: int, before: datetime) -> tuple[str, str]:
    """当前节气名+交气时刻(交气必不晚于参考点;跨年时取上一年)。"""
    t = s_term(year, term_idx)
    if t > before:
        t = s_term(year - 1, term_idx)
    return SOLAR_TERM[term_idx], t.strftime("%Y-%m-%d %H:%M")


def build_chart(
    pan: Pan,
    *,
    cast_time: datetime,
    time_source: str,
    tz: str = "Asia/Shanghai",
    lng: float | None = None,
    matter: str = "",
) -> dict[str, Any]:
    """Pan → Chart JSON v1(dict,JSON 可序列化)。

    time_source ∈ {"auto", "explicit", "user_confirmed"}(O-3 三态)。
    lng 缺省 None = 不做真太阳时修正(O-3,报告须声明)。
    """
    flags = detect_flags(pan)
    # 节气跨年判定必须用换日后的有效时刻(pan.effective_dt):term_current 是按
    # 它取的,23:5x 起局撞上交气窗口时用 cast_time 会把交气时刻错报成上一年。
    eff = pan.effective_dt
    prev_name, prev_at = _term_time_str(eff.year, pan.term_current, eff)
    next_name, next_at = _next_term(eff, pan)

    palaces: dict[str, Any] = {}
    for gong in range(1, 10):
        pf = flags.palaces[gong]
        stars = []
        if gong != 5 and pan.xinpan[gong]:
            stars.append(STAR_FULL[pan.xinpan[gong]])
            if pan.xinpan[gong] == "芮":
                stars.append("天禽")  # D1: 天禽随天芮(co_star)
        entry: dict[str, Any] = {
            "name": GONG_NAMES[gong],
            "god": GOD_FULL.get(pan.shenpan[gong], "") if gong != 5 else "",
            "stars": stars,
            "door": DOOR_FULL.get(pan.menpan[gong], "") if gong != 5 else "",
            "heaven_stems": list(pan.tiangan[gong]) if gong != 5 else [],
            "earth_stems": list(pan.digan[gong]),
            "hidden_stems": list(pan.angan[gong]) if gong != 5 else [],
            "is_ji_gong_host": gong == 2,  # 坤二承寄(中宫干/暗干寄入)
            "flags": {
                "si_hai": pf.si_hai,
                "stem_flags": [
                    {"stem": sf.stem, "layer": sf.layer, "flags": list(sf.flags)}
                    for sf in pf.stem_flags
                ],
                "men_po": pf.men_po,
                "kong_shi": pf.kong_shi,
                "ma": pf.ma,
                "xing_fu_yin": pf.xing_fu_yin,
                "xing_fan_yin": pf.xing_fan_yin,
                "men_fu_yin": pf.men_fu_yin,
                "men_fan_yin": pf.men_fan_yin,
                "gan_fu_yin": pf.gan_fu_yin,
                "gan_fan_yin": pf.gan_fan_yin,
            },
        }
        palaces[str(gong)] = entry

    return {
        "schema": CHART_SCHEMA,
        "school": SCHOOL_LINE,
        "input": {
            "cast_time": cast_time.strftime("%Y-%m-%d %H:%M"),
            "tz": tz,
            "time_source": time_source,
            "lng": lng,
            "true_solar_corrected": False,  # O-3: 缺省不修正,报告声明
            "matter": matter,
        },
        "lunar": {
            "year": pan.lunar.year,
            "month": pan.lunar.month,
            "day": pan.lunar.day,
            "is_leap": pan.lunar.is_leap,
        },
        "pillars": {
            "year": cyclical(pan.year_cyl),
            "month": cyclical(pan.mon_cyl),
            "day": cyclical(pan.day_cyl),
            "hour": cyclical(pan.hour_cyl),
        },
        "jieqi": {
            "current": prev_name,
            "current_at": prev_at,
            "next": next_name,
            "next_at": next_at,
        },
        "yue_jiang": ZHI[11 - pan.jiang],
        "ju": {"dun": pan.dun, "number": pan.ju, "zixuan": pan.zixuan},
        "xun": {
            "shou": cyclical(pan.xun_shou),
            "kong_zhi": [ZHI[z] for z in pan.xun_kong_zhi],
            "kong_gong": sorted(pan.kong_gongs),
            "ma_zhi": ZHI[pan.ma_zhi],
            "ma_gong": pan.ma_gong,
        },
        "zhi_fu": {"star": f"天{pan.zhifu_star}", "gong": pan.sgg},
        "zhi_shi": {"door": f"{pan.zhishi_men}门", "gong": pan.mgg},
        "pan_flags": {
            "fu_yin": flags.pan_fu_yin,
            "fan_yin": flags.pan_fan_yin,
            "an_gan_fuyin_special": pan.fuyin_special,
            "an_gan_fuyin_double": pan.fuyin_double,
        },
        # 时辰级三时禁(M3 additive 键;旧盘落库无此键——消费方经 chart_shi_jin
        # 容错取用,从四柱现算,确定同源)
        "shi_jin": shi_jin_from_pan(pan),
        "palaces": palaces,
    }


def build_mingpan_section(
    pan: Pan,
    *,
    birth_dt: datetime,
    gender: str,
    person: str = "",
    count: int = 8,
) -> dict[str, Any]:
    """命盘附加节(Chart JSON 顶层 "mingpan" 键,additive——时空局盘无此键)。

    定宫算法与书证见 mingju.py;本函数只组装 JSON 契约形态。
    命盘 = 出生时刻的时家局 + 本节 overlay(命宫/平台/起运/大运序列)。
    """
    forward = da_yun_forward(pan, gender)  # type: ignore[arg-type]
    raw, qiyun = qi_yun_age(birth_dt, forward=forward)
    mg = ming_gong(pan)
    pt = ping_tai_gong(pan)
    yuns = da_yun_sequence(pan, birth_dt, gender, count=count)  # type: ignore[arg-type]
    return {
        "person": person,
        "birth_time": birth_dt.strftime("%Y-%m-%d %H:%M"),
        "gender": gender,
        "ming_gong": mg,
        "ming_gong_name": GONG_NAMES[mg],
        "ping_tai_gong": pt,
        "ping_tai_gong_name": GONG_NAMES[pt],
        "da_yun_forward": forward,
        "qi_yun": {"raw_years": round(raw, 2), "age": qiyun},
        "da_yun": [
            {
                "ganzhi": cyclical(y.cyl),
                "gan": y.gan,
                "start_age": y.start_age,
                "end_age": y.end_age,
                "start_year": y.start_year,
                "gong": y.gong,
                "gong_name": GONG_NAMES[y.gong],
            }
            for y in yuns
        ],
    }


def _next_term(cast_time: datetime, pan: Pan) -> tuple[str, str]:
    year = cast_time.year
    t = s_term(year, pan.term_next)
    if t < cast_time:  # 跨年(冬至后段 → 次年小寒)
        t = s_term(year + 1, pan.term_next)
    return SOLAR_TERM[pan.term_next], t.strftime("%Y-%m-%d %H:%M")


def chart_elements(chart: dict[str, Any], gong: int) -> set[str]:
    """某宫的全部可引用要素(facts 键归一前的原始集,verify-citation 回查用)。

    命局概念词注入(2026-07-06,dogfood caa8ba5d 缺陷修复):facts 检索是
    entry.keys <@ query keys(条目键须为查询键子集),命局条目键含概念词
    (命宫/平台宫/本命星/照命星/值使门/五合/大运)——不注入则命局断语在
    verify-citation 宫位重放中恒不命中,引用闸形同虚设。注入按**锚宫**收窄:
    关系对词(本命星×照命星/命宫×值使/命宫×平台/五合)锚在主语宫=命宫;
    平台关系在平台宫对称补「命宫」;大运词进各运宫;值使门另在值使宫通用可引。

    格局/时禁词注入(M3 格局批,同一 rationale):格局 facts 条目 keys=[格名],
    命中宫注入格名(从宫内天地盘干现算,旧盘同样适用);三时禁为时柱级全局凶时
    (百事皆凶,全局修正),命中时注入**全部九宫**——不注入则断语在重放中恒不命中。
    """
    p = chart["palaces"][str(gong)]
    out: set[str] = set()
    if p["god"]:
        out.add(p["god"])
    out.update(p["stars"])
    if p["door"]:
        out.add(p["door"])
    out.update(p["heaven_stems"])
    out.update(p["earth_stems"])
    out.update(p["hidden_stems"])
    out.update(p["flags"]["si_hai"])
    if p["flags"]["ma"]:
        out.add("马星")
    if p["flags"]["kong_shi"]:
        out.add("空亡")
    if gong in GONG_KEY_NAMES:
        out.add(GONG_KEY_NAMES[gong])  # 宝典条目以「X宫」为键(qimen-baodian 词汇)

    out.update(str(h["name"]) for h in chart_pattern_hits(chart, gong))
    sj = chart_shi_jin(chart)
    for flag_key, name in (
        ("wu_bu_yu_shi", "五不遇时"), ("shi_ru_mu", "入墓时"), ("shi_ji_xing", "击刑时"),
    ):
        if sj.get(flag_key):
            out.add(name)

    if gong == chart["zhi_shi"]["gong"]:
        out.add("值使门")  # 概念词(门名之外);时空局命局通用
    mp = chart.get("mingpan")
    if mp:
        if gong == mp["ming_gong"]:
            out.update({"命宫", "本命星", "照命星", "值使门", "平台宫", "五合"})
        if gong == mp["ping_tai_gong"]:
            out.update({"平台宫", "命宫"})
        if any(y["gong"] == gong for y in mp["da_yun"]):
            out.add("大运")
    return out


def pan_elements(chart: dict[str, Any]) -> set[str]:
    """盘级可引用词表(verify-citation gong=0 盘级引用的校验对象)。

    F批 2026-07-06:全盘伏吟/全盘反吟、三时禁这类**盘级断言**的 facts 条目
    键不属于任何一宫,旧回查强迫它们錨到某宫 → 恒不命中 → 模型猜谜循环。
    盘级词表 = 全盘伏/反吟命中词(含「伏吟」「反吟」短词)+ 三时禁命中词
    + 遁局名(如「阴遁6局」)。条目键 ⊆ 本词表即 PASS。
    """
    out: set[str] = set()
    pf = chart["pan_flags"]
    if pf["fu_yin"]:
        out.update({"全盘伏吟", "伏吟"})
    if pf["fan_yin"]:
        out.update({"全盘反吟", "反吟"})
    sj = chart_shi_jin(chart)
    for flag_key, name in (
        ("wu_bu_yu_shi", "五不遇时"), ("shi_ru_mu", "入墓时"), ("shi_ji_xing", "击刑时"),
    ):
        if sj.get(flag_key):
            out.add(name)
    ju = chart["ju"]
    out.add(f"{ju['dun']}遁{ju['number']}局")
    return out


def detect_chart_flags(pan: Pan) -> ChartFlags:
    """暴露给 detect-patterns 工具的入口(与 build_chart 同一 flags 来源)。"""
    return detect_flags(pan)


def chart_shi_jin(chart: dict[str, Any]) -> dict[str, bool]:
    """盘的时辰级三时禁 flags。

    新盘直读落库的 "shi_jin" 键;旧盘(M3 前落库,write-once 无此键)从四柱
    (pillars.day/hour)现算——geju.shi_jin_flags 是纯查表,两路确定同源。
    """
    sj = chart.get("shi_jin")
    if isinstance(sj, dict):
        return {k: bool(v) for k, v in sj.items()}
    return shi_jin_flags(chart["pillars"]["day"], chart["pillars"]["hour"])


def chart_pattern_hits(chart: dict[str, Any], gong: int) -> list[dict[str, object]]:
    """某宫的格局命中(正格/辅格/常用吉凶格,从落库盘面的天地盘干现算)。

    纯函数(宫内天地盘干 → 命中),不落库不缓存——新旧盘同一代码路径,
    与引擎级 run_pattern_detectors(吃 Pan)输出逐项一致(测试锚定)。
    """
    if gong == 5:
        return []  # 中宫无天盘干,格局不判
    p = chart["palaces"][str(gong)]
    return palace_geju_hits(gong, p["heaven_stems"], p["earth_stems"])
