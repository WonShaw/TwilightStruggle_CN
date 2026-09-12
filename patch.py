#!/usr/bin/env python3
"""
冷战热斗 (Twilight Struggle, Playdek/Steam macOS) 汉化补丁工具

从 backup/ 干净重建，每次全量应用，可重复运行。
  1. 把 Font(846) 的内嵌 TTF 换成中文字体
  2. 在 TMP Settings 里挂上全局回退字体，使所有字体资产都能显示汉字
  3. 按 translations.json 替换 resources.assets 里的字符串表词条
  4. 按 countries.json + scene_ui.json 替换 level2/level3 场景里的
     地图国名与 HUD 文本
  5. 装回游戏目录并用原权限重新 ad-hoc 签名

场景改动的安全边界：只改 m_Script 指向 TextMeshProUGUI 的组件，
且原文必须正好落在 m_text 字段偏移上。存内部标识的组件（另一个脚本，
国名在偏移 148）绝不触碰——改了会破坏卡牌效果的国家查找。

用法:  python3 patch.py [--dry-run] [--skip-scenes]
"""
import hashlib, json, os, shutil, struct, subprocess, sys
from gamepath import find_app

ROOT = os.path.dirname(os.path.abspath(__file__))   # 跟随本文件所在目录，整个文件夹可随意移动
BACKUP_DIR = os.path.join(ROOT, "backup")
FONT = os.path.join(ROOT, "ZH_sub.ttf")
TRANS = os.path.join(ROOT, "translations.json")
COUNTRIES = os.path.join(ROOT, "countries.json")
SCENE_UI = os.path.join(ROOT, "scene_ui.json")
BUILD = os.path.join(ROOT, "build")
MANIFEST = os.path.join(BACKUP_DIR, "MANIFEST.json")
APP = find_app()          # 从 Steam 库清单定位；--game-path / TS_GAME_PATH 可指定
DATA = os.path.join(APP, "Contents/Resources/Data")

FONT_PID = 846            # Font 对象 "LiberationSans"，回退字体资产的来源字体
TMPSETTINGS_PID = 30710   # TMP Settings
FALLBACK_PID = 30703      # "LiberationSans SDF - Fallback"，动态模式字体资产
FALLBACK_LIST_OFF = 172   # TMP Settings 内 m_fallbackFontAssets 的 size 字段偏移
MTEXT_OFF = 92            # TextMeshProUGUI 的 m_text 数据偏移（长度字段在其前 4 字节）
SCENES = ["level2", "level3"]
PATCHED_FILES = ["resources.assets"] + SCENES

# 用对象名而非仅凭编号来确认目标，游戏更新后编号可能整体位移
EXPECT_NAMES = {846: "LiberationSans", 30703: "LiberationSans SDF - Fallback",
                30710: "TMP Settings"}

DRY = "--dry-run" in sys.argv
SKIP_SCENES = "--skip-scenes" in sys.argv


def die(msg):
    print("错误: " + msg, file=sys.stderr)
    sys.exit(1)


def check_not_running():
    r = subprocess.run(["pgrep", "-f", "TwilightStruggle.app/Contents/MacOS"],
                       capture_output=True, text=True)
    if r.stdout.strip():
        die("游戏正在运行，请先退出后再打补丁。")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_backup_fresh():
    """确认 backup/ 与磁盘上的游戏是同一版本。

    游戏被 Steam 更新（或点了「验证游戏文件完整性」）之后，backup/ 里就是旧版，
    此时若照常打补丁，等于把旧版文件翻译好装回去——游戏被静默降级。必须拦住。
    """
    if not os.path.exists(MANIFEST):
        print("提示: 缺少 backup/MANIFEST.json，跳过版本校验（旧版备份）。")
        return
    m = json.load(open(MANIFEST))
    stale = []
    for f in PATCHED_FILES:
        cur = sha256(os.path.join(DATA, f))
        if cur not in (m["original"].get(f), m["patched"].get(f)):
            stale.append(f)
    if stale:
        die("游戏文件与 backup/ 对不上: " + ", ".join(stale) + "\n"
            "  多半是 Steam 更新过游戏，或你点了「验证游戏文件完整性」。\n"
            "  此时打补丁会把旧版文件装回去，等于降级——已中止。\n\n"
            "  正确做法：\n"
            "    1. 在 Steam 里「验证游戏文件完整性」，确保是干净的新版英文原版\n"
            "    2. rm -rf backup && python3 rebuild_backup.py   # 重新采集备份\n"
            "    3. python3 patch.py --dry-run                   # 确认各表命中数正常\n"
            "  若命中数骤降或报找不到对象，说明新版结构变了，需要重新探测 path ID。")


def check_objects(objs):
    """按名字确认关键对象没有因版本更新而位移。"""
    for pid, want in EXPECT_NAMES.items():
        if pid not in objs:
            die(f"找不到对象 {pid}（应为 {want!r}）——游戏结构已变，需重新探测 path ID。")
        try:
            got = objs[pid].read(check_read=False).m_Name
        except Exception:
            got = None
        if got != want:
            die(f"对象 {pid} 应为 {want!r}，实际是 {got!r}——游戏结构已变，"
                "编号发生位移，需重新探测 path ID。")


def update_manifest():
    m = (json.load(open(MANIFEST)) if os.path.exists(MANIFEST)
         else {"original": {f: sha256(os.path.join(BACKUP_DIR, f)) for f in PATCHED_FILES}})
    m["patched"] = {f: sha256(os.path.join(DATA, f)) for f in PATCHED_FILES}
    json.dump(m, open(MANIFEST, "w"), indent=1)


def read_str(raw, data_off):
    """读取偏移处的长度前缀字符串，返回 (文本, 该字段结束后的对齐偏移)。"""
    n, = struct.unpack("<I", raw[data_off - 4:data_off])
    if n > len(raw) - data_off or n > 4096:
        return None, None
    try:
        s = raw[data_off:data_off + n].decode("utf-8")
    except UnicodeDecodeError:
        return None, None
    end = data_off + n
    return s, end + (-end % 4)


def write_str(raw, data_off, new_text):
    """把偏移处的字符串替换成 new_text，保持 4 字节对齐。"""
    _, end = read_str(raw, data_off)
    b = new_text.encode("utf-8")
    pad = b"\0" * (-len(b) % 4)
    return raw[:data_off - 4] + struct.pack("<I", len(b)) + b + pad + raw[end:]


# ---------------------------------------------------------------- 字符串表

def patch_sheet(script, mapping, hit):
    header, sep, body = script.partition("\n")
    if not sep:
        die("无法识别的字符串表结构")
    outer = json.loads(body)
    for sheet in outer.values():
        rows = max(int(k.split(":")[0]) for k in sheet)
        cols = {sheet.get(f"1:{c}"): c
                for c in range(1, 40) if sheet.get(f"1:{c}") not in (None, "null")}
        en = cols.get("EN")
        if en is None:
            continue
        for r in range(2, rows + 1):
            k = sheet.get(f"{r}:1")
            if k in mapping:
                sheet[f"{r}:{en}"] = mapping[k]
                hit.add(k)
    return header + sep + json.dumps(outer, ensure_ascii=True, separators=(",", ":"))


def patch_resources(UnityPy, trans):
    env = UnityPy.load(os.path.join(BACKUP_DIR, "resources.assets"))
    objs = {o.path_id: o for o in env.objects}
    check_objects(objs)

    zh = open(FONT, "rb").read()
    d = objs[FONT_PID].read()
    old = len(d.m_FontData)
    d.m_FontData = zh
    d.save()
    print(f"[1] 字体: {old:,} -> {len(zh):,} 字节")

    raw = bytearray(objs[TMPSETTINGS_PID].get_raw_data())
    n, = struct.unpack("<i", raw[FALLBACK_LIST_OFF:FALLBACK_LIST_OFF + 4])
    if n == 0:
        objs[TMPSETTINGS_PID].set_raw_data(
            bytes(raw[:FALLBACK_LIST_OFF]) + struct.pack("<i", 1)
            + struct.pack("<iq", 0, FALLBACK_PID) + bytes(raw[FALLBACK_LIST_OFF + 4:]))
        print(f"[2] TMP 全局回退: 空 -> [{FALLBACK_PID}]")
    elif n == 1 and struct.unpack("<iq", raw[FALLBACK_LIST_OFF + 4:
                                             FALLBACK_LIST_OFF + 16]) == (0, FALLBACK_PID):
        print("[2] TMP 全局回退: 已挂载，跳过")
    else:
        die(f"TMP Settings 偏移 {FALLBACK_LIST_OFF} 处读到 {n}，不是预期的回退列表长度。\n"
            "  多半是游戏更新后序列化布局变了。若强行继续，中文会渲染成方块——已中止。")

    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        t = o.read()
        if t.m_Name not in trans:
            continue
        mapping = trans[t.m_Name]
        hit = set()
        t.m_Script = patch_sheet(t.m_Script, mapping, hit)
        t.save()
        miss = sorted(set(mapping) - hit)
        print(f"[3] {t.m_Name}: 替换 {len(hit)}/{len(mapping)} 条"
              + (f"，未命中 {miss[:6]}{'...' if len(miss) > 6 else ''}" if miss else ""))
    return env


# ---------------------------------------------------------------- 场景文本

def patch_scene(UnityPy, fname, mapping):
    env = UnityPy.load(os.path.join(BACKUP_DIR, fname))
    # 自动探测 TextMeshProUGUI 的脚本 PPtr：原文恰好落在 m_text 偏移上的组件
    from collections import Counter
    votes = Counter()
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        raw = o.get_raw_data()
        if len(raw) < MTEXT_OFF + 8:
            continue
        s, _ = read_str(raw, MTEXT_OFF)
        if s in mapping:
            votes[struct.unpack("<iq", raw[16:28])] += 1
    if not votes:
        print(f"[4] {fname}: 未找到可替换文本，跳过")
        return None, 0
    script, n = votes.most_common(1)[0]
    if len(votes) > 1:
        print(f"[4] {fname}: 警告 — 命中多个脚本 {dict(votes)}，只改 {script}")

    changed = 0
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        raw = o.get_raw_data()
        if len(raw) < MTEXT_OFF + 8:
            continue
        if struct.unpack("<iq", raw[16:28]) != script:
            continue
        s, _ = read_str(raw, MTEXT_OFF)
        if s in mapping:
            o.set_raw_data(write_str(raw, MTEXT_OFF, mapping[s]))
            changed += 1
    print(f"[4] {fname}: 场景文本替换 {changed} 处 (脚本 {script})")
    return env, changed


# ---------------------------------------------------------------- 主流程

def main():
    for p in (BACKUP_DIR, FONT, TRANS, COUNTRIES):
        if not os.path.exists(p):
            die("缺少文件: " + p)
    check_not_running()
    check_backup_fresh()

    import UnityPy
    trans = {k: v for k, v in json.load(open(TRANS)).items() if not k.startswith("_")}
    gloss = json.load(open(COUNTRIES))
    # 场景内按显示文本替换：语义表兜底 -> map_labels 覆盖缩写/区域名 -> HUD 文本
    scene_map = dict(gloss["countries"])
    scene_map.update(gloss["map_labels"])
    if os.path.exists(SCENE_UI):
        scene_map.update({k: v for k, v in json.load(open(SCENE_UI)).items()
                          if not k.startswith("_")})

    envs = {"resources.assets": patch_resources(UnityPy, trans)}
    if not SKIP_SCENES:
        for s in SCENES:
            env, n = patch_scene(UnityPy, s, scene_map)
            if env is not None and n:
                envs[s] = env

    if DRY:
        print("\n[dry-run] 未写入。")
        return

    os.makedirs(BUILD, exist_ok=True)
    for name, env in envs.items():
        env.save(out_path=BUILD)
        src = os.path.join(BUILD, name)
        shutil.copy(src, os.path.join(DATA, name))
        print(f"[5] 已安装 {name} ({os.path.getsize(src):,} 字节)")

    ent = os.path.join(BUILD, "ent.plist")
    with open(ent, "wb") as f:
        f.write(subprocess.run(["codesign", "-d", "--entitlements", "-", "--xml", APP],
                               capture_output=True).stdout)
    subprocess.run(["codesign", "--force", "--sign", "-", "--entitlements", ent,
                    "--options", "runtime", "--identifier",
                    "unity.Playdek.TwilightStruggle", APP],
                   check=True, capture_output=True)
    v = subprocess.run(["codesign", "--verify", APP], capture_output=True, text=True)
    print("[5] 重新签名: " + ("通过" if v.returncode == 0 else "失败 " + v.stderr))
    update_manifest()


if __name__ == "__main__":
    main()
