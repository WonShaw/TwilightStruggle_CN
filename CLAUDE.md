# 技术备忘

给改代码的人和 AI 看的。用户操作说明在 `README.md`，这里不重复。

## 硬约束

- **只重签主 app，绝不碰 `Contents/PlugIns/` 下任何 bundle。** 2026-09-05 曾对
  `TwilightStruggleLib-OSX.bundle`（原生 C++ AI 库）做过一次 ad-hoc 重签，签出来的
  CodeDirectory 只有 58 页哈希（原厂 229 页），1.9 MB 二进制大半不在签名覆盖内，
  之后每局必在 `twilight_ai::AIHandlerThread::ThreadMain` 里 SIGSEGV，野指针地址每次不同。
  Steam「验证游戏文件完整性」还原原厂签名后恢复正常。`patch.py` 只写
  `resources.assets` / `level2` / `level3` 并重签外层 app，这是正确且足够的。
- **不动硬编码在 IL2CPP 里的字符串。** 顶部提示条（`Place 7 Influence` 等）和卡牌历史背景
  文字都在 `il2cpp_data/Metadata/global-metadata.dat` 的字面量区（偏移 113768，长 408692，
  14189 条），紧邻下一分区无空隙，只能原地等长替换，改坏直接无法启动。放弃。
- 脚本 PPtr `(1, 563)` 的组件在偏移 148 存着国名，那是内部标识，改了会破坏卡牌效果的
  国家查找。**绝不能碰。** 只改 `(1, 1417)`（TextMeshProUGUI）。
- `backup/`（Playdek 资源）和 `ZH_sub.ttf`（苹果冬青黑体子集）是第三方版权内容，已在
  `.gitignore`，不提交不分发。`source_texts.json` 是英文原文全量（10 万字符，含整本规则书），
  `patch.py` 不读它，只有 `verify.py` / `merge.py` 用；公开仓库时可换成提取器。
- 提交信息只写做了什么，不写推理过程。

## 环境

- 游戏：Unity 6000.0.58f2，IL2CPP，Steam buildid 21119605，app 版本 1.4.11 (167)。
  主程序和 AI 插件都是 universal，但 `libsteam_api.dylib` 只有 x86_64，所以整个进程跑在
  Rosetta 下。`open -a` 会选 arm64 → `DllNotFoundException` 立即退出；
  必须 `open "steam://rungameid/406290"`。
- Python：本机是 miniconda base（3.13），`UnityPy` / `fonttools` 用 pip 装在里面。
  `verify.py` / `merge.py` / `gamepath.py` / `savetool/` 只用标准库。
- 游戏路径：`gamepath.find_app()` 解析 `steamapps/libraryfolders.vdf`，按 app id 406290 找库，
  目录名读 `appmanifest_406290.acf` 的 `installdir`。`--game-path` / `TS_GAME_PATH` 覆盖。

## 字符串表格式

Playdek 的表格式多语言系统，存成 Unity `TextAsset`：第一行是时间戳头（如 `31 May, (11:19)`），
之后是 JSON，键 `"<sheetId>": {"<row>:<col>": "value"}`，第 1 行是表头。
`TS_Cards` 的 sheetId 是 `1631793870`，列 `{2:EN, 3:FR, 4:IT, 5:DE, 6:ES, 7:NL, 8:Notes}`，
非 EN 列全是字面字符串 `"null"`。游戏预留了 `CH` 列但只填了 6 条机翻，卡牌和规则书没有任何
非英文译文，所以不走语言切换，**直接覆盖 EN 列**。

六张表共 1208 条：TS_Cards 344、Common_Ingame 22、TS_Ingame 157、Common_Strings 322、
TS_Strings 50、TS_RulesTutorial 313。`patch.py` 输出的命中数应与此一致。

原始表里没有任何空值先例，所以需要"留空"时填一个空格（见下面 Title2）。

## 字体：TMP 全局回退链

游戏所有字体都是 TextMeshPro 静态 SDF 图集，全拉丁，一个汉字都没有。不逐个替换图集，
而是走 TMP 的全局回退：

1. `Font(846)`「LiberationSans」内嵌的 TTF 换成 `ZH_sub.ttf`
2. 它是动态模式字体资产 `LiberationSans SDF - Fallback (30703)` 的来源字体，
   动态模式在运行时按需生成字形
3. `TMP Settings (30710)` 的 `m_fallbackFontAssets`（偏移 172 处的 size 字段）挂上 30703

任何字体渲染到汉字都会回退到这里。斜体、`<br>`、CJK 避头尾都正常。
三个 path ID 按对象名核对（`EXPECT_NAMES`），偏移 172 读到非预期值即中止。

## 场景文本（level2 / level3）

地图国名和 HUD（`Player Hand`、`Next Project:`）是场景里 TextMeshProUGUI 的 `m_text`，
不走字符串表。MonoBehaviour 原始布局：`m_GameObject` PPtr 在字节 4:12，`m_Enabled` 字节 12，
`m_Script` PPtr `(int fileID, long pathID)` 字节 16:28，`m_text` 数据在偏移 92
（长度字段在前 4 字节；Unity 字符串 = 4 字节长度 + UTF-8 + 补齐到 4 字节对齐）。
TMP 脚本 PPtr 不写死，`patch_scene()` 按多数投票探测。

**规则书和帮助页不用改场景。** `level2` 里躺着的那份英文是设计期占位，旁边挂着本地化组件
（脚本 `(1, 890)`），值形如 `${Help_Coup_Purpose}`，运行时按键去 `TS_RulesTutorial` 取译文
覆盖。`level2` 共 636 处绑定，239 处指向 `TS_RulesTutorial`。翻表即可。
没挂 `(1, 890)` 的文本对象才会原样显示，那些才进 `scene_ui.json`。要重新核对：
筛「有 `(1, 1417)`、同一 GameObject 上没有 `(1, 890)`」。

`level2` 还剩约 30 条英文：设计期占位（`PlayerName12345`、`Turn ##`）游戏里不显示；
孤立单词（`Before` / `After` / `War`）上下文不明，全局替换有误伤风险，未翻。

## 卡牌标题 Title1 / Title2

`resources.assets` 里卡牌预制体分两族：`C<NNN>` 是卡面，有 `Full` / `Half` / `Halfx2` 三个
尺寸变体；`D<NNN>` 是 TitlePlate，永远单行 `Title`。129 个 C 预制体里 14 个在标题处放的
不是一个文本对象，而是位置固定的 `Title1` / `Title2` 两个，通过 `${Card_XXXTitle1}` 绑定。
**拆不拆行是按尺寸变体烤进预制体的，与英文长短无关**（`Marshall Plan` 13 字拆，
`Ask Not What Your Country...` 42 字不拆）。

中文 ≤7 字的 11 张：整个标题放 `Title1`，`Title2` 填**一个空格**。空串实测会出问题。
代价是标题偏高约半行（只占上面那个槽位），要居中得改 RectTransform 坐标，权衡后没做。
>7 字的 `Card_016` / `Card_068` / `Card_110` 保持两行拆分。

单文本对象的标题**不要加 `<br>`**——TMP 会按变体宽度自适应折行，硬 `<br>` 反而在宽变体里
也强制断开。17 张 ≥8 字的标题目前靠自动折行，断点可能不理想，未处理。

卡牌上的星号（用过即移除）由代码按 Lua 里 `remove_if_used_as_event = true` 渲染，
不在文本里。`Card_012Title` 手动加了 `*` 因为短模式下系统没显示；`Card_082` 原文自带的
`*` 反而去掉了，否则重复。

`verify.py` 的 `EXCEPTIONS` 表登记有意与原文标记不一致的条目（目前只有 `Card_029`）。

## 游戏更新后

| 失效点 | 后果 | 防线 |
|---|---|---|
| `backup/` 过期 | 旧版文件装回去，静默降级 | `MANIFEST.json` 哈希比对，不符即中止 |
| path ID 位移 | 换错字体 / 回退没挂上（满屏方块） | 按对象名核对 846/30703/30710；偏移 172 读到非预期值即中止 |
| 原文措辞变化 | 该条保持英文 | 无需处理 |

译文的键（`Card_004Text`）很稳定；场景文本按原文精确匹配，措辞变了就退回英文。
`rebuild_backup.py` 用 `ZH_MARKER`（"朝鲜战争" 的 UTF-8）判断磁盘上是不是汉化版，拒绝从汉化版采集。

`make_font.py` 固定了 `SOURCE_DATE_EPOCH=0`，否则 fontTools 会把当前时间写进 `head.modified`，
两份仓库副本各自生成的字体不同，打出的 `resources.assets` 哈希也不同，另一份的
`MANIFEST.json` 校验会拒绝。系统字体或 fontTools 版本变了输出仍会变，那是内容真变了。

## 存档格式

位置 `~/Library/Application Support/unity.Playdek.TwilightStruggle/`，一局两个文件。

`Save1Full.dat`：224 字节（0xE0）头 + N 条 16 字节操作记录。**没有棋盘状态**，游戏靠重放
记录还原局面。头部 `0xB8` / `0xC8` / `0xD4` 三处记录数必须一起改；`0xB0` 验过不是
CRC32/Adler32/sum/xor，是随机数种子，不动；`0xCC` / `0xD0` 的两个 `-1` 原样保留。
一手从「出牌」（动作码 `0xa010`–`0xa013`）起到下一次出牌止，中间是选用途和逐国作用。
悔棋必须整手删，只删末尾一条会留下「牌出了没落子」的残缺状态。开局布置不以出牌开头，
`hand_starts()` 把索引 0 预置进去。玩家 ID：123 = Player，456 = AI Player。

`Save1Short.dat`：.NET BinaryFormatter（MS-NRBF），字段名在流里。`savedDataSize`（偏移 724）
必须等于 Full 的实际大小；偏移位移时全文搜该值，唯一命中才用。
`OfflineProfiles.dat` 是两条 NRBF 流拼接，`nrbf.py` 的 `run()` 在 MessageEnd 后若还有字节
就继续读。

NRBF 注意：PrimitiveTypeEnumeration **没有 4**——1 Boolean, 2 Byte, 3 Char, 5 Decimal,
6 Double, 7 Int16, 8 Int32, 9 Int64, 10 SByte, 11 Single, 12 TimeSpan, 13 DateTime,
14 UInt16, 15 UInt32, 16 UInt64, 17 Null, 18 String。曾因表错位把 UInt32 读成 UInt64，整个
结构错位。

## 签名

`patch.py` 用原 app 的 entitlements（`codesign -d --entitlements - --xml`）做 ad-hoc 重签，
`--options runtime`，identifier `unity.Playdek.TwilightStruggle`。entitlements 里有
`disable-library-validation`，所以外层 ad-hoc + 内层原厂签名的插件可以共存——
这正是正常工作的组合，不要为了"统一"去重签插件。

## 开发流程

- 译文分批：`merge.py <表名> <批次.json>` 合进 `translations.json`，`--status` 看进度。
- 改完必跑 `verify.py`：核对 `<br>` `<i>` `{0}` `%d` 等标记序列、占位符、长度。
  8 条固定提示是专有名词保留英文（Game Center、Playdek、Android、Kickstarter、STEAM、
  SCORING ×2、MilOPS），不是错误。
- `patch.py --dry-run` 看命中数不落盘；`--skip-scenes` 只做资源包。
- `build/` 是中间产物，`ent.plist` 是重签用的 entitlements。
- 崩溃报告在 `~/Library/Logs/DiagnosticReports/TwilightStruggle-*.ips`，
  第一行是元数据 JSON，之后是正文 JSON，`faultingThread` 索引到 `threads[]`。
