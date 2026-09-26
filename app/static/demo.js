const byId = (id) => document.getElementById(id);
let demoToken = "";
let sessionId = "";
let selectedIssueId = "";

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[char]);
}

function trueForgeUrl() {
  return sessionId
    ? `http://127.0.0.1:8790/sessions/${encodeURIComponent(sessionId)}`
    : "http://127.0.0.1:8790";
}

function setProof(id, passed) {
  const element = byId(id);
  element.textContent = passed ? "PROVEN" : "WAITING";
  element.className = passed ? "pass" : "";
}

function formatTime(value) {
  if (!value) return "Pending";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function renderStage(stage) {
  return `
    <article class="stage ${stage.state}">
      <span class="stage-number">${escapeHtml(stage.number)}</span>
      <h3>${escapeHtml(stage.name)}</h3>
      <p>${escapeHtml(stage.detail)}</p>
      <div class="stage-meta">
        <span>${escapeHtml(stage.system)}</span>
        <span class="stage-state">${escapeHtml(stage.state.toUpperCase())}</span>
      </div>
    </article>`;
}

function renderTickets(items) {
  const list = byId("ticket-list");
  if (!items.length) {
    list.innerHTML = '<p class="empty-row">No open Linear tickets found.</p>';
    return;
  }
  list.innerHTML = items.map((ticket) => `
    <article class="ticket-row ${ticket.id === selectedIssueId ? "selected" : ""}">
      <div><strong>${escapeHtml(ticket.identifier)}</strong><span>${escapeHtml(ticket.title)}</span></div>
      <div class="ticket-meta"><span>${escapeHtml(ticket.state)}</span>
        <button type="button" data-issue-id="${escapeHtml(ticket.id)}" ${ticket.eligible ? "" : "disabled"}>
          ${ticket.eligible ? "Select" : "Out of scope"}
        </button>
      </div>
    </article>`).join("");
  list.querySelectorAll("button[data-issue-id]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedIssueId = button.dataset.issueId;
      byId("queue-feedback").textContent = "Selected synthetic Linear ticket. Run workflow to send it to TrueForge.";
      renderTickets(items);
    });
  });
}

function renderEdges(items) {
  byId("edge-grid").innerHTML = items.map((item) => `
    <article><strong>${escapeHtml(item.ticket_id)}</strong><span>${escapeHtml(item.scenario.replaceAll("_", " "))}</span><em>${escapeHtml(item.expected)}</em></article>
  `).join("");
}

async function loadTickets() {
  const response = await fetch("/demo-assets/tickets", { cache: "no-store" });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  renderTickets(data.tickets);
  renderEdges(data.edge_cases);
  return data.tickets;
}

function render(data) {
  demoToken = data.demo_token || demoToken;
  sessionId = data.session_id || "";
  selectedIssueId ||= data.issue?.uuid || "";
  byId("provider-label").textContent = data.provider?.fallback
    ? `${data.provider.primary} → ${data.provider.fallback} fallback`
    : (data.provider?.primary || "provider unavailable");
  byId("trueforge-link").href = trueForgeUrl();
  if (!data.available) {
    byId("run-status").textContent = "Not started";
    byId("run-id").textContent = data.message;
    byId("stage-grid").innerHTML = "";
    byId("run-workflow").textContent = "Run workflow";
    return;
  }

  byId("run-status").textContent = data.status;
  byId("run-id").textContent = data.run_id;
  byId("side-issue").textContent = data.issue.id;
  byId("side-title").textContent = data.issue.title;
  byId("stage-grid").innerHTML = data.stages.map(renderStage).join("");
  byId("evidence-hash").textContent = data.evidence.hash || "No evidence hash";

  const calculation = data.calculation || {};
  byId("billed").textContent = `INR ${calculation.billed_amount || "0.00"}`;
  byId("expected").textContent = `INR ${calculation.expected_amount || "0.00"}`;
  byId("difference").textContent = `INR ${calculation.difference || "0.00"}`;

  byId("session-id").textContent = data.session_id || "Not started";
  byId("sandbox-id").textContent = data.trace.sandbox_id || "Not provisioned";
  byId("exec-count").textContent = String(data.trace.exec_calls);
  byId("turn-status").textContent = data.trace.status;

  const events = data.audit.length
    ? data.audit
    : [{ event: "Waiting for the first event", time: null }];
  byId("audit-list").innerHTML = events
    .map((item) => `<li><span>${escapeHtml(item.event.replaceAll("_", " "))}</span><time>${escapeHtml(formatTime(item.time))}</time></li>`)
    .join("");

  setProof("proof-real", data.proof.real_systems);
  setProof("proof-code", data.proof.executed_code);
  setProof("proof-stop", data.proof.safe_stop && !data.proof.customer_message_sent);

  const action = byId("run-workflow");
  const status = data.status.toLowerCase();
  if (status === "complete") {
    action.textContent = "Workflow complete";
    action.disabled = true;
  } else if (status.startsWith("awaiting")) {
    action.textContent = "Review in TrueForge";
    action.disabled = false;
  } else if (["blocked", "not reproducible", "rejected"].includes(status)) {
    action.textContent = "Workflow stopped";
    action.disabled = true;
  } else {
    action.textContent = "Run workflow";
    action.disabled = false;
  }
}

async function refresh() {
  const button = byId("refresh");
  button.disabled = true;
  button.textContent = "Refreshing";
  try {
    const response = await fetch("/demo-assets/state", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    render(await response.json());
  } catch (error) {
    byId("run-status").textContent = "Unavailable";
    byId("run-id").textContent = "Local runtime state could not be loaded";
  } finally {
    button.disabled = false;
    button.textContent = "Refresh trace";
  }
}

async function startWorkflow(issueId = selectedIssueId) {
  const action = byId("run-workflow");
  action.disabled = true;
  action.textContent = "Starting workflow";
  byId("run-feedback").textContent = "Creating a bounded TrueForge turn";
  const response = await fetch("/demo-assets/start", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Demo-Token": demoToken },
    body: JSON.stringify(issueId ? { issue_id: issueId } : {}),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
  sessionId = result.session_id || sessionId;
  byId("run-feedback").textContent = result.message;
  await refresh();
}

byId("refresh").addEventListener("click", refresh);
byId("show-tickets").addEventListener("click", async () => {
  try {
    byId("queue-feedback").textContent = "Loading bounded Linear queue…";
    const tickets = await loadTickets();
    byId("queue-feedback").textContent = `${tickets.length} open ticket${tickets.length === 1 ? "" : "s"} loaded (maximum 100).`;
  } catch (error) {
    byId("queue-feedback").textContent = error.message;
  }
});
byId("generate-run").addEventListener("click", async () => {
  const button = byId("generate-run");
  button.disabled = true;
  button.textContent = "Generating + starting";
  byId("queue-feedback").textContent = "Updating synthetic Atlas facts and creating a Linear ticket…";
  try {
    const response = await fetch("/demo-assets/tickets/random", {
      method: "POST",
      headers: { "X-Demo-Token": demoToken },
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
    selectedIssueId = result.issue.id;
    byId("queue-feedback").textContent = `${result.issue.identifier} created with random synthetic evidence; handing it to TrueForge.`;
    await loadTickets();
    await startWorkflow(selectedIssueId);
  } catch (error) {
    byId("queue-feedback").textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = "Generate random case + run";
  }
});
byId("run-workflow").addEventListener("click", async () => {
  const action = byId("run-workflow");
  if (action.textContent === "Review in TrueForge") {
    window.open(trueForgeUrl(), "_blank", "noopener,noreferrer");
    return;
  }
  try {
    await startWorkflow();
  } catch (error) {
    byId("run-feedback").textContent = error.message;
    action.disabled = false;
    action.textContent = "Run workflow";
  }
});
Promise.allSettled([refresh(), loadTickets()]);
setInterval(refresh, 5000);
