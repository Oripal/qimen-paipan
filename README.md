# qimen-paipan

阴盘奇门排盘的独立应用。输入一个时刻,给出盘面——只做排盘,不做断事解读。

取法固定为阴盘 · 时家 · 转盘,不做流派泛化。

## 目录

| 目录 | 内容 | 状态 |
|---|---|---|
| `engine/` | 排盘引擎 `qimen-engine`(Python,纯计算,无 IO) | 已导入,见下 |
| `scripts/` | 仓库维护脚本 | `sync-engine.sh` |

排盘接口(服务端)和交互盘面(前端)尚未开始。

## 引擎:从 VoborSpark 单向同步

`engine/` 不是在这里开发的。它的上游是 VoborSpark 平台仓库的
`shared/python/qimen_engine`,通过 git subtree 带历史导入。

- **不要直接改 `engine/`。** 引擎的词汇(神、星、门的全名)与平台里的断语语料配套,
  改动必须在 VoborSpark 里和语料一起改、一起测。
- 上游有改动后,在本仓库根目录跑:

  ```bash
  scripts/sync-engine.sh
  ```

  它会从 VoborSpark 的 `main` 取最新的引擎目录并合入 `engine/`。需要本机有
  VoborSpark 的工作副本(默认 `/root/Hydree/VoborSpark`,可用 `PLATFORM_REPO` 指定)。
  同步是开发机上的手工动作;本仓库的构建和部署不访问 VoborSpark。

引擎的用法、覆盖范围、测试与基准见 [engine/README.md](engine/README.md)。

```bash
cd engine && uv run pytest -q     # 引擎自测,不依赖本仓库其它部分
```


