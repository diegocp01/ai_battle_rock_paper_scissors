from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Literal
from dotenv import load_dotenv
load_dotenv()
client = OpenAI()


# Structured response for Rock Paper Scissors choice
class MoveAnswer(BaseModel):
    choice: Literal["rock", "paper", "scissors"]


# Models that use minimal reasoning (fast, no displayed reasoning)
MINIMAL_REASONING_MODELS = {'gpt-5-mini'}

# Models that use low reasoning effort (reasoning displayed, but lower effort)
LOW_REASONING_MODELS = {'gpt-5.1-low'}

# Models that use high reasoning effort
HIGH_REASONING_MODELS = {'gpt-5.2-high'}


def call_chatgpt_move(user_prompt: str, model: str = "gpt-5.1", model_key: str = None) -> tuple[str, str | None]:
    """
    Call ChatGPT to make a Rock Paper Scissors choice.
    Returns (choice, reasoning_summary) where choice is "rock", "paper", or "scissors".
    """
    # Use model_key if provided, otherwise infer from model name
    key = model_key or model
    use_full_reasoning = key not in MINIMAL_REASONING_MODELS
    use_low_reasoning = key in LOW_REASONING_MODELS
    use_high_reasoning = key in HIGH_REASONING_MODELS
    
    system_prompt = """You are playing Rock Paper Scissors against another AI.

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

OUTPUT: Choose exactly one of: rock, paper, or scissors."""

    if use_full_reasoning:
        # Full reasoning model call (low, medium, or high effort, display reasoning)
        if use_high_reasoning:
            reasoning_effort = "high"
        elif use_low_reasoning:
            reasoning_effort = "low"
        else:
            reasoning_effort = "medium"
        response = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=MoveAnswer,
            reasoning={
                "effort": reasoning_effort,
                "summary": "auto"
            },
        )
        
        choice = response.output_parsed.choice

        # Get reasoning summary
        reasoning_summary = None
        for item in response.output:
            if getattr(item, "type", None) == "reasoning":
                parts = []
                for s in (item.summary or []):
                    if getattr(s, "text", None):
                        parts.append(s.text)
                if parts:
                    reasoning_summary = "\n".join(parts)
                break

        return choice, reasoning_summary
    else:
        # Minimal reasoning for speed (don't display reasoning)
        response = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=MoveAnswer,
            reasoning={
                "effort": "minimal"
            },
        )
        
        choice = response.output_parsed.choice
        return choice, None  # Don't return reasoning for mini model


# Test
if __name__ == "__main__":
    test_prompt = """You are GPT playing Rock Paper Scissors. Round 3.

PREVIOUS ROUNDS:
Round 1: You chose ROCK, Opponent chose PAPER → You LOST
Round 2: You chose SCISSORS, Opponent chose SCISSORS → DRAW

SCORE: You 0 - Opponent 1 (1 draw)

Choose: rock, paper, or scissors."""

    choice, summary = call_chatgpt_move(test_prompt)
    print("Choice:", choice)
    print("\n🧠 Reasoning Summary:\n", summary or "No reasoning summary found.")
