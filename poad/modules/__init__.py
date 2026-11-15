"""Vulnerability modules.

Each module is self-describing: it declares its own inputs, supported
technologies/contexts, objectives, and which transforms are compatible. There is
deliberately no single universal questionnaire -- an LFI module asks about files
and traversal depth; an SSTI module asks about the template engine.
"""

from __future__ import annotations

from poad.modules.base import BaseModule, get_module, iter_modules, register
from poad.modules import (  # noqa: F401  (import side effect: registration)
    lfi,
    ssti,
    sqli,
    xss,
    command_injection,
    ssrf,
    xxe,
)

__all__ = ["BaseModule", "get_module", "iter_modules", "register"]
