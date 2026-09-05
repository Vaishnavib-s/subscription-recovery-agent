# RecoverFlow — Subscription Payment Recovery Agent

**Track:** AI Revenue Recovery — Razorpay AI Buildathon

## The problem

Razorpay handles subscription payment retries, but different payment failures can require different recovery strategies. A card-expired failure should not be treated the same way as a temporary insufficient-funds decline.

RecoverFlow adds a decision layer that classifies failures, applies controlled retry and escalation policies, communicates with customers, tracks recovery outcomes, and reports honestly on what was recovered.

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
```

For escalation, Groq generates the customer-facing message with a deterministic fallback if the API is unavailable.

## What's real vs. simulated

The Razorpay webhook integration, failure classification, recovery policy, recovery agent, retry/promise tracking, message generation, and audit logging run through the actual application pipeline.

For batch evaluation, the **starting subscription cases and downstream customer outcomes are synthetic**. This is necessary because a demo cannot wait for real customers to respond to recovery outreach.

The synthetic cases still pass through the same recovery pipeline used by the webhook flow.

## Batch demonstration

A 15-case synthetic batch is provided through `batch_runner.py` to demonstrate aggregate recovery outcomes.

Example evaluation:

| Metric | Result |
|---|---:|
| Amount at risk | ₹15,789 |
| Amount recovered | ₹11,791 |
| Recovery rate | ~74.7% |
| Unresolved | 2 |

The batch exercises the major recovery paths including STOP, RETRY, ESCALATE, RECOVERED, and EXHAUSTED outcomes.

## Failure handling

LLM calls are wrapped with fallback handling. If Groq is unavailable, the system falls back to deterministic behavior rather than crashing or silently dropping a recovery case.

## Razorpay integration

The system integrates with Razorpay Test Mode through a signed webhook endpoint.

The webhook verifies the Razorpay signature, extracts subscription and payment information, classifies payment failures, applies the recovery policy, and records the resulting action in the audit trail.

Test Mode is used for integration testing, while the batch runner provides repeatable aggregate evaluation without relying on real customer behavior.

## What we deliberately skipped

- Building our own payment processor — Razorpay handles payment execution.
- Allowing an LLM to make financial decisions — policy decisions remain deterministic.
- Treating simulated customer behavior as real revenue recovery — simulated outcomes are clearly separated from live Test Mode events.

## Files

`webhook.py` — Razorpay webhook endpoint  
`recovery_policy.py` — recovery decision engine  
`failure_classifier.py` — hard/soft failure classification  
`escalation_agent.py` — Groq messaging + fallback  
`recovery_agent.py` — executes recovery decisions  
`retry_manager.py` — retry state  
`promise_tracker.py` — recovery/promise state  
`audit_logger.py` — JSONL audit trail  
`batch_runner.py` — synthetic batch evaluation  
`streamlit_app.py` — recovery dashboard  
`orchestrator.py` — pipeline orchestration

## Run it
pip install -r requirements.txt
# add RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, GROQ_API_KEY to .env
python batch_runner.py
streamlit run streamlit_app.py