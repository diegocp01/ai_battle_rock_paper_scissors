"""The two players: GPT through the Codex SDK, Claude through the Claude Code CLI."""

from .common import PlayerError, VALID_CHOICES
from . import claude_cli, codex_sdk

__all__ = ["PlayerError", "VALID_CHOICES", "claude_cli", "codex_sdk"]
