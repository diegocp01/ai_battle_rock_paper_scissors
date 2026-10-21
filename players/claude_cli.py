"""Claude player: runs the Claude Code CLI (`claude -p`) for each move.

Uses whatever account the CLI is already signed in with, so no API key is
needed. Model aliases always point at the newest model in each family.
"""

import json
import os
import shutil
import subprocess

from .common import MOVE_SCHEMA, MOVE_TIMEOUT_SECONDS, SYSTEM_PROMPT, PlayerError, workdir

CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")

MODELS = [
    {"id": "fable", "name": "Claude Fable", "tag": "Most capable"},
    {"id": "opus", "name": "Claude Opus", "tag": "Deep reasoning"},
    {"id": "sonnet", "name": "Claude Sonnet", "tag": "Balanced"},
    {"id": "haiku", "name": "Claude Haiku", "tag": "Fastest"},
]

EFFORTS = ["low", "medium", "high", "xhigh", "max"]
DEFAULT_MODEL = "haiku"
DEFAULT_EFFORT = "medium"


def status() -> dict:
    """What the setup screen needs to offer Claude models."""
    ready = shutil.which(CLAUDE_BIN) is not None
    return {
        "ready": ready,
        "message": None if ready else "Claude Code CLI not found. Install it, then run `claude` once to sign in.",
        "models": [dict(m, efforts=EFFORTS, default_effort=DEFAULT_EFFORT) for m in MODELS],
        "default_model": DEFAULT_MODEL,
    }


def model_name(model_id: str) -> str:
    return next((m["name"] for m in MODELS if m["id"] == model_id), model_id)


def call_claude_move(prompt: str, model: str, effort: str) -> tuple[str | None, str | None]:
    """Ask Claude for a move. Returns (choice, reasoning)."""
    cmd = [
        CLAUDE_BIN,
        "-p",
        "--model", model,
        "--effort", effort,
        "--system-prompt", SYSTEM_PROMPT,
        "--output-format", "json",
        "--json-schema", json.dumps(MOVE_SCHEMA),
        # A bare game move: no tools, MCP servers, settings or saved session.
        "--tools", "",
        "--strict-mcp-config",
        "--setting-sources", "",
        "--no-session-persistence",
    ]

    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=MOVE_TIMEOUT_SECONDS,
            cwd=workdir(),
        )
    except FileNotFoundError:
        raise PlayerError("Claude Code CLI not found. Install it, then run `claude` once to sign in.")
    except subprocess.TimeoutExpired:
        raise PlayerError(f"Claude didn't answer within {MOVE_TIMEOUT_SECONDS}s.")

    data = _parse_result(proc.stdout)
    if data is None:
        detail = (proc.stderr or proc.stdout).strip()
        raise PlayerError(detail[-300:] or f"claude exited with code {proc.returncode}.")
    if data.get("is_error"):
        raise PlayerError(str(data.get("result") or data.get("subtype") or "Claude returned an error."))

    move = data.get("structured_output") or {}
    return move.get("choice"), move.get("reasoning")


def _parse_result(stdout: str) -> dict | None:
    """The CLI prints one JSON result object; tolerate stray lines around it."""
    text = stdout.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for line in reversed(text.splitlines()):
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("type") == "result":
            return data
    return None
