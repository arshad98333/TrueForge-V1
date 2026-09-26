# Roaming Charge Anomaly Resolver
## Five-Minute CEO-Style Workflow Story

### Core conclusion

**We are not building another chatbot. We are building a trusted operations agent that proves why a roaming charge is wrong before anyone changes money or contacts a customer.**

In five minutes, the audience should see one complete journey:

```text
Real customer issue
  -> verified evidence
  -> executable calculation
  -> clear business decision
  -> human approval before impact
```

The agent does three valuable things:

1. It reaches the systems where the truth lives.
2. It proves the answer by running the calculation in a controlled environment.
3. It knows the boundary between recommendation and action.

That is the difference between an AI assistant that talks and an AI operator that can be trusted.

---

## 1. CEO opening: the problem and the promise

“Every day, support teams receive questions that sound simple: *Why was I charged this amount?*

But answering that question requires people to inspect a ticket, a customer plan, a roaming pack, a tariff, usage events, and billing records. They must reconcile those sources manually, calculate the expected amount, write an explanation, and then decide whether it is safe to recommend a correction.

That process is slow, repetitive, and vulnerable to one dangerous failure: an agent that sounds confident without proving the facts.

Our product, the **Roaming Charge Anomaly Resolver**, handles the investigation end to end. It does not guess. It collects evidence, runs the calculation, explains the result, and stops before it can create financial or customer-facing impact without approval.”

---

## 2. Minto Principle: lead with the answer

### Situation

A customer reports an unexpected roaming charge. The support team needs a reliable answer, not a plausible paragraph.

### Complication

The answer is distributed across multiple systems. A duplicate charge can look like a valid charge unless the agent compares the usage session with every billed record. A missing tariff or conflicting record can make a confident answer unsafe.

### Resolution

The resolver connects the ticket to the evidence, reconstructs the charge in a sandbox, classifies the outcome, and pauses at the exact points where a human should remain accountable.

### Executive takeaway

**The product reduces investigation effort while increasing control. It automates the evidence work, not the responsibility.**

---

## 3. Five-minute workflow story

### Minute 0:00–0:45 — Start with a real customer problem

“Here is a real support workflow represented by our demo ticket: `TEL-1042`.

The customer travelled in Singapore, had an international roaming pack, and was billed **INR 2,400**. The question is simple: *Is this charge correct?*

The ticket is not a prompt for a generic chat response. It is a work item connected to a real support process.”

Show the ticket and its status: **Open**.

“The resolver receives this issue, creates one investigation run, and moves it into investigation. It does not allow the customer’s text to change the agent’s rules.”

### Minute 0:45–1:45 — Show the agent reaching the truth

“First, the agent reads the issue through the ticket tool. It extracts the customer, dates, country, amount, and currency.

Then it retrieves the evidence that matters:

- the customer’s plan;
- the roaming pack status;
- the effective Singapore tariff;
- the usage event;
- the charge records.

This is where the agent becomes operational. It is not answering from memory. It is reaching the systems where the facts live.”

Show the evidence panel:

- Customer: `CUST-7781`
- Country: Singapore
- Session: `SESSION-9912`
- Pack: active
- Tariff: INR 1,200
- Usage: one session
- Charges: two records of INR 1,200 each

“Every lookup is bounded to this customer and this travel period. The agent cannot wander through unrelated records or request an unlimited database export.”

### Minute 1:45–2:45 — Show proof, not confidence

“Now the agent has evidence, but evidence alone is not the answer. The important question is whether the calculation can be reproduced.

The resolver sends a bounded evidence bundle to the TrueForge sandbox. The calculation uses decimal currency arithmetic, applies the effective tariff, compares the expected amount with the billed amount, and checks whether stable identifiers were charged more than once.”

Show the execution timeline:

```text
Calculation requested
Sandbox provisioned
Charge reconstruction executed
Structured result returned
```

Show the result:

```text
Expected amount: INR 1,200.00
Billed amount:   INR 2,400.00
Difference:      INR 1,200.00
Duplicate:       CHG-SG-2001 and CHG-SG-2002
Session:         SESSION-9912
```

“The agent is not saying ‘this looks like a duplicate.’ It has run the calculation and can point to the exact records that explain the difference.”

### Minute 2:45–3:30 — Give the business decision

“The resolver now returns one clear classification: **duplicate charge**.

Its confidence is high because the same usage event and session identity appear in two billed records. The correct amount is INR 1,200, and the proposed correction is INR 1,200.”

Show the decision card:

```text
Classification: duplicate_charge
Confidence: high
Billed: INR 2,400.00
Reconstructed: INR 1,200.00
Proposed correction: INR 1,200.00
```

“This is the point where many automation systems make a mistake: they treat a correct analysis as permission to act.”

### Minute 3:30–4:15 — Show the first stop

“Our agent does not issue a refund. It does not edit billing records. It stops and asks for approval before making the correction recommendation.”

Show the exact approval request:

```text
Proposed correction: INR 1,200.00
Reason: the same roaming session was charged twice
Evidence: EVT-SG-1001, CHG-SG-2001, CHG-SG-2002
```

“The operator can approve, reject, or request more evidence. If the operator rejects it, no protected action occurs. If the operator approves it, the system records the recommendation and the evidence behind it.”

Approve the recommendation.

### Minute 4:15–4:45 — Show the second stop

“The customer-facing message is a separate decision. The system prepares a clear draft, but it does not confuse a draft with a sent message.”

Show the draft:

> “We reviewed your roaming usage and billing records. Your session was charged twice for the same usage. The correct charge is INR 1,200, so we are recommending a correction of INR 1,200.”

“The operator sees the exact destination and exact text. Only after a second approval can this message be sent through the ticket workflow.”

Approve the response and show the Linear update as **Replied**.

### Minute 4:45–5:00 — Close with control and scale

“Let us briefly change the evidence: if the tariff is missing, the agent does not invent one. It returns **not reproducible**. If the ticket contains a prompt injection, the agent treats it as customer text, not as a new instruction. If the database or sandbox is unavailable, the workflow stops safely.

That is the product promise: **reach the real systems, run the real proof, and stop before it hurts.**”

---

## 4. Three backing arguments for the conclusion

### Backing 1 — It reaches the real operating environment

The resolver uses the ticket system and the evidence store instead of simulating a conversation. This makes the outcome connected to a real support workflow.

**Proof shown in the demo:**

- Linear issue retrieval;
- MongoDB plan, pack, tariff, usage, and charge lookups;
- final approved Linear update.

### Backing 2 — It proves the financial explanation

The resolver does not rely on a model’s arithmetic or confidence. It passes bounded evidence to a sandbox and returns structured output using deterministic money rules.

**Proof shown in the demo:**

- sandbox lifecycle events;
- INR 1,200 reconstructed amount;
- INR 2,400 billed amount;
- duplicate charge IDs and session identity.

### Backing 3 — It preserves human accountability

The resolver separates investigation from action. It can recommend, but it cannot independently create a correction recommendation or send a customer reply.

**Proof shown in the demo:**

- correction approval card;
- separate customer-reply approval card;
- rejection path with no protected side effect;
- audit record for the final decision.

---

## 5. MECE view of the workflow

The workflow is divided into mutually exclusive, collectively exhaustive stages. Each stage has one job and one success condition.

| Stage | Question answered | Evidence of completion |
|---|---|---|
| **1. Intake** | What issue are we investigating? | Valid issue ID and bounded run created |
| **2. Evidence** | What facts are available? | Plan, pack, tariff, usage, and charges retrieved |
| **3. Verification** | Can the charge be reproduced? | Sandbox returns validated structured output |
| **4. Decision** | What is the correct classification? | Exactly one supported outcome with rationale |
| **5. Recommendation** | What should the operator consider doing? | Exact correction payload prepared |
| **6. Approval** | Is the operator authorizing the protected action? | Approval or rejection recorded |
| **7. Communication** | What should the customer receive? | Exact reply approved and delivered or marked unknown |
| **8. Audit** | Can we explain what happened later? | Session, evidence IDs, decision, and action hash stored |

This prevents category overlap:

- intake is not investigation;
- investigation is not calculation;
- calculation is not authorization;
- a draft is not a sent message;
- a recommendation is not a refund.

It is exhaustive because every run ends in one of three safe outcomes:

1. a verified resolution that reaches approval;
2. a verified result requiring no correction;
3. a blocked or not-reproducible outcome with no unsafe action.

---

## 6. Toyota’s Five Whys: why this product matters

### Why 1: Why was the customer billed INR 2,400?

Because the same roaming session was charged twice.

### Why 2: Why was the duplicate not caught immediately?

Because the support investigation depends on comparing records across the ticket, usage system, tariff data, and charge ledger.

### Why 3: Why does the comparison take time?

Because the evidence is distributed and the support representative must manually reconstruct the expected charge.

### Why 4: Why is manual reconstruction risky?

Because a missing tariff, expired pack, conflicting currency, timeout, or weak identifier can produce a confident but incorrect conclusion.

### Why 5: Why should an AI agent be involved?

Because the repetitive evidence collection and deterministic comparison can be accelerated, while approval checkpoints preserve human control over money and customer communication.

### Root cause

The core problem is not that support lacks a chat interface. The core problem is that **evidence is distributed, reconstruction is repetitive, and action requires accountability**.

### Product response

The resolver automates the evidence path and calculation path, then deliberately stops at the accountability boundary.

---

## 7. CEO-level value statement

### For the customer

A clearer explanation, backed by records rather than guesswork.

### For support

Less time searching across systems and more time handling exceptions that genuinely need judgment.

### For operations and finance

No silent refunds, no uncontrolled billing mutations, and an audit trail for every approved action.

### For engineering and security

Narrow tools, bounded queries, sandboxed execution, approval gates, and failure-safe behavior.

### For the business

A reusable pattern for trustworthy agents: **automate the work, preserve the decision.**

---

## 8. Closing statement

“Most AI demos end when the model gives an answer. Our workflow begins where accountability matters.

The Roaming Charge Anomaly Resolver reaches the real ticket, checks the real evidence, runs the real calculation, explains the outcome, and stops before it can create financial or customer-facing impact without a person.

That is how we move from AI that answers questions to AI that earns the right to operate.”
