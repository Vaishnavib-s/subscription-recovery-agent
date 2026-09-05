import json
from datetime import datetime, timezone, timedelta


RETRY_STATE_FILE = "retry_state.json"


def load_retry_state():
    try:
        with open(RETRY_STATE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_retry_state(state):
    with open(RETRY_STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2)


def schedule_retry(subscription_id, retry_number, retry_after_minutes):
    """
    Record a retry for a subscription.

    The retry is scheduled as application state for now.
    Actual Razorpay charging remains outside this layer.
    """

    state = load_retry_state()

    next_retry = datetime.now(timezone.utc) + timedelta(
        minutes=retry_after_minutes
    )

    state[subscription_id] = {
        "retry_number": retry_number,
        "max_retries": 2,
        "next_retry_at": next_retry.isoformat(),
        "status": "SCHEDULED"
    }

    save_retry_state(state)

    return state[subscription_id]


def get_retry_state(subscription_id):
    state = load_retry_state()
    return state.get(subscription_id)


if __name__ == "__main__":

    result = schedule_retry(
        subscription_id="sub_TEST_RETRY",
        retry_number=1,
        retry_after_minutes=60
    )

    print("\n========== RETRY SCHEDULE ==========")
    print("Subscription ID:", "sub_TEST_RETRY")
    print("Retry Number:", result["retry_number"])
    print("Max Retries:", result["max_retries"])
    print("Next Retry:", result["next_retry_at"])
    print("Status:", result["status"])
    print("====================================")