import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv(override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)


def generate_escalation_message(case):
    """
    Generate a customer-facing recovery message.

    The LLM only writes the message.
    The recovery policy has already decided that escalation
    is required.
    """

    prompt = f"""
You are a payment recovery assistant.

Write a short, professional and empathetic message
to a customer whose recurring payment has failed.

Recovery case:
- Subscription status: {case["status"]}
- Payment failure type: {case["decline_type"]}
- Failure reason: {case["failure_reason"]}
- Previous authentication attempts: {case["auth_attempts"]}
- Recovery decision: {case["decision"]}

Rules:
- Do not invent payment details.
- Do not threaten the customer.
- Do not mention internal systems, policies, or AI.
- Do not claim that payment was successfully made.
- Clearly ask the customer to take the appropriate payment action.
- Keep the message concise.
"""

    try:

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": "You write concise, professional payment recovery messages."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        message = response.choices[0].message.content or ""
        message = message.strip()

        return {
            "status": "GENERATED",
            "message": message,
            "source": "groq"
        }

    except Exception as e:

        print("Groq escalation generation failed:", e)

        # Deterministic fallback
        fallback_message = (
            "We were unable to process your scheduled payment. "
            "Please check your payment method and complete the payment "
            "at your earliest convenience."
        )

        return {
            "status": "FALLBACK",
            "message": fallback_message,
            "source": "deterministic_fallback"
        }


if __name__ == "__main__":

    test_case = {
        "subscription_id": "sub_TEST123",
        "status": "halted",
        "auth_attempts": 2,
        "decline_type": "soft",
        "failure_reason": "insufficient funds",
        "decision": "ESCALATE",
        "decision_reason": "retry limit reached or subscription halted"
    }

    result = generate_escalation_message(test_case)

    print("\n========== ESCALATION AGENT ==========")
    print("Status:", result["status"])
    print("Source:", result["source"])
    print("Message:", result["message"])
    print("======================================")