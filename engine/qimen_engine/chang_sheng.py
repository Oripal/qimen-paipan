"""十二长生 — 十天干在九宫(地支位)中的能量状态(师门第七章,含补页)。

来源 SoT:《道家阴盘奇门遁甲》第七章(主 md 行894-944:十干长生位置对照表+
十二态×事业/健康/婚恋含义表)+ 补页 corpora/qimen-daojia-yinpan/
第七章十二长生_补页.md(第一节十二态占测含义全文;第二节断局:
**双支宫定性=看年支阴阳,取宫内同阴阳之支的状态**;流年支直查长生态;
大运干同法;大运不旺时看同五行另一干判翻盘)。

- 阳干顺排、阴干逆排(书明文)。
- 宫→地支按 ZHI2GONG 反查:四正宫单支(坎子/震卯/离午/兑酉),四维宫双支
  (艮丑寅/巽辰巳/坤未申/乾戌亥)——四维宫出双态,宝典即按双态解读。
- **中五宫无本位地支——不判**(寄宫判法书无明文,gated 待师门)。
- 十二态含义(断语)进 facts(domain=十二长生),引擎只产状态;流派缺省
  主旺衰法=落宫长生态(Q6),月令旺衰为修正参考(wangshui_calc X-1 立场)。
"""

from __future__ import annotations

from typing import Final

from qimen_engine.data_tables import GAN, ZHI, ZHI2GONG

# 十天干长生位置对照表(书行913-922):甲亥/丙戊寅/庚巳/壬申/乙午/丁己酉/辛子/癸卯
CHANG_SHENG_BIRTH: Final[dict[str, str]] = {
    "甲": "亥", "丙": "寅", "戊": "寅", "庚": "巳", "壬": "申",
    "乙": "午", "丁": "酉", "己": "酉", "辛": "子", "癸": "卯",
}

# 十二态序列(长生起,阳顺阴逆)
TWELVE_STATES: Final[tuple[str, ...]] = (
    "长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养",
)

# 阳干(甲丙戊庚壬);阴干逆排
YANG_STEMS: Final[frozenset[str]] = frozenset(GAN[i] for i in range(0, 10, 2))

# 宫 → 本位地支(ZHI2GONG 反查;中五宫为空 tuple)
GONG_BRANCHES: Final[dict[int, tuple[str, ...]]] = {
    gong: tuple(ZHI[i] for i in range(12) if ZHI2GONG[i] == gong)
    for gong in range(1, 10)
}


def branch_is_yang(branch: str) -> bool:
    """地支阴阳(子寅辰午申戌=阳,丑卯巳未酉亥=阴)。"""
    if branch not in ZHI:
        raise ValueError(f"未知地支 {branch!r}")
    return ZHI.index(branch) % 2 == 0


def chang_sheng_state(stem: str, branch: str) -> str:
    """某天干在某地支位的长生态(阳干顺排、阴干逆排)。流年支直查即用本函数。"""
    if stem not in CHANG_SHENG_BIRTH:
        raise ValueError(f"未知天干 {stem!r}")
    if branch not in ZHI:
        raise ValueError(f"未知地支 {branch!r}")
    birth = ZHI.index(CHANG_SHENG_BIRTH[stem])
    pos = ZHI.index(branch)
    offset = (pos - birth) % 12 if stem in YANG_STEMS else (birth - pos) % 12
    return TWELVE_STATES[offset]


def zhang_sheng_states(stem: str, gong: int) -> list[tuple[str, str]]:
    """某天干落某宫的长生态列表 [(地支, 态), ...]。

    四维宫双支返回双态(按地支序);四正宫单态;中五宫返回空列表(无本位地支,
    寄宫判法 gated 待师门——定性走 zhang_sheng_primary,恒 None)。
    """
    if gong not in GONG_BRANCHES:
        raise ValueError(f"gong 须为 1-9,收到 {gong}")
    return [(branch, chang_sheng_state(stem, branch)) for branch in GONG_BRANCHES[gong]]


def zhang_sheng_primary(stem: str, gong: int, year_zhi: str) -> str | None:
    """落宫长生态定性(补页第二节断局规则)。

    双支宫定性=看年支阴阳:年支为阳支取宫内阳支之态,阴支取阴支之态
    (四维宫恰各含一阳一阴支,恒可定);单支宫直返该支之态;
    **中五宫不判,返回 None**(无本位地支,寄宫判法书无明文,gated 待师门)。
    """
    states = zhang_sheng_states(stem, gong)
    if not states:
        return None  # 中五宫
    if len(states) == 1:
        return states[0][1]
    want_yang = branch_is_yang(year_zhi)
    for branch, state in states:
        if branch_is_yang(branch) == want_yang:
            return state
    raise RuntimeError(f"宫{gong}双支阴阳异常:{states}")  # 四维宫恒一阳一阴,不可达


def same_element_partner(stem: str) -> str:
    """同五行另一干(甲↔乙/丙↔丁/戊↔己/庚↔辛/壬↔癸)。

    补页第二节:大运干不旺时,看同五行另一干的长生态判翻盘机会。
    """
    if stem not in GAN:
        raise ValueError(f"未知天干 {stem!r}")
    return GAN[GAN.index(stem) ^ 1]
