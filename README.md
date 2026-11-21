# GitHub Open Source Curator

Educational curator for GitHub profile **[elkouaym](https://github.com/elkouaym)**. It is designed to fork **at most one** licensed public upstream project per Casablanca-local day, preserving the original GitHub fork relationship, author history, and license. It does **not** claim authorship of the original code, delete repositories, or make fake commits to forks.

## Install or repair the repository

The existing project has a broken Python script. This package includes a starting library with the 3 public forks already verified on November 19–21, 2026. Replace these files on its `main` branch with the corrected versions included in this package:

- `.github/workflows/daily-forks.yml`
- `scripts/daily_fork.py`
- `tests/test_daily_fork.py`
- `data/fork_history.json`
- `LIBRARY.md`
- `README.md`

The ZIP is a bundle to extract first; do **not** upload it as a single ZIP file inside GitHub and expect GitHub Actions to read its contents. Using ChatGPT Work with an authorized GitHub browser session, or a local Git client, is easiest. In the GitHub web editor you can also edit/create the individual files.

## Authentication — required for unattended fork creation

GitHub's ordinary built-in `GITHUB_TOKEN` belongs to GitHub Actions, not to your personal GitHub user. A **personal user token** is needed to create a new fork under `elkouaym`. The required permissions depend on the token type and GitHub's API rules; a classic personal access token with `public_repo` scope can manage public repositories, and is broader than permission to fork alone. Review the risk before using it. Prefer the minimum permissions that work, keep it short-lived, and rotate if compromised.

**Never paste a token in ChatGPT, issues, README, commits, workflow YAML or logs.** Create a token only on GitHub's secure settings page and add it directly at:

`https://github.com/elkouaym/github-open-source-curator/settings/secrets/actions`

Click **New repository secret**, name it exactly `FORK_TOKEN`, enter the token privately and save. The token must belong to user `elkouaym` and be permitted to create public forks. Because a classic `public_repo` token is broad, keep it isolated to this repository and expire/revoke it when not needed.

GitHub Actions is configured with `contents: write` so its normal `GITHUB_TOKEN` can commit the generated library files in the *curator repo* only. It never changes source code inside the new forks.

## Safe test & schedule

1. In the repo's **Actions** tab, select **Daily educational open-source fork**.
2. Choose **Run workflow** with `dry_run=true` to test selection without creating a fork. It should finish green (tests and candidate selection).
3. Once configured, the workflow runs near **09:17 Africa/Casablanca** every day; scheduled tasks can be delayed by GitHub. A manual run with `dry_run=false` can create a real public fork and counts towards that date's limit.
4. Each successful run writes `data/fork_history.json` and `LIBRARY.md` with original source links and creation date. It detects manual forks created on the same local day and avoids a second new fork.
5. If token permissions, quota, or GitHub availability cause errors, the workflow stops and shows the real failure; it does not claim a fork exists without verification.

## How ChatGPT explains each publication

The separate, already-created ChatGPT automation **Fork GitHub + apprentissage** must inspect verified forks and give you an explanation in **français + darija latine**: what the project does, technologies, installation, three files, an exercise and two questions. ChatGPT automation and GitHub Actions are two different schedulers; scheduled ChatGPT execution may be delayed, and it can only verify what is visible at execution time. To avoid duplicate forks, it must check the GitHub profile before attempting any new one.

The source license belongs to the original project, and the project itself is for study only.
