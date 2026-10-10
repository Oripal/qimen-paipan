#!/usr/bin/env bash
# 把排盘引擎从 VoborSpark 同步到本仓库的 engine/ 目录。
#
# 方向只有一个:VoborSpark(上游)→ 本仓库。引擎的改动一律在 VoborSpark 的
# shared/python/qimen_engine 里做、测、合入 main,再跑本脚本带过来;
# 不要直接改本仓库的 engine/。
#
# 用法:scripts/sync-engine.sh            (平台仓库默认在 /root/Hydree/VoborSpark)
#       PLATFORM_REPO=/path/to/VoborSpark scripts/sync-engine.sh
set -euo pipefail

PLATFORM_REPO="${PLATFORM_REPO:-/root/Hydree/VoborSpark}"
PREFIX_UPSTREAM="shared/python/qimen_engine"
EXPORT_BRANCH="export/qimen-engine"

cd "$(git rev-parse --show-toplevel)"
if [ -n "$(git status --porcelain)" ]; then
  echo "工作区有未提交改动,先提交或清理再同步。" >&2
  exit 1
fi

git -C "$PLATFORM_REPO" fetch origin main --quiet
upstream_rev="$(git -C "$PLATFORM_REPO" rev-parse --short origin/main)"
# 把上游的引擎目录切成一段独立历史(确定性:同样的上游提交总得到同样的结果)
git -C "$PLATFORM_REPO" subtree split --prefix="$PREFIX_UPSTREAM" -b "$EXPORT_BRANCH" origin/main >/dev/null

git subtree pull --prefix=engine "$PLATFORM_REPO" "$EXPORT_BRANCH" \
  -m "sync(engine): 同步排盘引擎,上游 VoborSpark@${upstream_rev}"

echo "已同步到 VoborSpark@${upstream_rev}。跑一遍引擎测试:cd engine && uv run pytest -q"
