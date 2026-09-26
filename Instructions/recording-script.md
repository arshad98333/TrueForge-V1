# One Job, Finished — Recording Script

Target length: 2 minutes 15 seconds.

Record one continuous workflow. Do not cut around errors, approvals, or sandbox execution. Hide tokens, environment variables, and provider settings.

## Before recording

- Open the `TEL-1042` Linear issue.
- Open its TrueForge session in a second window.
- Keep the run timeline and tool details readable.
- Increase browser zoom so IDs and amounts are visible.
- Close terminals or tabs containing credentials.
- Start from a fresh run that has not posted its correction comment.

## 0:00–0:12 — The one job

Screen: Linear issue `TEL-1042`.

Voiceover:

> One job, finished. This customer was billed INR 2,400 for one Singapore roaming session. We need to determine whether the charge is correct and prepare the safe next step.

## 0:12–0:42 — Metric 1: reach something real

Screen: Start the resolver, then show `read_issue` and `read_evidence`.

Voiceover:

> First, the agent reaches the systems where the facts live. It reads the support ticket from Linear and retrieves the scoped plan, pack, tariff, usage event, and charge records from MongoDB.

Screen: Pause on `SESSION-9912`, `EVT-SG-1001`, and the two charge IDs.

Voiceover:

> One session has two separate INR 1,200 charge records. This is live tool output, not information copied into the prompt.

Overlay:

```text
1. Reaches real systems ✓
```

## 0:42–1:12 — Metric 2: run what it writes

Screen: Show the four-line Python runner, the sandbox creation event, and the execution result.

Voiceover:

> Next, the agent writes a small Python runner and executes that exact code in an isolated E2B sandbox. The workflow accepts the answer only after it verifies the command, execution trace, evidence hash, and successful output.

Screen: Pause on the result.

Voiceover:

> The billed amount is INR 2,400. The reconstructed amount is INR 1,200. The verified difference is INR 1,200, classified as a duplicate charge.

Overlay:

```text
2. Runs its code ✓
```

## 1:12–1:58 — Metric 3: know when to stop

Screen: Show the first approval prompt without immediately approving it.

Voiceover:

> A correct result is not authority to act. The agent stops before posting the correction recommendation and shows the exact destination, amount, evidence, and text for human approval.

Screen: Approve. Show the resulting Linear comment and its verified URL.

Voiceover:

> After approval, it posts once and verifies the comment in Linear.

Screen: Show the separate customer-reply approval. Approve it, then pause on `sent: false` and `Status: complete`.

Voiceover:

> It stops again for the customer reply. This approval marks the response as a draft only. Nothing is sent to the customer.

Overlay:

```text
3. Stops before impact ✓
Customer reply sent: no
```

## 1:58–2:15 — Close

Screen: Show the final run state, verified comment URL, and draft-only message together.

Voiceover:

> One real support ticket. One executed proof. Two controlled approvals. The investigation is complete, the recommendation is recorded, and the customer draft remains unsent. One job, finished.

## Final frame

```text
TEL-1042 — COMPLETE

Reached Linear + MongoDB       ✓
Ran verified code in E2B       ✓
Stopped before protected work  ✓

Correction recommendation recorded
Customer reply: draft only — not sent
```
