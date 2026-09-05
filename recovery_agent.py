from datetime import datetime, timezone

from escalation_agent import generate_escalation_message
from retry_manager import schedule_retry, get_retry_state


def execute_recovery_action(subscription_id, decision, case=None):
    """
    Execute the action selected by the recovery policy.

    Policy engine decides WHAT should happen.
    Recovery agent decides HOW to execute that decision.

    Retry state is persisted by retry_manager.py.
    """

    case = case or {}

    action = decision["decision"]
    reason = decision["reason"]

    print("\n========== RECOVERY AGENT ==========")
    print("Subscription ID:", subscription_id)
    print("Selected Action:", action)
    print("Policy Reason:", reason)

    # ---------------------------------
    # STOP
    # ---------------------------------

    if action == "STOP":

        result = {
            "status": "NO_ACTION",
            "action": "STOP",
            "message": "No recovery action required"
        }

    # ---------------------------------
    # RETRY
    # ---------------------------------

    elif action == "RETRY":

        # Read the current retry state.
        retry_state = get_retry_state(subscription_id)

        if retry_state:
            retry_number = retry_state["retry_number"] + 1
        else:
            retry_number = 1

        retry_info = schedule_retry(
            subscription_id=subscription_id,
            retry_number=retry_number,
            retry_after_minutes=60
        )

        result = {
            "status": "ACTION_REQUIRED",
            "action": "RETRY",
            "message": "Retry action scheduled",
            "retry_number": retry_info["retry_number"],
            "max_retries": retry_info["max_retries"],
            "next_retry_at": retry_info["next_retry_at"]
        }

    # ---------------------------------
    # ESCALATE
    # ---------------------------------

    elif action == "ESCALATE":

        escalation_message = generate_escalation_message(case)

        result = {
            "status": "ACTION_REQUIRED",
            "action": "ESCALATE",
            "message": escalation_message.get("message"),
            "message_source": escalation_message.get("source")
        }

    # ---------------------------------
    # UNKNOWN ACTION
    # ---------------------------------

    else:

        result = {
            "status": "ERROR",
            "action": action,
            "message": "Unknown recovery action"
        }

    # ---------------------------------
    # Audit information
    # ---------------------------------

    result["subscription_id"] = subscription_id
    result["timestamp"] = datetime.now(timezone.utc).isoformat()

    print("Action Status:", result["status"])
    print("Action:", result["action"])
    print("Message:", result["message"])

    if "message_source" in result:
        print("Message Source:", result["message_source"])

    if "retry_number" in result:
        print("Retry Number:", result["retry_number"])
        print("Max Retries:", result["max_retries"])
        print("Next Retry:", result["next_retry_at"])

    print("====================================\n")

    return result


if __name__ == "__main__":

    test_cases = [
        {
            "subscription_id": "sub_TEST_ACTIVE",
            "decision": {
                "decision": "STOP",
                "reason": "subscription is active"
            },
            "case": {
                "status": "active"
            }
        },
        {
            "subscription_id": "sub_TEST_RETRY",
            "decision": {
                "decision": "RETRY",
                "reason": "soft decline; retry 1 of 2"
            },
            "case": {
                "subscription_id": "sub_TEST_RETRY",
                "status": "pending",
                "retry_number": 0,
                "decline_type": "soft",
                "failure_reason": "insufficient funds",
                "decision": "RETRY"
            }
        },
        {
            "subscription_id": "sub_TEST_ESCALATE",
            "decision": {
                "decision": "ESCALATE",
                "reason": "retry limit reached"
            },
            "case": {
                "subscription_id": "sub_TEST_ESCALATE",
                "status": "halted",
                "auth_attempts": 2,
                "decline_type": "soft",
                "failure_reason": "insufficient funds",
                "decision": "ESCALATE",
                "decision_reason": "retry limit reached"
            }
        }
    ]

    for test_case in test_cases:

        execute_recovery_action(
            test_case["subscription_id"],
            test_case["decision"],
            test_case["case"]
        )