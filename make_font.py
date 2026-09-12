#!/usr/bin/env python3
"""生成汉化用的中文字体子集 ZH_sub.ttf。

从 macOS 自带的冬青黑体简体中文中提取第 0 号字体，裁掉用不到的字符集，
输出约 8 MB、含 2.1 万字符的子集。这个文件会被 patch.py 塞进游戏的
Font(846) 对象，作为 TMP 全局回退字体的来源。

依赖:  python3 -m pip install fonttools brotli
用法:  python3 make_font.py [--source <字体路径>] [--index N]

换字体：想要思源黑体等其他字体，用 --source 指向对应的 .ttf/.otf/.ttc 即可，
输出文件名不变，之后照常跑 patch.py。
"""
import argparse, os, sys

# fontTools 写 head.modified 时优先用这个变量；固定它，输出才逐字节可重现
os.environ.setdefault("SOURCE_DATE_EPOCH", "0")

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "ZH_sub.ttf")
DEFAULT_SRC = "/System/Library/Fonts/Hiragino Sans GB.ttc"

# 需要保留的码位：拉丁、拉丁补充、通用标点、CJK 标点、全角字符、CJK 统一表意文字
RANGES = [
    (0x20, 0x7F), (0xA0, 0x100), (0x2000, 0x206F),
    (0x3000, 0x3040), (0xFF00, 0xFFF0), (0x4E00, 0xA000),
]
EXTRA = {0x2018, 0x2019, 0x201C, 0x201D, 0x2026, 0x2014, 0x00B7, 0x00D7}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=DEFAULT_SRC)
    ap.add_argument("--index", type=int, default=0, help="ttc 内的字体序号")
    args = ap.parse_args()

    try:
        from fontTools.ttLib import TTFont, TTCollection
        from fontTools import subset
    except ImportError:
        sys.exit("缺少依赖，请先执行: python3 -m pip install fonttools brotli")

    if not os.path.exists(args.source):
        sys.exit(f"找不到源字体: {args.source}")

    tmp = os.path.join(ROOT, ".font_full.tmp.ttf")
    if args.source.lower().endswith(".ttc"):
        coll = TTCollection(args.source)
        print(f"源 ttc 含 {len(coll.fonts)} 个字体，取第 {args.index} 个")
        coll.fonts[args.index].save(tmp)
    else:
        TTFont(args.source).save(tmp)

    opts = subset.Options()
    opts.drop_tables += ["DSIG"]
    opts.layout_features = ["*"]
    opts.notdef_outline = True
    opts.recalc_bounds = True

    font = subset.load_font(tmp, opts)
    unicodes = set(EXTRA)
    for lo, hi in RANGES:
        unicodes |= set(range(lo, hi))
    sub = subset.Subsetter(options=opts)
    sub.populate(unicodes=unicodes)
    sub.subset(font)
    subset.save_font(font, OUT, opts)
    os.remove(tmp)

    cmap = TTFont(OUT).getBestCmap()
    missing = [c for c in "苏联美国影响力政变防御等级战略" if ord(c) not in cmap]
    print(f"已生成 {OUT}")
    print(f"  大小 {os.path.getsize(OUT)/1048576:.1f} MB，含 {len(cmap)} 个字符")
    print("  抽查常用字: " + ("有缺失 " + "".join(missing) if missing else "全部存在"))


if __name__ == "__main__":
    main()
