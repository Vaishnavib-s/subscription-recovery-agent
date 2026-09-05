import json
from datetime import datetime, timezone


AUDIT_LOG_FILE = "audit_log.jsonl"


def log_recovery_event(case, action_result):
    """
    Append one recovery event to the audit log.

    Each line in audit_log.jsonl is a separate JSON record.
    """

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subscription_id": case.get("subscription_id"),
        "status": case.get("status"),
        "auth_attempts": case.get("auth_attempts"),
        "decline_type": case.get("decline_type"),
        "failure_reason": case.get("failure_reason"),
        "decision": case.get("decision"),
        "decision_reason": case.get("decision_reason"),
        "action": action_result.get("action"),
        "action_status": action_result.get("status"),
        "message": action_result.get("message"),
        "message_source": action_result.get("message_source"),
        "amount_at_risk": case.get("amount_at_risk"),
        "amount_recovered": case.get("amount_recovered", 0)
    }

    with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")

    print("Audit log: event recorded")

    return record


if __name__ == "__main__":

    test_case = {
        "subscription_id": "sub_TEST123",
        "status": "halted",
        "auth_attempts": 2,
        "decline_type": "soft",
        "failure_reason": "insufficient funds",
        "decision": "ESCALATE",
        "decision_reason": "retry limit reached"
    }

    test_action = {
        "status": "ACTION_REQUIRED",
        "action": "ESCALATE",
        "message": "Please update your payment method.",
        "message_source": "groq"
    }

    record = log_recovery_event(
        test_case,
        test_action
    )

    print("\n========== AUDIT RECORD ==========")
    print(json.dumps(record, indent=2))
    print("==================================")