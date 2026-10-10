#!/usr/bin/env python3
"""lhg-rebuttal 插件冒烟测试：全部绿才算过。

检查项：
 1. 三个 JSON 合法（plugin.json / marketplace.json / hooks.json）
 2. 4 个 SKILL.md 都有 name/description frontmatter，且 150+ 行
 3. 3 个 commands 都有 description + argument-hint frontmatter
 4. 2 个 agents 都有 name/description/tools/model frontmatter
 5. skills 平台中立：不含 Claude Code 专有工具名
 6. fixtures：坏 fixture 的埋点规则必须全部命中且脚本 exit!=0；
    好 fixture 零 blocker 且 exit==0；规则总数 >=22
 7. hooks 脚本：commit 拦截 / 非 commit 放行 / 逃生开关 / 生硬语气与漏答提醒

用法：python3 smoke_test.py [--repo <插件根目录>]
退出码：0=全绿，1=有失败。
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

PASS, FAIL = "PASS", "FAIL"
results = []


def check(name, cond, detail=""):
    results.append((PASS if cond else FAIL, name, detail))
    return cond


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def frontmatter(path):
    """解析 markdown 顶部 --- YAML 块（只取一层 key: value）。"""
    text = read(path)
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fm = {}
    for ln in text[3:end].split("\n"):
        m = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", ln)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return fm


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                          **kw)


# 预期的埋点命中（坏 fixture 必须全部命中，24 条规则）
BAD_MUST = {
    "RB-COV-001", "RB-COV-002", "RB-COV-003", "RB-COV-004", "RB-COV-005",
    "RB-COV-006",
    "RB-TONE-001", "RB-TONE-002", "RB-TONE-003", "RB-TONE-004",
    "RB-TONE-005",
    "RB-TAB-001", "RB-TAB-002", "RB-TAB-003",
    "RB-STRUCT-001", "RB-STRUCT-002", "RB-STRUCT-003", "RB-STRUCT-004",
    "RB-STRUCT-005", "RB-STRUCT-006",
    "RB-STRAT-001", "RB-STRAT-002", "RB-STRAT-003",
    "RB-FORMAT-001",
}
# 平台中立红线：skill 正文不许出现这些 Claude Code 专有表述
NEUTRAL_DENY = ["Task tool", "Bash tool", "Edit tool", "Write tool",
                "Read tool", "AskUserQuestion", "subagent_type",
                "PreToolUse", "PostToolUse",
                "${CLAUDE_", "CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)
    AUDIT = os.path.join(repo, "scripts", "audit", "rebuttal_audit.py")

    # 1. JSON 合法
    for rel in [".claude-plugin/plugin.json", ".claude-plugin/marketplace.json",
                "hooks/hooks.json"]:
        p = os.path.join(repo, rel)
        try:
            d = json.loads(read(p))
            check("JSON 合法: " + rel, True)
            if rel.endswith("plugin.json"):
                check("plugin.json name==lhg-rebuttal",
                      d.get("name") == "lhg-rebuttal",
                      str(d.get("name")))
                check("plugin.json 有 version/description/author",
                      all(d.get(k) for k in ("version", "description",
                                             "author")))
            if rel.endswith("marketplace.json"):
                ps = d.get("plugins", [])
                check("marketplace.json source==./ 且 name 一致",
                      len(ps) == 1 and ps[0].get("source") == "./" and
                      ps[0].get("name") == "lhg-rebuttal", str(ps))
            if rel.endswith("hooks.json"):
                evts = d.get("hooks", {})
                check("hooks.json 有 PreToolUse+PostToolUse",
                      "PreToolUse" in evts and "PostToolUse" in evts,
                      str(list(evts)))
        except Exception as e:
            check("JSON 合法: " + rel, False, str(e))

    # 2. SKILL.md frontmatter + 行数 + 平台中立 + 出品区
    for skill in ["lhg-rb-parse", "lhg-rb-strategy", "lhg-rb-english",
                  "lhg-rb-diff"]:
        p = os.path.join(repo, "skills", skill, "SKILL.md")
        fm = frontmatter(p)
        check("skill frontmatter: " + skill,
              bool(fm.get("name")) and bool(fm.get("description")),
              "name=%s" % fm.get("name"))
        nlines = len(read(p).split("\n"))
        check("skill 行数>=150: %s (%d 行)" % (skill, nlines), nlines >= 150,
              str(nlines))
        body = read(p)
        bad_words = [w for w in NEUTRAL_DENY if w in body]
        check("skill 平台中立: " + skill, not bad_words,
              "命中: %s" % bad_words)
        check("skill 有出品区: " + skill,
              "出品：刘洪光" in body and "https://github.com/lhg-skills" in body)
        check("skill 有自检与反馈: " + skill, "自检与反馈" in body)

    # 3. commands
    for cmd in ["rebuttal", "rebuttal-check", "rebuttal-polish"]:
        p = os.path.join(repo, "commands", cmd + ".md")
        fm = frontmatter(p)
        check("command description+argument-hint: " + cmd,
              bool(fm.get("description")) and bool(fm.get("argument-hint")),
              str(fm.get("description"))[:50])

    # 4. agents
    for ag in ["rebuttal-strategist", "rebuttal-tone-reviewer"]:
        p = os.path.join(repo, "agents", ag + ".md")
        fm = frontmatter(p)
        check("agent frontmatter: " + ag,
              all(fm.get(k) for k in ("name", "description", "tools",
                                      "model")),
              str({k: fm.get(k) for k in ("name", "model")}))

    # 5. 审计脚本冒烟
    def audit_hits(target):
        r = run([sys.executable, AUDIT, "--target", target,
                 "--format", "json"])
        try:
            d = json.loads(r.stdout)
        except Exception:
            return None, r.returncode, []
        return (d["summary"], r.returncode,
                [f["rule_id"] for f in d["findings"]])

    s, code, ids = audit_hits(os.path.join(repo, "fixtures"))
    check("坏 fixture exit!=0", code != 0, "exit=%d" % code)
    check("坏 fixture blocker>0", s and s["blocker"] > 0, str(s))
    missing = BAD_MUST - set(ids)
    check("坏 fixture 埋点全命中 (%d/%d)"
          % (len(BAD_MUST - missing), len(BAD_MUST)),
          not missing, "缺失: %s" % sorted(missing))

    with tempfile.TemporaryDirectory() as td:
        shutil.copy(os.path.join(repo, "fixtures", "good_rebuttal.md"),
                    os.path.join(td, "good_rebuttal.md"))
        s, code, ids = audit_hits(td)
        check("好 fixture 零 blocker", s and s["blocker"] == 0, str(s))
        check("好 fixture exit==0", code == 0, "exit=%d" % code)
        check("规则总数>=22 (%d)" % s["rules_run"], s["rules_run"] >= 22,
              str(s["rules_run"]))

    # 6. hooks 脚本
    def hook(script, payload, env=None, cwd=None):
        e = dict(os.environ)
        e.update(env or {})
        return run([sys.executable, os.path.join(repo, "hooks", script)],
                   input=payload, env=e, cwd=cwd or repo)

    r = hook("pre_commit_rebuttal.py",
             '{"tool_input":{"command":"git status"}}')
    check("hook: 非 commit 放行", r.returncode == 0 and not r.stdout.strip())

    with tempfile.TemporaryDirectory() as td:
        run(["git", "init", "-q"], cwd=td)
        run(["git", "config", "user.email", "t@t.t"], cwd=td)
        run(["git", "config", "user.name", "t"], cwd=td)
        shutil.copy(os.path.join(repo, "fixtures", "bad_rebuttal.md"),
                    os.path.join(td, "response-letter_rb.md"))
        run(["git", "add", "-A"], cwd=td)
        payload = '{"tool_input":{"command":"git commit -m \\"x\\""}}'
        r = hook("pre_commit_rebuttal.py", payload, cwd=td)
        try:
            d = json.loads(r.stdout)
            denied = (d["hookSpecificOutput"]["permissionDecision"]
                      == "deny")
        except Exception:
            denied = False
        check("hook: commit 暂存坏回应拦截", denied, r.stdout[:120])
        r = hook("pre_commit_rebuttal.py", payload,
                 {"LHG_RB_HOOKS_OFF": "1"}, cwd=td)
        check("hook: 逃生开关生效",
              r.returncode == 0 and not r.stdout.strip())

    with tempfile.TemporaryDirectory() as td:
        bad_p = os.path.join(td, "rebuttal_rb.md")
        with open(bad_p, "w", encoding="utf-8") as f:
            f.write("### 回应 R1-C1\n\n你错了，绝对没问题。\n\n"
                    "## 审稿意见\n\n- R1-C2：还有一个问题。\n")
        r = hook("post_rebuttal_warn.py",
                 json.dumps({"tool_input": {"file_path": bad_p}}))
        check("hook: 生硬语气提醒", "additionalContext" in r.stdout
              and "生硬" in r.stdout, r.stdout[:100])
        check("hook: 漏答提醒", "additionalContext" in r.stdout
              and "R1-C2" in r.stdout, r.stdout[:100])
        good_p = os.path.join(td, "good_rb.md")
        with open(good_p, "w", encoding="utf-8") as f:
            f.write("### 回应 R1-C1\n\n感谢指出，我们同意并已修改。\n")
        r = hook("post_rebuttal_warn.py",
                 json.dumps({"tool_input": {"file_path": good_p}}))
        check("hook: 好回应不提醒", not r.stdout.strip(), r.stdout[:80])
        r = hook("post_rebuttal_warn.py",
                 json.dumps({"tool_input": {"file_path": bad_p}}),
                 {"LHG_RB_HOOKS_OFF": "1"})
        check("hook: 提醒逃生开关生效", not r.stdout.strip())
        other = os.path.join(td, "notes.md")
        with open(other, "w", encoding="utf-8") as f:
            f.write("你错了，绝对没问题。\n")
        r = hook("post_rebuttal_warn.py",
                 json.dumps({"tool_input": {"file_path": other}}))
        check("hook: 非回应文件放行", not r.stdout.strip())

    # 报告
    print("=" * 60)
    print("lhg-rebuttal 冒烟测试报告")
    print("=" * 60)
    fails = 0
    for st, name, detail in results:
        mark = "✓" if st == PASS else "✗"
        print("%s %s %s" % (mark, st, name))
        if detail and st == FAIL:
            print("    → %s" % detail)
        if st == FAIL:
            fails += 1
    print("=" * 60)
    print("共 %d 项，通过 %d，失败 %d"
          % (len(results), len(results) - fails, fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
