# Jane Street Puzzle Notification Bot — Spec

## Goal

Get notified as fast as possible when Jane Street publishes a new puzzle on HuggingFace, so you can start solving before the crowd arrives.

Read @PLAN.md for context.

## What We're Watching

Jane Street's HuggingFace org: `https://huggingface.co/jane-street`

Current inventory (as of Feb 2026):
- **Spaces:** `puzzle` (active), `droppedaneuralnet` (previous puzzle)
- **Models:** `dormant-model-1`, `dormant-model-2`, `dormant-model-3`, `dormant-model-warmup`, `2025-03-10`
- **Key contributors:** `ricsonc`, `alexwp`

New puzzles could appear as new Spaces, new Models, or updates to existing repos (e.g., the `puzzle` space was updated ~19hrs ago as of writing). The activity feed also shows model publishes days before space updates, suggesting models may be staged ahead of the puzzle space going live.

---

## Approach Options (Ranked by Complexity)

### Option 1: Just Watch the Org on HuggingFace (Zero Code)

**Difficulty: Trivial (~2 minutes)**

HuggingFace has a built-in notification system. Go to `https://huggingface.co/jane-street` and click **"Watch repos"** (or follow the org). Configure notification preferences at `https://huggingface.co/settings/notifications` to receive **email notifications** on new activity.

**Pros:** Zero code, zero maintenance, instant setup.
**Cons:** Noisy (triggers on any commit, discussion, PR — not just new puzzles). Email delivery latency could be minutes. No filtering logic. You'd need to manually check whether a notification is a new puzzle vs. a routine update.

**Verdict:** Do this immediately as a baseline, then layer a smarter system on top.

### Option 2: Polling Script + Telegram/SMS Alert (~2-3 hours)

**Difficulty: Easy**

A lightweight script that polls the HuggingFace API every N minutes and alerts you when something new appears.

#### Core Logic

```python
# HuggingFace has a public REST API — no auth required for public repos
import requests

def get_jane_street_repos():
    spaces = requests.get("https://huggingface.co/api/spaces?author=jane-street").json()
    models = requests.get("https://huggingface.co/api/models?author=jane-street").json()
    return {
        "spaces": {s["id"]: s["lastModified"] for s in spaces},
        "models": {m["id"]: m["lastModified"] for m in models},
    }

# Compare against last known state, alert on diff
```

#### Notification Options
- **Telegram Bot:** Easiest. Create a bot via @BotFather, send messages to yourself via `bot.sendMessage()`. Near-instant delivery with push notifications on your phone.
- **Twilio SMS:** ~$0.01/message. More reliable for waking you up at 3am.
- **Email via SMTP:** Free but slower delivery.
- **ntfy.sh:** Free, open-source push notifications. Zero signup. `curl -d "New JS puzzle!" ntfy.sh/your-secret-topic`

#### Deployment Options
- **Cron job on a VPS:** Cheapest. A $4/mo Hetzner or DigitalOcean box running a cron every 5 minutes.
- **GitHub Actions scheduled workflow:** Free tier gives you ~2000 min/month. Run every 5-10 min. State stored as a GitHub artifact or gist.
- **Railway/Render free tier:** Easy deployment, may have cold start issues.
- **Your own machine:** Simplest but only works while it's on.

#### Polling Interval Considerations
- **Every 5 minutes** is reasonable. HuggingFace API is public, unauthenticated, and rate-limited but generous.
- Worst case: you learn about a new puzzle 5 minutes after it drops. Best case: instantly.
- Be respectful — don't poll every 10 seconds. You're making unauthenticated requests to someone else's API.

### Option 3: HuggingFace Webhook → Serverless Function (~3-4 hours)

**Difficulty: Medium**

HuggingFace supports webhooks that fire on repo events. You can watch the `jane-street` org and get HTTP POST callbacks on any `repo` scope event with `action: "create"`.

#### Setup

1. Go to `https://huggingface.co/settings/webhooks`
2. Create a webhook watching the `jane-street` org
3. Set domains to `["repo"]` to catch new repo creation
4. Point the target URL to your serverless endpoint

#### Receiver

A small serverless function (Cloudflare Worker, AWS Lambda, Vercel edge function) that:
1. Validates the webhook secret
2. Checks if `event.action == "create"` and `event.repo.type in ["space", "model"]`
3. Sends you a Telegram/SMS notification

```python
# Pseudocode for the webhook handler
async def handle_webhook(payload):
    if payload["event"]["action"] == "create":
        repo = payload["repo"]
        notify(f"🚨 New Jane Street {repo['type']}: {repo['name']}")
```

**Pros:** True push — no polling delay. Fires within seconds of repo creation.
**Cons:** Requires a publicly accessible endpoint. HuggingFace webhooks are still marked as somewhat experimental. More moving parts (webhook config, serverless function, secret management).

---

## Recommended Implementation

**Layer 1 (do now):** Watch `jane-street` on HuggingFace for email notifications. Takes 2 minutes.

**Layer 2 (build in Claude Code):** Option 2 polling script with Telegram alerts, deployed as a GitHub Actions scheduled workflow. This is the sweet spot of reliability, simplicity, and speed. Estimated ~2 hours including Telegram bot setup.

**Layer 3 (optional upgrade):** If you want sub-minute latency, add the webhook approach as a complement. But realistically, a 5-minute polling interval means you'll know about a new puzzle within 5 minutes of it dropping — and given that solving these takes hours to days, those 5 minutes are negligible compared to the actual solving advantage you'd gain from just being *faster at the puzzle itself*.

---

## Smart Filtering

Not every HF activity is a new puzzle. The bot should distinguish:
- **New Space creation** → Almost certainly a new puzzle. High-priority alert.
- **New Model creation** → Possibly puzzle-related (see `dormant-model-*` pattern). Medium alert.
- **Updates to existing repos** → Could be puzzle edits, solver count updates, or minor fixes. Low priority unless it's the `puzzle` space getting a major update.

A simple heuristic: alert immediately on any new repo, and also alert if the `puzzle` space's `lastModified` changes by more than a few hours from last check (suggesting a content swap rather than a minor tweak).

---

## Bonus: Activity Pattern Analysis

From the current data, Jane Street's puzzle cadence looks like:
- `droppedaneuralnet` appeared ~28 days ago
- `puzzle` space (the new one) appeared shortly after and was updated ~19hrs ago
- `dormant-model-*` repos were published in Nov-Dec 2025

This suggests puzzles drop roughly monthly. The dormant models may be pre-staged puzzle components. Worth monitoring model publishes as potential early signals that a new puzzle is imminent.

---

## Files Needed

```
js-puzzle-notifier/
├── notifier.py          # Core polling logic + Telegram notification
├── requirements.txt     # requests, python-telegram-bot
├── .github/
│   └── workflows/
│       └── poll.yml     # GitHub Actions cron schedule
├── state.json           # Last known repo state (persisted between runs)
└── README.md
```

## Estimated Total Effort
- Option 1 (Watch org): **2 minutes**
- Option 2 (Polling bot): **2-3 hours** including Telegram setup and GitHub Actions deployment
- Option 3 (Webhook): **3-4 hours** including serverless function setup

The speed advantage comes from solving faster, not knowing 30 seconds sooner. Option 2 is the right call.