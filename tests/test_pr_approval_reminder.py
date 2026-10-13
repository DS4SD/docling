# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SPEC = importlib.util.spec_from_file_location(
    "pr_approval_reminder",
    Path(__file__).resolve().parents[1] / ".github/scripts/pr_approval_reminder.py",
)
assert SPEC is not None and SPEC.loader is not None
reminder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = reminder
SPEC.loader.exec_module(reminder)

NOW = datetime(2026, 10, 8, 6, 0, tzinfo=timezone.utc)


def run(sha: str, name: str, created: str, **overrides: Any) -> dict[str, Any]:
    data = {
        "head_sha": sha,
        "name": name,
        "event": "pull_request",
        "conclusion": "action_required",
        "created_at": created,
    }
    data.update(overrides)
    return data


def pull(number: int, sha: str, labels: tuple[str, ...] = (), **overrides: Any):
    data = {
        "number": number,
        "title": f"fix: change {number}",
        "html_url": f"https://github.com/o/r/pull/{number}",
        "user": {"login": f"user{number}"},
        "head": {"sha": sha},
        "draft": False,
        "labels": [{"name": label} for label in labels],
    }
    data.update(overrides)
    return data


def test_only_current_head_commits_of_ready_prs_count() -> None:
    runs = [
        run("aaa", "Run CI", "2026-10-06T06:00:00Z"),
        run("aaa", "Run Docs CI", "2026-10-05T06:00:00Z"),
        run("old", "Run CI", "2026-10-01T06:00:00Z"),
        run("bbb", "Run CI", "2026-10-07T06:00:00Z", conclusion="success"),
        run("ccc", "Run CI", "2026-10-07T06:00:00Z"),
    ]
    pulls = [
        pull(1, "aaa", ("ai:ci-safe", "docx")),
        pull(2, "new"),  # its waiting run belongs to an older commit
        pull(3, "bbb"),
        pull(4, "ccc", draft=True),
    ]
    prs = reminder.find_waiting_prs(pulls, reminder.waiting_runs_by_sha(runs))
    assert [pr.number for pr in prs] == [1]
    assert prs[0].workflows == ["Run CI", "Run Docs CI"]
    assert prs[0].waiting_since == datetime(2026, 10, 5, 6, tzinfo=timezone.utc)
    assert prs[0].ai_labels == ["ai:ci-safe"]


def test_message_puts_care_first_and_escapes_titles() -> None:
    safe = reminder.WaitingPr(
        1,
        "fix(docx): a <!channel> & b|c",
        "u1",
        "alice",
        NOW,
        ["Run CI"],
        ["ai:ci-safe"],
    )
    care = reminder.WaitingPr(
        2,
        "feat: x",
        "u2",
        "bob",
        datetime(2026, 10, 5, 6, tzinfo=timezone.utc),
        ["Run CI"],
        ["ai:ci-needs-care", "ai:possible-duplicate"],
    )
    plain = reminder.WaitingPr(3, "docs: y", "u3", "carol", NOW, ["Run CI"], [])
    payload = reminder.build_message([care, safe, plain], "o/r", NOW)
    sections = [b["text"]["text"] for b in payload["blocks"] if b["type"] == "section"]
    assert sections == [
        "*:warning: Needs care* (1)\n• <u2|#2 x> · 3 d",
        "*:grey_question: Not triaged* (1)\n• <u3|#3 y> · 0 h",
        "*:white_check_mark: No CI concern* (1)\n• <u1|#1 a &lt;!channel&gt; &amp; b¦c> · 0 h",
    ]
    assert payload["blocks"][0]["text"]["text"].endswith("oldest 3 d")
    assert payload["text"] == "3 PR(s) in o/r wait for a maintainer to approve CI"


def test_long_groups_link_the_rest_to_the_job_summary() -> None:
    prs = [
        reminder.WaitingPr(n, "t" * 90, f"https://x/{n}", "u", NOW, ["CI"], [])
        for n in range(60)
    ]
    run = "https://github.com/o/r/actions/runs/1"
    payload = reminder.build_message(prs, "o/r", NOW, run)
    (section,) = [
        b["text"]["text"] for b in payload["blocks"] if b["type"] == "section"
    ]
    assert section.count("\n• ") == reminder.MAX_PRS_PER_GROUP
    assert f"<{run}|+55 more>" in section
    assert f"<{run}|Full list (60 PRs)>" in payload["blocks"][-1]["elements"][0]["text"]

    summary = reminder.build_summary(prs, "o/r", NOW)
    assert summary.count("| [#") == 60
