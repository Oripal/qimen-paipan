"""排盘层 — 逐函数移植自师门引擎 iqm.js paipan/paipanrest(时家时盘)。

范围(v1 设计 §3.1):仅时家时盘;原引擎的刻局(paipan3)/山向/姓名盘不移植。
本门约定为编译期常量(v2 D3):阴盘·转盘·天禽随芮·定局=农历加数 mod9+节气半区。

师门已定项(2026-07-07 师傅确认,原 gated 转正):
- # Q1 ✅ 八神布法:阳遁顺布(SHEN2)/阴遁反序(SHEN)照码——师傅「可以」;
- # Q2 ✅ 提前入局:advance_minutes=0(不提前)——师傅「不提前」。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from qimen_engine.calendar import (
    LunarDate,
    cyclical,
    get_term,
    to_lunar,
)
from qimen_engine.data_tables import (
    FZHUAN,
    GAN,
    LIUYI,
    MEN,
    SHEN,
    SHEN2,
    SOLAR_TERM,
    XING,
    YIMA,
    YUEJIANG,
    ZHI,
    ZHI2GONG,
    ZHUAN,
)


@dataclass(frozen=True)
class QimenOptions:
    """本门可调常量;缺省全部按师门确认清单【暂按】。"""

    # Q2 ✅(师傅 2026-07-07:不提前):提前 N 分钟入局恒 0
    advance_minutes: int = 0
    # Q1 ✅(师傅 2026-07-07:可以):阴遁八神反序布照码,定稿
    shen_yin_dun_reversed: bool = True


DEFAULT_OPTIONS = QimenOptions()


@dataclass
class Pan:
    """排盘结果(内部短名形态,与 iqm.js 全局数组逐位对齐;宫号 1-9 索引)。"""

    dun: str  # "阴" | "阳"
    ju: int  # 1-9
    zixuan: bool  # 是否自选局
    lunar: LunarDate
    # 四柱(60 甲子序号)
    year_cyl: int
    mon_cyl: int
    day_cyl: int
    hour_cyl: int  # hCyl
    # 节气
    term_next: int  # tmp1: 下一节气序号(0-23)
    term_current: int  # tmp2: 当前节气序号(0-23)
    jiang: int  # 月将
    # 旬
    xun_shou: int  # 旬首 60 甲子序号(甲x)
    xun_kong_zhi: tuple[int, int]  # 时旬空地支序
    ma_zhi: int  # 马星地支序
    dg: int  # 旬首仪 Gan 下标
    # 有效排盘时刻 = 子时换日/提前入局处理后的 today(节气/农历都按它取)。
    # 消费方(chart 组装)判「当前节气是否跨年」必须用它,不能用换日前的
    # cast_time——23:5x 起局撞上交气窗口会把交气时刻错报成上一年。
    effective_dt: datetime = field(default=datetime(1900, 1, 31))
    dgg: int = 0  # 旬首仪落宫
    sgg: int = 0  # 值符(时干)落宫
    mgg: int = 0  # 值使落宫
    zhifu_star: str = ""  # 值符星(短名,中宫为"禽")
    zhishi_men: str = ""  # 值使门(短名)
    # 九宫盘面: 宫号 → 内容(0 位占位)
    digan: list[list[str]] = field(default_factory=list)  # 地盘干(宫2 为寄宫双干)
    tiangan: list[list[str]] = field(default_factory=list)  # 天盘干(随芮双干)
    angan: list[list[str]] = field(default_factory=list)  # 暗干
    menpan: list[str] = field(default_factory=list)  # 八门(短名)
    xinpan: list[str] = field(default_factory=list)  # 九星(短名)
    shenpan: list[str] = field(default_factory=list)  # 八神(短名)
    fuyin_special: bool = False  # 全伏吟暗干特例触发
    fuyin_double: bool = False  # 「还是伏吟」二次重排触发
    # 引干 = angan(写在宫外的天干,师傅《精微录》定义);即上面的 angan 字段。
    # 早先另加的 yin_gan(值使宫起时干,网文暂按)已撤——师傅文档只认写在宫外
    # 的引干=iqm.js angan,网文那套非师门排法(Q15 定,2026-07-05)。

    @property
    def kong_gongs(self) -> set[int]:
        """时旬空落宫。"""
        return {ZHI2GONG[z] for z in self.xun_kong_zhi}

    @property
    def ma_gong(self) -> int:
        return ZHI2GONG[self.ma_zhi]


def _wrap9(g: int) -> int:
    while g > 9:
        g -= 9
    while g < 1:
        g += 9
    return g


def _wrap8(j: int) -> int:
    while j > 8:
        j -= 8
    while j < 1:
        j += 8
    return j


def cast(
    dt: datetime,
    *,
    ju_override: tuple[str, int] | None = None,
    options: QimenOptions = DEFAULT_OPTIONS,
) -> Pan:
    """时家时盘排盘。dt 为 naive 中国民用时;ju_override=(遁, 局) 为自选局。

    逐行对齐 iqm.js paipan()+paipanrest(),含:
    - 提前入局旋钮(师门Q2,缺省 0;原码不修月末进位的行为一并照抄——旋钮为 0 时不触发)
    - 子时换日(23 时按次日,分钟保留)
    - 全伏吟暗干特例(iqm.js:682-715,含「还是伏吟」二次重排)
    """
    t_hour = dt.hour
    t_min = dt.minute + options.advance_minutes
    if t_min >= 60:
        t_min -= 60
        t_hour += 1
        if t_hour == 24:
            t_hour = 0
            # 原码在此仅调整变量、不进位 Today(iqm.js:498 注释自认忽略),照码移植

    today = datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute)
    if t_hour == 23:
        # iqm.js Today.setHours(24) 是**绝对置位**:无论 Today 现值几点(原始
        # 23:MM,或提前入局分钟进位后仍停在原始 22:MM),一律跳「次日 00:原分钟」。
        # 相对 +1h 只在原始 23 时等价,advance 溢出路径会少跳一天 → 日柱/局全错
        # (JS SoT 复核:2026-07-04 22:56 +5min = 阴7局庚辰日,+1h 版错出阴6局己卯日)。
        today = datetime(dt.year, dt.month, dt.day, 0, dt.minute) + timedelta(days=1)
        t_hour = 0

    lunar = to_lunar(today)

    t_zhi = math.floor(t_hour / 2 + 0.5)  # JS Math.round 语义
    h_gan = lunar.day_cyl % 10
    if h_gan > 4:
        h_gan -= 5
    h_cyl = h_gan * 12 + t_zhi

    tmp1 = get_term(today)
    if tmp1 > 23:
        tmp1 = 0
    tmp2 = 23 if tmp1 == 0 else tmp1 - 1
    jiang = YUEJIANG[tmp2]

    # == 求局数 ==
    v = lunar.month
    if v == 0:
        v = 12
    ju = (lunar.year_cyl % 12 + 1 + v + lunar.day + (h_cyl % 12 + 1)) % 9
    if ju == 0:
        ju = 9
    dun = "阴" if 11 <= tmp2 < 23 else "阳"

    zixuan = False
    if ju_override is not None:
        dun, ju = ju_override
        zixuan = True

    pan = Pan(
        dun=dun,
        ju=ju,
        zixuan=zixuan,
        lunar=lunar,
        year_cyl=lunar.year_cyl,
        mon_cyl=lunar.mon_cyl,
        day_cyl=lunar.day_cyl,
        hour_cyl=h_cyl,
        term_next=tmp1,
        term_current=tmp2,
        jiang=jiang,
        xun_shou=h_cyl % 60 // 10 * 10,
        xun_kong_zhi=((h_cyl % 60 // 10 * 10 + 10) % 12, (h_cyl % 60 // 10 * 10 + 11) % 12),
        ma_zhi=YIMA[h_cyl % 4],
        dg=h_cyl % 60 // 10 + 4,
        effective_dt=today,
    )
    _cast_rest(pan, options)
    return pan


def _cast_rest(pan: Pan, options: QimenOptions) -> None:
    """iqm.js paipanrest() 的排宫段(地盘/星门神/暗干/全伏吟特例)。"""
    yin = pan.dun == "阴"
    ju = pan.ju
    h_cyl = pan.hour_cyl
    dg = pan.dg

    # == 排地盘 ==
    digan: list[list[str]] = [[] for _ in range(10)]
    dgg = 0
    sgg = 0
    for i in range(9):
        g = _wrap9(ju - i if yin else ju + i)
        digan[g] = [GAN[LIUYI[i + 1]]]
        if LIUYI[i + 1] == dg:
            dgg = g  # 旬首仪落宫
        if LIUYI[i + 1] == h_cyl % 10:
            sgg = g  # 地盘时干落宫
    if sgg == 0:
        sgg = dgg  # 时干为甲 → 随旬首
    digan[2] = [digan[2][0], digan[5][0]]  # 中宫寄坤二

    pan.dgg, pan.sgg = dgg, sgg
    pan.zhifu_star = "禽" if dgg == 5 else XING[FZHUAN[dgg]]
    pan.zhishi_men = MEN[FZHUAN[dgg]]

    mgg = _wrap9(h_cyl % 10 + dgg if not yin else dgg - h_cyl % 10)
    pan.mgg = mgg

    # == 排星门 ==
    tiangan: list[list[str]] = [[] for _ in range(10)]
    xinpan: list[str] = [""] * 10
    v = FZHUAN[sgg] - FZHUAN[dgg]
    for i in range(1, 9):
        j = _wrap8(i - v)
        xinpan[ZHUAN[i]] = XING[j]
        tiangan[ZHUAN[i]] = list(digan[ZHUAN[j]])

    menpan: list[str] = [""] * 10
    v = FZHUAN[mgg] - FZHUAN[dgg]
    for i in range(1, 9):
        j = _wrap8(i - v)
        menpan[ZHUAN[i]] = MEN[j]

    # == 排神 ==  # 师门Q1: 阳顺(SHEN2)阴反(SHEN),切换点=options.shen_yin_dun_reversed
    shenpan: list[str] = [""] * 10
    v = FZHUAN[sgg] - 1
    shen_table = SHEN if (yin and options.shen_yin_dun_reversed) else SHEN2
    for i in range(1, 9):
        j = _wrap8(i - v)
        shenpan[ZHUAN[i]] = shen_table[j]

    # == 排暗干 ==
    angan: list[list[str]] = [[] for _ in range(10)]
    v = FZHUAN[sgg] - FZHUAN[mgg]
    for i in range(1, 9):
        j = _wrap8(i + v)
        angan[ZHUAN[i]] = list(digan[ZHUAN[j]])
    angan[5] = []

    # == 全伏吟暗干特例(iqm.js:682-715)==
    if angan[1] == tiangan[1] == digan[1]:
        pan.fuyin_special = True
        if h_cyl % 10 == 0:
            stem_idx = LIUYI[h_cyl // 10 + 1]
        else:
            stem_idx = h_cyl % 10
        _refill_angan(angan, yin, _liuyi_pos(stem_idx))
        if angan[1] == tiangan[1]:  # 还是伏吟 → 以 2 宫之干置中宫重排
            pan.fuyin_double = True
            gan = angan[2][0]
            _refill_angan(angan, yin, _liuyi_pos(GAN.index(gan)))
        angan[2] = [angan[2][0], angan[5][0]]
        angan[5] = []

    # 引干 = angan(师傅《精微录》:引干/隐干=写在宫外的天干)。早先另排的
    # 网文式 yin_gan(值使宫起时干)已撤——非师门排法(Q15 定,2026-07-05)。

    pan.digan = digan
    pan.tiangan = tiangan
    pan.angan = angan
    pan.menpan = menpan
    pan.xinpan = xinpan
    pan.shenpan = shenpan


def _liuyi_pos(stem_idx: int) -> int:
    """Gan 下标 → LIUYI 中的位置 j(1-9)。"""
    for j in range(1, 10):
        if LIUYI[j] == stem_idx:
            return j
    raise ValueError(f"stem index {stem_idx} not in LIUYI")


def _refill_angan(angan: list[list[str]], yin: bool, j: int) -> None:
    """全伏吟特例的暗干重排(iqm.js:687-695 / 701-709)。"""
    v = j + 4 if yin else j - 4
    for i in range(1, 10):
        g = _wrap9(v - i + 1 if yin else v + i - 1)
        angan[i] = [GAN[LIUYI[g]]]


def header_summary(pan: Pan) -> dict[str, str | int | bool | list[str]]:
    """人读头部字段(设计 §3.8-5 字段基线,供工具摘要与模板消费)。"""
    return {
        "dun": pan.dun,
        "ju": pan.ju,
        "zixuan": pan.zixuan,
        "pillars": [
            cyclical(pan.year_cyl),
            cyclical(pan.mon_cyl),
            cyclical(pan.day_cyl),
            cyclical(pan.hour_cyl),
        ],
        "lunar": (
            f"{pan.lunar.year}年"
            + ("闰" if pan.lunar.is_leap else "")
            + f"{pan.lunar.month}月{pan.lunar.day}日"
        ),
        "term_current": SOLAR_TERM[pan.term_current],
        "term_next": SOLAR_TERM[pan.term_next],
        "xun_shou": cyclical(pan.xun_shou),
        "kong_zhi": [ZHI[z] for z in pan.xun_kong_zhi],
        "ma_zhi": ZHI[pan.ma_zhi],
        "zhifu": f"天{pan.zhifu_star}星落{pan.sgg}宫",
        "zhishi": f"{pan.zhishi_men}门落{pan.mgg}宫",
    }
