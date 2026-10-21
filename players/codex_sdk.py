"""GPT player: runs a Codex thread through the OpenAI Codex Python SDK.

Uses whatever account Codex is already signed in with (ChatGPT or API key).
The model list comes from Codex itself, so it stays current.
"""

import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

from openai_codex import ApprovalMode, Codex, CodexError, Sandbox
from openai_codex.types import ReasoningEffort, ReasoningSummary

from .common import MOVE_SCHEMA, MOVE_TIMEOUT_SECONDS, SYSTEM_PROMPT, PlayerError, workdir

NOT_SIGNED_IN = "Codex isn't signed in. Run `python login_codex.py`, then reload this page."

_models_cache = None


def status() -> dict:
    """What the setup screen needs to offer GPT models."""
    global _models_cache
    try:
        with Codex() as codex:
            signed_in = _signed_in(codex)
            if _models_cache is None:
                _models_cache = [_model_info(m) for m in codex.models().data if not m.hidden]
    except Exception as e:  # SDK or runtime missing, app-server failed to start, ...
        return {"ready": False, "message": f"Codex is unavailable: {e}", "models": [], "default_model": None}

    default = next((m["id"] for m in _models_cache if m["is_default"]), None)
    return {
        "ready": signed_in,
        "message": None if signed_in else NOT_SIGNED_IN,
        "models": _models_cache,
        "default_model": default or (_models_cache[0]["id"] if _models_cache else None),
    }


def find_model(model_id: str) -> dict | None:
    if _models_cache is None:
        status()
    return next((m for m in _models_cache or [] if m["id"] == model_id), None)


def call_codex_move(prompt: str, model: str, effort: str) -> tuple[str | None, str | None]:
    """Ask GPT for a move. Returns (choice, reasoning)."""
    try:
        with Codex() as codex:
            if not _signed_in(codex):
                raise PlayerError(NOT_SIGNED_IN)

            thread = codex.thread_start(
                model=model,
                developer_instructions=SYSTEM_PROMPT,
                sandbox=Sandbox.read_only,
                approval_mode=ApprovalMode.deny_all,
                ephemeral=True,
                cwd=workdir(),
            )
            turn = thread.turn(
                prompt,
                effort=ReasoningEffort(effort),
                summary=ReasoningSummary("auto"),
                output_schema=MOVE_SCHEMA,
            )

            # turn.run() blocks until the model answers; give up after the timeout.
            pool = ThreadPoolExecutor(max_workers=1)
            try:
                result = pool.submit(turn.run).result(timeout=MOVE_TIMEOUT_SECONDS)
            except FutureTimeout:
                try:
                    turn.interrupt()
                except Exception:
                    pass
                raise PlayerError(f"GPT didn't answer within {MOVE_TIMEOUT_SECONDS}s.")
            finally:
                pool.shutdown(wait=False)
    except CodexError as e:
        raise PlayerError(str(e) or e.__class__.__name__)

    try:
        move = json.loads(result.final_response or "")
    except json.JSONDecodeError:
        move = {}

    # Prefer the model's own reasoning summary when Codex provides one.
    summaries = [text for item in result.items for text in _reasoning_summaries(item)]
    reasoning = "\n\n".join(summaries) or move.get("reasoning")
    return move.get("choice"), reasoning


def _signed_in(codex: Codex) -> bool:
    account = codex.account()
    return account.account is not None or not account.requires_openai_auth


def _model_info(model) -> dict:
    efforts = [option.reasoning_effort.value for option in model.supported_reasoning_efforts]
    return {
        "id": model.id,
        "name": model.display_name or model.id,
        "tag": model.description or "",
        "efforts": efforts,
        "default_effort": model.default_reasoning_effort.value,
        "is_default": bool(model.is_default),
    }


def _reasoning_summaries(item) -> list[str]:
    item = getattr(item, "root", item)
    if getattr(item, "type", None) != "reasoning":
        return []
    return [text.strip() for text in (item.summary or []) if text and text.strip()]
