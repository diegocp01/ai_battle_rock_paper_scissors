# Overview

AI battle arena where OpenAI's GPT models face off against Anthropic's Claude models in Rock Paper Scissors!

![rock paper scissors Demo](static/img/image.png?v=4)

No API keys needed. Each player runs through a local agent tool on your own account:

- **GPT** plays through the [OpenAI Codex Python SDK](https://github.com/openai/codex/tree/main/sdk/python) (`openai-codex`), signed in with your ChatGPT account.
- **Claude** plays through the [Claude Code](https://code.claude.com) CLI (`claude -p`), signed in with your Claude account.

Both players move at the same time, and each one explains its pick.

# Quickstart

Install dependencies (Python 3.10+):
```bash
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```
This also installs the Codex runtime the SDK uses.

Sign in to Codex (one time):
```bash
python login_codex.py
```

Install [Claude Code](https://code.claude.com/docs/en/setup) and sign in (one time):
```bash
curl -fsSL https://claude.ai/install.sh | bash
claude
```

Run the app:
```bash
python app.py
```
Then open http://localhost:5001.

# How it works

- `players/codex_sdk.py` keeps one Codex app-server running (with your plugins, apps, MCP servers and memories turned off, since a move needs none of them) and starts a read-only, throwaway thread for each move with structured output. The GPT model list on the setup screen comes straight from Codex, so it stays current.
- `players/claude_cli.py` runs `claude -p` with tools disabled and a JSON schema for the answer. Model choices are pinned model IDs (Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 5.5), so the version shown is the version that plays.
- You pick a reasoning effort for each player on the setup screen.

# Results

Use **Results** in the top right to open the saved game archive. It includes:

- Outcome charts by matchup, with filters for games where both players use the selected reasoning effort.
- Average response times on a shared scale.
- Expandable game logs with every choice, explanation, and response time.
- A JSON download of the complete archive.

Successful rounds save automatically to `data/results.json`. Games update in place after each round, including unfinished games, and survive server restarts. Writes use a file lock and atomic replacement. Failed or invalid model responses never count as played rounds.

The archive starts with these real experiments from October 21, 2026. Each pairing played one three-round game at each of **low**, **medium**, and **high** reasoning, with the same requested effort for both opponents:

| Matchup | GPT round wins | Claude round wins | Draws |
| --- | ---: | ---: | ---: |
| GPT-6 Luna vs. Claude Haiku 5.5 | 5 | 1 | 3 |
| GPT-6.1 Sol vs. Claude Sonnet 5.5 | 8 | 1 | 0 |
| GPT-6 Astra vs. Claude Opus 5.5 | 7 | 2 | 0 |
| **Total, 9 games / 27 rounds** | **20** | **4** | **3** |

Matching effort labels do not guarantee equal compute. These are small samples, not a model ranking. Response times include local runtime overhead.

To resume this batch without duplicating saved games:

```bash
python run_experiments.py --batch 2026-10-21-matched-effort
```

Use a new batch ID to run another nine-game experiment. Each game uses the same API routes as the arena, with simultaneous moves and history limited to that game.

Run the persistence and game-flow checks without invoking models or touching the real archive:

```bash
python -m unittest discover -s tests -v
```

Optional environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `RPS_MOVE_TIMEOUT` | `240` | Seconds a single move may take before the round stops |
| `CLAUDE_BIN` | `claude` | Path to the Claude Code CLI |
