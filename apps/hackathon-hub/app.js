const tracks = [
  {
    label: "Detect",
    title: "Watch AWS signals continuously",
    body:
      "Metrics, logs, and alarms feed an event-driven incident workflow as soon as the application shows unhealthy behavior."
  },
  {
    label: "Analyze",
    title: "Reason like a virtual cloud engineer",
    body:
      "The agent gathers context from CloudWatch and resource state, then identifies a likely cause instead of forwarding another alert."
  },
  {
    label: "Heal",
    title: "Execute a safe self-healing action",
    body:
      "Approved automation runs the remediation, verifies recovery, and records a short incident summary for operators."
  }
];

const deliverables = [
  "Problem statement tied to ops toil, downtime, and manual diagnosis",
  "Event-driven architecture showing telemetry, agent, orchestration, and action layers",
  "Primary demo path for CPU spike detection, diagnosis, and remediation",
  "Guardrails for what the agent can do automatically versus escalate",
  "Recovery evidence that proves the workload returned to a healthier state"
];

const timeline = [
  {
    title: "1. Incident detected",
    body:
      "A CPU spike or similar runtime issue crosses a threshold and triggers the event-driven workflow."
  },
  {
    title: "2. Agent diagnoses",
    body:
      "The agent reviews metrics, logs, and resource context, then selects a bounded remediation with a short explanation."
  },
  {
    title: "3. Recovery verified",
    body:
      "Automation executes the action, health signals improve, and operators receive a concise summary of what changed."
  }
];

const trackRoot = document.querySelector("#tracks");
const deliverableRoot = document.querySelector("#deliverables");
const timelineRoot = document.querySelector("#timeline");
const generatedOn = document.querySelector("#generated-on");

trackRoot.innerHTML = tracks
  .map(
    (track) => `
      <article class="track-card">
        <span class="badge">${track.label}</span>
        <h2>${track.title}</h2>
        <p>${track.body}</p>
      </article>
    `
  )
  .join("");

deliverableRoot.innerHTML = deliverables
  .map((item) => `<li><span>${item}</span></li>`)
  .join("");

timelineRoot.innerHTML = timeline
  .map(
    (step) => `
      <article class="timeline-step">
        <strong>${step.title}</strong>
        <p>${step.body}</p>
      </article>
    `
  )
  .join("");

generatedOn.textContent = `Generated on ${new Date().toLocaleDateString(undefined, {
  year: "numeric",
  month: "long",
  day: "numeric"
})} for the self-healing AWS demo`;
