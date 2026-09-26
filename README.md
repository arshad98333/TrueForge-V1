# TrueForge V1

Roaming Charge Resolver is a synthetic support agent that reads Linear and MongoDB, runs its calculation in E2B through TrueForge, and stops for human approval before posting a correction.

Live demo: [truefoundry.arshadify.online](https://truefoundry.arshadify.online/)

Video demo: [Watch the 3-minute TrueForge walkthrough on Loom](https://www.loom.com/share/6747053ab20b4603bb0e9b5ef90bb85e)

Demo narration: [three-minute-hackathon-demo-script.md](Instructions/three-minute-hackathon-demo-script.md)

![Operator UI](<Screenshots/USER INTERFACE.png>)

## Architecture

The first diagram shows every live system and tool boundary. The second diagram shows how TrueForge enforces scope, execution proof, and human control.

![Roaming Resolver system architecture](<Screenshots/roaming-resolver-system-architecture.png>)

![TrueForge agent harness and safety controls](<Screenshots/roaming-resolver-agent-harness.png>)

## 1. Install (PowerShell)

```powershell
git clone https://github.com/arshad98333/TrueForge-V1.git
cd TrueForge-V1
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
.\.venv\Scripts\python.exe -m app.cli init
```

## 2. Configure `.env`

Fill these values:

```dotenv
LINEAR_API_TOKEN=
LINEAR_TEAM_ID=
MONGODB_SEED_URI=
E2B_API_KEY=
```

Use either OpenAI only:

```dotenv
OPENAI_API_KEY=
TRUEFORGE_MODEL_NAME=openai/gpt-6-luna
```

Or Azure first with automatic OpenAI fallback:

```dotenv
AZURE_ENDPOINT=https://<resource>.openai.azure.com
AZURE_LLM_MODEL=<deployment-name>
OPENAI_API_KEY=
OPENAI_FALLBACK_ENABLED=true
OPENAI_FALLBACK_MODEL=gpt-6-luna
```

## 3. First run

```powershell
.\.venv\Scripts\python.exe -m app.cli seed
.\.venv\Scripts\python.exe -m app.cli setup-issue
.\scripts\run_investigation.ps1
```

Open [http://127.0.0.1:8000/demo](http://127.0.0.1:8000/demo).

## 4. Run the workflow

1. Click **Show all open** to load Linear tickets.
2. Click **Generate random case + run**.
3. Wait until all three proof cards show **PROVEN**.
4. Click **Review in TrueForge**.
5. Review the exact Linear comment, then click **Allow** or **Deny**.

![Linear tickets](<Screenshots/LINEAR ISSUES.png>)

![MongoDB evidence](<Screenshots/EXTERNAL DATABASE.png>)

![Human approval in TrueForge](<Screenshots/HITL.png>)

## 5. Later runs and tests

```powershell
.\scripts\start_demo.ps1
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp
npm test
```

The demo uses synthetic data only. It never refunds, changes billing, or contacts a customer.

## Hackathon fit

This project follows the [Agents That Act rubric](https://www.truefoundry.com/truefoundry-hackathon):

- The harness does the work: TrueForge reaches Linear and Atlas, runs code in E2B, and pauses for approval.
- It actually runs: the repository includes a short setup path, automated tests, and a working local UI.
- It knows where to stop: posting the correction requires approval, and customer delivery is unavailable.
- It completes a useful job: one disputed roaming charge is investigated end to end.
- The demo is clear: the UI exposes the tool path, calculation, trace IDs, approval state, and proof cards.

Build disclosure: OpenAI Codex assisted with implementation, testing, diagrams, and documentation. All credentials stay in `.env` and are excluded from screenshots and source control.
