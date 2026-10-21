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

Optional environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `RPS_MOVE_TIMEOUT` | `240` | Seconds a single move may take before the round stops |
| `CLAUDE_BIN` | `claude` | Path to the Claude Code CLI |
