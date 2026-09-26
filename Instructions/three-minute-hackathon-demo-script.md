Heading: 0:00 to 0:20 | Conclusion first

Screen: Open `http://127.0.0.1:8000/demo`. Keep the run status and proof cards visible.

Say: "This is the Roaming Charge Resolver. It completes one real support job: investigate a disputed charge, prove the result with executed code, and stop before external impact. The conclusion is simple: this is an agent that acts safely, not a chatbot. Three facts support that conclusion. It reaches Linear and MongoDB Atlas. It runs its calculation in E2B through TrueForge. It pauses for a person before posting to Linear."

Heading: 0:20 to 1:10 | How the UI and tools work

Screen: Show the open ticket queue and the tool path. Click **Show all open**. Point to **Generate random case + run**, but use the completed run for a reliable demo.

Say: "The console lists live open Linear tickets and only enables tickets carrying the exact synthetic scope marker. Generate random case plus run creates safe synthetic Atlas evidence, creates a Linear ticket, and hands its ID to the saved TrueForge agent. The tools are narrow. `read_issue` verifies the ticket and team. `read_evidence` reads only the customer, country, partner, and time window. `prepare_execution` freezes the exact calculation command. TrueForge executes that command once in E2B. `prepare_review` verifies the sandbox result and freezes the action preview. `post_correction` can post only the approved Linear comment. `approve_reply_draft` approves a local draft only. It never sends a customer message."

Heading: 1:10 to 1:40 | Show the proof

Screen: Scroll through the six stages, the decision record, the session ID, the sandbox ID, and the three PROVEN cards.

Say: "This run found INR 1,500 billed, INR 750 expected, and an INR 750 duplicate charge. The evidence hash binds the ticket, records, command, and result. This directly matches the hackathon goal: reach a real system, run real code, and know when to stop."

Heading: 1:40 to 2:05 | MECE explanation

Screen: Keep the six workflow stages visible.

Say: "The workflow is MECE. Discovery covers the Linear ticket and Atlas evidence. Execution covers command preparation, isolated E2B execution, and deterministic verification. Control covers approval, idempotent posting, and the held customer reply. These groups do not overlap, and together they cover the complete job from intake to safe outcome."

Heading: 2:05 to 2:40 | Toyota 5 Whys

Screen: Show the decision record, then click **Review in TrueForge**.

Say: "Why was the bill wrong? Two charge records point to one event and session. Why was that not obvious? The facts were split across the ticket, plan, pack, tariff, usage, and ledger. Why is manual review risky? It is slow and easy to miscalculate. Why use an agent? It can gather the bounded facts, write the calculation, and execute it. Why use TrueForge? Because proof is not permission. The harness records every step and stops at the irreversible boundary."

Heading: 2:40 to 3:00 | Human control and close

Screen: Show the exact `post_correction` request with **Allow** and **Deny** visible. Do not approve unless the demo owner intends to post the comment.

Say: "The operator sees the exact destination, text, amount, evidence hash, and expiry before deciding. No refund is issued, billing is unchanged, and the customer is not contacted. This is one useful job finished with a real tool, real execution, a clear safety boundary, and a README that another builder can run."
