"""五行旺衰层 — wangshui-calc 的确定性规则(v2 §3 工具表:死规则代码化)。

旺相休囚死按月令(节气月支)判:当令旺、令生者相、生令者休、克令者囚、令克者死。
土旺于四季月(辰未戌丑)。月令权重之争(师门Q6)是 Skill 裁量层的事;
本工具只回答「某五行/星/门/干 在某月令下的旺衰态」这一确定性问题。
"""

from __future__ import annotations

from typing import Final

WUXING: Final[tuple[str, ...]] = ("木", "火", "土", "金", "水")

# 相生: 木→火→土→金→水→木
_SHENG: Final[dict[str, str]] = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
# 相克: 木→土→水→火→金→木
_KE: Final[dict[str, str]] = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

STEM_WUXING: Final[dict[str, str]] = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}

# 九星五行(短名与全名双收)
STAR_WUXING: Final[dict[str, str]] = {
    "蓬": "水", "任": "土", "冲": "木", "辅": "木", "英": "火",
    "芮": "土", "柱": "金", "心": "金", "禽": "土",
}

DOOR_WUXING: Final[dict[str, str]] = {
    "休": "水", "生": "土", "伤": "木", "杜": "木",
    "景": "火", "死": "土", "惊": "金", "开": "金",
}

GOD_WUXING: Final[dict[str, str]] = {
    "值符": "土", "腾蛇": "火", "太阴": "金", "六合": "木",
    "白虎": "金", "玄武": "水", "九地": "土", "九天": "金",
}

GONG_WUXING: Final[dict[int, str]] = {
    1: "水", 2: "土", 3: "木", 4: "木", 5: "土", 6: "金", 7: "金", 8: "土", 9: "火",
}

# 月支 → 月令五行(土旺四季月)
BRANCH_SEASON: Final[dict[str, str]] = {
    "寅": "木", "卯": "木", "巳": "火", "午": "火",
    "申": "金", "酉": "金", "亥": "水", "子": "水",
    "辰": "土", "未": "土", "戌": "土", "丑": "土",
}


def element_of(symbol: str) -> str | None:
    """星/门/神/干/五行字符串 → 五行。识别不了返回 None。"""
    if symbol in WUXING:
        return symbol
    if symbol in STEM_WUXING:
        return STEM_WUXING[symbol]
    s = symbol.lstrip("天").rstrip("星")
    if s in STAR_WUXING:
        return STAR_WUXING[s]
    d = symbol.rstrip("门")
    if d in DOOR_WUXING:
        return DOOR_WUXING[d]
    if symbol in GOD_WUXING:
        return GOD_WUXING[symbol]
    return None


def wang_shuai(element: str, month_branch: str) -> str:
    """五行 × 月支 → 旺/相/休/囚/死。"""
    season = BRANCH_SEASON[month_branch]
    if element == season:
        return "旺"
    if _SHENG[season] == element:
        return "相"
    if _SHENG[element] == season:
        return "休"
    if _KE[element] == season:
        return "囚"
    return "死"


def sheng_ke(a: str, b: str) -> str:
    """五行 a 对 b 的关系:生/克/被生/被克/比和(宫际生克供参考)。"""
    if a == b:
        return "比和"
    if _SHENG[a] == b:
        return "生"
    if _KE[a] == b:
        return "克"
    if _SHENG[b] == a:
        return "被生"
    return "被克"
