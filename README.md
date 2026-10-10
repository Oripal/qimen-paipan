# qimen-engine

阴盘奇门排盘引擎(0_09 资产名 `qimen-engine`)。输入一个时刻,输出盘面;纯确定性,
无 LLM、无 IO、无平台依赖。m-runtime 的奇门工具(`cast-chart` 等)和独立排盘应用
共用这一份。

设计 SoT:`docs/05_Design/2026-07-04_Qimen_Agent_Platform_Native_Design.md`(§3.1 引擎、
§8 节气表扩展、§9 抽包)。

## 取法(编译期常量,不做流派泛化)

阴盘 · 时家 · 转盘 · 天禽随芮 · 中五寄坤二。定局 = (农历年支序 + 月 + 日 + 时支序) mod 9,
阴阳遁按节气半区(夏至→冬至为阴遁)。八神阳遁顺布、阴遁反序;不提前入局。

逐函数移植自师门 Android 应用的 JS 引擎 `iqm.js`(已获授权),它是排盘算法的可执行
SoT:Python 与它不一致时,以它为准。唯一有意的偏离是节气时刻表(见「覆盖范围」)。

## 用法

```python
from datetime import datetime
from qimen_engine import build_chart, cast

dt = datetime(2026, 10, 9, 10, 30)          # naive 北京时间
pan = cast(dt)                               # 排盘(内部短名形态)
chart = build_chart(pan, cast_time=dt, time_source="explicit")  # Chart JSON v1(对外契约)
```

- **时间一律是 naive 北京时间**(Asia/Shanghai 民用时)。时区折算由调用方做;引擎不做
  真太阳时修正。
- `Chart JSON v1`(`schema = "qimen_chart_v1"`)是对外数据契约:九宫的神/星/门/天地盘干/
  引干、四害与伏反吟标记、四柱、节气、旬空马星、值符值使。
- 命盘:`build_mingpan_section`(命宫/平台宫/起运/大运)。格局:`chart_pattern_hits`、
  `chart_shi_jin`。旺衰与十二长生:`wang_shuai`、`zhang_sheng_states`。

## 覆盖范围

| 项 | 范围 | 范围外 |
|---|---|---|
| 可排盘日期 | 1900-01-31 ~ 2049-12-31(农历表) | `ValueError` |
| 节气分钟精度 | 1930 ~ 2050 | 回退近似公式,时分归零(只影响 1930 年前出生的命盘) |

节气表两段,同编码、同截断到分的口径:

- 1930–2009:iqm.js 原表(`data_tables.FINEDATE`)。
- 2010–2050:JPL DE440s 星历计算段(`jieqi_computed.FINEDATE_COMPUTED`)。原表 2031 起
  无表,2011 起逐年偏早(2010–2030 的 504 项中 88 项早 1 分钟,例:2026 立春实为 04:02,
  原表 04:01),所以这一段不用原表。2027 年起是预报值,个别条目将来可能有 1 分钟出入。

## 模块

| 模块 | 内容 |
|---|---|
| `calendar` | 农历、干支、节气(iqm.js 历法层) |
| `caster` | 定局、地盘、星门神、引干、全伏吟特例 → `Pan` |
| `sihai` | 四害(门迫/击刑/入墓/旬空)、伏吟反吟、格局检测注册表 |
| `geju` | 第十二章格局(正格/辅格/吉凶格)+ 三时禁 |
| `chang_sheng` / `wuxing` | 十二长生、五行生克与月令旺衰 |
| `mingju` | 命盘定宫与大运 |
| `chart` | `Pan` → Chart JSON v1;宫名归一;可引用要素集 |
| `data_tables` / `jieqi_computed` | 生成的常量表,**不要手改** |

## 测试与基准

```bash
cd shared/python/qimen_engine && ../../../.venv/bin/pytest tests/ -q
```

- **golden**:`tests/fixtures/golden_charts.json` 由 node 执行原版 iqm.js 生成(46 例),
  Python 逐宫逐层对比。比对时节气表换回原表——这套测的是移植保真度。
- **节气计算段**:与寿星算法(`chinese_calendrics`)逐项对账,并对官方年历锚点。

重新生成。前两条需要原版 `iqm.js`:它不入库,用前放到 `tests/fixtures/vendor/iqm.js`
(该路径被 git 忽略):

```bash
node tests/fixtures/gen_tables.js > qimen_engine/data_tables.py
TZ=Asia/Shanghai node tests/fixtures/generate_golden.js > tests/fixtures/golden_charts.json
uv run tests/fixtures/gen_jieqi_computed.py > qimen_engine/jieqi_computed.py   # 首次下载 32MB 星历
```
