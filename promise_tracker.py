import json
from datetime import datetime, timezone


PROMISE_STATE_FILE = "promise_state.json"


def load_promise_state():
    try:
        with open(PROMISE_STATE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_promise_state(state):
    with open(PROMISE_STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2)


def record_promise(subscription_id, promised_date):
    """
    Record a customer's promise to pay.

    promised_date should be an ISO-format date/time string.
    """

    state = load_promise_state()

    state[subscription_id] = {
        "promised_date": promised_date,
        "status": "PROMISE_MADE",
        "recorded_at": datetime.now(timezone.utc).isoformat()
    }

    save_promise_state(state)

    return state[subscription_id]


def get_promise(subscription_id):
    state = load_promise_state()
    return state.get(subscription_id)


def mark_recovered(subscription_id):
    state = load_promise_state()

    if subscription_id not in state:
        return None

    state[subscription_id]["status"] = "RECOVERED"
    state[subscription_id]["resolved_at"] = (
        datetime.now(timezone.utc).isoformat()
    )

    save_promise_state(state)

    return state[subscription_id]


def mark_exhausted(subscription_id):
    state = load_promise_state()

    if subscription_id not in state:
        return None

    state[subscription_id]["status"] = "EXHAUSTED"
    state[subscription_id]["resolved_at"] = (
        datetime.now(timezone.utc).isoformat()
    )

    save_promise_state(state)

    return state[subscription_id]


if __name__ == "__main__":

    subscription_id = "sub_TEST_PROMISE"

    result = record_promise(
        subscription_id=subscription_id,
        promised_date="2026-09-10T12:00:00+00:00"
    )

    print("\n========== PROMISE TRACKER ==========")
    print("Subscription ID:", subscription_id)
    print("Promised Date:", result["promised_date"])
    print("Status:", result["status"])
    print("Recorded At:", result["recorded_at"])
    print("=====================================")