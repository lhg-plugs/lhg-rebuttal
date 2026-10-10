---
name: lhg-rb-english
description: 学术英语礼貌表达：回应信的感谢开头、缓冲语、概率语言、反驳句式库，附生硬表达对照表。
license: MIT
compatibility: 平台中立（Claude Code / 豆包 / Workbuddy 等 agent 平台通用）
metadata:
  version: 1.0.0
  category: academic-rebuttal
---

# lhg-rb-english：学术英语礼貌表达

## 何时使用

- 写英文 response letter，需要把"意思对但语气硬"的句子改得体时。
- 母语是中文，怕写出中式英语或无意冒犯审稿人时。
- 润色合作者写的回应初稿时。

不适用：期刊要求用其他语言回信（极少）——方法论相通，句式库需替换。

## 输入与输出

**输入**：待润色的回应段落（英文初稿或中文意思）。

**输出**：润色后的学术英语段落 + 改动说明（改了哪类问题）。

## 分步方法论

### 第 1 步：五段式结构

每条回应按这个顺序组织，缺一段就补一段：

1. **感谢**：Thank you for raising this important point. / We appreciate the reviewer's insightful comment.
2. **缓冲**（表态）：We agree... / We agree in part... / This is a valid concern...
3. **回应**：陈述修改或解释，用概率语言。
4. **证据**：As shown in Figure X... / Consistent with Smith et al. (2024)...
5. **收尾**：We have revised the manuscript accordingly (p. X, lines Y-Z). / We hope this clarifies the issue.

### 第 2 步：生硬表达对照表

| 生硬（不许） | 礼貌（改成） |
|---|---|
| You are wrong. | Our interpretation differs because... |
| This is obvious. | As shown in Figure X, ... |
| We definitely prove that... | Our results suggest that... / indicate that... |
| The reviewer misunderstood... | We apologize if our original description was unclear. ... |
| This comment is irrelevant. | While this point is beyond the scope of the current study, we have added a discussion (p. X). |
| We don't agree. | We respectfully disagree because [evidence]. |
| You should have known... | （删掉，任何版本都不许出现） |

### 第 3 步：概率语言

结论动词按"确定程度"降序使用，审稿语境里默认用中间档：

- 强：demonstrate, confirm, establish（只在证据确凿时用，慎用）
- **中（默认）：suggest, indicate, imply, appear to**
- 弱：may, might, could, seem to（承认局限时用）

"prove"在回应信里基本不许出现——科学上很少有 prove，写了等于给审稿人递刀子。

### 第 4 步：人称与语态

- 用"We"，不用"You"：写"We have clarified..."不写"You misunderstood..."。
- 反驳时把主语换成"证据"：不写"We disagree with you"，写"The data suggest a different interpretation"。
- 道歉只为"表达不清"道歉，不为"观点"道歉："We apologize if our description was unclear"（可以）；"We apologize for our wrong conclusion"（不许——结论没错为什么道歉）。

### 第 5 步：高频句式库

**开头致谢**：

- We thank the reviewers for their constructive comments, which have helped improve the manuscript.
- We appreciate the time and effort the reviewers devoted to evaluating our work.

**同意修改**：

- We agree with the reviewer and have [done X] (p. Y, lines Z-W).
- Following the reviewer's suggestion, we have added [X] in Section Y.

**部分同意**：

- We agree in part. [对的部分已改]. Regarding [不对的部分], our rationale is [理由], as evidenced by [证据].
- This is a valid concern. While [解释], we have [补充了什么] to address it.

**礼貌反驳**：

- We respectfully disagree for the following reasons. First, [证据一]. Second, [证据二].
- We understand the reviewer's concern. However, [证据]. To eliminate any confusion, we have added [补充内容] (p. X).

**结尾**：

- We hope our revisions and explanations address the reviewers' concerns.
- We thank the reviewers again for helping us strengthen the manuscript.

## 完整示例

改前（生硬）：

> You are wrong about the sample size. 50 samples definitely prove our conclusion. We don't agree with this comment.

改后（礼貌）：

> Thank you for raising this important point. We understand the concern about sample size. To address it, we have conducted additional experiments, expanding the sample from 50 to 120. As shown in the new Figure 4 (p. 3, lines 45-60), the main conclusion remains unchanged, which suggests that our findings are robust. We hope this clarifies the issue.

改动说明：删掉"You are wrong"（生硬反驳）→ 换成感谢+缓冲；"definitely prove"（绝对化）→ "suggest...robust"（概率语言）；补充了证据（Figure 4）与修改位置（p. 3）。

## 反模式

- **过度道歉**：每条回应都以"We are so sorry"开头——道歉三次以上，整封信显得心虚。
- **感谢注水**："Thank you for this very very insightful comment"——very 叠词是中式英语，一个 insightful 够了。
- **语气过软**：把反驳润色成了同意——润色不改变原意是铁律。
- **术语漂移**：润色时把"hyperparameter"改成"parameter"——术语一个字不许动。
- **丢修改位置**：润色完把"(p. 3, lines 45-60)"弄丢了——位置标注是回应的骨架，不许丢。

## 中式英语高频纠错表

| 中式英语（不许） | 地道说法 |
|---|---|
| We very very agree. | We fully agree. |
| This paper is very meaningful. | This work provides new insights into... |
| The result is very good. | The results are promising / encouraging. |
| We do a lot of experiments. | We conducted extensive experiments. |
| It is well known that...（滥用） | As reported by Smith et al. (2024), ... |
| In a word, ... | In summary, ... |
| What's more, ...（口语） | Furthermore, ... / Moreover, ... |
| Last but not least, ...（口语） | Finally, ... |

## 一句话速查

- 五段式：感谢→缓冲→回应→证据→收尾，缺一段补一段。
- "prove"基本不许出现，默认用 suggest/indicate。
- 反驳主语换成证据：不写"We disagree with you"，写"The data suggest a different interpretation"。
- 道歉只为表达不清，不为观点。
- 润色三不许：不改变原意、不编造证据、不动术语与数据。

## 自检与反馈

**质检门**（输出前自查）：

- [ ] 每条回应有感谢开头，五段式完整
- [ ] 无生硬表达（对照表逐项检查）
- [ ] 结论动词为概率语言（suggest/indicate 为主，无 prove/definitely）
- [ ] 人称全为"We"，无"You are wrong"类主语
- [ ] 术语、数据、修改位置标注与原文一致

**标准冒烟用例**：输入"You are wrong. Our 50 samples definitely prove the conclusion."，应输出含"Thank you for raising this point"开头、"suggest"替代"prove"、删掉"You are wrong"的版本，且原意（坚持结论）不变。

**一键反馈**：发现方法论缺口，以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-rebuttal/issues，正文写清"场景 → 当前方法的不足 → 期望补充什么"。

## 出品：刘洪光

本 skill 由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 视频号：搜「刘洪光实名上网」
- 微信：lhgsmsw
