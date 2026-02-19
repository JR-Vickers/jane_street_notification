import json
import os
import sys
from datetime import datetime, timezone

import requests

HUGGINGFACE_API = "https://huggingface.co/api"
JANE_STREET_ORG = "jane-street"
WATCHED_SPACE = "jane-street/puzzle"
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
REQUEST_TIMEOUT = 30


def fetch_repo_lists():
    spaces = requests.get(
        f"{HUGGINGFACE_API}/spaces",
        params={"author": JANE_STREET_ORG},
        timeout=REQUEST_TIMEOUT,
    ).json()
    models = requests.get(
        f"{HUGGINGFACE_API}/models",
        params={"author": JANE_STREET_ORG},
        timeout=REQUEST_TIMEOUT,
    ).json()
    return {
        "space_ids": sorted(s["id"] for s in spaces),
        "model_ids": sorted(m["id"] for m in models),
    }


def fetch_space_detail(space_id):
    resp = requests.get(
        f"{HUGGINGFACE_API}/spaces/{space_id}",
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "sha": data.get("sha"),
        "lastModified": data.get("lastModified"),
    }


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return None


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def detect_changes(old_state, new_state):
    changes = []

    new_spaces = set(new_state["space_ids"]) - set(old_state["space_ids"])
    for sid in sorted(new_spaces):
        changes.append(("HIGH", f"New Space: {sid}"))

    new_models = set(new_state["model_ids"]) - set(old_state["model_ids"])
    for mid in sorted(new_models):
        changes.append(("MEDIUM", f"New Model: {mid}"))

    old_detail = old_state.get("watched_space", {})
    new_detail = new_state.get("watched_space", {})
    if old_detail.get("sha") and new_detail.get("sha"):
        if old_detail["sha"] != new_detail["sha"]:
            changes.append(
                ("MEDIUM", f"Puzzle space updated (sha: {new_detail['sha'][:12]})")
            )

    return changes


def format_alert(changes):
    priority_icons = {"HIGH": "\U0001f6a8", "MEDIUM": "\U0001f4e6"}
    lines = ["<b>Jane Street HuggingFace Activity</b>\n"]
    for priority, msg in changes:
        icon = priority_icons.get(priority, "\u2139\ufe0f")
        lines.append(f"{icon} [{priority}] {msg}")
    lines.append(f"\nhttps://huggingface.co/{JANE_STREET_ORG}")
    return "\n".join(lines)


def send_telegram(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print(f"Telegram not configured. Would have sent:\n{message}")
        return False
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
        timeout=REQUEST_TIMEOUT,
    )
    if not resp.ok:
        print(f"Telegram API error: {resp.status_code} {resp.text}")
        return False
    return True


def main():
    try:
        repos = fetch_repo_lists()
        space_detail = fetch_space_detail(WATCHED_SPACE)
    except (requests.RequestException, ValueError) as e:
        print(f"API fetch failed: {e}")
        sys.exit(1)

    new_state = {
        **repos,
        "watched_space": space_detail,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    old_state = load_state()

    if old_state is None:
        print("First run — capturing initial state, no alerts sent.")
        save_state(new_state)
        return

    changes = detect_changes(old_state, new_state)

    if changes:
        message = format_alert(changes)
        sent = send_telegram(message)
        print(f"Detected {len(changes)} change(s). Telegram sent: {sent}")
    else:
        print("No changes detected.")

    save_state(new_state)


if __name__ == "__main__":
    main()
