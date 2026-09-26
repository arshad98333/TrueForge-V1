# Agents That Act Hackathon — Complete Step-by-Step Guide

**Event:** Agents That Act — TrueFoundry × Polaris Hackathon

**Official page:** <https://hackculture.io/hackathons/agents-that-act>
**Prepared:** 26 September 2026 (IST)

> **Important date note:** The event page shows the hackathon on **26 September 2026** in Bengaluru. Its hero section says **9:00 AM–9:00 PM IST**, while the schedule section says **9:00 AM–7:00 PM IST**. Confirm the actual check-in, build cutoff, and demo cutoff with the organizers before traveling.

---

## 1. What this hackathon is

This is an in-person, one-day hackathon focused on building **AI agents that act on real systems**, rather than agents that only answer questions.

A qualifying project should:

1. Connect to a real system or tool—for example a database, GitHub repository, cloud account, identity provider, or ticket queue.
2. Generate and/or run code safely inside a sandbox.
3. Stop and request human approval before an irreversible or destructive action.
4. Run on **TrueForge**, TrueFoundry’s open-source MIT-licensed agent harness.

You may build in any domain and use any programming language, framework, or model provider, but the agent itself must run on TrueForge.

---

## 2. Essential facts at a glance

| Item | Details |
|---|---|
| Format | In person |
| Venue | Polaris School of Technology, DivyaSree Technopark, A3, EPIP Zone, Brookefield, Bengaluru, Karnataka 560066, India |
| Date | 26 September 2026 |
| Event time | Page conflict: 9:00 AM–9:00 PM in hero; 9:00 AM–7:00 PM in schedule |
| Eligibility | Age 18+, able to write code, able to attend in person in Bengaluru |
| Who can join | Students, working engineers, founders |
| Team size | 1–4; solo participation is allowed |
| Cost | Free |
| Required harness | TrueForge |
| Languages/frameworks/models | Any, subject to the TrueForge requirement |
| Prize pool | ₹3,00,000 total |
| Food/Wi-Fi | Provided at venue |
| Travel | Participant’s responsibility |
| Support | events@polariscampus.com |

---

## 3. Prizes

| Prize | Amount |
|---|---:|
| 1st place | ₹1,00,000 |
| 2nd place | ₹75,000 |
| 3rd place | ₹50,000 |
| Best Build Story | ₹50,000 |
| Runner-up Build Story | ₹25,000 |
| **Total** | **₹3,00,000** |

### Community/build-story prizes

The page says the two build-story prizes are based on public posts. To enter:

- Post your build story publicly on **LinkedIn or X**.
- Tag **@truefoundry** and **@polariscodes**.
- The opportunity is open to all Round 1 registrants, so it is not limited to teams that reach the in-person round.

A strong post should explain the problem, why it matters, what your agent reaches, how sandboxing and approvals work, what you built during the hackathon, and a short demo or screenshots.

---

## 4. Eligibility and participation rules

You are eligible if all of the following are true:

- You are **18 or older**.
- You can write code.
- You can attend the final hackathon day **in person in Bengaluru**.
- You register individually in Round 1.
- You participate alone or in a team of **1–4 members**.
- You do not need prior TrueFoundry experience.

### Building requirements

- The project must be built **during the hackathon**.
- A pre-built project is not eligible.
- Prior research and reading TrueForge documentation are allowed.
- The agent must run on TrueForge.
- You may use any language, framework, or model provider.

### AI coding assistants

Claude, Copilot, Cursor, and similar tools are allowed. You must:

- Disclose the AI assistants used in the project README.
- Understand and be able to explain your architecture and code.

### Credentials and data

- Use only your own accounts, data, and credentials.
- Never commit API keys, tokens, passwords, or other sensitive credentials.
- Do not put secrets in a demo video, screenshots, README, logs, or public post.
- Use environment variables or the harness’s secret/configuration mechanism.

### Conduct and IP

- Maintain a respectful, professional environment.
- Harassment and inappropriate behavior are not tolerated.
- You retain full intellectual-property rights to what you build.
- Organizers may request permission to showcase your project; that does not transfer ownership.

---

## 5. Themes and what each must demonstrate

You are not limited to these themes, but they are good examples of the intended difficulty and safety model.

| Theme | Real system reached | Approval checkpoint |
|---|---|---|
| Cloud Cost Janitor | Cloud billing/infrastructure APIs | Deleting a resource |
| Migration Rehearsal Agent | Your database | Applying changes to production |
| Release Captain | GitHub and a package registry | Tagging and publishing |
| Ticket Resolver | Linear, Jira, or Zendesk | Replying to the customer |
| Access Reviewer | Identity provider | Revoking access |
| Runbook Executor | Your infrastructure | Every destructive step |

### Recommended choice for a one-day build

Choose a narrow workflow with:

- One clear user persona.
- One real integration.
- One safe sandbox execution path.
- One obvious approval gate.
- A deterministic demo that fits in 3–5 minutes.

Avoid building a general-purpose “do everything” agent.

---

## 6. Step-by-step action plan

### Step 0 — Check that you can attend

1. Confirm you are 18+.
2. Confirm you can physically reach the Polaris School of Technology campus in Bengaluru on 26 September 2026.
3. Budget your own travel and accommodation if needed.
4. Save the venue address and organizer email.
5. Plan to carry a government photo ID for campus entry.

### Step 1 — Register individually

1. Open the official registration link: <https://hackculture.io/hackathons/register/agents-that-act>.
2. Sign in using the available Google or GitHub option if prompted.
3. Complete the individual registration.
4. Prepare a concise, specific build idea and motivation statement.
5. Save any confirmation email or registration screenshot.

**Current page behavior:** The registration URL currently displays a HackCulture sign-in screen rather than exposing the form fields in the public page fetch. If you cannot access the form, contact **events@polariscampus.com** or HackCulture support at **support@hackculture.in**.

### Step 2 — Write a strong idea statement

Use this template:

> I will build **[agent name]**, an agent for **[specific user]** that handles **[real job]** by connecting to **[real system/tool]**. It will safely run **[generated code/action]** in a sandbox, produce **[evidence/output]**, and ask for approval before **[irreversible action]**. This matters because **[measurable pain/risk/time cost]**.

Example:

> I will build Release Captain, an agent for small engineering teams that reviews commits since the last tag, runs the project’s tests in a sandbox, generates release notes, and drafts a release. It can read GitHub and the package registry, but it must pause for approval before tagging or publishing. This reduces release toil without allowing an unreviewed production change.

Make the idea specific and technically plausible. The event FAQ says shortlisting is based on why you want to join and what you plan to build; a specific idea is more useful than a generic résumé.

### Step 3 — Form your team

1. Participate solo or form a team of up to four.
2. Complete team formation before the organizer’s team-formation deadline.
3. Assign roles, but keep everyone able to explain the whole system:
   - Agent/runtime owner
   - Integration/tool owner
   - Safety/evaluation owner
   - Demo/story owner
4. Decide who will present and who will operate the live demo.
5. Prepare a backup demo path in case the real integration is unavailable.

### Step 4 — Prepare your laptop and accounts

Before arriving, install and test:

- Node.js **22.14+** (the TrueForge repository states Node.js ≥22.14).
- Git.
- Your chosen language/runtime.
- Docker if you plan to use a local service or hosted setup.
- A code editor and any permitted AI coding assistant.
- A browser logged into only the accounts you intend to use.

Start TrueForge locally:

```bash
npx @truefoundry/trueforge@latest
```

The repository’s local mode uses SQLite and needs no extra infrastructure. Keep local mode on localhost; the official README warns that it is for personal use and should not be exposed to the internet.

Read before the event:

- Quickstart: <https://trueforge.dev/quickstart>
- Create an Agent: <https://trueforge.dev/create-agent/overview>
- Models: <https://trueforge.dev/models>
- MCP servers: <https://trueforge.dev/mcp-servers>
- Sandbox: <https://trueforge.dev/sandbox>
- API/SDK overview: <https://trueforge.dev/api/overview>

### Step 5 — Design the smallest qualifying agent

Write a one-page design before coding:

1. **User request:** What does the user ask for?
2. **Read-only discovery:** Which real system does the agent inspect?
3. **Reasoning/planning:** What does it calculate or decide?
4. **Sandbox action:** What code does it run, on what safe data or copy?
5. **Evidence:** What logs, diff, report, test result, or preview does it produce?
6. **Approval gate:** Which action is irreversible?
7. **Human decision:** What exactly does the user approve or reject?
8. **Final action:** What happens after approval?
9. **Failure path:** What does the agent say when it cannot reproduce, lacks permissions, or gets incomplete data?

### Step 6 — Connect the real system safely

Use a real integration, but minimize blast radius:

- Create a test repository, sandbox database, test ticket queue, or non-production cloud project.
- Use read-only permissions wherever possible.
- Scope tokens to one project/resource.
- Use fake or synthetic records for the demo if real data is not necessary.
- Keep a separate approval-only credential for the irreversible step.
- Add timeouts, retries, rate limits, and clear error messages.

### Step 7 — Implement the safety contract

Your agent should explicitly enforce this flow:

```text
User request
  -> inspect real system
  -> plan and explain proposed action
  -> execute generated code in sandbox
  -> show evidence / preview / diff
  -> request human approval
  -> only after approval: perform irreversible action
  -> report result and preserve trace
```

Do not merely display “Are you sure?” in the UI. Make the final tool call unavailable or blocked until approval is received. The demo should make the gate visible.

### Step 8 — Test adversarial cases

Run at least these tests:

- Normal successful request.
- User asks for a destructive action immediately.
- Sandbox code fails.
- Integration returns an empty or malformed response.
- User rejects approval.
- User gives ambiguous approval.
- Agent lacks permission.
- Agent tries to access a resource outside its scope.
- Network/API timeout.
- Duplicate request or retry after partial completion.

Record the expected behavior and actual output in `EVALUATION.md`.

### Step 9 — Create the README and demo

Your repository should contain:

- Problem statement and target user.
- Architecture diagram or short explanation.
- Setup instructions.
- Environment variables required, with a `.env.example` containing no secrets.
- How to run TrueForge and the agent.
- Real system/tool integration details.
- Sandbox behavior.
- Approval-gate behavior.
- Known limitations and failure modes.
- Test cases and results.
- Team members and roles.
- AI assistants used, as required by the rules.
- Credits/attributions for libraries and models.

Prepare a 3–5 minute demo:

1. State the real problem in 20–30 seconds.
2. Show the agent receiving a concrete request.
3. Show it reaching the real system.
4. Show generated code running in the sandbox.
5. Show the evidence or preview.
6. Stop at the approval gate.
7. Reject once, if time permits, to demonstrate safety.
8. Approve and show the controlled final action.
9. End with the measurable benefit and limitations.

Never show secrets in the terminal, browser, screen recording, logs, or slides.

### Step 10 — Publish the build story

To compete for the build-story prizes:

1. Write a public LinkedIn or X post.
2. Explain the problem, architecture, integration, sandbox, approval checkpoint, and result.
3. Include a safe demo link or redacted screenshots/video.
4. Tag **@truefoundry** and **@polariscodes**.
5. Do not include credentials or private customer data.

### Step 11 — Attend and submit/present

At the venue:

1. Arrive early for ID and check-in.
2. Confirm the actual build/demo cutoff with organizers because the page contains conflicting end times.
3. Join your team and verify everyone has the latest code.
4. Ask mentors targeted questions about TrueForge, MCP/tool connections, sandboxing, and approval events.
5. Freeze a known-good demo before the final hour.
6. Commit the final code and README.
7. Confirm any submission link or organizer-provided handoff process.
8. Present the working agent and explain its safety model clearly.

The public page describes showcasing the working project to judges, but the public registration page does not expose a separate submission form. Ask the organizers at check-in for the final submission mechanism and exact judging rubric.

---

## 7. Suggested one-day schedule

Adapt this to the organizer’s official agenda when announced.

| Time | Goal |
|---|---|
| 09:00–09:30 | Check-in, team confirmation, environment verification |
| 09:30–10:00 | Lock scope and success metric |
| 10:00–11:00 | Start TrueForge; connect model and one real system |
| 11:00–13:00 | Build the happy path and sandbox execution |
| 13:00–13:30 | Lunch and mentor checkpoint |
| 13:30–15:00 | Implement approval gate and final-action control |
| 15:00–16:00 | Test failures, denial, permissions, and retries |
| 16:00–17:00 | Improve UX, traces, README, and demo script |
| 17:00–18:00 | Freeze build; record backup demo; submit/present |
| Final hour | No new features; fix only show-stopping issues |

---

## 8. Technical reference: what TrueForge provides

The official TrueForge repository describes it as the runtime layer for:

- Model calls.
- MCP tools.
- Skills.
- Sandboxing.
- Approvals and user questions.
- Context management.
- Session state.
- Chat UI, HTTP API, TypeScript SDK, and embeddable UI SDK.

Relevant concepts for this hackathon:

- **Models:** TrueForge supports OpenAI, Anthropic, Google Gemini, other catalog providers, and OpenAI-compatible endpoints.
- **MCP tools:** Use these to reach external systems with authentication.
- **Sandbox:** Isolated code/file/shell execution; use it for generated code and test copies.
- **Human checkpoints:** Use tool approval or a structured user question before destructive operations.
- **Sessions and traces:** Preserve the reasoning/tool/action trail so judges can see what happened.
- **Local mode:** Best for the hackathon laptop; SQLite, one process, no extra infrastructure.

The hackathon highlights AWS and OpenAI credits for shortlisted teams. Do not assume credits are available before shortlisting; bring a fallback provider or local/mock integration plan.

---

## 9. What judges should be able to see

The page does not publish a detailed scoring table in the fetched content, so optimize for the stated challenge and make these dimensions obvious:

1. **Real usefulness:** Is this a job worth handing to an agent?
2. **Working integration:** Does it reach a real system rather than a fake chat-only demo?
3. **Agent autonomy:** Does it inspect, plan, execute, and produce useful output?
4. **Safety:** Does generated code run in a sandbox?
5. **Human control:** Does it stop before irreversible actions and wait for approval?
6. **Reliability:** Does it handle failures, denial, missing permissions, and bad data honestly?
7. **Clarity:** Can the team explain the architecture and show a clean demo?
8. **Build story:** Can others understand why the problem matters and how it was built during the event?

---

## 10. Pre-event checklist

### Administrative

- [ ] Registered individually.
- [ ] Registration confirmation saved.
- [ ] Team has 1–4 members.
- [ ] Team formation completed by the organizer deadline.
- [ ] Government photo ID packed.
- [ ] Venue and travel plan confirmed.
- [ ] Organizer contact saved: events@polariscampus.com.

### Technical

- [ ] Node.js ≥22.14 installed.
- [ ] `npx @truefoundry/trueforge@latest` tested.
- [ ] Model/provider access tested.
- [ ] Real integration selected.
- [ ] Test account/project/database created.
- [ ] Least-privilege credentials created.
- [ ] No secrets committed.
- [ ] Sandbox path tested.
- [ ] Approval gate tested.
- [ ] Backup demo data and backup provider prepared.

### Presentation

- [ ] One-sentence problem statement.
- [ ] 3–5 minute demo script.
- [ ] Architecture diagram.
- [ ] README includes AI-assistant disclosure.
- [ ] Failure cases documented.
- [ ] Screen recording or screenshots redacted.
- [ ] Public build-story draft prepared.

---

## 11. Common ways to become ineligible or lose points

Avoid these mistakes:

- Building most of the product before the hackathon.
- Demonstrating a chatbot that does not reach a real system.
- Claiming sandboxing without actually running generated code in a sandbox.
- Showing a confirmation message while the underlying destructive tool remains callable.
- Using production credentials or real private customer data.
- Committing `.env` files or API keys.
- Hiding the use of Copilot, Claude, Cursor, or other AI assistants.
- Building too many integrations to finish reliably.
- Adding features after the demo is stable and breaking the happy path.
- Failing to explain what happens when the agent cannot reproduce a task.
- Assuming AWS/OpenAI credits are guaranteed before shortlisting.
- Arriving without a government photo ID or without confirming the event’s actual end time.

---

## 12. Questions to ask organizers

Send these to **events@polariscampus.com** if the page does not answer them:

1. What is the exact check-in time and final demo/submission cutoff: 7:00 PM or 9:00 PM IST?
2. How are teams formed after individual registration, and what is the exact team-formation deadline?
3. What is the final submission format or URL?
4. Is there a published judging rubric or time limit per demo?
5. Are shortlisted-team AWS/OpenAI credits issued before the event or after shortlisting?
6. Are power outlets, extension boards, and campus network access available at every seat?
7. Are there restrictions on external APIs, hosted demos, or Docker?
8. What are the campus entry requirements beyond government photo ID?
9. How are prize eligibility, tax documentation, and prize distribution handled?
10. Are public build-story posts required before a particular cutoff?

---

## 13. Official source links

- Hackathon page: <https://hackculture.io/hackathons/agents-that-act>
- Registration: <https://hackculture.io/hackathons/register/agents-that-act>
- TrueForge GitHub: <https://github.com/truefoundry/trueforge>
- TrueForge Quickstart: <https://trueforge.dev/quickstart>
- TrueForge documentation: <https://trueforge.dev/>
- TrueFoundry Agent Harness overview: <https://www.truefoundry.com/docs/agent-platform/agent-harness/overview>
- Organizer support: <mailto:events@polariscampus.com>
- HackCulture support: <mailto:support@hackculture.in>

### Source caveat

This guide is based on the official HackCulture event page, its publicly accessible registration URL, the official TrueForge GitHub repository, and TrueFoundry’s official agent-harness documentation fetched on 26 September 2026. The registration page currently exposes authentication rather than the underlying form, and the event page does not expose a detailed judging rubric or separate submission form. Confirm those operational details with the organizers.
