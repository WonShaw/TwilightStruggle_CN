#!/usr/bin/env python3
"""定位 Steam 里《Twilight Struggle》的安装位置。

查找顺序：
  1. 命令行 --game-path <TwilightStruggle.app 路径>，或环境变量 TS_GAME_PATH
  2. Steam 自己的库清单 steamapps/libraryfolders.vdf：哪个库的 apps 里有 406290，
     游戏就在那个库；目录名从 appmanifest_406290.acf 的 installdir 读，不猜
  3. 兜底：默认库 ~/Library/Application Support/Steam

直接运行会把找到的路径打到 stdout，供 shell 脚本用：
  APP="$(python3 gamepath.py)"
"""
import os, re, sys

APP_ID = "406290"
STEAM_DIR = os.path.expanduser("~/Library/Application Support/Steam")
APP_NAME = "TwilightStruggle.app"


def _vdf(path):
    """极简 VDF 解析：只处理 "key" "value" 和 "key" { ... } 两种形式。"""
    toks = re.findall(r'"((?:[^"\\]|\\.)*)"|([{}])', open(path, encoding="utf-8").read())
    toks = [a if a else b for a, b in toks]
    pos = 0

    def block():
        nonlocal pos
        d = {}
        while pos < len(toks):
            t = toks[pos]; pos += 1
            if t == "}":
                return d
            if toks[pos] == "{":
                pos += 1
                d[t] = block()
            else:
                d[t] = toks[pos]; pos += 1
        return d
    return block()


def _from_steam():
    lf = os.path.join(STEAM_DIR, "steamapps", "libraryfolders.vdf")
    libs = []
    if os.path.exists(lf):
        root = _vdf(lf).get("libraryfolders", {})
        for v in root.values():
            if isinstance(v, dict) and "path" in v:
                libs.append((v["path"], APP_ID in v.get("apps", {})))
    libs.sort(key=lambda x: not x[1])          # 清单里声明装了本游戏的库排前面
    libs.append((STEAM_DIR, False))            # 兜底：默认库
    for lib, _ in libs:
        sa = os.path.join(lib, "steamapps")
        acf = os.path.join(sa, f"appmanifest_{APP_ID}.acf")
        subdir = "Twilight Struggle"
        if os.path.exists(acf):
            subdir = _vdf(acf).get("AppState", {}).get("installdir", subdir)
        app = os.path.join(sa, "common", subdir, APP_NAME)
        if os.path.isdir(app):
            return app
    return None


def find_app(argv=None):
    argv = sys.argv if argv is None else argv
    app = os.environ.get("TS_GAME_PATH")
    if "--game-path" in argv:
        i = argv.index("--game-path")
        if i + 1 >= len(argv):
            sys.exit("错误: --game-path 后面要跟 TwilightStruggle.app 的路径")
        app = argv[i + 1]
    if app:
        app = os.path.abspath(os.path.expanduser(app))
        if not os.path.isdir(os.path.join(app, "Contents", "Resources", "Data")):
            sys.exit(f"错误: {app} 不是 TwilightStruggle.app（缺 Contents/Resources/Data）")
        return app
    app = _from_steam()
    if not app:
        sys.exit("错误: 在 Steam 库里找不到《Twilight Struggle》。\n"
                 "  请确认已通过 Steam 安装；若装在非常规位置，用\n"
                 "    --game-path '/路径/到/TwilightStruggle.app'\n"
                 "  或设置环境变量 TS_GAME_PATH 指定。")
    return app


if __name__ == "__main__":
    print(find_app())
