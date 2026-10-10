"""奇门排盘引擎 — 移植自师门 Android 应用 JS 引擎 iqm.js(可执行 SoT)。

设计 SoT: docs/05_Design/2026-07-04_Qimen_Agent_Platform_Native_Design.md §3.1
Golden 基准: tests/fixtures/(node 执行原 JS 生成,跨语言 fixture 铁律)
师门 gated 项: caster.QimenOptions(Q1 八神布法 / Q2 提前入局)。
格局层(M3 批): geju.py(第十二章正格/辅格/吉凶格+三时禁,import 即注册
进 sihai.PATTERN_DETECTORS);十二长生: chang_sheng.py(第七章+补页)。
"""

from qimen_engine.calendar import (
    LunarDate,
    cyclical,
    get_term,
    s_term,
    to_lunar,
)
from qimen_engine.caster import (
    DEFAULT_OPTIONS,
    Pan,
    QimenOptions,
    cast,
    header_summary,
)
from qimen_engine.chang_sheng import (
    CHANG_SHENG_BIRTH,
    GONG_BRANCHES,
    TWELVE_STATES,
    branch_is_yang,
    chang_sheng_state,
    same_element_partner,
    zhang_sheng_primary,
    zhang_sheng_states,
)
from qimen_engine.chart import (
    CHART_SCHEMA,
    PALACE_NAME_ALIASES,
    build_chart,
    chart_elements,
    chart_pattern_hits,
    chart_shi_jin,
    detect_chart_flags,
    normalize_gong_name,
    pan_elements,
)
from qimen_engine.geju import (
    FU_GE,
    JI_XIONG_GE,
    SHI_JIN_LABELS,
    ZHENG_GE,
    palace_geju_hits,
    shi_jin_flags,
    shi_jin_from_pan,
)
from qimen_engine.sihai import (
    PATTERN_DETECTORS,
    ChartFlags,
    PalaceFlags,
    detect_flags,
    run_pattern_detectors,
)
from qimen_engine.wuxing import element_of, sheng_ke, wang_shuai

__all__ = [
    "CHANG_SHENG_BIRTH",
    "CHART_SCHEMA",
    "DEFAULT_OPTIONS",
    "FU_GE",
    "GONG_BRANCHES",
    "JI_XIONG_GE",
    "PATTERN_DETECTORS",
    "SHI_JIN_LABELS",
    "TWELVE_STATES",
    "ZHENG_GE",
    "ChartFlags",
    "LunarDate",
    "PALACE_NAME_ALIASES",
    "PalaceFlags",
    "Pan",
    "QimenOptions",
    "branch_is_yang",
    "build_chart",
    "cast",
    "chang_sheng_state",
    "chart_elements",
    "chart_pattern_hits",
    "chart_shi_jin",
    "cyclical",
    "detect_chart_flags",
    "detect_flags",
    "element_of",
    "get_term",
    "header_summary",
    "normalize_gong_name",
    "palace_geju_hits",
    "pan_elements",
    "run_pattern_detectors",
    "s_term",
    "same_element_partner",
    "sheng_ke",
    "shi_jin_flags",
    "shi_jin_from_pan",
    "to_lunar",
    "wang_shuai",
    "zhang_sheng_primary",
    "zhang_sheng_states",
]
