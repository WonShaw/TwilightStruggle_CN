#!/usr/bin/env python3
"""校验译文：标记、占位符必须与原文一致；长度异常给出提示。"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
trans = json.load(open(os.path.join(ROOT, "translations.json")))
src = json.load(open(os.path.join(ROOT, "source_texts.json")))

TAG = re.compile(r"</?(?:br|i|b|u|nobr|font|color|cspace|size|align|indent"
                 r"|margin|margin-right|margin-left|allcaps|sprite|pos|space"
                 r"|line-height|mspace|width|voffset|s|sub|sup)\b[^>]*>", re.I)
PLACE = re.compile(r"\{\d+\}|%[ds]%?%?")

errors, warns = [], []
for table, rows in src.items():
    for key, en in rows.items():
        zh = trans.get(table, {}).get(key)
        if zh is None:
            errors.append(f"{table}/{key}: 缺译文")
            continue
        # 标记：数量与种类必须一致（属性可不同，只比标记名与开闭）
        def norm(s):
            return sorted(m.group(0).split("=")[0].rstrip(">").lower() + ">"
                          for m in TAG.finditer(s))
        if norm(en) != norm(zh):
            errors.append(f"{table}/{key}: 标记不一致\n    原: {norm(en)}\n    译: {norm(zh)}")
        # 占位符必须原样保留
        if sorted(PLACE.findall(en)) != sorted(PLACE.findall(zh)):
            errors.append(f"{table}/{key}: 占位符不一致 {PLACE.findall(en)} -> {PLACE.findall(zh)}")
        # 中文应显著短于英文；过长可能是漏译
        if len(zh) > len(en) * 1.1 and len(en) > 20:
            warns.append(f"{table}/{key}: 译文偏长 ({len(en)} -> {len(zh)})")
        if re.search(r"[A-Za-z]{4,}", re.sub(TAG, "", zh)):
            leftover = re.findall(r"[A-Za-z]{4,}", re.sub(TAG, "", zh))
            warns.append(f"{table}/{key}: 残留英文 {leftover[:4]}")

for e in errors:
    print("错误 " + e)
for w in warns:
    print("提示 " + w)
print(f"\n共 {sum(len(r) for r in src.values())} 条；错误 {len(errors)}，提示 {len(warns)}")
sys.exit(1 if errors else 0)
