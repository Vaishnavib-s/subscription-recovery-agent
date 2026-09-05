# RecoverFlow — Subscription Payment Recovery Agent

**Track:** AI Revenue Recovery — Razorpay AI Buildathon

## The problem

Razorpay handles failed subscription payments, but different failures require different recovery strategies. A card-expired failure should not be treated the same way as a temporary insufficient-funds decline.

RecoverFlow adds the judgment layer: diagnose the failure, decide whether to retry, escalate, or stop, communicate with the customer, track recovery outcomes, and report honestly on what was recovered.

## Design principle

**The policy engine makes every money/state decision. The LLM is used for ambiguous failure classification and customer-facing outreach.**

Every retry, escalation, and stop decision is handled by explicit, auditable application logic rather than allowing an LLM to make financial decisions.

## Pipeline

```text
Razorpay Event
      ↓
Failure Classification
      ↓
Hard / Soft / Known State
      ↓
Recovery Policy
      ↓
RETRY / ESCALATE / STOP
      ↓
Recovery Agent
      ↓
Retry / Promise Tracking
      ↓
Audit Log
      ↓
Streamlit Dashboard
What's real vs. simulated

Classification, policy decisions, and message generation run through the real pipeline for every case — nothing about the decision-making is faked. What's simulated: whether the customer actually pays or responds, since no live customer behavior exists to test against here. batch_runner.py simulates that one step; everything upstream of it is real.

A real run

15-case batch (batch_runner.py, seed=42):

| Metric           |  Result |
| ---------------- | ------: |
| Amount at risk   | ₹15,789 |
| Amount recovered | ₹11,791 |
| Recovery rate    |  ~74.7% |
| Unresolved       |       2 |

All four policy branches exercised: STOP, RETRY, ESCALATE → RECOVERED/EXHAUSTED.
Failure handling

LLM calls are wrapped with fallback handling. If Groq is unavailable, the system falls back to deterministic behavior rather than crashing or silently dropping a recovery case.

Razorpay integration

The system integrates with Razorpay Test Mode through a signed webhook endpoint.

The webhook verifies the Razorpay signature, extracts subscription/payment information, classifies payment failures, applies the recovery policy, and records the resulting action in the audit trail.

Test Mode is used for integration testing; the batch runner is used for repeatable aggregate evaluation.

Run it
pip install -r requirements.txt
# add RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, GROQ_API_KEY to .env
python batch_runner.py
streamlit run streamlit_app.py