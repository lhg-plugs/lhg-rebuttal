#!/usr/bin/env python3
"""lhg-rebuttal 确定性返修回应审计：24 条规则，零第三方依赖。

扫描目标目录下的返修回应文档（*.md），检查：
  覆盖率（意见是否逐条回应）、语气（生硬反驳/绝对化/情绪化）、
  对照表（行列完整性）、结构（引用/致谢/落款）、策略（证据/承诺）。

用法：
    python3 rebuttal_audit.py --target <目录> [--format json|text] [--fail-on blocker|warning|nit]

有 blocker 时以 exit code 2 退出（供 hooks 与 CI 使用）。
规则文案均为本项目原创。
"""

import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "lhg-rebuttal/rebuttal-check"

SKIP_DIRS = {
    "node_modules", ".next", "dist", "build", ".git", "coverage",
    "__pycache__", "vendor", ".turbo", "out", "fixtures",
}
SCAN_EXTS = {".md", ".markdown", ".txt"}

SEVERITY_ORDER = {"blocker": 0, "warning": 1, "nit": 2}

OPINION_ID_RE = re.compile(r"\b([A-Z]\d+(?:-C\d+)?)\b")
RESPONSE_HEAD_RE = re.compile(
    r"回应\s*([A-Z]\d+(?:-C\d+)?)|[Rr]esponse(?:\s+to)?\s*([A-Z]\d+(?:-C\d+)?)")
BULLET_RE = re.compile(r"^\s*[-*]\s+\S")
QUOTE_RE = re.compile(r"原意见|引用|>\s*\S|审稿人指出|原文")
THANKS_RE = re.compile(r"感谢|Thank|appreciate|valuable|宝贵", re.I)
STRATEGY_RE = re.compile(r"同意|部分同意|反驳|接受|采纳|disagree|agree", re.I)
LOCATION_RE = re.compile(r"位置|第\s*\d+\s*页|\bp\.?\s*\d|Line|Section|表\s*\d|图\s*\d|Figure|Table")
HARSH_RE = re.compile(
    r"你错了|审稿人错了|无稽|胡说|You are wrong|unreasonable|nonsense", re.I)
ABSOLUTE_RE = re.compile(
    r"绝对|肯定没问题|必然|definitely|obviously|certainly|undoubtedly"
    r"|\bprove\b|\bproves\b", re.I)
EMOTIVE_RE = re.compile(r"荒谬|可笑|ridiculous|absurd|laughable", re.I)
BUFFER_RE = re.compile(r"感谢|Thank|good point|很好的|valuable|宝贵|constructive", re.I)
EVIDENCE_RE = re.compile(r"数据|文献|Figure|Table|图\s*\d|表\s*\d|et al|\(20\d{2}\)")
DISAGREE_RE = re.compile(r"不同意|disagree|无法同意", re.I)
EXTRA_EXP_RE = re.compile(r"补充实验|additional experiments|补做实验", re.I)
EXTRA_DONE_RE = re.compile(r"已补|已完成|正在|见第|见修改稿|补充了|as shown", re.I)


class Finding:
    __slots__ = ("rule_id", "severity", "category", "title", "file",
                 "line", "snippet", "detail")

    def __init__(self, rule_id, severity, category, title, file, line,
                 snippet, detail):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.title = title
        self.file = file
        self.line = line
        self.snippet = snippet
        self.detail = detail

    def to_dict(self):
        return {
            "rule_id": self.rule_id, "severity": self.severity,
            "category": self.category, "title": self.title,
            "file": self.file, "line": self.line,
            "snippet": self.snippet, "detail": self.detail,
        }


RULES = []
_RULE_BY_ID = {}


def rule(rule_id, severity, category, title, detail):
    def deco(fn):
        r = {"id": rule_id, "severity": severity, "category": category,
             "title": title, "detail": detail}
        _RULE_BY_ID[rule_id] = r
        r["check"] = fn
        RULES.append(r)
        return fn
    return deco


def _mk(rule_id, path, line, snippet):
    r = _RULE_BY_ID[rule_id]
    return Finding(r["id"], r["severity"], r["category"], r["title"],
                   path, line, snippet[:160], r["detail"])


def collect_files(target):
    out = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            _, ext = os.path.splitext(f)
            if ext in SCAN_EXTS:
                out.append(os.path.join(root, f))
    return sorted(out)


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _sections(lines):
    secs = {}
    cur = None
    for i, ln in enumerate(lines):
        # 只认 # / ## 为章节标题，### 及更深作为正文保留
        m = re.match(r"^#{1,2}(?!#)\s*(.+?)\s*$", ln.strip())
        if m:
            cur = m.group(1)
            secs.setdefault(cur, [])
        elif cur is not None:
            secs[cur].append((i + 1, ln))
    return secs


def _find_sec(secs, *keywords):
    out = []
    for title, body in secs.items():
        if any(k in title for k in keywords):
            out.extend(body)
    return out


def _opinion_ids(lines, text):
    """意见编号：审稿意见章节里出现的编号。"""
    secs = _sections(lines)
    body = _find_sec(secs, "审稿意见", "意见")
    blob = "\n".join(ln for _, ln in body) if body else text
    return [m.group(1).upper() for m in OPINION_ID_RE.finditer(blob)]


def _response_blocks(lines):
    """回应块：按「回应 ID」标题切分，返回 [(行号, 编号, 文本)]。"""
    secs = _sections(lines)
    body = _find_sec(secs, "回应", "逐条")
    if not body:
        return []
    blocks, cur = [], None
    for ln_no, ln in body:
        m = RESPONSE_HEAD_RE.search(ln)
        if m and re.match(r"^#{1,4}\s", ln.strip()):
            if cur:
                blocks.append(cur)
            rid = (m.group(1) or m.group(2)).upper()
            cur = [ln_no, rid, ln + "\n"]
        elif cur:
            cur[2] += ln + "\n"
    if cur:
        blocks.append(cur)
    return [(n, i, t) for n, i, t in blocks]


def _table_info(lines):
    """对照表信息：(表头列, 数据行数, 有无分隔行)。"""
    secs = _sections(lines)
    body = _find_sec(secs, "对照表")
    header, rows, sep = [], 0, False
    for _, ln in body:
        s = ln.strip()
        if not (s.startswith("|") and s.endswith("|")):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if re.match(r"^\|[\s:\-|]+\|$", s):
            sep = True
            continue
        if not header:
            header = cells
        else:
            rows += 1
    return header, rows, sep


# ================================================================ 覆盖率

@rule("RB-COV-001", "blocker", "覆盖率", "有编号的意见没有对应回应",
      "意见清单里的编号在回应里找不到。每条意见必须有回应，漏一条整封信作废：补上对应编号的回应。")
def _c001(lines, text, path, ctx):
    opinions = set(_opinion_ids(lines, text))
    responses = set(i for _, i, _ in _response_blocks(lines))
    missing = sorted(opinions - responses)
    if missing:
        return [_mk("RB-COV-001", path, 1,
                     "无回应的意见编号：%s" % "、".join(missing))]
    return []


@rule("RB-COV-002", "warning", "覆盖率", "回应缺修改位置标注",
      "回应里没写修改位置（页码/行号/图表）。只写「已修改」等于没写：补上修改稿的具体坐标。")
def _c002(lines, text, path, ctx):
    out = []
    for ln_no, rid, blob in _response_blocks(lines):
        if not LOCATION_RE.search(blob):
            out.append(_mk("RB-COV-002", path, ln_no,
                            "回应 %s 无修改位置标注" % rid))
    return out


@rule("RB-COV-003", "warning", "覆盖率", "无修改对照表",
      "文档没有修改对照表。意见超过 3 条时，对照表是编辑一眼看清「改了哪」的工具：按五列标准补上。")
def _c003(lines, text, path, ctx):
    if not _find_sec(_sections(lines), "对照表"):
        return [_mk("RB-COV-003", path, 1, "全文无修改对照表章节")]
    return []


@rule("RB-COV-004", "warning", "覆盖率", "全文无致谢",
      "回信没有感谢审稿人/编辑。致谢是回应信的基本礼仪：开头感谢付出，结尾再次致谢。")
def _c004(lines, text, path, ctx):
    if not THANKS_RE.search(text):
        return [_mk("RB-COV-004", path, 1, "全文无致谢表述")]
    return []


@rule("RB-COV-005", "warning", "覆盖率", "某位审稿人零回应",
      "检测到多位审稿人，但其中一位没有任何对应回应。审稿人会认为你无视了他：补上。")
def _c005(lines, text, path, ctx):
    reviewers = set(re.findall(r"Reviewer\s*(\d+)|审稿人\s*(\d+)",
                               text, re.I))
    revs = set(a or b for a, b in reviewers)
    if len(revs) < 2:
        return []
    responses = set(i for _, i, _ in _response_blocks(lines))
    out = []
    for r in sorted(revs):
        if not any(i.startswith("R%s-" % r) for i in responses):
            out.append(_mk("RB-COV-005", path, 1,
                            "Reviewer %s 零回应" % r))
    return out


@rule("RB-COV-006", "warning", "覆盖率", "编辑意见未回应",
      "检测到编辑（Editor）的意见，但没有对应回应。编辑是拍板的人，他的意见优先级最高：第一条回。")
def _c006(lines, text, path, ctx):
    if not re.search(r"Editor", text, re.I):
        return []
    responses = set(i for _, i, _ in _response_blocks(lines))
    if not any(i.startswith("E") for i in responses):
        return [_mk("RB-COV-006", path, 1, "编辑意见未回应")]
    return []


# ================================================================ 语气

@rule("RB-TONE-001", "warning", "语气", "生硬反驳词",
      "回应里出现生硬反驳词。反驳的是观点不是人：改成「我们的理解不同，证据如下」。")
def _t001(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        m = HARSH_RE.search(ln)
        if m:
            out.append(_mk("RB-TONE-001", path, i + 1,
                            "生硬表达：%s" % m.group(0)))
            if len(out) >= 5:
                break
    return out


@rule("RB-TONE-002", "warning", "语气", "绝对化表述",
      "回应里出现绝对化表述。「prove」在回应信里基本不许出现：改成 suggest/indicate 等概率语言。")
def _t002(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        m = ABSOLUTE_RE.search(ln)
        if m:
            out.append(_mk("RB-TONE-002", path, i + 1,
                            "绝对化表述：%s" % m.group(0)))
            if len(out) >= 5:
                break
    return out


@rule("RB-TONE-003", "warning", "语气", "情绪化词",
      "回应里出现情绪化词。哪怕心里这么想，写出来就是把审稿人往对立面推：删掉，用证据说话。")
def _t003(lines, text, path, ctx):
    out = []
    for i, ln in enumerate(lines):
        m = EMOTIVE_RE.search(ln)
        if m:
            out.append(_mk("RB-TONE-003", path, i + 1,
                            "情绪化词：%s" % m.group(0)))
            if len(out) >= 5:
                break
    return out


@rule("RB-TONE-004", "nit", "语气", "回应缺缓冲语",
      "回应块没有感谢/缓冲语。五段式（感谢→缓冲→回应→证据→收尾）缺了开头：补一句感谢。")
def _t004(lines, text, path, ctx):
    out = []
    for ln_no, rid, blob in _response_blocks(lines):
        if not BUFFER_RE.search(blob):
            out.append(_mk("RB-TONE-004", path, ln_no,
                            "回应 %s 缺缓冲语" % rid))
    return out


@rule("RB-TONE-005", "nit", "语气", "感叹号滥用",
      "回应块感叹号过多。学术写作里感叹号≈吵架：删掉，用陈述句。")
def _t005(lines, text, path, ctx):
    out = []
    for ln_no, rid, blob in _response_blocks(lines):
        if blob.count("!") + blob.count("！") >= 3:
            out.append(_mk("RB-TONE-005", path, ln_no,
                            "回应 %s 感叹号过多" % rid))
    return out


# ================================================================ 对照表

@rule("RB-TAB-001", "blocker", "对照表", "对照表缺关键列",
      "对照表缺「意见/回应/修改位置」关键列。五列标准：意见编号/审稿意见/回应摘要/修改位置/状态。")
def _tb001(lines, text, path, ctx):
    header, _, _ = _table_info(lines)
    if not header:
        return []
    blob = "|".join(header)
    if "意见" not in blob or "回应" not in blob or \
            ("修改位置" not in blob and "位置" not in blob):
        return [_mk("RB-TAB-001", path, 1,
                     "对照表缺关键列，现有列：%s" % blob)]
    return []


@rule("RB-TAB-002", "warning", "对照表", "对照表缺分隔行",
      "对照表表头下没有 |---|---| 分隔行。表格渲染会乱：补上分隔行。")
def _tb002(lines, text, path, ctx):
    header, rows, sep = _table_info(lines)
    if header and not sep:
        return [_mk("RB-TAB-002", path, 1, "对照表缺分隔行")]
    return []


@rule("RB-TAB-003", "warning", "对照表", "对照表行数与意见数不匹配",
      "对照表行数≠意见条数。行列必须一一对应：diff 一下，补上漏掉的行。")
def _tb003(lines, text, path, ctx):
    header, rows, _ = _table_info(lines)
    if not header:
        return []
    n_op = len(set(_opinion_ids(lines, text)))
    if n_op and rows != n_op:
        return [_mk("RB-TAB-003", path, 1,
                     "对照表 %d 行，意见 %d 条" % (rows, n_op))]
    return []


# ================================================================ 结构

@rule("RB-STRUCT-001", "warning", "结构", "回应未引用原意见",
      "回应块没有引用原意见。引用用原话，不 paraphrase：否则会被指「曲解我的意思」。")
def _s001(lines, text, path, ctx):
    out = []
    for ln_no, rid, blob in _response_blocks(lines):
        if not QUOTE_RE.search(blob):
            out.append(_mk("RB-STRUCT-001", path, ln_no,
                            "回应 %s 未引用原意见" % rid))
    return out


@rule("RB-STRUCT-002", "nit", "结构", "无开头致谢信",
      "全文没有「尊敬的编辑」/「Dear Editor」开头。回信要有信的样子：开头致谢，结尾再致谢。")
def _s002(lines, text, path, ctx):
    if not re.search(r"尊敬的编辑|Dear Editor", text, re.I):
        return [_mk("RB-STRUCT-002", path, 1, "全文无开头致谢信")]
    return []


@rule("RB-STRUCT-003", "warning", "结构", "回应过短疑似敷衍",
      "某条回应过短（不足 30 字）。「已修改」三个字不算回应：写清改了什么、改在哪。")
def _s003(lines, text, path, ctx):
    out = []
    for ln_no, rid, blob in _response_blocks(lines):
        core = QUOTE_RE.sub("", blob)
        core = re.sub(r"\s+", "", core)
        if len(core) < 30:
            out.append(_mk("RB-STRUCT-003", path, ln_no,
                            "回应 %s 仅 %d 字，疑似敷衍" % (rid, len(core))))
    return out


@rule("RB-STRUCT-004", "nit", "结构", "意见无编号",
      "审稿意见章节里有条目没编号。编号是「意见-回应-对照表」对齐的钥匙：补上 R1-C1 式编号。")
def _s004(lines, text, path, ctx):
    secs = _sections(lines)
    body = _find_sec(secs, "审稿意见", "意见")
    out = []
    for ln_no, ln in body:
        if BULLET_RE.match(ln) and not OPINION_ID_RE.search(ln) \
                and not re.search(r"Reviewer|审稿人|Editor|编辑", ln, re.I):
            out.append(_mk("RB-STRUCT-004", path, ln_no, ln.strip()[:60]))
            break
    return out


@rule("RB-STRUCT-005", "warning", "结构", "回应无页码行号",
      "回应章节里没有任何页码行号标注。编辑要的是能直接翻到的坐标：补上 p. X / Figure X。")
def _s005(lines, text, path, ctx):
    secs = _sections(lines)
    body = _find_sec(secs, "回应", "逐条")
    if not body:
        return []
    blob = "\n".join(ln for _, ln in body)
    if not re.search(r"第\s*\d+\s*页|\bp\.?\s*\d|Line|Figure|Table", blob):
        return [_mk("RB-STRUCT-005", path, body[0][0], "回应章节无页码行号")]
    return []


@rule("RB-STRUCT-006", "nit", "结构", "对照表无状态列",
      "对照表没有状态列（已修改/部分修改/未修改）。每行状态三选一，无空值。")
def _s006(lines, text, path, ctx):
    header, rows, _ = _table_info(lines)
    if header and not any("状态" in c for c in header):
        return [_mk("RB-STRUCT-006", path, 1, "对照表无状态列")]
    return []


# ================================================================ 策略

@rule("RB-STRAT-001", "warning", "策略", "补充实验承诺无落实",
      "回应承诺补充实验/数据，但没写状态（已完成/正在进行/时间表）。画饼会被编辑记住：写清三要素。")
def _st001(lines, text, path, ctx):
    out = []
    for ln_no, rid, blob in _response_blocks(lines):
        if EXTRA_EXP_RE.search(blob) and not EXTRA_DONE_RE.search(blob):
            out.append(_mk("RB-STRAT-001", path, ln_no,
                            "回应 %s 承诺补充实验但无落实说明" % rid))
    return out


@rule("RB-STRAT-002", "nit", "策略", "回应无策略表态",
      "回应块没有明确的策略表态（同意/部分同意/反驳）。先表态再展开：审稿人要一眼看懂你的立场。")
def _st002(lines, text, path, ctx):
    out = []
    for ln_no, rid, blob in _response_blocks(lines):
        if not STRATEGY_RE.search(blob):
            out.append(_mk("RB-STRAT-002", path, ln_no,
                            "回应 %s 无策略表态" % rid))
    return out


@rule("RB-STRAT-003", "warning", "策略", "反驳无证据",
      "回应表达了不同意，但附近没有数据/文献/图表证据。没证据的反驳叫狡辩：补上三选一证据。")
def _st003(lines, text, path, ctx):
    out = []
    for ln_no, rid, blob in _response_blocks(lines):
        if DISAGREE_RE.search(blob) and not EVIDENCE_RE.search(blob):
            out.append(_mk("RB-STRAT-003", path, ln_no,
                            "回应 %s 反驳无证据" % rid))
    return out


# ================================================================ 格式

@rule("RB-FORMAT-001", "nit", "格式", "回信无落款",
      "全文没有落款（此致/Sincerely）。回信要有信的样子：结尾署名+日期。")
def _f001(lines, text, path, ctx):
    if not re.search(r"此致|Sincerely|Best regards|诚挚", text, re.I):
        return [_mk("RB-FORMAT-001", path, 1, "全文无落款")]
    return []


# ================================================================ 主流程

def audit_file(path):
    text = read_text(path)
    lines = text.split("\n")
    ctx = {}
    findings = []
    for r in RULES:
        try:
            findings.extend(r["check"](lines, text, path, ctx) or [])
        except Exception:
            continue  # 单条规则出错不影响整体
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.file, f.line))
    return findings


def main():
    ap = argparse.ArgumentParser(description="lhg-rebuttal 返修回应确定性审计")
    ap.add_argument("--target", required=True, help="待扫描目录")
    ap.add_argument("--format", default="text", choices=["json", "text"])
    ap.add_argument("--fail-on", default="blocker",
                    choices=["blocker", "warning", "nit"])
    args = ap.parse_args()

    files = collect_files(args.target)
    all_findings = []
    for p in files:
        all_findings.extend(audit_file(p))

    sev_count = {"blocker": 0, "warning": 0, "nit": 0}
    for f in all_findings:
        sev_count[f.severity] += 1

    summary = {
        "tool": TOOL,
        "version": VERSION,
        "target": args.target,
        "files_scanned": len(files),
        "rules_run": len(RULES),
        "blocker": sev_count["blocker"],
        "warning": sev_count["warning"],
        "nit": sev_count["nit"],
        "total": len(all_findings),
    }

    if args.format == "json":
        print(json.dumps({"summary": summary,
                          "findings": [f.to_dict() for f in all_findings]},
                         ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("lhg-rebuttal 返修回应审计报告  v%s" % VERSION)
        print("=" * 60)
        print("扫描文件: %d  运行规则: %d" % (len(files), len(RULES)))
        print("blocker: %d  warning: %d  nit: %d" %
              (sev_count["blocker"], sev_count["warning"], sev_count["nit"]))
        print("-" * 60)
        cur = None
        for f in all_findings:
            if f.severity != cur:
                cur = f.severity
                print("\n[%s]" % cur.upper())
            print("  %s %s:%d" % (f.rule_id, os.path.basename(f.file), f.line))
            print("    %s" % f.title)
            if f.snippet:
                print("    > %s" % f.snippet)
        if not all_findings:
            print("\n未发现问题，回应结构完整。")

    threshold = SEVERITY_ORDER[args.fail_on]
    bad = any(SEVERITY_ORDER[f.severity] <= threshold for f in all_findings)
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
