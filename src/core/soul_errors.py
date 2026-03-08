"""Typed exception hierarchy for the soul loader subsystem."""


class SoulError(Exception):
    """Base exception for soul loading errors."""


class SoulNotFoundError(SoulError):
    """Raised when a soul directory or required file cannot be located."""


class SoulValidationError(SoulError):
    """Raised when a soul file fails schema or content validation."""


class SoulSecurityError(SoulError):
    """Raised when path traversal or other unsafe loading is detected."""


class RequiresHumanApproval(SoulError):
    """Raised when a proposal targets the L1 Orchestrator — cannot be auto-approved."""
