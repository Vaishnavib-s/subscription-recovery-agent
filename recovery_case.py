def build_recovery_case(
    subscription_id,
    status,
    auth_attempts,
    decline_type,
    failure_reason,
    decision,
    retry_number=0,
    max_retries=2,
    amount_at_risk=None,
    amount_recovered=0
):
    """
    Build the canonical recovery case used by all recovery components.
    """

    case = {
        "subscription_id": subscription_id,
        "status": status,
        "auth_attempts": auth_attempts,
        "decline_type": decline_type,
        "failure_reason": failure_reason,
        "decision": decision["decision"],
        "decision_reason": decision["reason"],
        "retry_number": retry_number,
        "max_retries": max_retries,
        "amount_at_risk": amount_at_risk,
        "amount_recovered": amount_recovered
    }

    return case


if __name__ == "__main__":

    test_decision = {
        "decision": "RETRY",
        "reason": "soft decline; retry 1 of 2"
    }

    case = build_recovery_case(
        subscription_id="sub_TEST_RETRY",
        status="pending",
        auth_attempts=1,
        decline_type="soft",
        failure_reason="insufficient funds",
        decision=test_decision,
        retry_number=1,
        max_retries=2,
        amount_at_risk=None,
        amount_recovered=0
    )

    print("\n========== RECOVERY CASE ==========")

    for key, value in case.items():
        print(f"{key}: {value}")

    print("===================================")