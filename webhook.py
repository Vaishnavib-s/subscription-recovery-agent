from flask import Flask, request
import os
import hmac
import hashlib
import json

from dotenv import load_dotenv

from recovery_policy import decide_action
from failure_classifier import classify_failure
from recovery_case import build_recovery_case
from recovery_agent import execute_recovery_action
from audit_logger import log_recovery_event
from retry_manager import get_retry_state


load_dotenv(override=True)

app = Flask(__name__)

WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")


@app.route("/webhook", methods=["POST"])
def webhook():

    # =========================================================
    # 1. VERIFY RAZORPAY WEBHOOK SIGNATURE
    # =========================================================

    raw_body = request.get_data()

    signature = request.headers.get("X-Razorpay-Signature")

    print("Webhook secret loaded:", WEBHOOK_SECRET is not None)
    print(
        "Webhook secret length:",
        len(WEBHOOK_SECRET) if WEBHOOK_SECRET else 0
    )
    print("Signature received:", signature is not None)
    print(
        "Signature length:",
        len(signature) if signature else 0
    )

    if not WEBHOOK_SECRET:
        return "Webhook secret not configured", 500

    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    if not signature or not hmac.compare_digest(
        signature,
        expected_signature
    ):
        return "Invalid signature", 400

    # =========================================================
    # 2. PARSE WEBHOOK
    # =========================================================

    data = request.get_json()

    print("\n========== FULL WEBHOOK PAYLOAD ==========")
    print(json.dumps(data, indent=2))
    print("==========================================")

    if not data:
        return "Invalid JSON", 400

    event = data.get("event")

    print("\n========== RAZORPAY WEBHOOK ==========")
    print("Event:", event)

    # =========================================================
    # 3. EXTRACT SUBSCRIPTION
    # =========================================================

    subscription = (
        data.get("payload", {})
            .get("subscription", {})
            .get("entity", {})
    )

    if subscription:

        print("Subscription ID:", subscription.get("id"))
        print("Status:", subscription.get("status"))
        print(
            "Auth Attempts:",
            subscription.get("auth_attempts")
        )
        print(
            "Paid Count:",
            subscription.get("paid_count")
        )

    # =========================================================
    # 4. EXTRACT PAYMENT
    # =========================================================

    payment = (
        data.get("payload", {})
            .get("payment", {})
            .get("entity", {})
    )

    # ---------------------------------------------------------
    # Amount at risk
    # ---------------------------------------------------------

    amount_at_risk = None

    if (
        event == "payment.failed"
        and payment
        and payment.get("amount") is not None
    ):
        # Razorpay amount is in smallest currency unit.
        # For INR: paise -> rupees.
        amount_at_risk = payment["amount"] / 100

        print("Amount at Risk: ₹", amount_at_risk)

    else:
        print("Amount at Risk: unavailable in webhook")

    # ---------------------------------------------------------
    # Amount recovered
    # ---------------------------------------------------------

    amount_recovered = 0

    if (
        event == "subscription.charged"
        and payment
        and payment.get("status") == "captured"
        and payment.get("amount") is not None
    ):
        # Successful captured payment.
        # Razorpay amount: paise -> rupees.
        amount_recovered = payment["amount"] / 100

        print("Amount Recovered: ₹", amount_recovered)

    else:
        print("Amount Recovered: ₹0")

    # ---------------------------------------------------------
    # Payment failure details
    # ---------------------------------------------------------

    if event == "payment.failed" and payment:

        print("\n--- Payment Failure ---")
        print("Payment ID:", payment.get("id"))
        print("Payment Status:", payment.get("status"))
        print("Error Code:", payment.get("error_code"))
        print(
            "Error Description:",
            payment.get("error_description")
        )
        print("Error Source:", payment.get("error_source"))
        print("Error Step:", payment.get("error_step"))
        print("Error Reason:", payment.get("error_reason"))

    # =========================================================
    # 5. CLASSIFY PAYMENT FAILURE
    # =========================================================

    classification = None

    if event == "payment.failed" and payment:

        failure = {
            "error_code": payment.get("error_code"),
            "error_description": payment.get("error_description"),
            "error_reason": payment.get("error_reason")
        }

        classification = classify_failure(failure)

        print("\n--- Failure Classification ---")
        print(
            "Type:",
            classification["decline_type"].upper()
        )
        print(
            "Reason:",
            classification["reason"]
        )

    # =========================================================
    # 6. PROCESS SUBSCRIPTION RECOVERY
    # =========================================================

    if subscription:

        subscription_id = subscription.get("id")
        status = subscription.get("status")

        # -----------------------------------------------------
        # Determine decline type
        # -----------------------------------------------------

        if classification:

            decline_type = classification["decline_type"]

        else:

            # Subscription events such as subscription.halted
            # may arrive without payment.failed.
            decline_type = "soft"

        # -----------------------------------------------------
        # Determine failure / payment reason
        # -----------------------------------------------------

        if event == "payment.failed" and payment:

            failure_reason = (
                payment.get("error_description")
                or payment.get("error_reason")
                or "payment failure"
            )

        elif (
            event == "subscription.charged"
            and payment
            and payment.get("status") == "captured"
        ):

            failure_reason = "payment successfully captured"

        else:

            failure_reason = (
                "subscription event without payment failure"
            )

        # =====================================================
        # 7. LOAD OUR APPLICATION RETRY STATE
        # =====================================================

        retry_state = get_retry_state(subscription_id)

        if retry_state:

            retry_number = retry_state.get(
                "retry_number",
                0
            )

            print("\n--- Existing Retry State ---")
            print("Retry Number:", retry_number)
            print(
                "Retry Status:",
                retry_state.get("status")
            )

        else:

            retry_number = 0

            print("\n--- Retry State ---")
            print("No existing retry state")

        # =====================================================
        # 8. RUN RECOVERY POLICY
        # =====================================================

        policy_input = {
            "status": status,
            "decline_type": decline_type,
            "retry_number": retry_number,
            "auth_attempts": subscription.get(
                "auth_attempts",
                0
            )
        }

        decision = decide_action(policy_input)

        print("\n--- Recovery Decision ---")
        print(
            "Decision:",
            decision["decision"]
        )
        print(
            "Reason:",
            decision["reason"]
        )

        # =====================================================
        # 9. BUILD CANONICAL RECOVERY CASE
        # =====================================================

        case = build_recovery_case(
            subscription_id=subscription_id,
            status=status,
            auth_attempts=subscription.get(
                "auth_attempts",
                0
            ),
            decline_type=decline_type,
            failure_reason=failure_reason,
            decision=decision,
            retry_number=retry_number,
            max_retries=2,
            amount_at_risk=amount_at_risk,
            amount_recovered=amount_recovered
        )

        print("\n--- Recovery Case ---")
        print(case)

        # =====================================================
        # 10. EXECUTE RECOVERY ACTION
        # =====================================================

        action_result = execute_recovery_action(
            subscription_id,
            decision,
            case
        )

        # =====================================================
        # 11. AUDIT LOG
        # =====================================================

        log_recovery_event(
            case,
            action_result
        )

    print("======================================\n")

    return "Webhook received", 200


if __name__ == "__main__":

    app.run(
        port=5000,
        debug=True
    )