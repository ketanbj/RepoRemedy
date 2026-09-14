"""Regression checks for PR-size accounting, runnable with the standard library."""

import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import patch

from check_pr_size import changed_lines, main


class SizeTests(unittest.TestCase):
    def test_additions_and_deletions_count_with_tests_and_configuration(self):
        data = (
            "200\t80\tsrc/reporemedy/cli.py\0"
            "100\t20\ttests/test_cli.py\0"
            "30\t5\t.github/workflows/ci.yml\0"
            "10\t2\tpyproject.toml\0"
            "3\t1\t.env.example\0"
        )
        self.assertEqual(changed_lines(data), (451, 0))

    def test_docs_locks_fixtures_and_pilot_data_are_excluded(self):
        data = (
            "50\t10\tREADME.md\0"
            "1200\t0\tuv.lock\0"
            "40\t0\ttests/fixtures/example.py\0"
            "600\t0\tdocs/pilot-results.json\0"
        )
        self.assertEqual(changed_lines(data), (0, 1900))

    def test_renames_count_only_changed_lines_and_check_both_paths(self):
        data = "2\t1\t\x00old.py\x00new.py\x003\t4\t\x00old.py\x00old.txt\x00"
        self.assertEqual(changed_lines(data), (10, 0))

    def test_binary_empty_and_unusual_names(self):
        self.assertEqual(changed_lines(""), (0, 0))
        self.assertEqual(changed_lines("-\t-\tdiagram.png\0"), (0, 0))
        self.assertEqual(changed_lines("1\t2\tsrc/name\twith\nspaces.py\0"), (3, 0))

    def test_limit_boundary_and_smaller_changes(self):
        for count, expected in [(0, 0), (100, 0), (500, 0), (501, 1)]:
            with (
                self.subTest(count=count),
                redirect_stdout(StringIO()),
                redirect_stderr(StringIO()),
            ):
                responses = ["a" * 40, "b" * 40, f"{count}\t0\tsrc/app.py\0".encode()]
                with patch("check_pr_size.subprocess.check_output", side_effect=responses) as git:
                    self.assertEqual(main(["base", "head"]), expected)
                    self.assertIn("a" * 40 + "..." + "b" * 40, git.call_args.args[0])

    def test_missing_revisions_fail_without_running_git(self):
        with redirect_stderr(StringIO()), patch("check_pr_size.subprocess.check_output") as git:
            self.assertEqual(main([]), 2)
            git.assert_not_called()


if __name__ == "__main__":
    unittest.main()
