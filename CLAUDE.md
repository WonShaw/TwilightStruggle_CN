# 技术备忘

## 硬约束

- **只重签主 app，绝不碰 `Contents/PlugIns/`。** 2026-09-05 对 `TwilightStruggleLib-OSX.bundle`
  （原生 AI 库）做过一次 ad-hoc 重签，CodeDirectory 只覆盖 58 页（原厂 229 页），之后每局在
  `twilight_ai::AIHandlerThread::ThreadMain` SIGSEGV。Steam 验证完整性还原后正常。
  外层 ad-hoc + 内层原厂签名是正确组合，entitlements 里有 `disable-library-validation`。
- **不动 IL2CPP 字面量。** 顶部提示条和卡牌历史背景在 `global-metadata.dat` 字面量区
  （偏移 113768，长 408692），无空隙，只能等长替换。放弃。
- **脚本 PPtr `(1, 563)` 偏移 148 的国名是内部标识，绝不能改**，改了卡牌效果找不到国家。
  只改 `(1, 1417)`。
- `backup/`、`ZH_sub.ttf` 不提交。`source_texts.json` 是 10 万字符英文原文含整本规则书，
  `patch.py` 不读它，公开时可换成提取器。
- 提交信息只写做了什么。

## 环境

- Unity 6000.0.58f2 IL2CPP，Steam buildid 21119605，app 1.4.11 (167)。
- 进程跑在 Rosetta 下（`libsteam_api.dylib` 只有 x86_64）。`open -a` 会选 arm64 然后
  `DllNotFoundException` 退出，必须 `open "steam://rungameid/406290"`。
- conda 环境 `ts-cn`：`~/miniconda3/envs/ts-cn/bin/python`，base 里不装本项目的包。
  重建：`conda create -n ts-cn python=3.13 && conda run -n ts-cn pip install -r requirements.txt`。
  只有 `patch.py` / `rebuild_backup.py` / `make_font.py` 需要它，其余脚本纯标准库。

## 字符串表

- TextAsset：第一行时间戳头，之后 JSON `"<sheetId>": {"<row>:<col>": v}`，行 1 是表头。
  `TS_Cards` sheetId `1631793870`，列 2=EN 3=FR 4=IT 5=DE 6=ES 7=NL 8=Notes，非 EN 列是字面串 `"null"`。
- 游戏有 `CH` 列但只有 6 条机翻，**直接覆盖 EN 列**，不走语言切换。
- 六表 1208 条：TS_Cards 344、Common_Ingame 22、TS_Ingame 157、Common_Strings 322、
  TS_Strings 50、TS_RulesTutorial 313。
- 原表无空值先例，要留空填一个空格，空串实测出问题。

## 字体

所有字体是静态 SDF 图集，无汉字。不换图集，走 TMP 全局回退：`Font(846)` 的 TTF 换成
`ZH_sub.ttf` → 它是动态字体资产 `30703` 的来源 → `TMP Settings (30710)` 的
`m_fallbackFontAssets`（偏移 172）挂上 30703。斜体、`<br>`、避头尾都正常。

`make_font.py` 固定 `SOURCE_DATE_EPOCH=0`，否则每次输出不同，跨仓库副本 MANIFEST 校验会拒绝。

## 场景 level2 / level3

- 规则书、帮助页**不用改场景**。场景里的英文是占位，旁边 `(1, 890)` 组件绑着 `${Key}`，
  运行时从 `TS_RulesTutorial` 取。level2 共 636 处绑定。
- 没挂 `(1, 890)` 的 TMP 文本才原样显示，那些进 `scene_ui.json`。
- level2 剩约 30 条英文：占位文本（`PlayerName12345`）不显示；孤立单词（`Before`/`War`）
  上下文不明，全局替换会误伤，有意不翻。

## 卡牌标题

- 卡面预制体 `C<NNN>` 有 Full/Half/Halfx2 变体，14 个在标题处是定位的 `Title1`/`Title2` 两槽，
  **拆行是烤进预制体的，与英文长短无关**。`D<NNN>` TitlePlate 永远单行。
- 中文 ≤7 字的 11 张整个放 `Title1`，`Title2` 一个空格，代价是偏高半行。>7 字的
  `Card_016/068/110` 保持拆分。
- 单文本对象标题**不加 `<br>`**，TMP 按变体宽度自适应，硬断反而在宽变体里也断。
- 星号由代码按 Lua `remove_if_used_as_event` 渲染，不在文本里。`Card_012Title` 手动加了 `*`
  （短模式系统不显示），`Card_082` 原文自带的去掉了（重复）。
- `verify.py` 的 `EXCEPTIONS` 登记有意与原文标记不一致的条目。8 条固定提示是专有名词保留英文，不是错。

## 存档

- `Save1Full.dat` = 0xE0 头 + 16 字节记录 × N，**无棋盘状态**，靠重放。头部 0xB8/0xC8/0xD4
  三处计数一起改；0xB0 是随机种子不是校验和；0xCC/0xD0 的 -1 不动。
- 悔棋必须整手删：一手从出牌（`0xa010`–`0xa013`）到下一次出牌，开局布置不以出牌开头。
  玩家 123=Player，456=AI。
- `Save1Short.dat` 是 NRBF，`savedDataSize` 必须等于 Full 大小。`OfflineProfiles.dat` 是两条
  NRBF 流拼接。PrimitiveTypeEnumeration 没有 4，曾因此整个结构错位。
- 游戏退出时会覆盖存档，改之前必须先退游戏。
