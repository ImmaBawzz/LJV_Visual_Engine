const stateEls = {
  connectionStatus: document.getElementById("connectionStatus"),
  overallStatus: document.getElementById("overallStatus"),
  progressPct: document.getElementById("progressPct"),
  progressFill: document.getElementById("progressFill"),
  runningStep: document.getElementById("runningStep"),
  runtimeState: document.getElementById("runtimeState"),
  stepsList: document.getElementById("stepsList"),
  logsBox: document.getElementById("logsBox"),
  artifactsBox: document.getElementById("artifactsBox"),
  reportCards: document.getElementById("reportCards"),
  startBtn: document.getElementById("startBtn"),
  resumeBtn: document.getElementById("resumeBtn"),
  retryBtn: document.getElementById("retryBtn"),
  forceBtn: document.getElementById("forceBtn"),
  previewPlayer: document.getElementById("previewPlayer"),
  previewMeta: document.getElementById("previewMeta"),
  layoutCards: document.getElementById("layoutCards"),
  assetBrowser: document.getElementById("assetBrowser"),
};

let logCursor = 0;
const maxLogs = 300;

function badgeClassForStatus(status) {
  const value = String(status || "unknown").toLowerCase();
  if (["completed", "pass", "ok", "success"].includes(value)) return "ok";
  if (["running", "in_progress"].includes(value)) return "run";
  if (["failed", "error", "fail"].includes(value)) return "bad";
  return "warn";
}

function htmlEscape(input) {
  return String(input || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function bytesToMb(sizeBytes) {
  return (Number(sizeBytes || 0) / (1024 * 1024)).toFixed(2);
}

async function getJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Request failed: ${path}`);
  }
  return response.json();
}

async function postAction(path) {
  const response = await fetch(path, { method: "POST" });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || "Action failed");
  }
  return response.json();
}

function renderState(payload) {
  const runtime = payload.runtime || {};
  const checkpoint = payload.checkpoint || {};
  const controls = payload.controls || {};

  const status = checkpoint.overall_status || "unknown";
  stateEls.overallStatus.innerHTML = `${htmlEscape(status)}<span class="badge ${badgeClassForStatus(status)}">${htmlEscape(status)}</span>`;

  const progress = Number(checkpoint.progress_pct || 0);
  stateEls.progressPct.textContent = progress.toFixed(1);
  stateEls.progressFill.style.width = `${Math.min(100, Math.max(0, progress))}%`;

  if (checkpoint.running_step) {
    stateEls.runningStep.textContent = `#${checkpoint.running_step.id} ${checkpoint.running_step.name || "Unnamed"}`;
  } else {
    stateEls.runningStep.textContent = "idle";
  }

  stateEls.runtimeState.innerHTML = runtime.active
    ? `active (pid ${runtime.pid}) <span class="badge run">running</span>`
    : `inactive <span class="badge warn">idle</span>`;

  stateEls.startBtn.disabled = !Boolean(controls.can_start);
  stateEls.resumeBtn.disabled = !Boolean(controls.can_resume);
  stateEls.retryBtn.disabled = !Boolean(controls.can_retry);
  stateEls.forceBtn.disabled = Boolean(runtime.active);

  if (runtime.last_error === "runtime_lock_expired") {
    stateEls.connectionStatus.textContent = "Recovered stale lock";
  }
}

function renderCheckpoint(checkpointPayload) {
  const cp = checkpointPayload.checkpoint || {};
  const steps = cp.steps || {};
  const ids = Object.keys(steps)
    .map((id) => Number(id))
    .filter((id) => Number.isFinite(id))
    .sort((a, b) => a - b);

  if (ids.length === 0) {
    stateEls.stepsList.innerHTML = '<div class="step">No checkpoint data yet.</div>';
    return;
  }

  stateEls.stepsList.innerHTML = ids.map((id) => {
    const step = steps[String(id)] || steps[id] || {};
    const status = step.status || "pending";
    const badge = `<span class="badge ${badgeClassForStatus(status)}">${htmlEscape(status)}</span>`;
    const duration = step.duration_sec ? `${step.duration_sec}s` : "-";
    const error = step.error ? `<div class="meta">error: ${htmlEscape(step.error)}</div>` : "";
    return `
      <div class="step">
        <div><strong>#${id} ${htmlEscape(step.name || "Unnamed Step")}</strong>${badge}</div>
        <div class="meta">duration: ${htmlEscape(duration)} | exit: ${htmlEscape(step.exit_code ?? "-")}</div>
        ${error}
      </div>
    `;
  }).join("");
}

function renderLogs(payload) {
  const entries = payload.entries || [];
  if (!entries.length) return;

  const existing = stateEls.logsBox.querySelectorAll(".log").length;
  const fragment = entries.map((entry) => {
    const level = entry.level || "INFO";
    return `
      <div class="log">
        <div><strong>${htmlEscape(level)}</strong> ${htmlEscape(entry.message || "")}</div>
        <div class="meta">${htmlEscape(entry.timestamp || "-")} | ${htmlEscape(entry.step || "-")} | exit=${htmlEscape(entry.exit_code ?? "-")}</div>
      </div>
    `;
  }).join("");

  if (existing === 0) {
    stateEls.logsBox.innerHTML = fragment;
  } else {
    stateEls.logsBox.insertAdjacentHTML("beforeend", fragment);
  }

  while (stateEls.logsBox.querySelectorAll(".log").length > maxLogs) {
    stateEls.logsBox.firstElementChild?.remove();
  }

  stateEls.logsBox.scrollTop = stateEls.logsBox.scrollHeight;
}

function renderReports(payload) {
  const cards = [
    ["Preflight", payload.preflight?.summary],
    ["Quality Gate", payload.quality_gate?.summary],
    ["Release Readiness", payload.release_readiness?.summary],
  ];

  stateEls.reportCards.innerHTML = cards.map(([title, summary]) => {
    const status = summary?.status || "missing";
    const warnings = summary?.warnings ?? 0;
    const errors = summary?.errors ?? 0;
    return `
      <div class="report-card">
        <div><strong>${htmlEscape(title)}</strong><span class="badge ${badgeClassForStatus(status)}">${htmlEscape(status)}</span></div>
        <div class="meta">errors: ${htmlEscape(errors)} | warnings: ${htmlEscape(warnings)}</div>
      </div>
    `;
  }).join("");
}

function renderArtifacts(payload) {
  const files = payload.files || [];
  if (!files.length) {
    stateEls.artifactsBox.innerHTML = '<div class="artifact">No artifacts found yet.</div>';
    return;
  }

  stateEls.artifactsBox.innerHTML = files.slice(0, 60).map((item) => `
      <div class="artifact">
        <div><strong>${htmlEscape(item.path || "-")}</strong></div>
        <div class="meta">${bytesToMb(item.size_bytes)} MB | ${htmlEscape(item.modified_at || "-")}</div>
      </div>
    `).join("");
}

function renderLayouts(payload) {
  const layouts = payload.layouts || [];
  if (!layouts.length) {
    stateEls.layoutCards.innerHTML = '<div class="artifact">No layout metadata found.</div>';
    return;
  }

  stateEls.layoutCards.innerHTML = layouts.map((layout) => `
    <div class="layout-card">
      <div class="layout-title"><strong>${htmlEscape(layout.target || "unknown")}</strong></div>
      <div class="meta">${htmlEscape(layout.dimensions || "unknown")} @ ${htmlEscape(layout.fps || "unknown")} fps</div>
      <div class="meta">videos: ${htmlEscape(layout.videos ?? 0)}</div>
      <div class="meta">folder: ${htmlEscape(layout.folder || "-")}</div>
    </div>
  `).join("");
}

function renderPreview(payload) {
  if (!payload.exists || !payload.video) {
    stateEls.previewPlayer.removeAttribute("src");
    stateEls.previewPlayer.load();
    stateEls.previewMeta.textContent = "No preview video available yet.";
    return;
  }

  const video = payload.video;
  const nextSrc = video.download_url || "";
  if (stateEls.previewPlayer.getAttribute("src") !== nextSrc) {
    stateEls.previewPlayer.src = nextSrc;
    stateEls.previewPlayer.load();
  }

  stateEls.previewMeta.textContent = `${video.path} | ${bytesToMb(video.size_bytes)} MB | ${video.modified_at || "-"}`;
}

function renderAssetBrowser(payload) {
  const groups = payload.groups || {};
  const groupNames = Object.keys(groups);

  if (!groupNames.length) {
    stateEls.assetBrowser.innerHTML = '<div class="artifact">No grouped assets yet.</div>';
    return;
  }

  stateEls.assetBrowser.innerHTML = groupNames.map((groupName) => {
    const entries = (groups[groupName] || []).slice(0, 8);
    const list = entries.map((entry) => {
      const playButton = entry.is_video
        ? `<button class="mini" data-preview="${htmlEscape(entry.download_url)}" data-path="${htmlEscape(entry.path)}">Preview</button>`
        : "";
      return `
        <div class="artifact-row">
          <div>
            <div class="path">${htmlEscape(entry.path)}</div>
            <div class="meta">${bytesToMb(entry.size_bytes)} MB | ${htmlEscape(entry.modified_at || "-")}</div>
          </div>
          <div class="asset-actions">
            ${playButton}
            <a href="${htmlEscape(entry.download_url)}" class="mini-link" target="_blank" rel="noopener">Download</a>
          </div>
        </div>
      `;
    }).join("");

    return `
      <div class="asset-group">
        <div class="asset-group-title">${htmlEscape(groupName)} <span class="badge warn">${groups[groupName].length}</span></div>
        <div class="asset-group-list">${list}</div>
      </div>
    `;
  }).join("");

  stateEls.assetBrowser.querySelectorAll("button[data-preview]").forEach((button) => {
    button.addEventListener("click", () => {
      const preview = button.getAttribute("data-preview") || "";
      const path = button.getAttribute("data-path") || "";
      stateEls.previewPlayer.src = preview;
      stateEls.previewPlayer.load();
      stateEls.previewMeta.textContent = path;
    });
  });
}

async function refreshState() {
  const [statePayload, checkpointPayload] = await Promise.all([
    getJson("/api/state"),
    getJson("/api/checkpoint"),
  ]);

  renderState(statePayload);
  renderCheckpoint(checkpointPayload);
}

async function refreshLogs() {
  const logsPayload = await getJson(`/api/logs?cursor=${logCursor}&limit=80`);
  renderLogs(logsPayload);
  logCursor = logsPayload.next_cursor || logCursor;
}

async function refreshDashboardData() {
  const [reportsPayload, artifactsPayload, layoutsPayload, previewPayload, assetBrowserPayload] = await Promise.all([
    getJson("/api/reports"),
    getJson("/api/artifacts?limit=80"),
    getJson("/api/layouts"),
    getJson("/api/preview/default"),
    getJson("/api/artifact-browser?limit=140"),
  ]);

  renderReports(reportsPayload);
  renderArtifacts(artifactsPayload);
  renderLayouts(layoutsPayload);
  renderPreview(previewPayload);
  renderAssetBrowser(assetBrowserPayload);
}

async function handleAction(path, confirmText) {
  if (confirmText && !window.confirm(confirmText)) {
    return;
  }
  try {
    await postAction(path);
    await refreshState();
    stateEls.connectionStatus.textContent = "Action sent";
  } catch (error) {
    window.alert(error.message);
  }
}

async function tick() {
  try {
    await refreshState();
    await refreshLogs();
    stateEls.connectionStatus.textContent = "Live";
  } catch (error) {
    stateEls.connectionStatus.textContent = "Reconnecting";
  }
}

function bindActions() {
  stateEls.startBtn.addEventListener("click", () => handleAction("/api/control/start", "Start a new pipeline run?"));
  stateEls.resumeBtn.addEventListener("click", () => handleAction("/api/control/resume", "Resume from last non-completed step?"));
  stateEls.retryBtn.addEventListener("click", () => handleAction("/api/control/retry", "Retry the failed step using resume mode?"));
  stateEls.forceBtn.addEventListener("click", () => handleAction("/api/control/force", "Force reset checkpoint and restart from step 1?"));
}

async function bootstrap() {
  bindActions();
  await tick();
  await refreshDashboardData();

  setInterval(tick, 1000);
  setInterval(refreshDashboardData, 5000);
}

bootstrap();
