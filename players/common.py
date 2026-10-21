"""Prompt, output schema and errors shared by both players."""

import os
import tempfile

VALID_CHOICES = ("rock", "paper", "scissors")

SYSTEM_PROMPT = """You are playing Rock Paper Scissors against another AI.

RULES:
- Rock beats Scissors
- Scissors beats Paper
- Paper beats Rock
- Same choice = Draw

STRATEGY:
- You cannot see your opponent's choice before making yours
- Try to be unpredictable
- Consider patterns from previous rounds if available
- Sometimes random is best

Answer with your choice and a short explanation of why you picked it.
Do not use any tools. Just decide.""".strip()

# Both players return this shape. Asking for the reasoning in the output keeps
# it visible even when a model's raw thinking is hidden.
MOVE_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {
            "type": "string",
            "description": "One to three sentences explaining the pick.",
        },
        "choice": {"type": "string", "enum": list(VALID_CHOICES)},
    },
    "required": ["reasoning", "choice"],
    "additionalProperties": False,
}

EFFORT_LABELS = {
    "none": "None",
    "minimal": "Minimal",
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "xhigh": "Extra High",
    "max": "Max",
    "ultra": "Ultra",
}

# How long one move may take before the round is abandoned.
MOVE_TIMEOUT_SECONDS = int(os.environ.get("RPS_MOVE_TIMEOUT", "240"))


class PlayerError(Exception):
    """A failure with a message that is safe to show in the UI."""


_workdir = None


def workdir() -> str:
    """An empty directory for the agents to run in, away from this repo."""
    global _workdir
    if _workdir is None:
        _workdir = tempfile.mkdtemp(prefix="rps-arena-")
    return _workdir
