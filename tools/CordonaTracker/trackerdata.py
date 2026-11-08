"""Reads the project's progress from the repo: the task queue in docs/handoff.md, the plan in docs/roadmap.html, and git log.

Read-only. The handoff note is the single source of truth for tasks; this module never writes anything.
Python standard library only.
"""
from __future__ import annotations

import html
import os
import re
import subprocess
from dataclasses import dataclass, field

STATES = ("running", "waiting", "queued", "on hold", "done", "retired")
ID_RX = re.compile(r"CRD-\d{3}")
ROW_RX = re.compile(r"^\|\s*(CRD-\d{3})\s*\|(.*)\|\s*$")
HASH_RX = re.compile(r"^[0-9a-f]{7,40}$")


@dataclass
class Task:
    id: str
    title: str
    state: str                 # one of STATES, or "unknown"
    commit: str = ""           # from the table, else from git log
    commit_from_git: bool = False
    detail: str = ""           # the task's bullet(s) in the handoff note, plain text


@dataclass
class Step:
    num: str
    title: str
    sub: str
    badge: str                 # Done / In progress / Next / Planned
    items: list = field(default_factory=list)   # (text, state) for a step's bullet list, state done/partial/open


@dataclass
class Progress:
    tasks: list
    queue_source: str          # "table" or "bullets" (fallback, states guessed)
    updated: str               # the handoff note's "Last updated" line
    steps: list
    gate: str                  # the stability gate text
    understanding: list        # (text, state) for the 12 items
    warnings: list


# ------------------------------------------------------------------ handoff.md
def parse_queue_table(text):
    """Rows of the 'Queue at a glance' table: | CRD-nnn | Task | State | Commit |. Returns (tasks, warnings)."""
    tasks, warnings, seen = [], [], set()
    for n, line in enumerate(text.splitlines(), 1):
        m = ROW_RX.match(line.strip())
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        if len(cells) < 2:
            warnings.append(f"handoff line {n}: {m.group(1)} has too few cells")
            continue
        title, state = cells[0], cells[1].lower()
        commit = cells[2] if len(cells) > 2 else ""
        if state not in STATES:
            warnings.append(f"handoff line {n}: {m.group(1)} state '{cells[1]}' is not one of {', '.join(STATES)}")
            state = "unknown"
        if commit and not HASH_RX.match(commit):
            warnings.append(f"handoff line {n}: {m.group(1)} commit '{commit}' is not a hash")
            commit = ""
        if m.group(1) in seen:
            warnings.append(f"handoff line {n}: {m.group(1)} is listed twice; the first row wins")
            continue
        seen.add(m.group(1))
        tasks.append(Task(m.group(1), title, state, commit))
    return tasks, warnings


def guess_state(text):
    """Fallback for a bullet with no table row: the first state word near the start."""
    head = text.lower()[:160]
    for word, state in (("retired", "retired"), ("done", "done"), ("running", "running"), ("queued", "queued"),
                        ("waits", "waiting"), ("waiting", "waiting"), ("on hold", "on hold")):
        if word in head:
            return state
    return "unknown"


def task_bullets(text):
    """CRD-nnn -> the plain text of every bullet or numbered item in section 1 that starts with that ID."""
    sec = section(text, 1)
    out, cur_id, cur = {}, None, []

    def flush():
        if cur_id:
            out.setdefault(cur_id, []).append(" ".join(cur))

    for line in sec.splitlines():
        m = re.match(r"^(?:-|\d+\.)\s+(?:\*\*)?(CRD-\d{3})\b", line)
        if m:
            flush()
            cur_id, cur = m.group(1), [line.strip()]
        elif cur_id and line[:1] in (" ", "\t") and line.strip():
            cur.append(line.strip())
        else:
            flush()
            cur_id, cur = None, []
    flush()
    return {k: plain_md("\n\n".join(v)) for k, v in out.items()}


def plain_md(s):
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    return s.replace("**", "").replace("`", "")


def section(text, num):
    """The body of '## <num>. ...' up to the next '## '."""
    m = re.search(rf"^## {num}\..*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def parse_handoff(text):
    warnings = []
    tasks, w = parse_queue_table(text)
    warnings += w
    bullets = task_bullets(text)
    source = "table"
    if not tasks:
        source = "bullets"
        warnings.append("no 'Queue at a glance' table in docs/handoff.md; states are guessed from the bullets")
        for tid, body in sorted(bullets.items()):
            after = ID_RX.sub("", body, count=1).lstrip("-*. ,")
            title = re.split(r"[:(]", after, 1)[0].strip() or tid
            tasks.append(Task(tid, title[:70], guess_state(after)))
    for t in tasks:
        t.detail = bullets.get(t.id, "")
    m = re.search(r"^Last updated:\s*(.+)$", text, re.M)
    return tasks, source, (m.group(1).strip() if m else ""), warnings


# ------------------------------------------------------------------ roadmap.html
def strip_tags(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def item_state(text):
    t = text.lower()
    if re.search(r"\bdone\b", t) and not re.search(r"done in a first form|partly", t):
        return "done"
    if re.search(r"done in a first form|first findings|partly", t):
        return "partial"
    return "open"


def parse_roadmap(text):
    """The numbered steps of 'The plan', the stability gate and the twelve Full Understanding items."""
    warnings = []
    m = re.search(r'<h2 id="plan">(.*?)<h2 id="detail">', text, re.S)
    plan = m.group(1) if m else ""
    if not plan:
        warnings.append("docs/roadmap.html: no 'The plan' section found")
    steps = []
    for card in re.findall(r'<details class="card".*?</details>', plan, re.S):
        s = re.search(r'<span class="num">(.*?)</span><span class="title">(.*?)<small>(.*?)</small></span>'
                      r'<span class="badge[^"]*">(.*?)</span>', card, re.S)
        if not s:
            continue
        num = strip_tags(s.group(1))
        if not num.isdigit():
            continue   # the Full Understanding card, read below
        body = card.split("</summary>", 1)[-1]
        items = [(strip_tags(li), item_state(strip_tags(li))) for li in re.findall(r"<li>(.*?)</li>", body, re.S)]
        steps.append(Step(num, strip_tags(s.group(2)), strip_tags(s.group(3)), strip_tags(s.group(4)), items))
    gate, fu = "", []
    f = re.search(r"First: stability.*?</h3>\s*<p>(.*?)</p>", plan, re.S)
    if f:
        gate = strip_tags(f.group(1))
    f = re.search(r"Then the twelve items</h3>\s*<ol>(.*?)</ol>", plan, re.S)
    if f:
        fu = [(strip_tags(li), item_state(strip_tags(li))) for li in re.findall(r"<li>(.*?)</li>", f.group(1), re.S)]
    else:
        warnings.append("docs/roadmap.html: the Full Understanding list was not found")
    return steps, gate, fu, warnings


# ------------------------------------------------------------------ git
def git_commits(repo):
    """CRD-nnn -> newest short hash whose subject names it. Empty when git is missing or fails."""
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        out = subprocess.run(["git", "-C", repo, "log", "--format=%h %s", "-n", "2000"], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=10, creationflags=flags).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    found = {}
    for line in out.splitlines():
        h, _, subj = line.partition(" ")
        for tid in ID_RX.findall(subj):
            found.setdefault(tid, h)   # git log is newest first
    return found


# ------------------------------------------------------------------ everything
def read_text(path):
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def load(repo, use_git=True):
    warnings = []
    hpath = os.path.join(repo, "docs", "handoff.md")
    rpath = os.path.join(repo, "docs", "roadmap.html")
    tasks, source, updated = [], "table", ""
    if os.path.exists(hpath):
        tasks, source, updated, w = parse_handoff(read_text(hpath))
        warnings += w
    else:
        warnings.append(f"not found: {hpath}")
    steps, gate, fu = [], "", []
    if os.path.exists(rpath):
        steps, gate, fu, w = parse_roadmap(read_text(rpath))
        warnings += w
    else:
        warnings.append(f"not found: {rpath}")
    if use_git:
        commits = git_commits(repo)
        for t in tasks:
            if not t.commit and t.id in commits:
                t.commit, t.commit_from_git = commits[t.id], True
    return Progress(tasks, source, updated, steps, gate, fu, warnings)


def find_repo(start):
    """The folder above start that holds docs/handoff.md."""
    d = os.path.abspath(start)
    for _ in range(6):
        if os.path.exists(os.path.join(d, "docs", "handoff.md")):
            return d
        d = os.path.dirname(d)
    return None
