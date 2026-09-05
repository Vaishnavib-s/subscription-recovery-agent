import json
import os

import pandas as pd
import streamlit as st


AUDIT_FILE = "audit_log.jsonl"


# -----------------------------------------
# Load audit log
# -----------------------------------------

def load_audit_log():
    if not os.path.exists(AUDIT_FILE):
        return []

    records = []

    try:
        with open(AUDIT_FILE, "r", encoding="utf-8") as file:

            for line in file:
                line = line.strip()

                if not line:
                    continue

                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        return records

    except OSError:
        return []


# -----------------------------------------
# Page configuration
# -----------------------------------------

st.set_page_config(
    page_title="Subscription Recovery Agent",
    page_icon="💳",
    layout="wide"
)


# -----------------------------------------
# Header
# -----------------------------------------

st.title("Subscription Recovery Agent")
st.caption("Recovery monitoring and audit dashboard")


# -----------------------------------------
# Load data
# -----------------------------------------

records = load_audit_log()


if not records:

    st.warning("No audit records found.")

    st.info(
        "Run the webhook or recovery pipeline first so that "
        "audit_log.json contains recovery events."
    )

    st.stop()


df = pd.DataFrame(records)


# -----------------------------------------
# Normalize columns
# -----------------------------------------

for column in [
    "subscription_id",
    "status",
    "decline_type",
    "failure_reason",
    "decision",
    "decision_reason",
    "action",
    "action_status",
    "message_source"
]:
    if column not in df.columns:
        df[column] = "N/A"


# -----------------------------------------
# Headline metrics
# -----------------------------------------

total_cases = len(df)

escalated = len(
    df[df["action"] == "ESCALATE"]
)

retry_cases = len(
    df[df["action"] == "RETRY"]
)

no_action = len(
    df[df["action"] == "STOP"]
)


# We only count money as recovered when the
# audit record explicitly contains a confirmed
# recovered amount.

if "amount_recovered" in df.columns:
    recovered_amount = pd.to_numeric(
        df["amount_recovered"],
        errors="coerce"
    ).fillna(0).sum()
else:
    recovered_amount = 0


if "amount_at_risk" in df.columns:
    at_risk_amount = pd.to_numeric(
        df["amount_at_risk"],
        errors="coerce"
    ).fillna(0).sum()
else:
    at_risk_amount = 0


# -----------------------------------------
# Metrics
# -----------------------------------------

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Recovery Cases",
        total_cases
    )

with col2:
    st.metric(
        "₹ Recovered",
        f"₹{recovered_amount:,.2f}"
    )

with col3:
    st.metric(
        "₹ At Risk",
        f"₹{at_risk_amount:,.2f}"
    )

with col4:
    st.metric(
        "Escalated",
        escalated
    )


st.divider()


# -----------------------------------------
# Outcome summary
# -----------------------------------------

st.subheader("Recovery Outcomes")

outcome_counts = pd.Series({
    "Recovered": len(
        df[df.get("amount_recovered", pd.Series(dtype=float)).fillna(0) > 0]
    ) if "amount_recovered" in df.columns else 0,

    "Retry Scheduled": retry_cases,

    "Escalated": escalated,

    "No Action": no_action
})

st.bar_chart(outcome_counts)


# -----------------------------------------
# Unresolved cases
# -----------------------------------------

st.subheader("⚠️ Unresolved Recovery Cases")

# "Unresolved" means the case reached a genuine dead end (EXHAUSTED) --
# not just any case that started as RETRY/ESCALATE, since many of those
# get closed out by a later follow-up row (RECOVERED). Counting the
# initial decision alone would overstate how much is still open.
unresolved = df[
    df["action"] == "EXHAUSTED"
]

if unresolved.empty:

    st.success("No unresolved recovery cases.")

else:

    st.warning(
        f"{len(unresolved)} case(s) currently require "
        "further action."
    )

    st.dataframe(
        unresolved[
            [
                "subscription_id",
                "status",
                "decline_type",
                "failure_reason",
                "decision",
                "action",
                "action_status"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )


# -----------------------------------------
# Audit trail
# -----------------------------------------

st.subheader("Audit Trail")

audit_columns = [
    "subscription_id",
    "status",
    "decline_type",
    "failure_reason",
    "decision",
    "decision_reason",
    "action",
    "action_status"
]

available_columns = [
    column
    for column in audit_columns
    if column in df.columns
]

st.dataframe(
    df[available_columns],
    use_container_width=True,
    hide_index=True
)


# -----------------------------------------
# Customer messages
# -----------------------------------------

if "message" in df.columns:

    st.subheader("Generated Customer Messages")

    for _, row in df.iterrows():

        if row.get("message"):

            with st.expander(
                f"{row.get('subscription_id', 'Unknown')} — "
                f"{row.get('action', 'Unknown')}"
            ):

                st.write(row["message"])

                if "message_source" in row:
                    st.caption(
                        f"Source: {row['message_source']}"
                    )