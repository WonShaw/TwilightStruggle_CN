#!/bin/bash
# 一键还原英文原版（含资源包与场景文件），并恢复签名。
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"        # 跟随本脚本所在目录
APP="$(python3 "$HERE/gamepath.py" "$@")"                    # 支持 --game-path
DATA="$APP/Contents/Resources/Data"
BK="$HERE/backup"

if pgrep -f "TwilightStruggle.app/Contents/MacOS" > /dev/null; then
  echo "游戏正在运行，请先退出。" >&2
  exit 1
fi

for f in resources.assets level2 level3; do
  cp "$BK/$f" "$DATA/$f"
  echo "已还原 $f"
done

mkdir -p "$HERE/build"
codesign -d --entitlements - --xml "$APP" 2>/dev/null > "$HERE/build/ent.plist"
codesign --force --sign - --entitlements "$HERE/build/ent.plist" --options runtime \
  --identifier unity.Playdek.TwilightStruggle "$APP" 2>/dev/null
echo "已重新签名。游戏已还原为英文原版。"
