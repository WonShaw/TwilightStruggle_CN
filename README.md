# 冷战热斗 汉化补丁（macOS / Steam 版）

> 非官方民间汉化，与 Playdek、GMT Games 无关，也未获其授权。
> 本仓库只包含补丁脚本与译文，**不含任何游戏文件或字体文件**，
> 使用前需自行拥有 Steam 正版游戏。补丁会修改本机游戏文件并使原厂签名失效，
> 风险自负；`restore.sh` 可随时还原。

针对 Playdek 的《Twilight Struggle》Steam macOS 版。卡牌、界面、规则书与游戏内帮助页均已汉化。

## 需要什么

- macOS，已通过 Steam 安装好游戏，并至少启动过一次
- Python 3.9 或更新（终端里 `python3 --version` 能看到版本号即可）

## 首次安装

在本文件夹里依次执行四条命令：

```bash
python3 -m pip install -r requirements.txt
```

```bash
python3 make_font.py
```

```bash
python3 rebuild_backup.py
```

```bash
python3 patch.py
```

四步分别是：装依赖、从系统自带的冬青黑体生成中文字体、把游戏英文原版备份到 `backup/`、打补丁。
最后一步结束时看到 `重新签名: 通过` 就完成了，启动游戏即为中文。

游戏位置会从 Steam 的库清单自动找到，装在外置盘或第二个库也没关系。
如果报「找不到《Twilight Struggle》」，用 `--game-path` 指定 `TwilightStruggle.app` 的位置：

```bash
python3 patch.py --game-path '/Volumes/外置盘/SteamLibrary/steamapps/common/Twilight Struggle/TwilightStruggle.app'
```

`rebuild_backup.py` 和 `restore.sh` 也认这个参数，或者设环境变量 `TS_GAME_PATH`。

## 之后

**还原成英文原版：**

```bash
./restore.sh
```

**重新打补丁**（比如改了译文）：直接再跑 `python3 patch.py`，它每次都从 `backup/` 干净重建，可以反复运行。

**Steam 更新了游戏之后：** 不要直接重跑 `patch.py`——它会发现 `backup/` 是旧版并拒绝执行，
以免把旧版文件装回去。正确顺序：

1. 在 Steam 里对本游戏执行「验证游戏文件完整性」，拿到干净的新版
2. `python3 rebuild_backup.py` 重新备份
3. `python3 patch.py`

若第 3 步报「找不到对象」或「结构已变」，说明新版重新打了包，补丁需要更新，请提 issue。

**不要删 `backup/`。** 它是游戏英文原版的唯一副本；删了之后想还原英文，只能先在 Steam 里「验证游戏文件完整性」再重新备份。

整个文件夹可以随意移动或改名，`backup/` 跟着走就行。

## 改译文

编辑 `translations.json`（键是游戏内部标识，值是中文），然后：

```bash
python3 verify.py && python3 patch.py
```

`verify.py` 会检查 `<br>` `<i>` `{0}` 这些标记有没有和原文对上，漏一个卡面排版就会错位，别跳过。
国名在 `countries.json`，用词规范见 `GLOSSARY.md`。

想换字体（例如思源黑体）：`python3 make_font.py --source 字体文件.otf`，然后重新 `patch.py`。

## 已知限制

- 顶部提示条仍是英文（`Place 7 Influence`、`Select a Region` 这类）。它们硬编码在程序里，不在可改的资源中
- 11 张卡的标题在小尺寸卡面上偏高约半行（英文标题占两行的位置，中文只需一行）
- **联机对战未验证**，建议只在单机用
- 逗号句号偏居中，是冬青黑体的字形风格，换思源黑体可改善
- `Game Center`、`Playdek`、`Android` 等专有名词保留英文
- 打补丁后游戏不再是 Playdek 官方签名，而是本机 ad-hoc 签名

## 常见报错

| 报错 | 原因 | 处理 |
|---|---|---|
| 找不到《Twilight Struggle》 | 游戏不在 Steam 库清单里 | 用 `--game-path` 指定 |
| 游戏正在运行 | — | 退出游戏再跑 |
| 缺少文件: …/backup | 还没备份 | `python3 rebuild_backup.py` |
| 缺少文件: …/ZH_sub.ttf | 还没生成字体 | `python3 make_font.py` |
| 游戏文件与 backup/ 对不上 | Steam 更新过游戏 | 按上面「Steam 更新了游戏之后」的顺序 |
| 磁盘上的游戏已经是汉化版 | 在汉化版上跑了 `rebuild_backup.py` | Steam「验证游戏文件完整性」后再跑 |
| 找不到对象 / 结构已变 | 新版游戏重新打包 | 提 issue |

## 附：存档悔棋工具

`savetool/` 和汉化无关，是个单机存档的悔棋工具。**先退出游戏再用**，游戏退出时会覆盖存档。

```bash
python3 savetool/undo_move.py            # 列出这局的每一手，只读
python3 savetool/undo_move.py --undo 1   # 悔一手（整手撤销，不能只撤半手）
python3 savetool/undo_move.py --restore  # 从 .bak 还原
```

## 文件说明

| 文件 | 用途 |
|---|---|
| `patch.py` | 打补丁 |
| `restore.sh` | 还原英文原版 |
| `rebuild_backup.py` | 备份游戏英文原版到 `backup/` |
| `make_font.py` | 生成中文字体 `ZH_sub.ttf` |
| `gamepath.py` | 定位游戏安装位置，上面三个脚本共用 |
| `verify.py` | 改译文后校验标记 |
| `merge.py` | 分批合并译文，`--status` 看进度 |
| `translations.json` | 译文 |
| `countries.json` | 国名与地图标签 |
| `scene_ui.json` | 地图与 HUD 上写死的文本 |
| `source_texts.json` | 英文原文，供校验对照 |
| `GLOSSARY.md` | 术语规范 |
| `savetool/` | 存档悔棋工具 |
| `CLAUDE.md` | 技术备忘：文件格式、字体机制、path ID、存档结构等，改代码前先看 |
| `backup/`、`ZH_sub.ttf` | 本地生成，不在仓库里，也不要分发 |
