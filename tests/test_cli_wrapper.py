import subprocess
import unittest
from unittest.mock import patch

from src.core.cli_wrapper import OpenClawCLI


class OpenClawCLITests(unittest.TestCase):
    def test_run_command_translates_missing_binary_error(self) -> None:
        cli = OpenClawCLI()
        with patch("src.core.cli_wrapper.subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaises(RuntimeError):
                cli._run_command(["--version"])

    def test_memory_search_passes_raw_query_without_shell_quotes(self) -> None:
        cli = OpenClawCLI()
        captured_cmd = {}

        def fake_run(cmd, **kwargs):
            captured_cmd["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, stdout="item-1\nitem-2\n", stderr="")

        with patch("src.core.cli_wrapper.subprocess.run", side_effect=fake_run):
            entries = cli.memory_search("risk limits")

        self.assertEqual(entries, ["item-1", "item-2"])
        self.assertEqual(captured_cmd["cmd"][-1], "risk limits")


if __name__ == "__main__":
    unittest.main()
