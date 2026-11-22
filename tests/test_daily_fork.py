import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import daily_fork as curator


class CuratorTests(unittest.TestCase):
    def test_local_day_conversion(self):
        # Casablanca used UTC+1 in July and UTC+0 during Ramadan in March.
        self.assertEqual(curator.local_date("2024-07-01T23:30:00Z"), dt.date(2024, 7, 2))
        self.assertEqual(curator.local_date("2024-03-20T23:30:00Z"), dt.date(2024, 3, 20))

    def test_eligible_requires_license_and_recent_activity(self):
        good = {
            "license": {"spdx_id": "MIT"}, "private": False, "fork": False,
            "archived": False, "disabled": False, "size": 1024,
            "pushed_at": "2026-11-20T12:00:00Z", "owner": {"login": "somebody"},
        }
        self.assertTrue(curator.eligible(good, dt.date(2026, 11, 21)))
        self.assertFalse(curator.eligible({**good, "license": None}, dt.date(2026, 11, 21)))
        self.assertFalse(curator.eligible({**good, "fork": True}, dt.date(2026, 11, 21)))

    def test_cannot_fork_if_existing_fork_created_today(self):
        today = dt.date(2026, 11, 21)
        existing = [{"name": "awesome-compose", "html_url": "https://github.com/elkouaym/awesome-compose",
                     "fork": True, "private": False, "created_at": "2026-11-21T12:00:00Z",
                     "full_name": "elkouaym/awesome-compose"}]
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(curator, "HISTORY_FILE", Path(tmp) / "history.json"), \
                 patch.object(curator, "LIBRARY_FILE", Path(tmp) / "LIBRARY.md"), \
                 patch.object(curator, "get_my_repositories", return_value=existing), \
                 patch.object(curator, "api", return_value={"parent": {"full_name": "docker/awesome-compose"}}) as mocked:
                result = curator.run(token="", today=today, dry_run=True)
                self.assertEqual(result, "already_exists")
                self.assertEqual(mocked.call_count, 1)

    def test_renamed_fork_skips_its_original_project(self):
        existing = [{"name": "my-notes", "full_name": "elkouaym/my-notes", "fork": True}]
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(curator, "HISTORY_FILE", Path(tmp) / "history.json"), \
             patch.object(curator, "get_my_repositories", return_value=existing), \
             patch.object(curator, "candidate_order", return_value=[("docker/awesome-compose", "devops", "Docker")]), \
             patch.object(curator, "api", return_value={"parent": {"full_name": "Docker/Awesome-Compose"}}) as api:
            with self.assertRaisesRegex(RuntimeError, "No eligible"):
                curator.run(token="", today=dt.date(2026, 11, 22), dry_run=True)
            api.assert_called_once_with("/repos/elkouaym/my-notes", token="")

    def test_record_keeps_attribution_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(curator, "HISTORY_FILE", Path(tmp) / "data" / "history.json"), \
                 patch.object(curator, "LIBRARY_FILE", Path(tmp) / "LIBRARY.md"):
                entries = []
                curator.save_entry(entries, "docker/awesome-compose", "https://github.com/elkouaym/awesome-compose",
                                   "devops", "Docker study", "2026-11-21")
                curator.save_entry(entries, "docker/awesome-compose", "https://github.com/elkouaym/awesome-compose",
                                   "devops", "Docker study", "2026-11-21")
                self.assertEqual(len(entries), 1)
                self.assertIn("github.com/docker/awesome-compose", curator.LIBRARY_FILE.read_text())
                self.assertEqual(len(json.loads(curator.HISTORY_FILE.read_text())), 1)


if __name__ == "__main__":
    unittest.main()
