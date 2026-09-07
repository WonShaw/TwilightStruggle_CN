#!/usr/bin/env python3
"""冷战热斗（Playdek / Steam macOS）存档悔棋工具。

与汉化补丁无关，只是顺手做的存档工具，放在这里免得丢。

存档是一对文件：
  Save1Full.dat   224 字节头 + N 条 16 字节操作记录
  Save1Short.dat  .NET BinaryFormatter 序列化的摘要，供读档列表显示

关键点：Full 里**没有棋盘状态**——5 KB 装不下 86 个国家的影响力、手牌和弃牌堆。
游戏是靠**重放**那 N 条记录还原局面的。所以「悔棋」就是砍掉末尾若干条记录，
再同步头部三处计数器与摘要里的 savedDataSize。

记录格式（小端）:
  +0  u32  玩家 ID    123 / 456
  +4  u16  参数1
  +6  u16  目标       >=100 -> 牌号(-100)；<100 -> 国家序号
  +8  u16  动作码     0xa0XX，0xa01X 是「打出一张牌」
  +10 u16  恒为 0
  +12 i32  参数3

必须整手删。一手 = 从 0xa01X 出牌起，到下一次出牌前为止，中间是选用途
（0xa0X0）和逐个作用到国家（0xa0X1/2/3）。只删末尾一条会留下「牌打出去了
但没落子」的残缺状态，重放到那里就卡住了。

用法:
  python3 undo_move.py                列出所有手（只读，不写任何文件）
  python3 undo_move.py --undo N       悔掉末尾 N 手（默认 1）
  python3 undo_move.py --restore      从 .bak 还原
  python3 undo_move.py --slot 2       操作 Save2*.dat
"""
import argparse, os, shutil, struct, subprocess, sys

SAVE_DIR = os.path.expanduser("~/Library/Application Support/unity.Playdek.TwilightStruggle")

LOG_OFF   = 0xE0                  # 日志区起点
REC_SIZE  = 16
COUNT_OFF = (0xB8, 0xC8, 0xD4)    # 头部三处记录数，必须一起改
SIZE_OFF  = 724                   # Save*Short.dat 里 savedDataSize 的偏移（会校验，不符则重新搜）
MAGIC     = b"PLAYDEK\0"
NEW_HAND  = {0xa010, 0xa011, 0xa012, 0xa013}   # 出牌 = 一手的起点

PLAYERS = {123: "Player", 456: "AI Player"}


def die(msg):
    print("错误: " + msg, file=sys.stderr)
    sys.exit(1)


def check_not_running():
    r = subprocess.run(["pgrep", "-f", "TwilightStruggle.app/Contents/MacOS"],
                       capture_output=True, text=True)
    if r.stdout.strip():
        die("游戏正在运行。退出游戏时它会把内存里的局面写回存档，覆盖本次修改。\n"
            "  请先完全退出游戏再运行本工具。")


def find_size_field(short, want):
    """定位摘要里的 savedDataSize。

    先试已知偏移；对不上就全文搜该值，只有唯一一处才敢用——
    游戏更新后字段位移能自愈，位置有歧义则宁可报错。
    """
    if len(short) >= SIZE_OFF + 4 and struct.unpack_from("<i", short, SIZE_OFF)[0] == want:
        return SIZE_OFF
    hits = [i for i in range(len(short) - 3)
            if struct.unpack_from("<i", short, i)[0] == want]
    if len(hits) == 1:
        print(f"提示: savedDataSize 不在偏移 {SIZE_OFF}，已重新定位到 {hits[0]}（游戏可能更新过）。")
        return hits[0]
    die(f"在摘要文件里找不到唯一的 savedDataSize（值应为 {want}，找到 {len(hits)} 处）。\n"
        "  存档格式与预期不符，已中止，未做任何修改。")


def load(slot):
    full_p = os.path.join(SAVE_DIR, f"Save{slot}Full.dat")
    short_p = os.path.join(SAVE_DIR, f"Save{slot}Short.dat")
    for p in (full_p, short_p):
        if not os.path.exists(p):
            die("找不到存档: " + p)
    full = bytearray(open(full_p, "rb").read())
    short = bytearray(open(short_p, "rb").read())

    if bytes(full[:8]) != MAGIC:
        die(f"{os.path.basename(full_p)} 开头不是 PLAYDEK，格式与预期不符")
    body = len(full) - LOG_OFF
    if body <= 0 or body % REC_SIZE:
        die(f"日志区 {body} 字节，不是 {REC_SIZE} 的整数倍，格式与预期不符")
    n = body // REC_SIZE

    # 三处计数器必须彼此一致，且与文件长度算出的条数一致；对不上说明格式变了
    counts = [struct.unpack_from("<i", full, o)[0] for o in COUNT_OFF]
    if set(counts) != {n}:
        die(f"头部计数器 {counts} 与实际记录数 {n} 不符，存档可能损坏或格式已变")
    size_off = find_size_field(short, len(full))
    return full_p, short_p, full, short, n, size_off


def records(full, n):
    return [struct.unpack_from("<IHHHHi", full, LOG_OFF + i * REC_SIZE) for i in range(n)]


def hand_starts(recs):
    """按出牌记录切分成「手」，返回每手的起始下标。"""
    b = [i for i, r in enumerate(recs) if r[3] in NEW_HAND]
    if not b or b[0] != 0:
        b = [0] + b          # 开局布置影响力不以出牌开头
    return b


def describe(recs, s, e):
    r0 = recs[s]
    who = PLAYERS.get(r0[0], f"玩家{r0[0]}")
    what = f"卡{r0[2] - 100}" if r0[2] >= 100 else "开局布置"
    return f"{who:9s} {what:8s} ({e - s} 条记录 #{s}..#{e - 1})"


def main():
    ap = argparse.ArgumentParser(description="冷战热斗存档悔棋工具")
    ap.add_argument("--undo", type=int, nargs="?", const=1, default=None,
                    help="悔掉末尾 N 手（默认 1）")
    ap.add_argument("--restore", action="store_true", help="从 .bak 还原")
    ap.add_argument("--slot", type=int, default=1, help="存档槽位，默认 1")
    args = ap.parse_args()

    if args.restore:
        check_not_running()
        done = False
        for name in (f"Save{args.slot}Full.dat", f"Save{args.slot}Short.dat"):
            p = os.path.join(SAVE_DIR, name)
            if not os.path.exists(p + ".bak"):
                die("找不到备份: " + p + ".bak")
            shutil.copy2(p + ".bak", p)
            print("已还原 " + name)
            done = True
        if done:
            print("存档已回到悔棋前的状态。")
        return

    full_p, short_p, full, short, n, size_off = load(args.slot)
    recs = records(full, n)
    starts = hand_starts(recs) + [n]
    total = len(starts) - 1

    print(f"{os.path.basename(full_p)}  {len(full)} 字节，{n} 条记录，共 {total} 手\n")
    for j in range(total):
        if j < 2 or j >= total - 6:
            print(f"  第{j + 1:3d}手  {describe(recs, starts[j], starts[j + 1])}")
        elif j == 2:
            print("     ...")

    if args.undo is None:
        print("\n（只读。加 --undo 悔棋）")
        return

    k = args.undo
    if not 1 <= k < total:
        die(f"只能悔 1..{total - 1} 手")
    cut = starts[total - k]          # 悔棋后保留的记录数

    print(f"\n将删除最后 {k} 手：")
    for j in range(total - k, total):
        print(f"    第{j + 1}手  {describe(recs, starts[j], starts[j + 1])}")

    new_full = full[:LOG_OFF + cut * REC_SIZE]
    for o in COUNT_OFF:
        struct.pack_into("<i", new_full, o, cut)
    struct.pack_into("<i", short, size_off, len(new_full))

    check_not_running()              # 写之前再确认一次
    for p in (full_p, short_p):
        if not os.path.exists(p + ".bak"):
            shutil.copy2(p, p + ".bak")
            print(f"  已备份 {os.path.basename(p)}.bak")
    open(full_p, "wb").write(new_full)
    open(short_p, "wb").write(short)

    print(f"\n完成: {n} -> {cut} 条记录，{len(full)} -> {len(new_full)} 字节")
    print(f"  头部计数器 {tuple(hex(o) for o in COUNT_OFF)} 已同步为 {cut}")
    print(f"  savedDataSize (偏移 {size_off}) 已同步为 {len(new_full)}")
    print("  还原: python3 undo_move.py --restore")


if __name__ == "__main__":
    main()
