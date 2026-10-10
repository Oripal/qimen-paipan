"""格局层 — 第十二章特殊格局(正格9类/辅格25格/常用吉凶格15)+ 时辰级三时禁。

来源 SoT:《道家阴盘奇门遁甲》第十二章(corpora/qimen-daojia-yinpan/
道家阴盘奇门遁甲.md 行1327-1505)。识别条件逐字照书——全部为天地盘干对照表
(辅格另乘落宫组),机械可判;书没写的不发明(正冲/背冲格原文仅列 4 对,照录
不补全)。断语**不进 engine**——进 facts(facts_entries.json domain=格局/时禁),
引擎只产命中标记,LLM 经 facts-query 取断语(与四害同一双职能模式)。

- 正格 9 类(§1,行1329-1366):进/退格(天地盘同五行顺/逆向)、前间/后间格
  (顺/逆隔一位;前间格附「查中间干落宫找受阻原因」解读步)、上合/下合格
  (五合顺/逆)、正冲/背冲格(天克地/地克天)、支破格(六仪暗支相冲 6 对)。
- 辅格 25 格(§2,行1370-1440):同五行干对(两序)×落宫组矩阵(五行各 5 格)。
- 常用吉凶格 15(§6,行1490-1505):吉 7 凶 8;龙返首附加条件(忌落震宫击刑、
  离宫子午相冲)同为机械判,命中时在 hit 带 note。
- 三时禁(§3-5,行1444-1486):五不遇时/入墓时/击刑时——时柱级全局凶时 flags,
  与宫位级击刑/入墓(sihai.JI_XING/RU_MU)显式区分命名(*_SHI 表 / shi_* 键)。

吉凶不加权不排序(格局×四害权重待师门,Q3 注记)——检测器并列输出全部命中;
同一干对可同时命中多层(如 丁+癸 = 背冲格 + 朱雀投江),照书并列。
检测器签名 (Pan, ChartFlags) 满足 sihai.PatternDetector;本模块 import 即注册。
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from typing import Final

from qimen_engine.calendar import cyclical
from qimen_engine.caster import Pan
from qimen_engine.data_tables import GAN
from qimen_engine.sihai import PATTERN_DETECTORS, ChartFlags

Hit = dict[str, object]

# ---- 正格 9 类(§1):(天盘干, 地盘干) → 格名 ----
ZHENG_GE: Final[dict[tuple[str, str], str]] = {
    # 进格:甲+乙、丙+丁、戊+己、庚+辛、壬+癸(顺向排列)
    ("甲", "乙"): "进格", ("丙", "丁"): "进格", ("戊", "己"): "进格",
    ("庚", "辛"): "进格", ("壬", "癸"): "进格",
    # 退格:乙+甲、丁+丙、己+戊、辛+庚、癸+壬(逆向排列)
    ("乙", "甲"): "退格", ("丁", "丙"): "退格", ("己", "戊"): "退格",
    ("辛", "庚"): "退格", ("癸", "壬"): "退格",
    # 前间格:甲+丙、乙+丁、丙+戊、丁+己、戊+庚、己+辛、庚+壬、辛+癸、壬+甲、癸+乙(顺向隔一位)
    ("甲", "丙"): "前间格", ("乙", "丁"): "前间格", ("丙", "戊"): "前间格",
    ("丁", "己"): "前间格", ("戊", "庚"): "前间格", ("己", "辛"): "前间格",
    ("庚", "壬"): "前间格", ("辛", "癸"): "前间格", ("壬", "甲"): "前间格",
    ("癸", "乙"): "前间格",
    # 后间格:甲+壬、乙+癸、丙+甲、丁+乙、戊+丙、己+丁、庚+戊、辛+己、壬+庚、癸+辛(逆向隔一位)
    ("甲", "壬"): "后间格", ("乙", "癸"): "后间格", ("丙", "甲"): "后间格",
    ("丁", "乙"): "后间格", ("戊", "丙"): "后间格", ("己", "丁"): "后间格",
    ("庚", "戊"): "后间格", ("辛", "己"): "后间格", ("壬", "庚"): "后间格",
    ("癸", "辛"): "后间格",
    # 上合格:甲+己、乙+庚、丙+辛、丁+壬、戊+癸(天干五合顺向)
    ("甲", "己"): "上合格", ("乙", "庚"): "上合格", ("丙", "辛"): "上合格",
    ("丁", "壬"): "上合格", ("戊", "癸"): "上合格",
    # 下合格:己+甲、庚+乙、辛+丙、壬+丁、癸+戊(天干五合逆向)
    ("己", "甲"): "下合格", ("庚", "乙"): "下合格", ("辛", "丙"): "下合格",
    ("壬", "丁"): "下合格", ("癸", "戊"): "下合格",
    # 正冲格:庚+甲、辛+乙、壬+丙、癸+丁(天盘克地盘;原文 4 对照录,不补全)
    ("庚", "甲"): "正冲格", ("辛", "乙"): "正冲格", ("壬", "丙"): "正冲格",
    ("癸", "丁"): "正冲格",
    # 背冲格:甲+庚、乙+辛、丙+壬、丁+癸(地盘克天盘;原文 4 对照录,不补全)
    ("甲", "庚"): "背冲格", ("乙", "辛"): "背冲格", ("丙", "壬"): "背冲格",
    ("丁", "癸"): "背冲格",
    # 支破格:戊+辛、己+壬、庚+癸、辛+戊、壬+己、癸+庚(六仪暗藏的地支相冲)
    ("戊", "辛"): "支破格", ("己", "壬"): "支破格", ("庚", "癸"): "支破格",
    ("辛", "戊"): "支破格", ("壬", "己"): "支破格", ("癸", "庚"): "支破格",
}

# ---- 辅格 25 格(§2):同五行干对(两序均可)× 落宫 → 格名 ----
FU_GE: Final[dict[frozenset[str], dict[int, str]]] = {
    # 一、木行辅格(甲、乙木组合)
    frozenset({"甲", "乙"}): {
        3: "曲直格", 4: "曲直格",  # 落震、巽宫
        1: "温润格",               # 落坎宫
        2: "创兴格", 8: "创兴格",  # 落坤、艮宫
        6: "伐木格", 7: "伐木格",  # 落乾、兑宫
        9: "焚木格",               # 落离宫
    },
    # 二、火行辅格(丙、丁火组合)
    frozenset({"丙", "丁"}): {
        9: "炎上格",
        1: "减光格",
        2: "晦光格", 8: "晦光格",
        3: "增辉格", 4: "增辉格",
        6: "门讼格", 7: "门讼格",
    },
    # 三、土行辅格(戊、己土组合)
    frozenset({"戊", "己"}): {
        2: "稼穑格", 8: "稼穑格",
        1: "迫水格",
        3: "倾陷格", 4: "倾陷格",
        6: "精尽格", 7: "精尽格",
        9: "转机格",
    },
    # 四、金行辅格(庚、辛金组合)
    frozenset({"庚", "辛"}): {
        6: "从革格", 7: "从革格",
        1: "泄耗格",
        2: "扬威格", 8: "扬威格",
        3: "交战格", 4: "交战格",
        9: "抑格",
    },
    # 五、水行辅格(壬、癸水组合)
    frozenset({"壬", "癸"}): {
        1: "润下格",
        2: "减绝格", 8: "减绝格",
        3: "枯竭格", 4: "枯竭格",
        6: "津润格", 7: "津润格",
        9: "冲激格",
    },
}

# ---- 常用吉凶格 15(§6):(天盘干, 地盘干) → (格名, 吉|凶);格名照书原字 ----
# (书写「鸟跌穴/龙返首/蛇夭矫」,通行别称「飞鸟跌穴/青龙返首/腾蛇夭矫」不采,照书)
JI_XIONG_GE: Final[dict[tuple[str, str], tuple[str, str]]] = {
    # 一、常用吉格(7)
    ("丙", "戊"): ("鸟跌穴", "吉"),
    ("戊", "丙"): ("龙返首", "吉"),  # 但忌落震宫击刑、离宫子午相冲(命中带 note)
    ("丁", "戊"): ("青龙转光", "吉"),
    ("戊", "丁"): ("青龙耀明", "吉"),
    ("乙", "丙"): ("奇仪顺遂", "吉"),
    ("丙", "乙"): ("日月并行", "吉"),
    ("乙", "丁"): ("奇仪相佐", "吉"),
    # 二、常用凶格(8)
    ("乙", "辛"): ("青龙逃走", "凶"),
    ("辛", "乙"): ("白虎猖狂", "凶"),
    ("丁", "癸"): ("朱雀投江", "凶"),
    ("癸", "丁"): ("蛇夭矫", "凶"),
    ("丙", "庚"): ("荧入太白", "凶"),
    ("戊", "庚"): ("值符飞宫", "凶"),
    ("癸", "癸"): ("天网四张", "凶"),
    ("庚", "癸"): ("大格", "凶"),  # 寅申相冲百事皆凶
}


def _pairs(tian: Sequence[str], di: Sequence[str]) -> Iterator[tuple[str, str]]:
    """双干宫逐干组合(天盘干 × 地盘干 全积;去重防御双列重干)。"""
    seen: set[tuple[str, str]] = set()
    for t in tian:
        for d in di:
            if (t, d) not in seen:
                seen.add((t, d))
                yield t, d


def zheng_ge_hits(gong: int, tian: Sequence[str], di: Sequence[str]) -> list[Hit]:
    """正格命中(§1)。前间格附解读步 note(书:查中间干落宫寻受阻原因)。"""
    hits: list[Hit] = []
    for t, d in _pairs(tian, di):
        name = ZHENG_GE.get((t, d))
        if name is None:
            continue
        hit: Hit = {"gong": gong, "name": name, "kind": "正格", "pair": f"天{t}+地{d}"}
        if name == "前间格":
            mid = GAN[(GAN.index(t) + 1) % 10]
            hit["note"] = f"中间干为{mid}——书:需查看夹在中间的那个天干落宫以寻找受阻原因"
        hits.append(hit)
    return hits


def fu_ge_hits(gong: int, tian: Sequence[str], di: Sequence[str]) -> list[Hit]:
    """辅格命中(§2):同五行干对(两序)×落宫组;书无中宫组,中宫恒不中。"""
    hits: list[Hit] = []
    for t, d in _pairs(tian, di):
        if t == d:
            continue  # 辅格为两干组合(甲+乙/乙+甲 等),同干不成对
        name = FU_GE.get(frozenset({t, d}), {}).get(gong)
        if name is None:
            continue
        hits.append({"gong": gong, "name": name, "kind": "辅格", "pair": f"天{t}+地{d}"})
    return hits


def ji_xiong_ge_hits(gong: int, tian: Sequence[str], di: Sequence[str]) -> list[Hit]:
    """常用吉凶格命中(§6)。龙返首书注条件(震宫击刑/离宫子午相冲)机械判进 note。"""
    hits: list[Hit] = []
    for t, d in _pairs(tian, di):
        entry = JI_XIONG_GE.get((t, d))
        if entry is None:
            continue
        name, kind = entry
        hit: Hit = {"gong": gong, "name": name, "kind": kind, "pair": f"天{t}+地{d}"}
        if name == "龙返首":
            if gong == 3:
                hit["note"] = "书注「忌落震宫击刑」命中:本盘即落震宫(戊落震三宫为击刑)"
            elif gong == 9:
                hit["note"] = "书注「忌离宫子午相冲」命中:本盘即落离宫(戊暗支子与离宫午相冲)"
        hits.append(hit)
    return hits


def palace_geju_hits(gong: int, tian: Sequence[str], di: Sequence[str]) -> list[Hit]:
    """单宫全部格局命中(正格+辅格+吉凶格并列;不加权不排序)。"""
    return (
        zheng_ge_hits(gong, tian, di)
        + fu_ge_hits(gong, tian, di)
        + ji_xiong_ge_hits(gong, tian, di)
    )


_Scanner = Callable[[int, Sequence[str], Sequence[str]], list[Hit]]


def _pan_hits(pan: Pan, scanner: _Scanner) -> list[Hit]:
    hits: list[Hit] = []
    for gong in range(1, 10):
        if gong == 5:
            continue  # 中宫无天盘干,格局不判(中宫干寄坤二,已含在坤二地盘干对中)
        hits.extend(scanner(gong, pan.tiangan[gong], pan.digan[gong]))
    return hits


def detect_zheng_ge(pan: Pan, flags: ChartFlags) -> list[Hit]:
    """正格检测器(PatternDetector 签名;正格纯干对照表,flags 不参与)。"""
    del flags
    return _pan_hits(pan, zheng_ge_hits)


def detect_fu_ge(pan: Pan, flags: ChartFlags) -> list[Hit]:
    """辅格检测器(PatternDetector 签名;干对×落宫组,flags 不参与)。"""
    del flags
    return _pan_hits(pan, fu_ge_hits)


def detect_ji_xiong_ge(pan: Pan, flags: ChartFlags) -> list[Hit]:
    """常用吉凶格检测器(PatternDetector 签名;干对照表,flags 不参与)。"""
    del flags
    return _pan_hits(pan, ji_xiong_ge_hits)


# import 即注册(engine/__init__ 导入本模块保证生效)
PATTERN_DETECTORS["正格"] = detect_zheng_ge
PATTERN_DETECTORS["辅格"] = detect_fu_ge
PATTERN_DETECTORS["常用吉凶格"] = detect_ji_xiong_ge


# ---- 时辰级三时禁(§3-5)——时柱级全局凶时,与宫位级四害显式区分命名 ----

# 五不遇时对照表(§3,行1451-1463):日干 → 凶时(时柱干支);时干克日干且同阴阳
WU_BU_YU_SHI: Final[dict[str, str]] = {
    # 阳干克阳干
    "甲": "庚午", "丙": "壬辰", "戊": "甲寅", "庚": "丙子", "壬": "戊申",
    # 阴干克阴干
    "乙": "辛巳", "丁": "癸卯", "己": "乙丑", "辛": "丁酉", "癸": "己未",
}

# 入墓时(§4):当下时辰干支入墓(与具体奇门盘无关)
SAN_QI_RU_MU_SHI: Final[frozenset[str]] = frozenset({"丙戌", "丁丑"})
LIU_YI_RU_MU_SHI: Final[frozenset[str]] = frozenset({"戊戌", "己丑", "壬辰", "癸未"})
RU_MU_SHI: Final[frozenset[str]] = SAN_QI_RU_MU_SHI | LIU_YI_RU_MU_SHI

# 击刑时(§5):时辰与当值旬首构成相刑(书列固定清单,照录)
JI_XING_SHI: Final[frozenset[str]] = frozenset({"己未", "庚寅", "壬辰", "癸巳"})

# 人读标签(detect-patterns 盘头行用;描述语照书§3-5)
SHI_JIN_LABELS: Final[tuple[tuple[str, str, str], ...]] = (
    ("wu_bu_yu_shi", "五不遇时", "时干克日干,奇门择日之大忌,百事皆凶"),
    ("shi_ru_mu", "入墓时", "时辰干支入墓,百事不宜,人事物功能无法发挥"),
    ("shi_ji_xing", "击刑时", "时辰与当值旬首相刑,寸步难行"),
)


def shi_jin_flags(day_ganzhi: str, hour_ganzhi: str) -> dict[str, bool]:
    """时辰级三时禁 flags(键名与宫位级四害区分:shi_* / *_SHI)。

    day_ganzhi/hour_ganzhi 为日柱/时柱干支(如 "甲申"/"庚午")——与 Chart JSON
    pillars 同形态,旧盘(无 "shi_jin" 键)可从四柱现算,结果确定同源。
    """
    return {
        "wu_bu_yu_shi": WU_BU_YU_SHI.get(day_ganzhi[:1]) == hour_ganzhi,
        "shi_ru_mu": hour_ganzhi in RU_MU_SHI,
        "shi_ji_xing": hour_ganzhi in JI_XING_SHI,
    }


def shi_jin_from_pan(pan: Pan) -> dict[str, bool]:
    """从排盘结果取三时禁 flags(日柱/时柱为 SoT,含子时换日后的换日柱)。"""
    return shi_jin_flags(cyclical(pan.day_cyl), cyclical(pan.hour_cyl))
