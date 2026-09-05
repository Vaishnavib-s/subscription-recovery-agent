import os
import json
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv(override=True)


# --------------------------------
# Groq client
# --------------------------------

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)


# --------------------------------
# Deterministic rules
# --------------------------------

HARD_FAILURES = {
    "card_expired",
    "card_blocked",
    "invalid_card",
}

SOFT_FAILURES = {
    "insufficient_funds",
    "timeout",
    "bank_error",
}


def classify_failure(failure: dict) -> dict:
    """
    Classify a Razorpay payment failure.

    1. Use deterministic rules for obvious failures.
    2. Use Groq only when the failure is ambiguous.
    3. Fall back to SOFT if the LLM fails.
    """

    error_code = (failure.get("error_code") or "").lower()
    error_description = (failure.get("error_description") or "").lower()
    error_reason = (failure.get("error_reason") or "").lower()

    text = " ".join([
        error_code,
        error_description,
        error_reason
    ])

    # --------------------------------
    # Clearly HARD
    # --------------------------------

    hard_keywords = [
        "card_expired",
        "card expired",
        "card_blocked",
        "card blocked",
        "invalid card",
        "invalid_card",
    ]

    for keyword in hard_keywords:
        if keyword in text:
            return {
                "decline_type": "hard",
                "reason": f"deterministic rule matched: {keyword}"
            }

    # --------------------------------
    # Clearly SOFT
    # --------------------------------

    soft_keywords = [
        "insufficient funds",
        "insufficient_funds",
        "timeout",
        "timed out",
        "bank error",
        "bank_error",
    ]

    for keyword in soft_keywords:
        if keyword in text:
            return {
                "decline_type": "soft",
                "reason": f"deterministic rule matched: {keyword}"
            }

    # --------------------------------
    # Ambiguous → Groq
    # --------------------------------

    prompt = f"""
You are classifying a payment failure for a subscription recovery system.

Classify the failure as exactly one of:

HARD
- Retrying is unlikely to help.
- Examples: expired card, blocked card, invalid card.

SOFT
- Retrying may reasonably succeed.
- Examples: insufficient funds, temporary bank error, timeout.

AMBIGUOUS
- There is not enough information to safely classify it.

Payment failure:

error_code: {failure.get("error_code")}
error_description: {failure.get("error_description")}
error_reason: {failure.get("error_reason")}

Return ONLY valid JSON in this format:

{{
    "classification": "HARD" or "SOFT" or "AMBIGUOUS",
    "reason": "short explanation"
}}
"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": "You classify payment failures. Return only JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            timeout=10
        )

        content = response.choices[0].message.content.strip()

        result = json.loads(content)

        classification = result.get("classification", "").upper()

        if classification == "HARD":
            return {
                "decline_type": "hard",
                "reason": f"Groq classification: {result.get('reason', '')}"
            }

        if classification == "SOFT":
            return {
                "decline_type": "soft",
                "reason": f"Groq classification: {result.get('reason', '')}"
            }

        return {
            "decline_type": "ambiguous",
            "reason": f"Groq could not safely classify: {result.get('reason', '')}"
        }

    except Exception as e:

        print("Groq classification failed:", str(e))

        return {
            "decline_type": "soft",
            "reason": "Groq unavailable; deterministic fallback treats failure as soft"
        }


# --------------------------------
# Test
# --------------------------------

if __name__ == "__main__":

    test_cases = [
        {
            "name": "Hard - expired card",
            "data": {
                "error_code": "CARD_EXPIRED",
                "error_description": "Card has expired",
                "error_reason": "card_expired"
            }
        },
        {
            "name": "Soft - insufficient funds",
            "data": {
                "error_code": "PAYMENT_FAILED",
                "error_description": "Insufficient funds",
                "error_reason": "insufficient_funds"
            }
        },
        {
            "name": "Ambiguous - Razorpay mandate failure",
            "data": {
                "error_code": "BAD_REQUEST_ERROR",
                "error_description": "Mandate debit not as per frequency",
                "error_reason": ""
            }
        }
    ]

    for case in test_cases:

        result = classify_failure(case["data"])

        print(f"\n{case['name']}")
        print("Classification:", result["decline_type"].upper())
        print("Reason:", result["reason"])