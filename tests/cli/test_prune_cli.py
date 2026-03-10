"""Integration tests for the prune CLI subcommand wiring in main.py."""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from src.cli.prune import register_prune_parser, handle_prune


# ---------------------------------------------------------------------------
# Parser registration tests
# ---------------------------------------------------------------------------


class TestRegisterPruneParser:
    """Verify register_prune_parser adds 'prune' with correct flags."""

    def _make_parser(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        register_prune_parser(sub)
        return parser

    def test_prune_subcommand_registered(self):
        parser = self._make_parser()
        args = parser.parse_args(["prune"])
        assert args.command == "prune"

    def test_dry_run_flag_default_false(self):
        parser = self._make_parser()
        args = parser.parse_args(["prune"])
        assert args.dry_run is False

    def test_dry_run_flag_set(self):
        parser = self._make_parser()
        args = parser.parse_args(["prune", "--dry-run"])
        assert args.dry_run is True

    def test_days_flag_default_90(self):
        parser = self._make_parser()
        args = parser.parse_args(["prune"])
        assert args.days == 90

    def test_days_flag_custom(self):
        parser = self._make_parser()
        args = parser.parse_args(["prune", "--days", "30"])
        assert args.days == 30

    def test_no_archive_flag_default_false(self):
        parser = self._make_parser()
        args = parser.parse_args(["prune"])
        assert args.no_archive is False

    def test_no_archive_flag_set(self):
        parser = self._make_parser()
        args = parser.parse_args(["prune", "--no-archive"])
        assert args.no_archive is True

    def test_all_flags_combined(self):
        parser = self._make_parser()
        args = parser.parse_args(["prune", "--dry-run", "--days", "7", "--no-archive"])
        assert args.command == "prune"
        assert args.dry_run is True
        assert args.days == 7
        assert args.no_archive is True


# ---------------------------------------------------------------------------
# handle_prune dispatch tests (mocked MemoryService)
# ---------------------------------------------------------------------------


class TestHandlePrune:
    """Verify handle_prune returns correct exit codes."""

    @patch("src.cli.prune.MemoryRegistry")
    @patch("src.cli.prune.MemoryService")
    def test_returns_0_on_success_empty_collection(self, mock_svc_cls, mock_reg_cls):
        """Empty ChromaDB collection -> nothing to prune -> exit 0."""
        mock_svc = MagicMock()
        mock_svc.health_check.return_value = True
        mock_svc.list_documents.return_value = []
        mock_svc_cls.return_value = mock_svc

        mock_reg = MagicMock()
        mock_reg.get_active_rules.return_value = []
        mock_reg_cls.return_value = mock_reg

        args = argparse.Namespace(dry_run=False, days=90, no_archive=False)
        assert handle_prune(args) == 0

    @patch("src.cli.prune.MemoryRegistry")
    @patch("src.cli.prune.MemoryService")
    def test_returns_0_on_dry_run_empty(self, mock_svc_cls, mock_reg_cls):
        """Dry-run with empty collection -> exit 0."""
        mock_svc = MagicMock()
        mock_svc.health_check.return_value = True
        mock_svc.list_documents.return_value = []
        mock_svc_cls.return_value = mock_svc

        mock_reg = MagicMock()
        mock_reg.get_active_rules.return_value = []
        mock_reg_cls.return_value = mock_reg

        args = argparse.Namespace(dry_run=True, days=90, no_archive=False)
        assert handle_prune(args) == 0

    @patch("src.cli.prune.MemoryService")
    def test_returns_1_on_health_check_failure(self, mock_svc_cls):
        """ChromaDB health_check fails -> graceful exit 1."""
        mock_svc = MagicMock()
        mock_svc.health_check.return_value = False
        mock_svc_cls.return_value = mock_svc

        args = argparse.Namespace(dry_run=False, days=90, no_archive=False)
        assert handle_prune(args) == 1

    @patch("src.cli.prune.MemoryService")
    def test_returns_1_on_init_exception(self, mock_svc_cls):
        """MemoryService constructor raises -> graceful exit 1."""
        mock_svc_cls.side_effect = ConnectionError("ChromaDB down")

        args = argparse.Namespace(dry_run=False, days=90, no_archive=False)
        assert handle_prune(args) == 1


# ---------------------------------------------------------------------------
# main.py wiring tests
# ---------------------------------------------------------------------------


class TestMainPyWiring:
    """Verify main.py registers prune and dispatches correctly."""

    @patch("src.cli.prune.handle_prune", return_value=0)
    def test_prune_dispatch_from_main(self, mock_handle):
        """main() dispatches 'prune' command to handle_prune."""
        with patch("sys.argv", ["main", "prune", "--dry-run"]):
            with pytest.raises(SystemExit) as exc_info:
                from src.main import main
                main()
            assert exc_info.value.code == 0
            mock_handle.assert_called_once()

    def test_prune_appears_in_help(self, capsys):
        """'prune' appears in --help output."""
        with patch("sys.argv", ["main", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                from src.main import main
                main()
            assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "prune" in captured.out
