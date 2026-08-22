#!/usr/bin/env python3
"""游戏更新后，从干净的英文原版重新采集 backup/。

务必先在 Steam 里「验证游戏文件完整性」，确认磁盘上是未打补丁的新版原版，
否则采集到的会是汉化版——那样 restore.sh 再也还原不回英文，而且补丁会在
已翻译的文件上再翻一遍。本脚本会主动检查这一点。

用法:  python3 rebuild_backup.py
"""
import hashlib, json, os, shutil, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(ROOT, "backup")
MANIFEST = os.path.join(BACKUP_DIR, "MANIFEST.json")
HOME = os.path.expanduser("~")
APP = os.path.join(HOME, "Library/Application Support/Steam/steamapps/common",
                   "Twilight Struggle", "TwilightStruggle.app")
DATA = os.path.join(APP, "Contents/Resources/Data")

PATCHED_FILES = ["resources.assets", "level2", "level3"]
EXTRA_FILES = ["level0", "level1", "sharedassets0.assets", "globalgamemanagers.assets"]
EXTRA_TREES = ["StreamingAssets", "il2cpp_data/Metadata"]

# 汉化过的资源里必然出现的字节；用它判断磁盘上的游戏是不是还没打补丁
ZH_MARKER = "朝鲜战争".encode("utf-8")


def die(msg):
    print("错误: " + msg, file=sys.stderr)
    sys.exit(1)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if not os.path.isdir(DATA):
        die("找不到游戏目录: " + DATA)

    # 关键防线：磁盘上的游戏必须是未汉化的原版
    with open(os.path.join(DATA, "resources.assets"), "rb") as f:
        blob = f.read()
    if ZH_MARKER in blob:
        die("磁盘上的游戏已经是汉化版，不能作为备份来源。\n"
            "  请先在 Steam 里对《Twilight Struggle》执行「验证游戏文件完整性」，\n"
            "  等它把英文原版下载回来之后再运行本脚本。")

    if os.path.isdir(BACKUP_DIR):
        old = BACKUP_DIR + ".old"
        if os.path.isdir(old):
            shutil.rmtree(old)
        os.rename(BACKUP_DIR, old)
        print(f"原备份已移到 {os.path.basename(old)}/（确认无误后可自行删除）")
    os.makedirs(BACKUP_DIR, exist_ok=True)

    for f in PATCHED_FILES + EXTRA_FILES:
        src = os.path.join(DATA, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(BACKUP_DIR, f))
            print(f"  已备份 {f}")
    for t in EXTRA_TREES:
        src = os.path.join(DATA, t)
        if os.path.isdir(src):
            dst = os.path.join(BACKUP_DIR, t)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copytree(src, dst)
            print(f"  已备份 {t}/")

    json.dump({"note": "original=英文原版的哈希; patched=本工具最近一次装入游戏的产物哈希。"
                       "二者都对不上，说明游戏被更新或校验过，backup 已过期。",
               "original": {f: sha256(os.path.join(BACKUP_DIR, f)) for f in PATCHED_FILES},
               "patched": {}},
              open(MANIFEST, "w"), indent=1)

    print("\n备份重建完成。接下来：")
    print("  python3 patch.py --dry-run    # 先看各表命中数是否正常")
    print("如果命中数骤降，或报「找不到对象 / 结构已变」，说明新版打包结构变了，")
    print("需要重新探测 patch.py 顶部那几个 path ID 再打补丁。")


if __name__ == "__main__":
    main()
