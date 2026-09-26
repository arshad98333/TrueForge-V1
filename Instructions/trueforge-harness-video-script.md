# TrueForge Harness: 3 to 4 Minute Video Script

Target length: 3 minutes 35 seconds.

Record one happy path live. Pre-run the edge cases so their Atlas states and Linear tickets are ready to show without waiting. Never show `.env`, tokens, connection strings, or provider credentials.

## 0:00 to 0:20: One job

Screen: Open a synthetic Linear ticket for an unexpected Singapore roaming charge.

Say:

> One job, finished. A customer disputes an INR 2,400 roaming charge. Our agent must find the facts, execute the proof, and stop before it can affect money or contact the customer.

## 0:20 to 0:55: Metric 1, reach something real

Screen: Open `http://127.0.0.1:8000/demo`. Click **Run workflow** once.

Pause on stage 01 and stage 02 as they become complete. Show the Linear case ID and matching Atlas evidence hash in the console.

Say:

> One click creates or resumes one bounded TrueForge workflow. The workflow reads the traceable synthetic case from Linear and MongoDB Atlas. It does not receive a result in its prompt.

On-screen proof:

```text
Linear issue: created
Atlas fixture: created and read back
Run IDs: matched
```

## 0:55 to 1:45: Metric 2, run what it writes

Screen: Watch stage 03 change when execution is verified. Open the TrueForge session from the console and show its event timeline.

Say:

> The calculation is executable, not conversational. The runner validates the plan, pack, tariff, usage identity, charge identities, currencies, and amounts using decimal arithmetic.

> TrueForge owns the agent turn. The agent calls native sandbox execution exactly once. TrueForge provisions E2B, executes the immutable command, and persists the tool call and response. The harness rejects a changed command, another tool, a missing E2B event, a failed exit code, invalid JSON, or a result bound to different evidence.

Screen: Point to these trace elements:

```text
TrueForge session ID
TrueForge turn ID
sandbox.created with v1:e2b ID
one native exec tool call
exit code 0
matching evidence hash
```

Then show:

```text
Billed:         INR 2,400.00
Expected:       INR 1,200.00
Difference:     INR 1,200.00
Classification: duplicate_charge
```

## 1:45 to 2:15: Metric 3, know when to stop

Screen: Pause on `turn.done`, `required_actions: []`, the single `exec` call, and the final terminal output.

Say:

> Proof is not permission. This harness exposes no refund, billing update, ticket-close, or customer-send tool. The verifier requires a completed turn with no unresolved actions and rejects any tool call other than the single approved sandbox execution.

On-screen proof:

```text
Correction posted: no
Refund issued: no
Ticket closed: no
Customer contacted: no
```

## 2:15 to 3:05: What-if failures

Screen: List the supported cases:

```powershell
.\.venv\Scripts\python.exe scripts\realtime_customer_support_demo.py --list-scenarios
```

Say:

> A useful harness asks what happens when reality is messy. These cases cover missing and ambiguous records, currency and tariff conflicts, wrong session identity, duplicate record IDs, wrong amounts, query overflow, evidence drift, prompt injection, runner tampering, invalid output, and sandbox timeout.

Screen: Show a pre-recorded or live missing-tariff run:

```powershell
.\.venv\Scripts\python.exe scripts\realtime_customer_support_demo.py --scenario missing-tariff
```

Say:

> With no tariff, the workflow stops before creating a sandbox. It does not invent a price.

Screen: Show a runner-tamper result:

```powershell
.\.venv\Scripts\python.exe scripts\realtime_customer_support_demo.py --scenario runner-tamper
```

Say:

> If the runner changes, the hash check stops the workflow before execution. Sandbox failures, timeouts, invalid JSON, and evidence drift also terminate without retrying or moving to a later stage.

## 3:05 to 3:35: Finish

Screen: Show the successful run record in Atlas with `state: verified` and its `trueforge_proof` object. Then show one edge-case record with `state: stopped_expected` and `stop_reason`.

Say:

> The result is one narrow support job with evidence an operator can audit: real systems reached, code executed through TrueForge in E2B, and explicit stopping behavior for both success and failure. One job, finished.

## Final frame

```text
REAL SYSTEMS                 PASS
TRUEFORGE + E2B EXECUTION    PASS
SAFE TERMINAL BOUNDARIES     PASS

No refund. No billing write. No customer message.
```

## Recording checklist

- Keep the Linear issue identifier, Atlas run ID, TrueForge session ID, turn ID, and E2B sandbox ID visible.
- Show the runner before showing its execution result.
- Show at least one `verified` record and one `stopped_expected` record.
- Do not claim that a customer reply was sent.
- Do not show credentials, raw headers, `.env`, or provider configuration values.
