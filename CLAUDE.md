# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A notification bot that polls the HuggingFace API to detect new Jane Street puzzle releases and sends alerts via Telegram. Deployed as a GitHub Actions scheduled workflow (every 5 minutes).

## Architecture

- **notifier.py**: Core script — fetches Jane Street's HuggingFace spaces/models via public REST API, compares against persisted state, sends Telegram alerts on changes
- **state.json**: Auto-generated on first run. Tracks known repo IDs and the `puzzle` space's commit sha. Committed back to repo by GitHub Actions after each run.
- **.github/workflows/poll.yml**: GitHub Actions cron workflow. Needs `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as repo secrets.

## Key APIs

- HuggingFace list endpoints (no auth): `/api/spaces?author=jane-street`, `/api/models?author=jane-street` — return repo IDs but NOT `lastModified`
- HuggingFace detail endpoint: `/api/spaces/jane-street/puzzle` — returns `sha` and `lastModified`
- Telegram Bot API: `POST /bot{token}/sendMessage`

## Detection Logic

- New space ID in list → HIGH priority alert
- New model ID in list → MEDIUM priority alert
- `puzzle` space sha changed → MEDIUM priority alert (content swap)
- First run: captures state silently, no alerts

## Build & Run

```bash
uv sync
uv run notifier.py
```

Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` env vars for notifications. Without them, alerts print to stdout.
