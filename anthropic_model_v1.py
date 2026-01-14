import json
import time
import logging
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

# Retry configuration for handling thinking-only responses
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1  # seconds (exponential backoff: 1s, 2s, 4s)

# Models that DON'T use thinking (standard models)
NON_THINKING_MODELS = {'claude-haiku-4.5-standard'}

MOVE_SYSTEM_PROMPT = """You are playing Rock Paper Scissors against another AI.

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

OUTPUT FORMAT (strict JSON):
{"choice": "rock"}

Valid choices: "rock", "paper", or "scissors"
No extra text. Output only valid JSON.""".strip()


MOVE_SCHEMA = {
    "type": "object",
    "properties": {
        "choice": {
            "type": "string",
            "enum": ["rock", "paper", "scissors"]
        }
    },
    "required": ["choice"],
    "additionalProperties": False
}


def call_claude_move(user_prompt: str, model: str = "claude-haiku-4-5-20251001") -> tuple[str, str | None]:
    """
    Call Claude to make a Rock Paper Scissors choice.
    Returns (choice, reasoning_summary) where choice is "rock", "paper", or "scissors".
    """
    use_thinking = model != "claude-haiku-4-5-20251001" or "standard" not in str(model).lower()
    
    for attempt in range(MAX_RETRIES):
        if use_thinking:
            response = client.beta.messages.create(
                model=model,
                max_tokens=2048,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 1024,
                },
                betas=["structured-outputs-2025-11-13"],
                system=MOVE_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                output_format={
                    "type": "json_schema",
                    "schema": MOVE_SCHEMA
                }
            )

            thinking_summary = None
            thinking_parts = []
            for block in response.content:
                if getattr(block, "type", None) == "thinking":
                    s = getattr(block, "thinking", None) or getattr(block, "summary", None) or ""
                    if s:
                        thinking_parts.append(s)
            if thinking_parts:
                thinking_summary = "\n".join(thinking_parts).strip()

            json_text = ""
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    t = getattr(block, "text", "") or ""
                    if t.strip():
                        json_text += t

            if not json_text.strip():
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_BASE * (2 ** attempt)
                    logging.warning(f"Claude move returned thinking-only response, retry {attempt+1}/{MAX_RETRIES} in {delay}s")
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"No text response from Claude model after {MAX_RETRIES} attempts.")

            try:
                data = json.loads(json_text)
            except json.JSONDecodeError:
                raise RuntimeError(f"Expected JSON from model, got:\n{json_text}")

            choice = data["choice"]
            return choice, thinking_summary
        else:
            response = client.beta.messages.create(
                model=model,
                max_tokens=2048,
                betas=["structured-outputs-2025-11-13"],
                system=MOVE_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                output_format={
                    "type": "json_schema",
                    "schema": MOVE_SCHEMA
                }
            )

            json_text = ""
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    t = getattr(block, "text", "") or ""
                    if t.strip():
                        json_text += t

            if not json_text.strip():
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_BASE * (2 ** attempt)
                    logging.warning(f"Claude move returned empty response, retry {attempt+1}/{MAX_RETRIES} in {delay}s")
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"No text response from Claude model after {MAX_RETRIES} attempts.")

            try:
                data = json.loads(json_text)
            except json.JSONDecodeError:
                raise RuntimeError(f"Expected JSON from model, got:\n{json_text}")

            choice = data["choice"]
            return choice, None
    
    raise RuntimeError("Unexpected error in call_claude_move")


def call_claude_move_with_thinking_flag(user_prompt: str, model: str, use_thinking: bool) -> tuple[str, str | None]:
    """
    Call Claude to make a Rock Paper Scissors choice with explicit thinking flag.
    Returns (choice, reasoning_summary) where choice is "rock", "paper", or "scissors".
    """
    for attempt in range(MAX_RETRIES):
        if use_thinking:
            response = client.beta.messages.create(
                model=model,
                max_tokens=2048,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 1024,
                },
                betas=["structured-outputs-2025-11-13"],
                system=MOVE_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                output_format={
                    "type": "json_schema",
                    "schema": MOVE_SCHEMA
                }
            )

            thinking_summary = None
            thinking_parts = []
            for block in response.content:
                if getattr(block, "type", None) == "thinking":
                    s = getattr(block, "thinking", None) or getattr(block, "summary", None) or ""
                    if s:
                        thinking_parts.append(s)
            if thinking_parts:
                thinking_summary = "\n".join(thinking_parts).strip()

            json_text = ""
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    t = getattr(block, "text", "") or ""
                    if t.strip():
                        json_text += t

            if not json_text.strip():
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_BASE * (2 ** attempt)
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"No text response from Claude model after {MAX_RETRIES} attempts.")

            data = json.loads(json_text)
            return data["choice"], thinking_summary
        else:
            response = client.beta.messages.create(
                model=model,
                max_tokens=2048,
                betas=["structured-outputs-2025-11-13"],
                system=MOVE_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                output_format={
                    "type": "json_schema",
                    "schema": MOVE_SCHEMA
                }
            )

            json_text = ""
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    t = getattr(block, "text", "") or ""
                    if t.strip():
                        json_text += t

            if not json_text.strip():
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_BASE * (2 ** attempt)
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"No text response from Claude model after {MAX_RETRIES} attempts.")

            data = json.loads(json_text)
            return data["choice"], None
    
    raise RuntimeError("Unexpected error in call_claude_move_with_thinking_flag")


# Test
if __name__ == "__main__":
    test_prompt = """You are Claude playing Rock Paper Scissors. Round 2.

PREVIOUS ROUNDS:
Round 1: You chose SCISSORS, Opponent chose ROCK → You LOST

SCORE: You 0 - Opponent 1

Choose: rock, paper, or scissors."""

    choice, summary = call_claude_move(test_prompt)
    print("Choice:", choice)
    print("\n🧠 Reasoning Summary:\n", summary or "No reasoning summary found.")