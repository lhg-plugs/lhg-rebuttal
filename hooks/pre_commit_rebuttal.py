#!/usr/bin/env python3
"""lhg-rebuttal 硬门①：git commit 前检查暂存区里的返修回应文档，有 blocker 则拦截。

触发：PreToolUse / Bash。先判断本次 Bash 是否为 git commit，
不是则 0 开销直接放行；是则看暂存区有无返修回应文档
（文件名含 rebuttal/返修/response/response-letter/回信，或 *_rb.md），
有则对这些文件所在目录跑插件自带的 rebuttal 审计脚本，有 blocker 才拦截。

逃生方式（按推荐度排序）：
  1. 修掉 blocker 后重新 commit（推荐：补漏答的意见/补对照表关键列）。
  2. 紧急情况：LHG_RB_HOOKS_OFF=1 git commit -m "..."（单次豁免本次 hook）。
  3. /plugin disable lhg-rebuttal（整个插件停用，hooks 不再触发）。

设计原则：脚本内部出错（无 git、审计脚本缺失、超时等）fail-open 直接放行；
真正的门禁在 /lhg-rebuttal:rebuttal-check。零第三方依赖。
"""

import json
import os
import re
import subprocess
import sys

AUDIT_TIMEOUT = 60
COMMIT_RE = re.compile(r"(^|[;&|])\s*git\s+.*\bcommit\b")
REBUTTAL_RE = re.compile(r"rebuttal|返修|response|回信|_rb\.md$", re.I)


def _git(args, cwd):
    try:
        p = subprocess.run(["git"] + args, capture_output=True, text=True,
                           timeout=15, cwd=cwd)
        return p.stdout if p.returncode == 0 else ""
    except Exception:
        return ""


def main() -> int:
    # 逃生开关
    if os.environ.get("LHG_RB_HOOKS_OFF") == "1":
        return 0

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0  # 输入解析失败：fail-open

    tool_input = payload.get("tool_input", {}) or {}
    command = tool_input.get("command", "") or ""

    # 非 git commit：快速放行
    if not COMMIT_RE.search(command):
        return 0

    cwd = os.getcwd()
    staged = _git(["-c", "core.quotepath=false", "diff", "--cached",
                   "--name-only", "--diff-filter=ACM"], cwd).split()
    rb_files = [f for f in staged
                if REBUTTAL_RE.search(os.path.basename(f))]
    if not rb_files:
        return 0  # 暂存区无返修回应文档：放行

    plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script = os.path.join(plugin_root, "scripts", "audit",
                          "rebuttal_audit.py")
    if not os.path.isfile(script):
        return 0  # 审计脚本缺失：fail-open

    targets = sorted({os.path.dirname(os.path.join(cwd, f)) or cwd
                      for f in rb_files})
    blockers = []
    for target in targets:
        try:
            proc = subprocess.run(
                [sys.executable, script, "--target", target,
                 "--format", "json"],
                capture_output=True, text=True, timeout=AUDIT_TIMEOUT)
            data = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except Exception:
            continue  # 单个目标失败：fail-open，不拦
        for f in (data.get("findings") or []):
            if f.get("severity") == "blocker":
                blockers.append("%s %s:%s" % (
                    f.get("rule_id"), os.path.basename(f.get("file", "")),
                    f.get("line", "?")))

    if not blockers:
        return 0

    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason":
                "lhg-rebuttal：返修回应有 %d 个 blocker 未处理，"
                "commit 已拦截。请先修掉再提交，或用 "
                "LHG_RB_HOOKS_OFF=1 单次豁免。\n%s"
                % (len(blockers), "\n".join(blockers[:10])),
        }
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
