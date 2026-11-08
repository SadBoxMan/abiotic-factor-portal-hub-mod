"""Mock test for the Cordona Tracker's reader (no window).

1. Parses the repo's current docs/handoff.md and docs/roadmap.html and checks the queue and the release path.
2. Feeds made-up handoff text to check bad rows, duplicates and the fallback to bullets.
Run:  python tools\\CordonaTracker\\tests\\test_tracker.py      (exit code 0 = all passed)
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import trackerdata as td  # noqa: E402

fails = []
count = 0


def check(name, ok, info=""):
    global count
    count += 1
    print(("ok   " if ok else "FAIL ") + name + (f"  ({info})" if info and not ok else ""))
    if not ok:
        fails.append(name)


# ------------------------------------------------------------------ 1. the real files
repo = td.find_repo(HERE)
check("repo found", repo is not None)
p = td.load(repo, use_git=False)
ids = [t.id for t in p.tasks]
check("queue read from the table", p.queue_source == "table", p.queue_source)
check("no warnings", not p.warnings, "; ".join(p.warnings))
check("at least 17 tasks", len(p.tasks) >= 17, len(p.tasks))
check("ids unique", len(ids) == len(set(ids)))
check("ids in order", ids == sorted(ids))
check("every state known", all(t.state in td.STATES for t in p.tasks), [t.id for t in p.tasks if t.state not in td.STATES])
check("every title filled", all(t.title for t in p.tasks))
# every CRD id the handoff's section 1 names in a bullet also has a table row
with open(os.path.join(repo, "docs", "handoff.md"), encoding="utf-8") as f:
    text = f.read()
bullet_ids = set(td.task_bullets(text))
check("every task bullet has a table row", bullet_ids <= set(ids), sorted(bullet_ids - set(ids)))
by = {t.id: t for t in p.tasks}
check("CRD-011 done at 2e1ad3b", by.get("CRD-011") and by["CRD-011"].state == "done" and by["CRD-011"].commit == "2e1ad3b")
check("CRD-008 retired", by.get("CRD-008") and by["CRD-008"].state == "retired")
check("CRD-011 has its detail bullet", by.get("CRD-011") and "reload" in by["CRD-011"].detail)
check("last updated line read", bool(p.updated))

check("6 roadmap steps", [s.num for s in p.steps] == ["1", "2", "3", "4", "5", "6"], [s.num for s in p.steps])
check("every step has a badge", all(s.badge for s in p.steps))
one = next((s for s in p.steps if "1.0" in s.title), None)
check("1.0 step found with 3 pieces", one is not None and len(one.items) == 3, one and len(one.items))
check("1.0: the config GUI piece is done", one is not None and any(t.startswith("The config GUI") and st == "done" for t, st in one.items))
check("12 Full Understanding items", len(p.understanding) == 12, len(p.understanding))
check("World name counts as started", p.understanding and p.understanding[1][1] == "partial")
check("Skybox is open", p.understanding and p.understanding[0][1] == "open")
check("stability gate read", "Hook stability" in p.gate)

# git: commits named by ID are found (skipped quietly if git is missing)
commits = td.git_commits(repo)
if commits:
    check("git log names CRD-011", commits.get("CRD-011") == "2e1ad3b", commits.get("CRD-011"))

# ------------------------------------------------------------------ 2. made-up text
mock = """# Handoff
Last updated: 1 January 2027 (CRD-099).

## 1. Work queue

| ID | Task | State | Commit |
|---|---|---|---|
| CRD-020 | Good row | Running | abc1234 |
| CRD-021 | Bad state | finished | |
| CRD-022 | Bad commit | done | not-a-hash |
| CRD-020 | Duplicate | done | |
| CRD-023 | On hold row | on hold | |

- CRD-020 good row: running, see the detail.
  continued line.

## 2. Next section
- CRD-020 should not be read from here.
"""
tasks, source, updated, warnings = td.parse_handoff(mock)
m = {t.id: t for t in tasks}
check("mock: 4 rows (duplicate dropped)", len(tasks) == 4, len(tasks))
check("mock: state is case-insensitive", m["CRD-020"].state == "running")
check("mock: bad state -> unknown + warning", m["CRD-021"].state == "unknown" and any("CRD-021" in w for w in warnings))
check("mock: bad commit dropped + warning", m["CRD-022"].commit == "" and any("CRD-022" in w for w in warnings))
check("mock: duplicate warned", any("twice" in w for w in warnings))
check("mock: 'on hold' read", m["CRD-023"].state == "on hold")
check("mock: detail only from section 1, with continuation",
      "continued line" in m["CRD-020"].detail and "should not" not in m["CRD-020"].detail)
check("mock: last updated", updated.startswith("1 January 2027"))

loose = "## 1. Queue\n- CRD-030 thing one: done 3 Nov.\n- CRD-031 thing two: queued.\n## 2. x\n"
tasks, source, _, warnings = td.parse_handoff(loose)
check("fallback: bullets used when no table", source == "bullets" and len(tasks) == 2)
check("fallback: states guessed", [t.state for t in tasks] == ["done", "queued"], [t.state for t in tasks])
check("fallback: warns", any("guessed" in w for w in warnings))

print(f"\n{count - len(fails)} of {count} checks passed")
sys.exit(1 if fails else 0)
