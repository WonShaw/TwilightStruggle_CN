# 冷战热斗 汉化补丁（macOS / Steam 版）

> 非官方民间汉化，与 Playdek、GMT Games 无关，也未获其授权。
> 本仓库只包含补丁脚本与译文，**不含任何游戏文件或字体文件**，
> 使用前需自行拥有 Steam 正版游戏。补丁会修改本机游戏文件并使原厂签名失效，
> 风险自负；`restore.sh` 可随时还原。

针对 Playdek 的《Twilight Struggle》Steam macOS 版（Unity 6000.0.58f2，IL2CPP）。
覆盖 845 条游戏文本 + 211 处地图标签。规则书与教程未翻译。

## 日常使用

在本文件夹里执行：

```bash
python3 patch.py
```

**Steam 每次更新游戏后，补丁会被覆盖，重跑上面这条命令即可。**
点了「验证游戏文件完整性」也一样。补丁从 `backup/` 干净重建，可以反复运行。

还原成英文原版：

```bash
./restore.sh
```

所有脚本都以自身所在目录定位资源，整个文件夹可以随意移动或改名，
只要 `backup/` 一起跟着走就行。

## 改词条

编辑 `translations.json`（键是游戏内部标识，值是中文），然后：

```bash
python3 verify.py && python3 patch.py
```

`verify.py` 会检查 `<br>` `<i>` `{0}` `%d` 这些标记有没有和原文对上——漏一个 `<br>`
卡面排版就会错位，所以别跳过这步。国名改 `countries.json`，用词规范见 `GLOSSARY.md`。

## 文件说明

| 文件 | 用途 |
|---|---|
| `patch.py` | 主补丁工具，从 backup 重建并安装、重签名 |
| `restore.sh` | 一键还原英文原版 |
| `verify.py` | 译文标记校验 |
| `merge.py` | 分批合并译文；`--status` 看进度 |
| `translations.json` | 845 条译文 |
| `countries.json` | 国名与地图标签对照表 |
| `source_texts.json` | 英文原文，供对照 |
| `GLOSSARY.md` | 术语规范 |
| `make_font.py` | 生成 `ZH_sub.ttf`；`--source` 可换其他字体 |
| `ZH_sub.ttf` | 中文字体（冬青黑体简体中文子集，2.1 万字，8.2 MB） |
| `backup/` | 原始文件备份，**不要删**，见下 |

## 关于 backup/ 和 ZH_sub.ttf

两者都**不是运行时生成**的，且性质不同：

- **`ZH_sub.ttf` 可重现**：`python3 make_font.py` 即可从系统字体重新生成。
- **`backup/` 不可重现**：它是游戏**英文原版**的副本，而磁盘上的游戏已被汉化。
  删掉后从游戏目录再拷一份，得到的是汉化版，`restore.sh` 将再也还原不回英文。
  真要重建，必须先在 Steam 里「验证游戏文件完整性」下回原版，拷完备份再重打补丁。

两者都是第三方版权内容（Playdek 的游戏资源、苹果的冬青黑体），
已列入 `.gitignore`，**不要提交到公开仓库或对外分发**。

## 技术原理

游戏本身有一套表格式多语言系统，甚至预留了 `CH` 列，但只填了 6 条机翻，
卡牌和规则书压根没有任何非英文译文。所以走的不是它的语言切换，而是直接覆盖 `EN` 列。

真正的难点是字体：游戏所有字体都是 TextMeshPro 的静态 SDF 图集，
全是拉丁字体，一个汉字字形都没有。解法是利用 TMP 的**全局回退字体链**——

1. 把 `Font(846)` 内嵌的 LiberationSans TTF 换成中文字体子集
2. 该 Font 是动态模式字体资产 `LiberationSans SDF - Fallback (30703)` 的来源字体，
   动态模式意味着字形在运行时按需生成，不受预烤图集限制
3. 在 `TMP Settings (30710)` 的 `m_fallbackFontAssets` 里挂上 30703

这样任何字体渲染到汉字时都会回退到这里现场生成字形，不必逐个替换十几个字体图集。
斜体、`<br>` 断行、CJK 标点避头尾都能正常工作。

地图国名在 `level2`/`level3` 场景里是 TextMeshProUGUI 组件的 `m_text`。
**只改 `m_Script` 指向 TMP 文本组件的对象**（脚本 PPtr `(1, 1417)`，国名在偏移 92）；
另有一组脚本 `(1, 563)` 的组件同样存着国名（偏移 148），那是内部标识，
改了会破坏卡牌效果的国家查找——绝不能碰。

## 已知限制

- **顶部提示条仍是英文**，如 `Place 7 Influence`、`Waiting for Opponent to decide...`、
  `2 OPS: Roll 1-3`、`Select a Region`。这些不在任何资源表里，而是硬编码成
  IL2CPP 字面量存在 `il2cpp_data/Metadata/global-metadata.dat`。
  该文件的字面量数据区（偏移 113768，长 408692）紧邻下一分区，中间没有空隙，
  只能在原字节长度内原地替换，改坏了游戏直接无法启动——风险与收益不成正比，故放弃。
- **游戏内 HUD 部分英文**：`PLAYER HAND`、`DISCARD`、`REMOVED`、`Game Log`、
  `NEXT PROJECT:` 等写死在 `level2` 场景里。技术上可用现有机制翻译，只是尚未做。
- **规则书和教程仍是英文**（`TS_RulesTutorial` 19.5 万字符，以及 `level2` 里的
  内置规则帮助页，均未在本次范围内）
- **联机对战未验证**。单机确认正常；改过文件是否影响联机校验不清楚，建议只在单机用
- 逗号句号的垂直位置偏居中，是冬青黑体的风格，换思源黑体可改善
- `Game Center`、`Playdek`、`Android` 等专有名词按惯例保留英文
- 修改会使原厂签名失效，`patch.py` 会用原权限做 ad-hoc 重签名；
  这在本机运行没问题，但游戏不再是 Playdek 官方签名
