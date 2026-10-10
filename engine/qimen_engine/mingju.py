"""命局层(命盘/断运)定宫算法 — 师门著作《道家阴盘奇门遁甲》第十三/十四章定参。

定参依据(2026-07-06 著作批,取代原 fail-closed scaffold):

- **Q17 命宫=日干天盘落宫;平台宫=时干天盘落宫**(第十三章第一节明文)。
- **Q18 大运=标准八字大运**:月柱为锚,年干阳顺阴逆(×性别反转),每运 10 年,
  起运岁=出生距相邻「节」天数÷3(顺排数至下节/逆排数至上节),四舍五入取整岁;
  **大运宫=大运天干的天盘落宫**(第十三章:「以大运天干所落的宫位代表命主这
  10 年的大致运势」)。
- **锚干为甲 → 以戊(甲子戊)落宫**(第十六章案例一书注「时干甲(甲子戊)」;
  甲不上盘,直取甲子旬首仪,非本柱旬遁)。

案例复排铁证(引擎重排 vs 书中符号叙述;书 md 案例**宫名**被转换损坏,
**符号层**完好且全部指向引擎宫位——few-shot 提取须以引擎复排定宫名):

- 案例 14-1(1977-04-06 09:26 阳5局):命宫癸@坤二(值符+天蓬+伤门迫+地戊+癸墓
  五符号全中);平台丁@震三(开门+玄武+天芮);六运 癸卯0-9…戊戌50-59 逐运落宫
  符号链全中(壬寅→空亡宫艮八/辛丑→蛇+杜@兑七/庚子→休门@巽四/己亥→生门+
  九天@离九/戊戌→开门事业@震三);起运 1.15 天÷3=0.38→0 岁。
- 案例 14-2(1967-06-04 15:11 阳3局):命宫己@乾六(蛇+景+空亡+地辛);
  庚运@艮八(击刑+入墓+天芮);起运 29.08 天÷3=9.69→10 岁,庚子运 50-59
  =2017-2026(书:2016-2023 咨询期「正走庚运」)。
- 案例 14-3(2006-05-07 05:49 阳2局):平台辛与大运甲(→戊)同落乾六(死门+戊+壬;
  芮=文昌),书「平台和大运对文昌暗中扶持…19 岁之前」;起运 29.91÷3=9.97→10 岁,
  甲午运 10-19 精确命中(实证起运岁是真算非固定值)。
- 案例 16-3(1968-06-05 12:24):生于芒种前 11 小时,起运 0.15→0 岁,癸亥运
  50-59,2019 年(51 岁)「大运走癸运」✓。

待师门验证(非 blocker,进确认清单):①阴年女命顺排(通行八字规则,书中案例
均可按男解,无女命正例);②甲=甲子戊直取(16-1/16-3 盘面转录损坏无法双验,
以 16-1 书注+14-3 吻合落码)。

命盘本体 = 以出生时间起的时家局(cast(birth_dt) 现成;年份护栏 1900-2049 覆盖
出生年;晚子时/真太阳时按 Q20 暂按=与时盘同)。流年=年支九宫本位(Q19 ✅
师傅确认 2026-07-07;精微录两处+社区终身局形态三方互证)。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final, Literal

from qimen_engine.calendar import cyclical, js_round_half_up, s_term
from qimen_engine.caster import Pan
from qimen_engine.data_tables import GAN, ZHI, ZHI2GONG

Gender = Literal["male", "female"]

#: 十二节(月界,偶数节气序:0小寒 2立春 4惊蛰 6清明 8立夏 10芒种
#: 12小暑 14立秋 16白露 18寒露 20立冬 22大雪)——八字起运只数「节」不数中气。
_JIE_INDEXES: Final[tuple[int, ...]] = tuple(range(0, 24, 2))

#: 每步大运管几年(第十三章:「10 年一转」)。
YEARS_PER_YUN: Final[int] = 10


@dataclass(frozen=True)
class DaYun:
    """一步大运。start_age/end_age 为周岁(含两端);start_year=公历起始年。"""

    cyl: int  # 干支 60 甲子序
    gan: str
    zhi: str
    start_age: int
    end_age: int
    start_year: int
    gong: int  # 大运宫 = 运干天盘落宫(甲→戊)


def liu_nian_gong(year_zhi: int) -> int:
    """流年落宫 = 流年地支的九宫本位(Q19 ✅ 师傅确认「正确」2026-07-07)。

    互证:精微录「流年能量走到了艮宫…2021、2022 就会变得好了」(丑寅=艮八)、
    「流年在坎宫」(子=坎一);社区终身局分析形态同(流年直读支位宫)。
    year_zhi: 地支序 0-11(子=0)。
    """
    if not 0 <= year_zhi <= 11:
        raise ValueError(f"year_zhi 须为 0-11(子=0),收到 {year_zhi}")
    return ZHI2GONG[year_zhi]


def find_stem_gong(pan: Pan, stem: str, layer: str = "天") -> int:
    """某干在盘上的落宫(天盘/地盘;双干宫按含即中)。0=未找到(甲遁不现)。"""
    plane = pan.tiangan if layer == "天" else pan.digan
    for gong in range(1, 10):
        if stem in plane[gong]:
            return gong
    return 0


def anchor_stem_gong(pan: Pan, stem: str) -> int:
    """锚干(日干/时干/大运干)的天盘落宫;甲以戊(甲子戊)代落。

    甲不上盘;书证=第十六章「时干甲(甲子戊)」——直取甲子旬首仪戊,
    非本柱旬遁(甲午柱亦按戊,不按辛)。
    """
    if stem not in GAN:
        raise ValueError(f"未知天干 {stem!r}")
    target = "戊" if stem == "甲" else stem
    gong = find_stem_gong(pan, target, layer="天")
    if gong == 0:  # 转盘天盘恒含九干(芮宫双干),走到这里说明盘面异常
        raise ValueError(f"天盘找不到 {target!r}(盘面异常)")
    return gong


def ming_gong(pan: Pan) -> int:
    """命宫 = 日干天盘落宫(Q17,第十三章书证)。"""
    return anchor_stem_gong(pan, GAN[pan.day_cyl % 10])


def ping_tai_gong(pan: Pan) -> int:
    """平台宫 = 时干天盘落宫(第十三章书证)。"""
    return anchor_stem_gong(pan, GAN[pan.hour_cyl % 10])


def da_yun_forward(pan: Pan, gender: Gender) -> bool:
    """大运顺逆:阳年干+男/阴年干+女=顺排;反之逆排(通行八字规则)。

    书证核算:14-1 丁(阴)男逆✓/14-3 丙(阳)男顺✓/16-3 戊(阳)男(明说)顺✓。
    阴年女=顺排为通行规则推论,书无女命正例——师门确认清单挂验证勾。
    """
    if gender not in ("male", "female"):
        raise ValueError(f"gender 须为 male/female,收到 {gender!r}")
    year_gan_yang = pan.year_cyl % 10 % 2 == 0  # 甲丙戊庚壬=阳
    return year_gan_yang == (gender == "male")


def _adjacent_jie(dt: datetime, *, forward: bool) -> datetime:
    """出生时刻相邻的「节」交气时刻(顺=下一节,逆=上一节;恰逢交气按已入节)。"""
    terms = [s_term(y, n) for y in (dt.year - 1, dt.year, dt.year + 1) for n in _JIE_INDEXES]
    if forward:
        return min(t for t in terms if t > dt)
    return max(t for t in terms if t <= dt)


def qi_yun_age(birth_dt: datetime, *, forward: bool) -> tuple[float, int]:
    """起运岁 = 出生距相邻节的天数 ÷ 3,返回 (精确年数, 取整岁)。

    取整用 JS round 语义(0.5 恒向上),四案例核算:0.38→0/9.69→10/9.97→10/
    0.15→0 全部吻合书中运段。
    """
    jie = _adjacent_jie(birth_dt, forward=forward)
    days = abs((jie - birth_dt).total_seconds()) / 86400
    raw = days / 3
    return raw, js_round_half_up(raw)


def da_yun_sequence(
    pan: Pan,
    birth_dt: datetime,
    gender: Gender,
    count: int = 8,
) -> tuple[DaYun, ...]:
    """标准八字大运序列(Q18 书证):月柱锚,逐运换干支,每运 10 年。

    birth_dt 用真实出生时刻(勿用 pan.effective_dt——晚子时换日仅排盘用,
    节气距离按实际出生瞬间算)。
    """
    forward = da_yun_forward(pan, gender)
    _, qiyun = qi_yun_age(birth_dt, forward=forward)
    step = 1 if forward else -1
    yuns: list[DaYun] = []
    for i in range(count):
        cyl = (pan.mon_cyl + step * (i + 1)) % 60
        gan = GAN[cyl % 10]
        start_age = qiyun + i * YEARS_PER_YUN
        yuns.append(
            DaYun(
                cyl=cyl,
                gan=gan,
                zhi=ZHI[cyl % 12],
                start_age=start_age,
                end_age=start_age + YEARS_PER_YUN - 1,
                start_year=birth_dt.year + start_age,
                gong=anchor_stem_gong(pan, gan),
            )
        )
    return tuple(yuns)


def da_yun_at(yuns: tuple[DaYun, ...], age: int) -> DaYun | None:
    """某周岁所处的大运;未起运(幼运期)或超出序列 → None(调用方如实声明)。"""
    for yun in yuns:
        if yun.start_age <= age <= yun.end_age:
            return yun
    return None


def da_yun_label(yun: DaYun) -> str:
    """展示用:「癸卯运(0-9 岁,1977-1986)」。"""
    return (
        f"{cyclical(yun.cyl)}运({yun.start_age}-{yun.end_age} 岁,"
        f"{yun.start_year}-{yun.start_year + YEARS_PER_YUN - 1})"
    )
