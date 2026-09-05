MAX_SOFT_RETRIES = 2


def decide_action(subscription: dict) -> dict:
    """
    Decide the recovery action for a subscription.

    Required fields:
        status
        decline_type

    Optional fields:
        retry_number
        auth_attempts

    retry_number is the application's recovery retry count.
    auth_attempts is kept as Razorpay information and is not
    treated as our retry counter.
    """

    status = subscription["status"]
    decline_type = subscription.get("decline_type")
    retry_number = subscription.get("retry_number", 0)

    # ---------------------------------
    # Active subscription
    # ---------------------------------

    if status == "active":
        return {
            "decision": "STOP",
            "reason": "subscription is active; no recovery action needed"
        }

    # ---------------------------------
    # Hard decline
    # ---------------------------------

    if decline_type == "hard":
        return {
            "decision": "ESCALATE",
            "reason": "hard decline detected; skipping retries"
        }

    # ---------------------------------
    # Halted subscription
    # ---------------------------------

    if status == "halted":
        return {
            "decision": "ESCALATE",
            "reason": "subscription is halted"
        }

    # ---------------------------------
    # Soft decline - retries remaining
    # ---------------------------------

    if decline_type == "soft" and retry_number < MAX_SOFT_RETRIES:
        return {
            "decision": "RETRY",
            "reason": (
                f"soft decline; retry "
                f"{retry_number + 1} of {MAX_SOFT_RETRIES}"
            )
        }

    # ---------------------------------
    # Soft decline - retries exhausted
    # ---------------------------------

    if decline_type == "soft" and retry_number >= MAX_SOFT_RETRIES:
        return {
            "decision": "ESCALATE",
            "reason": "retry limit reached"
        }

    # ---------------------------------
    # Fallback
    # ---------------------------------

    return {
        "decision": "ESCALATE",
        "reason": "unhandled case, defaulting to escalation"
    }


if __name__ == "__main__":

    test_cases = [
        {
            "name": "Active subscription",
            "data": {
                "status": "active",
                "retry_number": 0,
                "decline_type": "soft"
            }
        },
        {
            "name": "Soft decline - first retry",
            "data": {
                "status": "pending",
                "retry_number": 0,
                "decline_type": "soft"
            }
        },
        {
            "name": "Soft decline - second retry",
            "data": {
                "status": "pending",
                "retry_number": 1,
                "decline_type": "soft"
            }
        },
        {
            "name": "Soft decline - retries exhausted",
            "data": {
                "status": "pending",
                "retry_number": 2,
                "decline_type": "soft"
            }
        },
        {
            "name": "Hard decline",
            "data": {
                "status": "pending",
                "retry_number": 0,
                "decline_type": "hard"
            }
        },
        {
            "name": "Halted subscription",
            "data": {
                "status": "halted",
                "retry_number": 0,
                "decline_type": "soft"
            }
        }
    ]

    for case in test_cases:

        result = decide_action(case["data"])

        print(f"\n{case['name']}")
        print("Decision:", result["decision"])
        print("Reason:", result["reason"])