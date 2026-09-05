from recovery_policy import decide_action
from recovery_agent import execute_recovery_action
from retry_manager import get_retry_state


def process_recovery_case(case):
    """
    Main orchestration layer for the subscription recovery system.

    Flow:
        Recovery case
            ↓
        Load retry state
            ↓
        Recovery policy
            ↓
        Recovery agent
            ↓
        Final result
    """

    subscription_id = case["subscription_id"]

    print("\n========== ORCHESTRATOR ==========")
    print("Processing:", subscription_id)

    # ---------------------------------
    # Load application retry state
    # ---------------------------------

    retry_state = get_retry_state(subscription_id)

    if retry_state:
        retry_number = retry_state.get("retry_number", 0)

        print("Existing Retry State:")
        print("Retry Number:", retry_number)
        print("Retry Status:", retry_state.get("status"))
    else:
        retry_number = case.get("retry_number", 0)
        print("No existing retry state")

    # ---------------------------------
    # Build policy input
    # ---------------------------------

    policy_input = {
        "status": case["status"],
        "decline_type": case.get("decline_type"),
        "retry_number": retry_number
    }

    # ---------------------------------
    # Ask recovery policy for decision
    # ---------------------------------

    decision = decide_action(policy_input)

    print("\n--- Policy Decision ---")
    print("Decision:", decision["decision"])
    print("Reason:", decision["reason"])

    # ---------------------------------
    # Build complete recovery case
    # ---------------------------------

    case["retry_number"] = retry_number
    case["decision"] = decision["decision"]
    case["decision_reason"] = decision["reason"]

    # ---------------------------------
    # Execute selected action
    # ---------------------------------

    result = execute_recovery_action(
        subscription_id=subscription_id,
        decision=decision,
        case=case
    )

    # ---------------------------------
    # Final result
    # ---------------------------------

    print("\n--- Orchestration Complete ---")
    print("Final Action:", result["action"])
    print("Action Status:", result["status"])
    print("================================\n")

    return {
        "case": case,
        "decision": decision,
        "result": result
    }


if __name__ == "__main__":

    test_cases = [

        {
            "subscription_id": "sub_ORCH_ACTIVE",
            "status": "active",
            "auth_attempts": 0,
            "decline_type": "soft",
            "failure_reason": None
        },

        {
            "subscription_id": "sub_ORCH_RETRY",
            "status": "pending",
            "auth_attempts": 1,
            "decline_type": "soft",
            "failure_reason": "insufficient funds"
        },

        {
            "subscription_id": "sub_ORCH_HARD",
            "status": "pending",
            "auth_attempts": 1,
            "decline_type": "hard",
            "failure_reason": "card expired"
        },

        {
            "subscription_id": "sub_ORCH_ESCALATE",
            "status": "halted",
            "auth_attempts": 2,
            "decline_type": "soft",
            "failure_reason": "insufficient funds"
        }
    ]

    for case in test_cases:
        process_recovery_case(case)