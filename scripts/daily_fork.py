 and (repo.get("pushed_at") or "") >= "2024-01-01"
        and (repo.get("owner") or {}).get("login", "").lower() != OWNER
    )


def save(history, upstream, fork_url, category):
 history.append({"date": dt.date.today().isoformat(),
                    "upstream": upstream, "url": fork_url,
                    "category": category})
 HISTORY.parent.mkdir(parents=True, exist_ok=True)
 HISTORY.write_text(json.dumps(history, indent=2) + "\n")
 rows = [
        "# Open Source Learning Library",
        "",
        "Educational forks only. Credit and original licenses belong to upstream authors.",
        "These forks are for code study and future personal contributions.",
        "",
        "| Date | Subject | My fork | Original author/project |",
        "| --- | --- | --- | --- |",
    ]
    for item in reversed(history):
 rows.append(
            f'| {item["date"]} | {item["category"]} | '
            f'[Study fork]({item["url"]}) | '
            f'[Upstream](https://github.com/{item["upstream"]}) |'
        )
 LIBRARY.write_text("\n".join(rows) + "\n")


def main():
    if not TOKEN:
        raise SystemExit("Missing FORK_TOKEN GitHub Actions secret.")
 user = api("/user")
    if user.get("login", "").lower() != OWNER:
        raise SystemExit("Token must belong to GitHub user elkouaym.")
 history = json.loads(HISTORY.read_text()) if HISTORY.exists() else []
 seen = {x["upstream"].lower() for x in history}
 day = dt.date.today().toordinal()
 candidates = SEEDS[day % len(SEEDS):] + SEEDS[:day % len(SEEDS)]
    for topic in TOPICS:
        try:
 q = quote(f"topic:{topic} stars:>300 fork:false archived:false")
 data = api(f"/search/repositories?q={q}&sort=stars&per_page=6")
            for repo in data.get("items", []):
 candidates.append((repo["full_name"], topic))
        except RuntimeError as exc:
            print("Search skipped:", exc)
    for upstream, category in candidates:
        if upstream.lower() in seen:
            continue
        try:
 repo = api("/repos/" + upstream)
            if not eligible(repo):
                continue
 ame = repo["name"]
            if api(f"/repos/{OWNER}/{quote( ame)}", optional404=True):
                continue
            print("Selected:", upstream, "|", category)
            api(f"/repos/{upstream}/forks", "POST", {"default_branch_only": True})
            for _ in range(12):
 fork = api(f"/repos/{OWNER}/{quote( ame)}", optional404=True)
 parent = ((fork or {}).get("parent") or {}).get("full_name", "")
                if fork and fork.get("fork") and parent.lower() == upstream.lower():
                    save(history, upstream, fork["html_url"], category)
                    print("Verified public educational fork:", fork["html_url"])
                    return
 time.sleep(5)
            raise SystemExit("Fork was requested but could not be verified. Check account.")
        except RuntimeError as exc:
            print("Candidate skipped:", upstream, exc)
    print("No new eligible project found; no fork created.")


if __name__ == "__main__":
    main()
