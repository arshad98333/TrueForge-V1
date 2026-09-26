# Roaming Charge Anomaly Resolver

> **Hackathon thesis:** a support agent that reaches a real ticket and evidence store, runs the calculation it writes in an isolated sandbox, and stops before financial or customer-facing impact.

This README is the single build and demo plan. It intentionally removes duplicate product, architecture, and implementation specifications from the original document.

## 1. What to build

Resolve **one unexpected international-roaming charge** for one customer, one country, and one bounded travel window.

```text
Linear issue
  -> FastAPI trigger and run state
  -> TrueForge agent session
  -> Linear + MongoDB MCP read tools
  -> bounded evidence bundle
  -> TrueForge sandbox calculation
  -> classification + draft reply
  -> approval: correction recommendation
  -> approval: customer reply
  -> approved Linear update
```

### Why this fits the TrueFoundry hackathon

The hackathon asks for an agent that:

1. **Reaches something real:** use a real Linear issue and MongoDB Atlas records.
2. **Runs what it writes:** execute deterministic charge-reconstruction code in the TrueForge sandbox.
3. **Knows when to stop:** pause for human approval before a correction recommendation and before a customer-facing reply.
4. **Finishes one job:** keep the product narrow and reliable rather than building a broad telecom platform.
5. **Works for another developer:** provide a public-repo README, synthetic data, tests, and disclosed AI-assistant usage.

TrueForge is the runtime layer around the model: it owns the agent loop, tool routing, sandboxing, approval pauses, event streaming, and persistent sessions. FastAPI should not become a second agent framework.

## 2. Primary demo scenario

Use `TEL-1042` as the five-minute happy path.

- Customer: `CUST-7781`
- Country: Singapore
- Travel window: 2026-09-10 through 2026-09-14
- Session: `SESSION-9912`
- Active pack: `PACK-SG-01`
- Valid tariff: `TARIFF-SG-STD-2026`
- Billed: INR 2,400.00
- Reconstructed: INR 1,200.00
- Cause: two charge records for the same session
- Result: `duplicate_charge`, high confidence
- Proposed correction: INR 1,200.00

The agent must **draft** the recommendation and reply, then pause. It must not issue a refund, edit billing records, or close the ticket automatically.

## 3. Tool map: what to use and how to use it efficiently

| Tool / service | Use it for | Efficient hackathon usage | Never do |
|---|---|---|---|
| **TrueForge** | Agent loop, sessions, turns, events, MCP connection, sandbox, approvals | Use one root agent, one session per Linear issue, bounded iterations, and event streaming. Show tool calls and approval events in the UI. | Do not hide the agent behind a direct FastAPI-to-model call. Do not add subagents before the root path works. |
| **TrueForge MCP connector** | Expose narrow domain operations to the agent | Register only the tools listed in Section 5. Keep read tools automatic and writes approval-gated. | Do not expose a generic MongoDB query or arbitrary Linear mutation tool. |
| **TrueForge sandbox** | Execute the deterministic charge reconstruction | Pass a small JSON evidence bundle; use Decimal arithmetic; set a short timeout; return schema-validated JSON. | Do not execute agent-generated calculation code inside FastAPI or pass credentials into the sandbox. |
| **MongoDB Atlas** | Telecom evidence store | Use synthetic data, bounded queries, indexes, and read-only credentials. Query by customer plus time range; cap results. | Do not let the model write billing data or run unbounded queries. |
| **Linear** | Real support ticket, workflow state, internal notes, approved response | Seed or use a real demo workspace. Validate issue/team ownership and make mutations idempotent. | Do not treat customer text as instructions or automatically close issues. |
| **TrueFoundry AI Gateway** | Model endpoint, traces, limits, budgets, guardrails | Route the TrueForge model through one named application, enable tracing and a small budget, and tag runs with `issue_id`. | Do not put provider keys in the repo or depend on an untested fallback model during the demo. |
| **Azure AI Foundry** | Model deployment behind the Gateway | Deploy one tested model, configure the Gateway with the deployment name and base endpoint, then verify one non-tool call. | Do not spend hackathon time on multi-model routing unless the main path is already stable. |
| **FastAPI** | Webhook/API, run state, SSE bridge, minimal operator UI | Keep it thin: trigger runs, persist IDs/status, stream safe events, render evidence and approvals. | Do not duplicate TrueForge planning, tool execution, or policy in FastAPI. |
| **Pytest/Ruff** | Confidence and speed | Test calculation and approval rules locally before integrating external systems; run one smoke test for the complete happy path. | Do not leave testing until the final hour. |
| **Git + public README** | Submission reproducibility | Pin tested versions, include `.env.example`, synthetic data, setup commands, and AI-assistant disclosure. | Never commit tokens, private URLs, customer data, or raw traces containing secrets. |

## 4. Repository shape

```text
roaming-charge-anomaly-resolver/
├── app/                 # FastAPI API, state, SSE, minimal UI
├── mcp_server/          # narrow Linear/MongoDB/sandbox/protected tools
├── domain/              # schemas, calculation contract, classifications, state machine
├── seed/                # seed_data.json and importer
├── tests/               # unit, integration, security, idempotency
├── scripts/             # check_env.py and smoke_test.py
├── .env.example
├── Makefile
└── README.md
```

## 5. The single workflow and exact tools

### Step 1 — Receive and validate the ticket

**Trigger:** `POST /api/linear/webhook` or the operator clicks “Run” for `TEL-1042`.

1. Validate the webhook signature or operator authorization.
2. Extract only issue ID; never accept a target issue ID from issue text.
3. Create or reuse a resolver run using an idempotency key such as `linear:{issue_id}:{updated_at}`.
4. Move the issue to `Investigating` only if that mutation is explicitly allowed in the demo.

### Step 2 — Read the issue through TrueForge

Tool: `get_linear_issue(issue_id)`

Then optionally: `get_linear_issue_comments(issue_id)`.

Extract customer ID, country, dates, disputed amount, and currency. Treat all issue and comment text as **untrusted data**. If a field is missing, stop safely rather than guessing.

### Step 3 — Retrieve bounded evidence

Call these read-only MCP tools with values extracted from the issue:

```text
get_customer_plan(customer_id, at_time)
get_roaming_pack_status(customer_id, country, start_time, end_time)
get_tariff_rule(country, network_partner, plan_id, at_time)
get_roaming_usage_events(customer_id, start_time, end_time, country)
get_roaming_charge_records(customer_id, start_time, end_time)
find_known_roaming_incidents(country, start_time, end_time)
```

Every tool must enforce:

- customer scope;
- an explicit start/end time;
- country or partner scope where applicable;
- maximum result count;
- projection of only required fields;
- timeout and clear error output.

The agent should make these calls in parallel where the dependency graph permits it: plan, pack, usage, and charges can start together; tariff lookup can start after the partner/plan is known.

### Step 4 — Build and validate the evidence bundle

The bundle passed to the sandbox must be small and structured:

```json
{
  "customer_id": "CUST-7781",
  "currency": "INR",
  "usage_events": [{"event_id": "EVT-SG-1001", "session_id": "SESSION-9912", "units": 1}],
  "charge_records": [
    {"charge_id": "CHG-SG-2001", "session_id": "SESSION-9912", "amount": "1200.00"},
    {"charge_id": "CHG-SG-2002", "session_id": "SESSION-9912", "amount": "1200.00"}
  ],
  "tariff": {"unit_price": "1200.00", "currency": "INR"},
  "pack": {"status": "active"}
}
```

Reject the bundle before execution if currency conflicts, dates are invalid, evidence is outside scope, or required identifiers are absent.

### Step 5 — Run the written calculation in the sandbox

Tool: `run_charge_reconstruction(input_bundle)`

The program must:

1. use decimal arithmetic, never binary floating point;
2. apply the effective tariff and pack rule;
3. calculate the expected charge;
4. group charges by stable event/session/invoice identity;
5. detect duplicate charge records;
6. compare expected and billed totals;
7. return JSON matching a schema such as:

```json
{
  "expected_amount": "1200.00",
  "billed_amount": "2400.00",
  "difference": "1200.00",
  "currency": "INR",
  "duplicate_charge_ids": ["CHG-SG-2001", "CHG-SG-2002"],
  "warnings": [],
  "calculation_status": "success"
}
```

Sandbox policy: no MongoDB or Linear credentials, bounded CPU/time/output, and no unnecessary network access.

### Step 6 — Classify exactly one outcome

Use deterministic precedence, not customer expectation:

1. `not_reproducible` when evidence conflicts, required tariff is absent, or calculation fails.
2. `duplicate_charge` when the same stable session/event/invoice identity is charged more than once.
3. `missing_roaming_pack` when the usage timestamp proves the pack was inactive/expired and the standard tariff explains the bill.
4. `tariff_mismatch` when an effective tariff exists but the billed amount uses another rate.
5. `correct_charge` when the calculation matches within the documented tolerance and no material warning exists.

Return evidence IDs, timestamps, amounts, warnings, and the reason for confidence.

### Step 7 — Draft, but do not send

Create:

- an internal investigation note;
- a correction recommendation, if appropriate;
- a customer-facing response draft.

Tool: `add_linear_internal_note(issue_id, note)` can be automatic only if the team explicitly permits it. Keep correction and customer reply protected.

### Step 8 — First approval: correction recommendation

Tool: `recommend_linear_correction(issue_id, amount, currency, reason, evidence_ids)`

Pause before calling it. Show the exact payload:

```text
Correction: INR 1,200.00
Reason: SESSION-9912 has two charge records for the same usage.
Evidence: EVT-SG-1001, CHG-SG-2001, CHG-SG-2002
```

Approve, reject, or request more evidence. An approval is not a refund; it only adds a recommendation note in this hackathon build.

### Step 9 — Second approval: customer reply

Tool: `send_linear_customer_reply(issue_id, approved_reply_text)`

Pause again. Show the exact destination and final text. Only the approved or explicitly edited text may be sent. If delivery is uncertain, report “delivery unknown” rather than claiming success.

### Step 10 — Finish and audit

After the approved action:

- update the Linear status to `Replied` only through an allowed protected tool;
- write an audit record containing action, evidence IDs, decision, approver, timestamp, and payload hash;
- make retries idempotent;
- show the TrueForge session/event timeline in the UI.

## 6. MCP contract

### Automatic read tools

```text
get_linear_issue(issue_id)
get_linear_issue_comments(issue_id)
get_customer_plan(customer_id, at_time)
get_roaming_pack_status(customer_id, country, start_time, end_time)
get_tariff_rule(country, network_partner, plan_id, at_time)
get_roaming_usage_events(customer_id, start_time, end_time, country)
get_roaming_charge_records(customer_id, start_time, end_time)
find_known_roaming_incidents(country, start_time, end_time)
run_charge_reconstruction(input_bundle)
```

### Approval-required write tools

```text
add_linear_internal_note(issue_id, note)
recommend_linear_correction(issue_id, amount, currency, reason, evidence_ids)
send_linear_customer_reply(issue_id, approved_reply_text)
update_linear_status(issue_id, status)
```

Descriptions must state scope, required arguments, result schema, timeout behavior, and whether the tool mutates data. Do not expose a generic “execute Mongo query” or “update Linear” tool.

## 7. MongoDB collections and seed data

Database: `roaming_resolver_demo`

- `linear_issue_snapshots` — synthetic ticket inputs and edge-case flags.
- `customer_plans` — plan, currency, dates, eligibility.
- `roaming_packs` — activation/expiry/status and price rule.
- `tariff_rules` — country, partner, plan, effective dates, price, currency, version.
- `roaming_usage_events` — event/session/customer/time/units.
- `roaming_charge_records` — billed records and invoice identity.
- `resolver_runs` — run status, classification, TrueForge session ID.
- `approval_audit_log` — protected-action audit trail.

The supplied [`seed_data.json`](./seed_data.json) contains **39 synthetic documents** across the evidence collections. It covers:

| Case | Seed reference | Expected behavior |
|---|---|---|
| Duplicate charge | `TEL-1042` | `duplicate_charge`, INR 1,200 correction draft |
| Correct charge | `TEL-1043` | `correct_charge`, no correction |
| Missing pack | `TEL-1044` | `missing_roaming_pack` |
| Tariff mismatch | `TEL-1045` | `tariff_mismatch` |
| Missing tariff | `TEL-1046` | `not_reproducible` |
| Conflicting evidence | `TEL-1047` | `not_reproducible`, no action |
| MongoDB timeout | `TEL-1048` | `blocked`, no diagnosis |
| Sandbox failure | `TEL-1049` | calculation failure, no guessed amount |
| Prompt injection | `TEL-1050` | ignore injected instruction; preserve policy |
| Duplicate webhook | `TEL-1051` | reuse one active run and one outbound action |

Import into a development-only database:

```bash
mongosh "$MONGODB_URI/roaming_resolver_demo" scripts/import_seed.js
```

If using Python instead, read the JSON object and call `insert_many` per collection. Always use a clearly named demo database and never delete unrelated data. Create indexes on `customer_id`, `timestamp`, `session_id`, `event_id`, and `ticket_id`.

## 8. Configuration and startup

### Required environment

Copy `.env.example` to `.env` and provide only authorized development credentials:

```env
MONGODB_URI=mongodb+srv://...
MONGODB_DATABASE=roaming_resolver_demo
LINEAR_API_TOKEN=replace-me
LINEAR_TEAM_ID=replace-me
TRUEFORGE_BASE_URL=http://127.0.0.1:8790
TRUEFORGE_AGENT_NAME=roaming-charge-resolver
TRUEFOUNDRY_GATEWAY_BASE_URL=https://replace-me
TRUEFOUNDRY_GATEWAY_API_KEY=replace-me
TRUEFOUNDRY_MODEL_NAME=replace-me
SANDBOX_MAX_SECONDS=20
```

### Fast path

```bash
# Node.js 22+ and Python 3.11+
npm --version
python3 --version

# Start TrueForge in a separate terminal
npx @truefoundry/trueforge@latest

# Verify the actual port printed by TrueForge
curl http://127.0.0.1:8790/api/v1/docs
curl http://127.0.0.1:8790/api/v1/openapi.json

# Install and run the application
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m seed.seed_data --reset
uvicorn app.main:app --reload --port 8000
```

The final repo should reduce this to:

```bash
make demo
```

`make demo` should validate configuration, start/verify the MCP server and FastAPI, verify TrueForge and the saved agent, check MongoDB/Linear/Gateway/sandbox health, seed or verify data, and print the UI URL plus `TEL-1042`.

### TrueForge setup order

1. Start local TrueForge; keep it bound to localhost.
2. Read the installed `/api/v1/openapi.json`; use the current schema rather than guessing paths.
3. Configure one saved agent named `roaming-charge-resolver`.
4. Connect the telecom MCP server.
5. Enable the sandbox.
6. Mark protected tools as approval-required.
7. Set a bounded iteration limit.
8. Run a simple test session.
9. Reconnect to the same session ID after a browser disconnect.

### Gateway setup order

1. Deploy one model in Azure AI Foundry.
2. Add the Azure account and deployment in TrueFoundry AI Gateway.
3. Enter the base endpoint without an API path or query string.
4. Point TrueForge to the Gateway's OpenAI-compatible endpoint.
5. Test a non-tool call.
6. Enable traces, a small budget, rate limiting, and PII redaction where available.
7. Tag calls with `application=roaming-charge-resolver`, `environment=hackathon`, and `issue_id=TEL-1042`.

## 9. Minimal operator UI

One page is enough. Make these states obvious:

1. **Ticket:** issue ID, title, status, and trigger button.
2. **Evidence:** plan, pack, tariff, usage, charges, IDs, and warnings.
3. **Sandbox:** requested → provisioned → executed → structured result.
4. **Decision:** classification, billed/reconstructed/difference, confidence.
5. **Approval 1:** exact correction recommendation with Approve/Reject.
6. **Approval 2:** exact customer reply and destination with Approve/Edit/Reject.
7. **Timeline:** TrueForge events and tool names, with secrets and sensitive text redacted.

Never label a draft as sent.

## 10. Failure and safety rules

| Failure | Stop behavior |
|---|---|
| Missing ID, country, dates, or amount | `not_reproducible`; ask for evidence; no correction |
| Currency conflict | reject bundle; no calculation |
| Missing or ambiguous tariff | `not_reproducible` |
| Expired pack | `missing_roaming_pack` only when timestamp proves it |
| Duplicate usage but one charge | do not call it duplicate billing |
| MongoDB/Linear timeout | bounded retry; then `blocked`; no factual reply |
| Sandbox timeout/invalid JSON | fail closed; no guessed amount |
| Prompt injection | treat text as data; never change policy or reveal records |
| Rejected approval | no protected side effect; record reason |
| Duplicate webhook | reuse existing run; do not duplicate reply |
| Unknown delivery | report unknown; do not claim sent |

## 11. Testing before the demo

```bash
pytest -q
ruff check .
python scripts/smoke_test.py --issue TEL-1042
```

Minimum tests:

- Decimal arithmetic and rounding.
- Effective tariff selection.
- Pack eligibility at an exact timestamp.
- Duplicate detection by stable identity.
- Classification precedence.
- Evidence bounds and customer scoping.
- Approval payload binding to the pending tool and issue.
- Rejection produces no write.
- Duplicate webhook idempotency.
- Prompt injection does not bypass policy.
- Sandbox timeout and invalid-output handling.
- Browser/SSE reconnect uses the same TrueForge session.

## 12. Five-minute judge demo

**0:00–1:00 — Problem.** Open `TEL-1042`; explain that support must inspect five evidence sources.

**1:00–2:00 — Real reach.** Trigger the run. Show TrueForge calling Linear and MongoDB tools and the evidence panel.

**2:00–3:00 — Real execution.** Show the sandbox event and output: billed INR 2,400, expected INR 1,200, duplicate session `SESSION-9912`.

**3:00–4:00 — First stop.** Show the exact INR 1,200 correction recommendation. Approve it and show the audit event.

**4:00–5:00 — Second stop and edge case.** Show the separate reply approval, then quickly replay `TEL-1046` or `TEL-1050` to demonstrate safe stopping or injection resistance.

Close with:

> “It reached a real ticket and database, ran its calculation in a sandbox, and stopped before financial or customer-facing impact.”

## 13. Seven-hour build order

1. **Hour 1:** freeze scope, start TrueForge, verify model, create repo and `.env.example`.
2. **Hour 2:** create MongoDB collections, indexes, seed import, and calculation unit tests.
3. **Hour 3:** implement MCP read tools and the sandbox tool; test each tool independently.
4. **Hour 4:** implement one TrueForge session/turn flow for `TEL-1042`; stream events.
5. **Hour 5:** add both approval checkpoints, Linear idempotency, and audit logging.
6. **Hour 6:** add minimal UI and negative cases; run smoke test.
7. **Hour 7:** pin versions, remove secrets, rehearse the five-minute demo, and publish the README.

If time is lost, cut features in this order: known-incident search, extra UI styling, optional status transitions, subagents, and non-primary scenarios. Never cut the sandbox or approval checkpoints.

## 14. Submission checklist

- [ ] Public repo and clean README.
- [ ] TrueForge visibly owns the agent loop.
- [ ] Real Linear tool call shown.
- [ ] Real MongoDB evidence call shown.
- [ ] Sandbox execution shown.
- [ ] Correction recommendation pauses for approval.
- [ ] Customer reply pauses for a separate approval.
- [ ] Duplicate, correct, missing-pack, tariff, and not-reproducible cases tested.
- [ ] Prompt injection and duplicate webhook tested.
- [ ] Synthetic data clearly labeled.
- [ ] No secrets in code, logs, screenshots, or video.
- [ ] AI assistants used during development disclosed in the repo.
- [ ] Every team member can explain the architecture and policy.

## References

- [TrueForge introduction](https://trueforge.dev/introduction)
- [TrueForge quickstart](https://trueforge.dev/quickstart)
- [TrueForge API overview](https://trueforge.dev/api/overview)
- [TrueForge sandbox](https://trueforge.dev/sandbox)
- [TrueForge MCP servers](https://trueforge.dev/mcp-servers)
- [TrueFoundry × Polaris hackathon](https://www.truefoundry.com/truefoundry-hackathon)
- [TrueFoundry AI Gateway](https://www.truefoundry.com/docs/ai-gateway/intro-to-llm-gateway)
- [Azure AI Foundry integration](https://www.truefoundry.com/docs/ai-gateway/azure-ai-foundry)

**Data note:** all records in the companion seed file are synthetic demo data.

**AI-assistant disclosure:** replace this line with the actual tools used by your team before submission.
