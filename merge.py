#!/usr/bin/env python3
"""把一批译文合并进 translations.json。

用法:  python3 merge.py <表名> <批次json文件>
       python3 merge.py --status          查看各表翻译进度
"""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TRANS = os.path.join(ROOT, "translations.json")
SOURCE = os.path.join(ROOT, "source_texts.json")


def status():
    trans = json.load(open(TRANS))
    src = json.load(open(SOURCE))
    total_done = total_all = 0
    for table, rows in src.items():
        done = len(set(trans.get(table, {})) & set(rows))
        total_done += done
        total_all += len(rows)
        bar = "#" * int(28 * done / len(rows)) if rows else ""
        print(f"  {table:16s} {done:4d}/{len(rows):4d}  {bar:<28s} {100*done//max(len(rows),1):3d}%")
    print(f"  {'合计':14s} {total_done:4d}/{total_all:4d}  {100*total_done//max(total_all,1):3d}%")
    for table, rows in src.items():
        missing = [k for k in rows if k not in trans.get(table, {})]
        if missing:
            print(f"\n  {table} 待翻 {len(missing)} 条，下一条: {missing[0]}")


def main():
    if "--status" in sys.argv:
        status()
        return
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    table, path = sys.argv[1], sys.argv[2]
    trans = json.load(open(TRANS))
    batch = json.load(open(path))
    src = json.load(open(SOURCE)).get(table, {})

    unknown = [k for k in batch if k not in src]
    if unknown:
        print(f"警告: {len(unknown)} 个键在原文中不存在: {unknown[:5]}")
    trans.setdefault(table, {})
    before = len(trans[table])
    trans[table].update(batch)
    with open(TRANS, "w") as f:
        json.dump(trans, f, ensure_ascii=False, indent=1)
    print(f"{table}: {before} -> {len(trans[table])} 条 (本批 {len(batch)})")


if __name__ == "__main__":
    main()
