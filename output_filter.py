#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Output filter for CheetahClaws — scrubs sensitive patterns from agent output
before it reaches the browser.

This is a second-line defence (after the system prompt, before browser render).
The principle: block patterns, not intentions.  We don't try to understand what
the model *meant* — we just redact anything that looks like a file path, IP
address, internal URL, or project identifier.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class _Rule:
    """One replacement rule: if `pattern` matches, substitute `replacement`."""

    pattern: str | re.Pattern
    replacement: str
    description: str  # for logging / debugging
    flags: int = 0


# ── Rule set ─────────────────────────────────────────────────────────────────

_RULES: list[_Rule] = [
    # ── File paths (Windows) ──────────────────────────────────────────
    _Rule(
        re.compile(r"[A-Za-z]:\\(?:Users|home|Program Files|ProgramData|Windows|opt|var|etc|tmp|dev|work)\\(?:[^\s,.，。]{0,60}\\?){0,5}", re.IGNORECASE),
        "[已过滤]",
        "windows-absolute-path",
    ),
    # ── File paths (Unix) ────────────────────────────────────────────
    _Rule(
        re.compile(r"(?:^|(?<=\s))/(?:home|var|etc|opt|tmp|usr|root|mnt|srv)/(?:[^\s,.，。]{0,60}/?){0,5}", re.IGNORECASE),
        "[已过滤]",
        "unix-absolute-path",
    ),
    # ── Project-specific project roots ────────────────────────────────
    _Rule(
        re.compile(r"(?:/|\\|^)(?:RICH|cheetahclaws|web_interface|cheetah_claws)(?:/|\\)", re.IGNORECASE),
        "[已过滤]",
        "project-name-in-path",
    ),
    # ── IP addresses and localhost ────────────────────────────────────
    _Rule(
        re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d{2,5})?\b"),
        "[已过滤]",
        "ip-address",
    ),
    _Rule(
        re.compile(r"\blocalhost\b", re.IGNORECASE),
        "[已过滤]",
        "localhost",
    ),
    # ── Internal API routes ───────────────────────────────────────────
    _Rule(
        re.compile(r"/api(?:/v\d)?/(?:agent|events|prompt|approve|sessions|config|stream|input|auth|folders|lab|session)", re.IGNORECASE),
        "[已过滤]",
        "api-route",
    ),
    # ── Port numbers in suspicious context ────────────────────────────
    _Rule(
        re.compile(r"(?:port|端口)[\s:：]*\d{4,5}", re.IGNORECASE),
        "[已过滤]",
        "port-number",
    ),
    _Rule(
        re.compile(r":8765\b"),
        "[已过滤]",
        "agent-port",
    ),
    # ── Source code / project structure hints ─────────────────────────
    _Rule(
        re.compile(r"\b(?:src|dist|node_modules|__pycache__|\.venv|\.git)(?:/|\\)", re.IGNORECASE),
        "[已过滤]",
        "code-dir",
    ),
    _Rule(
        re.compile(r"\b(?:backend|frontend)\s*(?:/|\\)\s*(?:app|src|api|services)", re.IGNORECASE),
        "[已过滤]",
        "project-structure",
    ),
    # ── Python module references that leak structure ─────────────────
    _Rule(
        re.compile(r"\b(?:app|cheetahclaws|web_interface|cheetah_claws)\.\w+(?:\.\w+)+\b", re.IGNORECASE),
        "[已过滤]",
        "python-import-leak",
    ),
    _Rule(
        re.compile(r"\bfrom\s+(\w+)\.\w+\s+import", re.IGNORECASE),
        "[已过滤]",
        "python-from-import",
    ),
    # ── Environment variable names with values ────────────────────────
    _Rule(
        re.compile(r'\b[A-Z_]{3,30}\s*=\s*["\'][^"\']{6,}["\']', re.IGNORECASE),
        "[已过滤]",
        "env-var-value",
    ),
]


def filter_text(text: str, *, redact: bool = True) -> str:
    """Apply all output-filter rules to *text*.

    Args:
        text: Raw text from the agent (one chunk).
        redact: If True (default), replace matches with ``[已过滤]``.
                If False, return the original text unchanged (useful as a
                feature-flag escape hatch).

    Returns:
        Filtered (redacted) text.
    """
    if not text:
        return text
    if not redact:
        return text

    result = text
    for rule in _RULES:
        try:
            result = rule.pattern.sub(rule.replacement, result)
        except Exception:
            # Never let a filter crash the chat stream.
            continue
    return result


def filter_optional(text: Optional[str], *, redact: bool = True) -> Optional[str]:
    """Same as ``filter_text`` but passes through None."""
    if text is None:
        return None
    return filter_text(text, redact=redact)


def create_filter(config: Optional[dict] = None) -> Callable[[str], str]:
    """Return a configured filter function.

    Reads ``output_filter`` from *config* if provided.  The config key is:

    - ``output_filter``: ``"on"`` (default) or ``"off"`` — escape hatch.

    Usage::

        _filter = create_filter(session.config)
        safe_text = _filter(raw_text)
    """
    if config is None:
        config = {}
    enabled = config.get("output_filter", "on")
    redact = str(enabled).strip().lower() not in ("off", "false", "0", "no", "disabled")

    def _f(text: str) -> str:
        return filter_text(text, redact=redact)

    return _f
