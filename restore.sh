#!/bin/bash
# 一键还原英文原版（含资源包与场景文件），并恢复签名。
set -e
APP="$HOME/Library/Application Support/Steam/steamapps/common/Twilight Struggle/TwilightStruggle.app"
DATA="$APP/Contents/Resources/Data"
BK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/backup"   # 跟随本脚本所在目录

if pgrep -f "TwilightStruggle.app/Contents/MacOS" > /dev/null; then
  echo "游戏正在运行，请先退出。" >&2
  exit 1
fi

for f in resources.assets level2 level3; do
  cp "$BK/$f" "$DATA/$f"
  echo "已还原 $f"
done

codesign -d --entitlements - --xml "$APP" 2>/dev/null > /tmp/ts_ent.plist
codesign --force --sign - --entitlements /tmp/ts_ent.plist --options runtime \
  --identifier unity.Playdek.TwilightStruggle "$APP" 2>/dev/null
echo "已重新签名。游戏已还原为英文原版。"
