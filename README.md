<!-- About 简介（推送后填写到仓库 About 栏）：
论文返修一次过：审稿意见逐条拆解、回应策略、修改对照表、礼貌化学术英语润色 ｜ 一键安装：/plugin marketplace add lhg-plugs/lhg-rebuttal
-->
<!-- topics（推送后打）：claude-code, claude-plugin, agent-skills, academic-writing, peer-review, paper -->

# lhg-rebuttal：论文返修专家

> **一句话介绍**：给 AI 助手装上"论文返修全流程"——审稿意见逐条拆解编号、回应策略三选一（同意/部分同意/礼貌反驳）、修改对照表、礼貌化学术英语润色，输出可直接投稿的 response letter。
>
> **一键安装**：在 Claude Code 里运行
> ```
> /plugin marketplace add lhg-plugs/lhg-rebuttal
> /plugin install lhg-rebuttal@lhg-plugs
> ```

## 它是什么

`lhg-rebuttal` 是一个 Claude Code 插件（plugin 为主、skill 为辅）：

- **3 个命令**（小白入口）：`rebuttal` 返修一条龙（拆解→策略→对照表→润色→成信），`rebuttal-check` 回应完整性自查，`rebuttal-polish` 礼貌化润色工作坊
- **4 个平台中立 skill**（方法论，可移植到豆包/Workbuddy 等 agent 平台）：审稿意见解析、回应策略、学术英语礼貌表达、修改对照表规范
- **2 个专家 agent**：返修策略专家、语气审查员
- **2 个硬门 hooks**：commit 前返修回应审计拦截、写回应时生硬语气与漏答提醒（均可一键豁免）
- **24 条确定性审计规则**：纯 Python、零第三方依赖，查意见覆盖率、生硬语气词、对照表行列完整性

差异化：**意见编号 vs 回应编号机器 diff**（漏答一条直接 blocker）、**生硬反驳词零容忍**（"你错了""绝对""prove"一律报警）、**策略三选一先行**（同意/部分同意/礼貌反驳，边写边想策略=没策略）、**反驳必须有证据**（数据/文献/图表三选一，没证据的反驳叫狡辩）。

## 3 个命令用法

| 命令 | 作用 | 示例 |
|---|---|---|
| `/lhg-rebuttal:rebuttal` | 粘贴审稿意见→逐条拆解→回应策略→对照表→润色→完整 response letter | `/lhg-rebuttal:rebuttal 审稿意见文件路径` |
| `/lhg-rebuttal:rebuttal-check` | 24 条规则审计 + 人工评审清单（投稿前必跑） | `/lhg-rebuttal:rebuttal-check 回应目录` |
| `/lhg-rebuttal:rebuttal-polish` | 把生硬回应逐段改写成礼貌学术英语，原意不变 | `/lhg-rebuttal:rebuttal-polish 回应草稿` |

## 自查说明

自查 = 确定性脚本（机器）+ 人工评审（人）：

1. 先跑 `scripts/audit/rebuttal_audit.py`（24 条规则），零 LLM 成本；
2. 发现分三级：**blocker**（有编号的意见无对应回应、对照表缺关键列，commit 前 hook 会拦截）、**warning**（生硬反驳词、绝对化表述、回应过短、反驳无证据等）、**nit**（缺缓冲语、无落款等）；
3. 再按人工清单过一遍脚本抓不到的（逐条打勾防漏答、朗读测语气、反驳证据是否充分、承诺是否写清时间表、对照表页码是否与修改稿一致）。

blocker 清零才算做完；为清零改规则算作弊，不许。投稿前 24 小时必须跑一遍，且由合作者过一遍人工清单。

## 目录结构

```
lhg-rebuttal/
├── .claude-plugin/          # plugin.json（插件清单）+ marketplace.json（本仓即市场）
├── commands/                # 3 个命令：rebuttal / rebuttal-check / rebuttal-polish
├── skills/                  # 4 个平台中立 skill（parse/strategy/english/diff）
├── agents/                  # 2 个专家 agent（rebuttal-strategist / rebuttal-tone-reviewer）
├── hooks/                   # 2 个硬门（commit 前审计拦截 / 生硬语气与漏答提醒）+ 豁免说明
├── scripts/audit/           # 24 条确定性审计规则（零第三方依赖）
├── fixtures/                # 冒烟测试用例（坏/好对照）
├── smoke_test.py            # 一键冒烟测试
├── ATTRIBUTION.md           # 灵感来源与许可声明
└── LICENSE                  # MIT
```

## 什么时候用 / 什么时候不用（FAQ）

**什么时候用：**

- 收到 major revision / minor revision，不知道从哪下手回时 → 用 `/lhg-rebuttal:rebuttal` 一条龙
- 回应写完了，怕漏答某条、语气得罪审稿人时 → 跑 `/lhg-rebuttal:rebuttal-check`
- 回应意思对但英文生硬，怕"you are wrong"式表达惹毛审稿人时 → 用 `/lhg-rebuttal:rebuttal-polish`
- 你是导师/合作者，想给学生立一套"投稿前必须自查"的纪律时 → 它的 hooks 硬门开箱即用

**什么时候不用：**

- 审稿意见是"accept as is"无实质内容 → 直接致谢即可，不用走全套
- 你希望 AI 无条件按你的原话出回应、不接受"这句太生硬"的打回 → 它的语气零容忍会让你烦（这是设计，不是 bug）
- 回应需要编造实验数据来"证明"审稿人错了 → 这是学术不端，插件不会帮你，策略 C 只接受有真实证据的反驳

## lhg-plugs 插件矩阵

| 插件 | 一句话 | 安装 |
|---|---|---|
| [lhg-rebuttal](https://github.com/lhg-plugs/lhg-rebuttal) | 论文返修专家：审稿意见逐条拆解→回应策略→修改对照表→礼貌化学术英语润色 | `/plugin install lhg-rebuttal@lhg-plugs` |
| *（后续插件在此追加，保持表格格式一致）* | | |

## 自检与反馈

本插件自带质检：每次使用后可跑 `python3 smoke_test.py` 一键验证（JSON 合法、skill/command/agent 完整性、24 条规则、fixtures 命中、hooks 行为）。

发现 bug 或有改进建议，以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-rebuttal/issues，正文写清"复现步骤 → 实际表现 → 期望表现"。

## 出品：刘洪光

本插件由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 视频号：搜「刘洪光实名上网」
- 微信：lhgsmsw
