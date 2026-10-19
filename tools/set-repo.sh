#!/bin/bash
# 用法：tools/set-repo.sh <github 用户名> [仓库名，默认 dsh-xhs-batch-studio]
# 作用：把包内所有 OWNER 占位符替换成真实 GitHub 用户名/仓库名。
set -euo pipefail
OWNER="${1:?用法: tools/set-repo.sh <github 用户名> [仓库名]}"
REPO="${2:-dsh-xhs-batch-studio}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SUB="$ROOT/../dist/awesome-dsh-plugin-submission/data/plugins"

cd "$ROOT"
perl -pi -e "s/OWNER/$OWNER/g; s#/dsh-xhs-batch-studio\b#/$REPO#g" package.json README.md 2>/dev/null || true

for f in "$SUB"/OWNER__*.yml; do
  [ -e "$f" ] || continue
  perl -pi -e "s/OWNER/$OWNER/g; s#/dsh-xhs-batch-studio\b#/$REPO#g" "$f"
  mv "$f" "$SUB/${OWNER}__${REPO}.yml"
done

echo "已写入：$OWNER/$REPO"
grep -n '"url"' package.json | head -2
