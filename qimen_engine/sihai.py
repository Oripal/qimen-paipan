"""四害检测层 — 按《四害判定规格》(v2 D2)实现,与 iqm.js DrawPaipan 配色语义对齐。

规格四要素(v2 §6 D2):
- 门迫 13 项(含「休门落离算迫」默认)
- 击刑 6 项(戊震3/己坤2/庚艮8/辛离9/壬巽4/癸巽4)——此六项即师门「六仪击刑」
  (精微录第五章:天盘六仪加在与地盘相刑的宫位;三奇乙丙丁无旬首地支不成六仪击刑,
  故本表恒为六仪。Q3 门内用作凶格局,断语走 facts/精微录 prose)
- 入墓四维宫本墓表(乾6:乙丙戊 · 艮8:丁己庚 · 巽4:辛壬 · 坤2:癸)。
  原 App 另有「旬首仪落坤=甲墓」转承(iqm.js:917/974)——**师门 2026-07-06 定
  不用**(师傅:庚在未不入墓、在坤二宫不入墓;书面师门材料亦无此说),缺省关,
  仅 golden 以 jia_mu_xun_yi_at_kun=True 锚定 vendor 移植保真
- 旬空映射(时旬空)。原 D2「日空并标」补齐层已撤——师门裁定(Q21,2026-07-06
  师傅盘面纠偏「去掉日空」):门内只用时旬空;App/精微录/宝典均无日空层。
默认两项:天地盘皆标、休门落离算迫。

detect-patterns(设计 §3.9e 护栏②):伏吟/反吟标记+四害+空亡/马星+吉凶格局。
师门Q3 已定(2026-07-05)=门内用格局。已落地格局:伏吟/反吟(全盘/星/门/干)+
**六仪击刑**(=JI_XING 击刑标记,精微录第五章确认此六项即六仪击刑格局,断语见精微录
prose)。PATTERN_DETECTORS 具名格局层已由 M3 格局批填充(geju.py:第十二章
正格9类/辅格25格/常用吉凶格15,import 即注册;断语在 facts domain=格局)。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Final

from qimen_engine.caster import Pan
from qimen_engine.data_tables import FZHUAN, GAN, MEN, XING

# 六仪击刑 6 项: 干 → 落宫(精微录第五章;此确定性标记即六仪击刑格局的识别层,
# Q3 门内用作凶格局,断语在 facts/精微录 prose——引擎只标记不产断语)
JI_XING: Final[dict[str, int]] = {
    "戊": 3, "己": 2, "庚": 8, "辛": 9, "壬": 4, "癸": 4,
}

# 入墓四维宫十干表: 宫 → 入墓之干(甲另由旬首仪承载)
RU_MU: Final[dict[int, frozenset[str]]] = {
    6: frozenset({"乙", "丙", "戊"}),
    8: frozenset({"丁", "己", "庚"}),
    4: frozenset({"辛", "壬"}),
    2: frozenset({"癸"}),
}

# 门迫 13 项: 宫 → 迫门集(门克宫;含休门落离)
MEN_PO: Final[dict[int, frozenset[str]]] = {
    1: frozenset({"生", "死"}),
    2: frozenset({"伤", "杜"}),
    3: frozenset({"开", "惊"}),
    4: frozenset({"开", "惊"}),
    6: frozenset({"景"}),
    7: frozenset({"景"}),
    8: frozenset({"伤", "杜"}),
    9: frozenset({"休"}),
}

# 对宫(反吟位)
OPPOSITE: Final[dict[int, int]] = {1: 9, 9: 1, 2: 8, 8: 2, 3: 7, 7: 3, 4: 6, 6: 4}


@dataclass(frozen=True)
class StemFlag:
    stem: str
    layer: str  # "天" | "地"
    flags: tuple[str, ...]  # ⊆ ("击刑", "入墓")


@dataclass
class PalaceFlags:
    """单宫四害/动静标记(全部确定性代码产出,LLM 只搬运)。"""

    gong: int
    stem_flags: list[StemFlag] = field(default_factory=list)
    men_po: bool = False
    kong_shi: bool = False  # 时旬空(空亡唯一基准,Q21 师门已裁)
    ma: bool = False
    xing_fu_yin: bool = False  # 星伏吟(星落本宫)
    xing_fan_yin: bool = False  # 星反吟(星落对宫)
    men_fu_yin: bool = False
    men_fan_yin: bool = False
    gan_fu_yin: bool = False  # 干伏吟:天地盘干相同(主干比对)
    gan_fan_yin: bool = False  # 干反吟:天盘干落对宫(主干==对宫地盘主干);师门:干反吟影响大

    @property
    def si_hai(self) -> list[str]:
        """本宫命中的四害类目(facts-query requires_flags 词汇)。"""
        out: list[str] = []
        if any("击刑" in sf.flags for sf in self.stem_flags):
            out.append("击刑")
        if any("入墓" in sf.flags for sf in self.stem_flags):
            out.append("入墓")
        if self.men_po:
            out.append("门迫")
        if self.kong_shi:
            out.append("空亡")
        return out


@dataclass
class ChartFlags:
    palaces: dict[int, PalaceFlags]
    pan_fu_yin: bool  # 全盘伏吟(九星皆居本宫)
    pan_fan_yin: bool  # 全盘反吟(九星皆居对宫)


def stem_flags_for(
    stem: str, gong: int, xun_shou_yi: str, *, jia_mu_xun_yi_at_kun: bool = False,
) -> tuple[str, ...]:
    """单干落单宫的击刑/入墓标记。

    jia_mu_xun_yi_at_kun=原 App「旬首仪落坤=甲墓」转承(iqm.js:917/974)——
    **师门 2026-07-06 已定不用**(师傅:庚在未不入墓、在坤二宫不入墓;精微录/宝典
    亦无甲墓转承说法,十干只按本墓表 RU_MU)。缺省 False=师门行为;True 仅供
    golden 对 vendor 的移植保真锚定,生产不得开启。
    """
    flags: list[str] = []
    if JI_XING.get(stem) == gong:
        flags.append("击刑")
    if stem in RU_MU.get(gong, frozenset()):
        flags.append("入墓")
    elif (
        jia_mu_xun_yi_at_kun
        and gong == 2 and stem == xun_shou_yi and "入墓" not in flags
    ):
        flags.append("入墓")  # 原 App 甲墓转承(vendor 保真闸专用)
    return tuple(flags)


def detect_flags(pan: Pan, *, jia_mu_xun_yi_at_kun: bool = False) -> ChartFlags:
    """全盘四害+动静标记。天地盘皆标(D2 默认);中宫(5)不参与门/神层判定。

    jia_mu_xun_yi_at_kun 语义见 stem_flags_for——缺省 False=师门行为
    (2026-07-06 定:旬首仪落坤不按甲墓标墓),True 仅供 golden vendor 保真。
    """
    xun_shou_yi = GAN[pan.dg]
    palaces: dict[int, PalaceFlags] = {}
    fu_count = 0
    fan_count = 0

    for gong in range(1, 10):
        pf = PalaceFlags(gong=gong)
        if gong != 5:
            for stem in pan.tiangan[gong]:
                flags = stem_flags_for(
                    stem, gong, xun_shou_yi,
                    jia_mu_xun_yi_at_kun=jia_mu_xun_yi_at_kun,
                )
                if flags:
                    pf.stem_flags.append(StemFlag(stem, "天", flags))
        for stem in pan.digan[gong]:
            flags = stem_flags_for(
                stem, gong, xun_shou_yi,
                jia_mu_xun_yi_at_kun=jia_mu_xun_yi_at_kun,
            )
            if flags:
                pf.stem_flags.append(StemFlag(stem, "地", flags))
        if gong != 5:
            pf.men_po = pan.menpan[gong] in MEN_PO.get(gong, frozenset())
            home_xing = XING[FZHUAN[gong]]
            opp = OPPOSITE[gong]
            pf.xing_fu_yin = pan.xinpan[gong] == home_xing
            pf.xing_fan_yin = pan.xinpan[gong] == XING[FZHUAN[opp]]
            home_men = MEN[FZHUAN[gong]]
            pf.men_fu_yin = pan.menpan[gong] == home_men
            pf.men_fan_yin = pan.menpan[gong] == MEN[FZHUAN[opp]]
            pf.gan_fu_yin = bool(pan.tiangan[gong]) and (
                pan.tiangan[gong][0] == pan.digan[gong][0]
            )
            # 干反吟(伏吟/反吟为星/门/干三层;精微录:干反吟影响大、一时难成):
            # 天盘主干回到其地盘本位的对宫 ⇔ 天盘主干 == 对宫地盘主干。
            pf.gan_fan_yin = bool(pan.tiangan[gong]) and (
                pan.tiangan[gong][0] == pan.digan[opp][0]
            )
            fu_count += int(pf.xing_fu_yin)
            fan_count += int(pf.xing_fan_yin)
        pf.kong_shi = gong in pan.kong_gongs
        pf.ma = gong == pan.ma_gong
        palaces[gong] = pf

    return ChartFlags(
        palaces=palaces,
        pan_fu_yin=fu_count == 8,
        pan_fan_yin=fan_count == 8,
    )


# ---- 格局检测注册表(师门Q3 已定=用格局;M3 格局批由 geju.py 注册:
# 正格/辅格/常用吉凶格三组,import 即生效) ----
PatternDetector = Callable[[Pan, ChartFlags], list[dict[str, object]]]
PATTERN_DETECTORS: dict[str, PatternDetector] = {}


def run_pattern_detectors(pan: Pan, flags: ChartFlags) -> list[dict[str, object]]:
    """执行已注册的格局检测器(hit 至少含 gong/name/kind/pair,详 geju.Hit)。"""
    hits: list[dict[str, object]] = []
    for name, detector in PATTERN_DETECTORS.items():
        for hit in detector(pan, flags):
            hits.append({"detector": name, **hit})
    return hits
