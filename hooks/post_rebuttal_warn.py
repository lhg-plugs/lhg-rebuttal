#!/usr/bin/env python3
"""lhg-rebuttal 硬门②：写返修回应文档后，检查生硬语气词与意见覆盖情况。

触发：PostToolUse / Write|Edit。只看文件名像返修回应的文档
（rebuttal/返修/response/回信/_rb.md），其他文件 0 开销放行。
发现生硬反驳词/绝对化表述，或"有意见编号但无对应回应"时，
通过 additionalContext 给出提醒（不拦截）。

逃生方式：LHG_RB_HOOKS_OFF=1（本次 hook 直接放行）。

设计原则：内部出错 fail-open；这是一个提醒，不是门禁。
真正的门禁在 /lhg-rebuttal:rebuttal-check。零第三方依赖。
"""

import json
import os
import re
import sys

REBUTTAL_RE = re.compile(r"rebuttal|返修|response|回信|_rb\.md$", re.I)
HARSH_RE = re.compile(
    r"你错了|审稿人错了|无稽|胡说|荒谬|可笑|You are wrong|"
    r"unreasonable|nonsense|ridiculous|absurd", re.I)
ABSOLUTE_RE = re.compile(
    r"绝对|肯定没问题|必然|definitely|obviously|certainly|"
    r"undoubtedly|\bprove\b|\bproves\b", re.I)
OPINION_ID_RE = re.compile(r"\b([A-Z]\d+(?:-C\d+)?)\b")
RESPONSE_ID_RE = re.compile(r"回应\s*([A-Z]\d+(?:-C\d+)?)|"
                            r"[Rr]esponse(?:\s+to)?\s*([A-Z]\d+(?:-C\d+)?)")


def main() -> int:
    if os.environ.get("LHG_RB_HOOKS_OFF") == "1":
        return 0
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0
    tool_input = payload.get("tool_input", {}) or {}
    fp = tool_input.get("file_path", "") or ""
    if not REBUTTAL_RE.search(os.path.basename(fp)):
        return 0  # 非返修回应文档：放行
    try:
        with open(fp, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return 0

    notes = []
    harsh = sorted(set(m.group(0) for m in HARSH_RE.finditer(text)))
    if harsh:
        notes.append("检测到生硬表达：%s。回应信里不许出现这类词，"
                     "改成礼貌说法（见 lhg-rb-english 生硬表达对照表）。"
                     % "、".join(harsh[:5]))
    absolute = sorted(set(m.group(0) for m in ABSOLUTE_RE.finditer(text)))
    if absolute:
        notes.append("检测到绝对化表述：%s。改成概率语言"
                     "（suggest/indicate），\"prove\"在回应信里基本不许出现。"
                     % "、".join(absolute[:5]))
    opinions = set(m.group(1) for m in OPINION_ID_RE.finditer(text))
    responses = set(g for m in RESPONSE_ID_RE.finditer(text)
                    for g in m.groups() if g)
    missing = sorted(opinions - responses)
    if opinions and missing:
        notes.append("以下意见编号没有对应回应：%s。每条意见必须有回应，"
                     "漏一条整封信作废。" % "、".join(missing[:8]))
    if notes:
        notes.append("投稿前跑 /lhg-rebuttal:rebuttal-check 做全量自查。")
        print(json.dumps({"additionalContext": "\n".join(notes)},
                         ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
