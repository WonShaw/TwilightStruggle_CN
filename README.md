# 冷战热斗 汉化补丁（macOS / Steam 版）

> 非官方民间汉化，与 Playdek、GMT Games 无关，也未获其授权。
> 本仓库只包含补丁脚本与译文，**不含任何游戏文件或字体文件**，
> 使用前需自行拥有 Steam 正版游戏。补丁会修改本机游戏文件并使原厂签名失效，
> 风险自负；`restore.sh` 可随时还原。

针对 Playdek 的《Twilight Struggle》Steam macOS 版（Unity 6000.0.58f2，IL2CPP）。
覆盖 1208 条字符串表词条 + 688 处场景文本（地图国名与 HUD）。
卡牌、界面、规则书与游戏内帮助页均已汉化。

## 日常使用

在本文件夹里执行：

```bash
python3 patch.py
```

补丁从 `backup/` 干净重建，可以反复运行。

### Steam 更新游戏之后

**不要直接重跑 `patch.py`。** 更新后磁盘上是新版，而 `backup/` 里还是旧版，
照常打补丁等于把旧版文件翻译好装回去，游戏被静默降级。
`patch.py` 会用 `backup/MANIFEST.json` 里的哈希比对并主动拦下这种情况。

正确流程：

```bash
# 1. 先在 Steam 里「验证游戏文件完整性」，拿到干净的新版英文原版
python3 rebuild_backup.py     # 2. 重新采集备份（会拒绝从汉化版采集）
python3 patch.py --dry-run    # 3. 确认各表命中数正常
python3 patch.py              # 4. 命中数正常再真正打上
```

第 3 步是关键：若命中数骤降，或报「找不到对象 / 结构已变」，说明新版重新打了包，
`patch.py` 顶部那几个 path ID 已经位移，需要重新探测后才能继续。

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
| `rebuild_backup.py` | 游戏更新后重新采集 `backup/` |
| `verify.py` | 译文标记校验 |
| `merge.py` | 分批合并译文；`--status` 看进度 |
| `translations.json` | 1208 条译文 |
| `countries.json` | 国名与地图标签对照表 |
| `scene_ui.json` | `level2`/`level3` 场景里写死的 HUD 文本对照表 |
| `source_texts.json` | 英文原文，供对照 |
| `GLOSSARY.md` | 术语规范 |
| `make_font.py` | 生成 `ZH_sub.ttf`；`--source` 可换其他字体 |
| `ZH_sub.ttf` | 中文字体（冬青黑体简体中文子集，2.1 万字，8.2 MB） |
| `backup/` | 原始文件备份 + `MANIFEST.json` 校验哈希，**不要删**，见下 |
| `savetool/` | 存档工具，与汉化无关，见文末 |

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

地图国名与 HUD 文字（`Player Hand`、`Next Project:` 等）在 `level2`/`level3`
场景里是 TextMeshProUGUI 组件的 `m_text`，不走字符串表。
**只改 `m_Script` 指向 TMP 文本组件的对象**（脚本 PPtr `(1, 1417)`，国名在偏移 92）；
另有一组脚本 `(1, 563)` 的组件同样存着国名（偏移 148），那是内部标识，
改了会破坏卡牌效果的国家查找——绝不能碰。

### 规则书与帮助页为什么只翻表就够

`level2` 场景里也躺着一整份规则书和帮助页的英文原文，看上去像是要逐条替换场景文本，
其实不必：这些文本对象旁边还挂着一个本地化组件（脚本 PPtr `(1, 890)`），
值形如 `${Help_Coup_Purpose}`，运行时按这个键去 `TS_RulesTutorial` 表取译文覆盖显示。
`level2` 里共 636 处这样的绑定，其中 239 处指向 `TS_RulesTutorial`。
所以场景里那份英文只是设计期的占位内容，**翻表即可，不用动场景**。

反过来，少数文本对象没挂本地化组件，会原样显示场景里的文字，
这部分才需要写进 `scene_ui.json`。要重新核对哪些是漏网的，可以按
「有 `(1, 1417)` 组件、同一 GameObject 上没有 `(1, 890)` 组件」筛一遍。

## 游戏更新后会怎样

三类失效，严重程度不同，脚本对前两类都会**报错中止**而不是静默出错：

| 失效点 | 后果 | 防线 |
|---|---|---|
| `backup/` 过期 | 游戏被降级，且看不出异常 | `MANIFEST.json` 哈希比对，不符即中止 |
| path ID 位移 | 换错字体、回退没挂上（满屏方块） | 按对象名核对 846/30703/30710；TMP 偏移读到非预期值即中止 |
| 原文措辞变化 | 该条保持英文 | 无需处理，优雅降级 |

译文的键（`Card_004Text` 之类）很稳定，一般能跨版本沿用；
地图与 HUD 按原文精确匹配，改了措辞的条目会退回英文，不会出错。

## 附：存档悔棋工具

`savetool/` 和汉化没关系，是顺手做的，放这儿免得丢。

存档在 `~/Library/Application Support/unity.Playdek.TwilightStruggle/`，
一局占两个文件：`Save1Full.dat` 是局面，`Save1Short.dat` 是读档列表用的摘要
（.NET BinaryFormatter 序列化，字段名就写在流里）。

关键点是 **`Save1Full.dat` 里没有棋盘状态**——5 KB 装不下 86 个国家的影响力、
手牌和弃牌堆。它是 224 字节头 + N 条 16 字节操作记录，游戏靠**重放**这些记录
还原局面。所以悔棋 = 砍掉末尾记录 + 同步计数器：

```bash
python3 savetool/undo_move.py            # 列出所有手，只读
python3 savetool/undo_move.py --undo 1   # 悔一手
python3 savetool/undo_move.py --restore  # 从 .bak 还原
```

必须**整手删**。一手是从「打出一张牌」（动作码 `0xa01X`）起，到下一次出牌为止，
中间是选用途和逐个作用到国家。只删末尾一条会留下「牌打出去了但没落子」的残缺
状态，重放到那里就卡住。

要改的地方一共三处，少一处游戏就读不出来：

| 位置 | 内容 |
|---|---|
| `Save1Full.dat` 尾部 | 截掉整手的记录 |
| 头部 `0xB8` / `0xC8` / `0xD4` | 三处记录数，必须一起改 |
| `Save1Short.dat` 的 `savedDataSize` | 与 Full 的新大小对上 |

头部 `0xB0` 那个值验过不是 CRC32/Adler32/sum/xor 里的任何一种，是随机数种子
（骰子要能跟着日志一起重放），不用动；`0xCC`/`0xD0` 的两个 `-1` 也原样保留。

工具默认只读，写之前会检查：游戏没在运行（**游戏退出时会把内存里的局面写回存档，
边玩边改等于白改**）、三处计数器彼此一致且与文件长度相符、`savedDataSize` 对得上。
任一不符直接中止，不做部分修改。`savedDataSize` 的偏移若因游戏更新而位移，
会全文搜该值，唯一命中才用，有歧义则报错。

`savetool/nrbf.py` 是配套的 BinaryFormatter 解析器，用来读摘要和
`OfflineProfiles.dat`（战绩），字段位移后靠它重新对偏移。

## 已知限制

- **顶部提示条仍是英文**，如 `Place 7 Influence`、`Waiting for Opponent to decide...`、
  `2 OPS: Roll 1-3`、`Select a Region`。这些不在任何资源表里，而是硬编码成
  IL2CPP 字面量存在 `il2cpp_data/Metadata/global-metadata.dat`。
  该文件的字面量数据区（偏移 113768，长 408692）紧邻下一分区，中间没有空隙，
  只能在原字节长度内原地替换，改坏了游戏直接无法启动——风险与收益不成正比，故放弃。
- `level2` 里还剩约 30 条英文，都是设计期占位内容（`PlayerName12345`、`Text goes here`、
  `Turn ##`、`Military Coup in Phillipines` 之类）和孤立单词（`Before`/`After`/`War`/
  `Country`/`Early`）。前者游戏里不会显示，后者上下文不明、全局替换有误伤风险，故未翻
- **联机对战未验证**。单机确认正常；改过文件是否影响联机校验不清楚，建议只在单机用
- 逗号句号的垂直位置偏居中，是冬青黑体的风格，换思源黑体可改善
- `Game Center`、`Playdek`、`Android` 等专有名词按惯例保留英文
- 修改会使原厂签名失效，`patch.py` 会用原权限做 ad-hoc 重签名；
  这在本机运行没问题，但游戏不再是 Playdek 官方签名
