#!/usr/bin/env python3
"""Curate one attributed public open-source fork per Casablanca-local day.

Requires FORK_TOKEN for writes. Nothing is ever deleted or pushed into forks.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

OWNER = "elkouaym"
BASE_URL = "https://api.github.com"
TZ = ZoneInfo("Africa/Casablanca")
HISTORY_FILE = Path("data/fork_history.json")
LIBRARY_FILE = Path("LIBRARY.md")
TIMEOUT_SECONDS = 25
TOPICS = ("java", "python", "sql-data", "devops", "ai-ml", "backend", "security", "mobile")
# Curated, diversified upstream choices. GitHub API revalidates each live.
PROJECTS = (
    ("spring-projects/spring-petclinic", "java", "Spring Boot Java architecture"),
    ("TheAlgorithms/Java", "java", "Algorithms and Java"),
    ("TheAlgorithms/Python", "python", "Python algorithms and tests"),
    ("DataWithBaraa/sql-data-analytics-project", "sql-data", "Sales analytics and T-SQL"),
    ("sqlfluff/sqlfluff", "sql-data", "SQL linting and Python tooling"),
    ("docker/awesome-compose", "devops", "Docker Compose application examples"),
    ("kubernetes/examples", "devops", "Kubernetes examples"),
    ("microsoft/ML-For-Beginners", "ai-ml", "Machine-learning lessons and notebooks"),
    ("microsoft/Data-Science-For-Beginners", "ai-ml", "Data-science curriculum"),
    ("fastapi/full-stack-fastapi-template", "backend", "FastAPI, React and databases"),
    ("prisma/prisma-examples", "backend", "Backend and relational database examples"),
    ("OWASP/CheatSheetSeries", "security", "Defensive application security guides"),
    ("expo/examples", "mobile", "React Native and Expo examples"),
)


class GitHubError(RuntimeError):
    def __init__(self, code: int, path: str):
        super().__init__(f"GitHub API HTTP {code} at {path}")
        self.code = code


def api(path: str, *, token: str = "", method: str = "GET", payload=None, missing_ok: bool = False):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "EMSI-educational-github-curator",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(BASE_URL + path, method=method, headers=headers, data=body)
    try:
        with urlopen(req, timeout=TIMEOUT_SECONDS) as result:
            return json.load(result)
    except HTTPError as exc:
        if missing_ok and exc.code == 404:
            return None
        raise GitHubError(exc.code, path) from exc
    except URLError as exc:
        raise RuntimeError(f"GitHub network request failed for {path}") from exc


def get_my_repositories(token: str) -> list[dict]:
    result: list[dict] = []
    for page in range(1, 11):
        batch = api(f"/users/{OWNER}/repos?per_page=100&page={page}&sort=created&direction=desc", token=token)
        result.extend(r for r in batch if not r.get("private"))
        if len(batch) < 100:
            return result
    raise RuntimeError("More than 1000 repositories: pagination limit, stopping safely")


def local_date(iso_time: str) -> dt.date:
    parsed = dt.datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
    return parsed.astimezone(TZ).date()


def eligible(repo: dict, now: dt.date) -> bool:
    pushed_at = repo.get("pushed_at")
    return (
        bool((repo.get("license") or {}).get("spdx_id"))
        and (repo.get("license") or {}).get("spdx_id") != "NOASSERTION"
        and not repo.get("private", True)
        and not repo.get("fork", False)
        and not repo.get("archived", False)
        and not repo.get("disabled", False)
        and (repo.get("size") or 0) < 160000  # GitHub size in KB; avoid very large forks
        and bool(pushed_at)
        and local_date(pushed_at) >= now - dt.timedelta(days=365)
        and repo.get("owner", {}).get("login", "").lower() != OWNER
    )


def save_entry(entries: list[dict], upstream: str, fork_url: str, topic: str, description: str, date: str) -> None:
    if any(e.get("upstream", "").lower() == upstream.lower() for e in entries):
        return
    entries.append({"date": date, "upstream": upstream, "fork_url": fork_url,
                    "topic": topic, "description": description})
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Open Source Learning Library", "",
        "These are **attributed educational forks**, not original works.",
        "Respect the original author(s), license, and repository history.", "",
        "| Date (Morocco) | Theme | Study fork | Original source | What to study |",
        "| --- | --- | --- | --- | --- |",
    ]
    for e in reversed(entries):
        lines.append(
            f'| {e["date"]} | {e["topic"]} | [Fork]({e["fork_url"]}) | '
            f'[Upstream](https://github.com/{e["upstream"]}) | {e["description"]} |'
        )
    LIBRARY_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def candidate_order(entries: list[dict]):
    previous = entries[-1]["topic"] if entries else None
    topics = list(TOPICS)
    if previous in topics:
        offset = (topics.index(previous) + 1) % len(topics)
    else:
        offset = dt.datetime.now(TZ).date().toordinal() % len(topics)
    topics = topics[offset:] + topics[:offset]
    for topic in topics:
        for project in PROJECTS:
            if project[1] == topic:
                yield project


def run(*, token: str, today: dt.date, dry_run: bool = False) -> str:
    if not dry_run:
        if not token:
            raise RuntimeError("Missing FORK_TOKEN secret. No fork attempted.")
        user = api("/user", token=token)
        if user.get("login", "").lower() != OWNER:
            raise RuntimeError("FORK_TOKEN is not owned by elkouaym. No fork attempted.")

    entries = json.loads(HISTORY_FILE.read_text(encoding="utf-8")) if HISTORY_FILE.exists() else []
    existing = get_my_repositories(token)
    # If today's attributed fork exists (also if created manually), index that instead.
    same_day = [r for r in existing if r.get("fork") and r.get("created_at") and local_date(r["created_at"]) == today]
    if same_day:
        repo = same_day[0]
        detail = api("/repos/" + repo["full_name"], token=token)
        parent = detail.get("parent", {}).get("full_name")
        print("Already have a public fork for today:", repo["html_url"])
        if parent and not dry_run:
            info = next((p for p in PROJECTS if p[0].lower() == parent.lower()), None)
            save_entry(entries, parent, repo["html_url"], info[1] if info else "other",
                       info[2] if info else "Study the upstream README", today.isoformat())
        return "already_exists"
    if any(e.get("date") == today.isoformat() for e in entries):
        print("Fork already recorded today; skipping duplicate.")
        return "already_recorded"

    owned_names = {r["name"].lower() for r in existing}
    already_forked = set()
    for r in existing:
        if r.get("fork"):
            # Listing repositories omits the parent. We must not fork a second time
            # from another upstream with the same destination name.
            already_forked.add(r["name"].lower())
    known_upstreams = {e.get("upstream", "").lower() for e in entries}

    for upstream, topic, description in candidate_order(entries):
        if upstream.lower() in known_upstreams:
            continue
        name = upstream.split("/")[-1]
        if name.lower() in owned_names or name.lower() in already_forked:
            continue
        try:
            metadata = api("/repos/" + upstream, token=token)
        except GitHubError as exc:
            if exc.code in (404, 410):
                print("Source unavailable:", upstream)
                continue
            raise
        if not eligible(metadata, today):
            continue
        # Fetch README as a lightweight installation/documentation check.
        try:
            api("/repos/" + upstream + "/readme", token=token)
        except GitHubError as exc:
            if exc.code == 404:
                continue
            raise

        if dry_run:
            print("DRY RUN only. Would fork:", upstream, "->", f"{OWNER}/{name}")
            return "dry_run"

        print("Forking public licensed repo:", upstream)
        api("/repos/" + upstream + "/forks", token=token, method="POST",
            payload={"default_branch_only": True})
        for attempt in range(15):
            fork = api(f"/repos/{OWNER}/{quote(name)}", token=token, missing_ok=True)
            parent = ((fork or {}).get("parent") or {}).get("full_name", "")
            if fork and fork.get("fork") and not fork.get("private") and parent.lower() == upstream.lower():
                save_entry(entries, upstream, fork["html_url"], topic, description, today.isoformat())
                print("VERIFIED public attributed fork:", fork["html_url"])
                return "forked"
            time.sleep(4)
        raise RuntimeError("Fork requested, but upstream attribution not verified. Check account manually.")
    raise RuntimeError("No eligible unowned curated source available. No fork created.")


def main() -> int:
    dry_run = os.environ.get("DRY_RUN", "false").strip().lower() == "true"
    token = os.environ.get("FORK_TOKEN", "")
    try:
        result = run(token=token, today=dt.datetime.now(TZ).date(), dry_run=dry_run)
        print("Result:", result)
    except (RuntimeError, GitHubError, ValueError, KeyError) as exc:
        print("Curator stopped safely:", exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
