"""
Import boundary smoke tests.

Verifies that core leaf modules can be imported in isolation without
pulling in agents, orchestrator, or runtime singletons. Add a new
assertion here whenever a new core module is introduced.

These tests catch circular imports before they reach production.
"""
import importlib
import sys


def _isolated_import(module_path: str) -> None:
    """Import a module with a clean sys.modules slate for project modules."""
    # Remove any already-imported project modules so we get a fresh load
    project_keys = [k for k in sys.modules if k.startswith("src.")]
    saved = {k: sys.modules.pop(k) for k in project_keys}
    try:
        importlib.import_module(module_path)
    finally:
        sys.modules.update(saved)


class TestCoreLeafImports:
    """Core leaf modules must import without touching agents or orchestrator."""

    def test_soul_errors_imports_cleanly(self):
        _isolated_import("src.core.soul_errors")

    def test_soul_loader_imports_cleanly(self):
        _isolated_import("src.core.soul_loader")

    def test_state_imports_cleanly(self):
        _isolated_import("src.graph.state")

    def test_audit_logger_imports_cleanly(self):
        _isolated_import("src.core.audit_logger")

    def test_decision_card_imports_cleanly(self):
        _isolated_import("src.core.decision_card")

    def test_kami_imports_cleanly(self):
        _isolated_import("src.core.kami")

    def test_soul_proposal_imports_cleanly(self):
        _isolated_import("src.core.soul_proposal")

    def test_agent_church_imports_cleanly(self):
        _isolated_import("src.core.agent_church")

    def test_ars_auditor_imports_cleanly(self):
        _isolated_import("src.core.ars_auditor")


class TestNoCoreToAgentImport:
    """Leaf core modules must not import from agents or orchestrator."""

    def _get_module_imports(self, module_path: str) -> set[str]:
        mod = importlib.import_module(module_path)
        return {
            name
            for name in vars(mod).values()
            if hasattr(name, "__module__") and isinstance(getattr(name, "__module__", None), str)
        }

    def test_soul_loader_does_not_import_orchestrator(self):
        import src.core.soul_loader as m
        source_file = m.__file__ or ""
        # Read raw source to check for forbidden imports
        with open(source_file, encoding="utf-8") as f:
            source = f.read()
        assert "from src.graph.orchestrator" not in source
        assert "import orchestrator" not in source

    def test_soul_loader_does_not_import_agents(self):
        import src.core.soul_loader as m
        with open(m.__file__, encoding="utf-8") as f:
            source = f.read()
        assert "from src.graph.agents" not in source

    def test_audit_logger_does_not_import_orchestrator(self):
        import src.core.audit_logger as m
        with open(m.__file__, encoding="utf-8") as f:
            source = f.read()
        assert "from src.graph.orchestrator" not in source

    def test_soul_errors_has_no_project_imports(self):
        import src.core.soul_errors as m
        with open(m.__file__, encoding="utf-8") as f:
            source = f.read()
        assert "from src." not in source
        assert "import src." not in source

    def test_soul_proposal_does_not_import_graph(self):
        import src.core.soul_proposal as m
        with open(m.__file__, encoding="utf-8") as f:
            lines = f.readlines()
        # Check only actual import statement lines (not docstrings/comments)
        import_lines = [l for l in lines if l.startswith("from ") or l.startswith("import ")]
        for line in import_lines:
            assert "src.graph" not in line, (
                f"soul_proposal.py must not import from src.graph.*: {line.strip()}"
            )

    def test_agent_church_does_not_import_graph(self):
        import src.core.agent_church as m
        with open(m.__file__, encoding="utf-8") as f:
            lines = f.readlines()
        # Check only actual import statement lines (not docstrings/comments)
        import_lines = [l for l in lines if l.startswith("from ") or l.startswith("import ")]
        for line in import_lines:
            assert "src.graph" not in line, (
                f"agent_church.py must not import from src.graph.*: {line.strip()}"
            )

    def test_ars_auditor_does_not_import_graph(self):
        import src.core.ars_auditor as m
        with open(m.__file__, encoding="utf-8") as f:
            lines = f.readlines()
        # Check only actual import statement lines (not docstrings/comments)
        import_lines = [l for l in lines if l.startswith("from ") or l.startswith("import ")]
        for line in import_lines:
            assert "src.graph" not in line, (
                f"ars_auditor.py must not import from src.graph.*: {line.strip()}"
            )
