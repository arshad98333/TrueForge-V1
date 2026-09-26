# One Job, Finished — Live Demo Script

## Goal

Resolve one customer-support ticket end to end: determine whether the INR 2,400 roaming charge in `TEL-1042` is valid.

Do not show architecture slides or extra features. Keep Linear, TrueForge, and the approval screen visible.

## Opening — 10 seconds

Say:

> One job, finished. A customer disputes an INR 2,400 roaming charge. This agent will investigate that one ticket, prove the result, and stop before anything consequential happens without approval.

## 1. Reach something real — 30 seconds

On screen:

1. Open the real Linear issue `TEL-1042`.
2. Start the saved resolver workflow.
3. Show the `read_issue` and `read_evidence` tool results.
4. Point to these returned records:
   - Customer: `CUST-7781`
   - Usage event: `EVT-SG-1001`
   - Session: `SESSION-9912`
   - Pack: `PACK-SG-01`, INR 1,200.00
   - Tariff: `TARIFF-SG-STD-2026`, INR 1,200.00
   - Charges: `CHG-SG-2001` and `CHG-SG-2002`, INR 1,200.00 each

Say:

> Metric one: it reaches something real. The agent read the ticket from Linear and the supporting records from MongoDB. It did not answer from the prompt or from memory.

Visible proof:

```text
Linear issue read: yes
MongoDB evidence read: yes
Evidence bound to TEL-1042: yes
```

## 2. Run what it writes — 35 seconds

On screen:

1. Show the runner produced by the agent:

```python
import json
from charge_rules import reconstruct
result = reconstruct(evidence)
print(json.dumps(result, sort_keys=True))
```

2. Show `prepare_execution` returning the immutable command and execution ID.
3. Show the E2B sandbox execution event.
4. Show the verified result:

```text
Expected:       INR 1,200.00
Billed:         INR 2,400.00
Difference:     INR 1,200.00
Classification: duplicate_charge
```

Say:

> Metric two: it runs what it writes. The agent wrote this runner, executed that exact runner in an isolated E2B sandbox, and the workflow verified the execution trace before accepting the answer.

Visible proof:

```text
Runner hash shown: yes
Sandbox execution shown: yes
Exit code: 0
Verified structured result: yes
```

## 3. Know when to stop — 45 seconds

On screen:

1. Show the exact correction recommendation prepared for Linear.
2. Stop at the first approval prompt.

Say:

> Metric three: it knows when to stop. A proved result is not permission to act. The agent cannot post this correction recommendation until a human approves the exact destination and text.

Approve the correction recommendation. Show the verified Linear comment URL.

Then show the customer reply draft and the second approval prompt.

Say:

> The customer reply is a separate decision. Even after approval, this workflow only marks the reply as an approved draft. It does not send it.

Approve the draft and show:

```text
Customer reply: draft only — not sent.
Status: complete
```

Visible proof:

```text
Stopped before external write: yes
Human approved exact Linear comment: yes
Stopped before customer delivery: yes
Customer message sent: no
```

## Close — 10 seconds

Say:

> One ticket was read from real systems, calculated with executed code, and completed with human control. One job, finished.

## Demo pass condition

The demonstration passes only if the audience sees all three events in the same run:

1. Live Linear and MongoDB reads.
2. A successful E2B execution of the displayed runner.
3. Two explicit stops, ending with a verified Linear comment and an unsent customer draft.
