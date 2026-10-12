/**
 * Public Grievance Auto-Routing System (PG-ARS)
 * Frontend Application Logic
 * Standardized municipal portal: pure JavaScript, high reliability, zero fake metrics.
 */

const API_BASE = "";

// Sample Grievances for fast demonstration
const DEMO_SAMPLES = {
  pothole: {
    name: "Ramesh C. Gupta",
    phone: "+91 98220 44109",
    email: "ramesh.gupta@example.com",
    ward: "Ward 3",
    locality: "Station Road near Tilak Statue",
    text: "Deep pothole right in front of bus shelter on Station Road. Multiple two-wheelers have skidded and fallen, especially at night."
  },
  pipe: {
    name: "Sunita Kulkarni",
    phone: "+91 98501 32910",
    email: "sunita.k@example.com",
    ward: "Ward 5",
    locality: "Shastri Nagar Sector 2",
    text: "Contaminated brownish muddy water coming from kitchen municipal tap since yesterday morning. Emitting foul chemical odor."
  },
  wire: {
    name: "Anand R. Verma",
    phone: "+91 98224 55301",
    email: "anand.verma@example.com",
    ward: "Ward 4",
    locality: "Mayur Colony Main Street",
    text: "Live electrical wire snapped and dangling 4 feet above pedestrian sidewalk near Anand Sweets. Extremely hazardous."
  },
  garbage: {
    name: "Sarita Deshpande",
    phone: "+91 98229 11488",
    email: "sarita.d@example.com",
    ward: "Ward 12",
    locality: "Karve Road Mandai Area",
    text: "Community garbage bin overflowing onto street. Stray cows and dogs scattering wet rotten food waste across 50 meters."
  },
  manhole: {
    name: "Rajiv Tandon",
    phone: "+91 98221 44099",
    email: "rtandon@example.com",
    ward: "Ward 14",
    locality: "Aundh Main Chowk",
    text: "Open sewer manhole cover missing on busy junction road. Poses severe fatal risk to cyclists and vehicles in night."
  },
  dengue: {
    name: "Dr. Hemant Barve",
    phone: "+91 98230 88200",
    email: "dr.barve@example.com",
    ward: "Ward 2",
    locality: "Prabhat Road Lane 9",
    text: "Severe mosquito infestation due to stagnant water in open plot. Three confirmed dengue cases in our apartment building, urgent fogging requested."
  },
  hawker: {
    name: "Vikram Sethi",
    phone: "+91 98211 44882",
    email: "vikram.sethi@example.com",
    ward: "Ward 5",
    locality: "FC Road Commercial Stretch",
    text: "Unauthorized illegal tea stalls and food carts constructed permanent iron sheds occupying 80% of pedestrian sidewalk."
  },
  ambiguous: {
    name: "Balwant Singh",
    phone: "+91 98110 33400",
    email: "bsingh@example.com",
    ward: "Ward 8",
    locality: "Katraj Ghat Road",
    text: "There is a terrible problem near my house since three days, please send an officer to inspect."
  }
};

const DEPT_NAMES = {
  roads: "Roads & Footpaths",
  water_supply: "Water Supply & Pipelines",
  electricity: "Electricity & Streetlighting",
  sanitation: "Solid Waste & Sanitation",
  drainage: "Drainage & Sewerage",
  public_health: "Public Health & Pest Control",
  encroachment: "Encroachments & Town Planning",
  unassigned: "Unassigned (Triage Desk)"
};

// Application State
const state = {
  activeView: "view-submit",
  summary: null,
  modelEval: null,
  departments: [],
  complaints: [],
  selectedComplaint: null,
  previewDebounceTimer: null,
  duplicateDebounceTimer: null,
  simulationPresets: [],
  simulationResult: null,
  systemConfig: { confidence_threshold: 0.65, class_margin_threshold: 0.15, cities: ["Pune"] },
  role: "citizen",
  selectedCity: "Pune"
};

// Document Ready Initialization
document.addEventListener("DOMContentLoaded", () => {
  initRoleWorkspaces();
  initNavigation();
  initFormListeners();
  initConsoleFilters();
  initModals();
  initQuickTokens();
  initSimulation();
  
  // Initial data fetch
  refreshAllData();
});

// Navigation Handling
function initNavigation() {
  const navBtns = document.querySelectorAll(".gov-nav-btn");
  navBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetView = btn.getAttribute("data-view");
      switchView(targetView);
    });
  });

  document.getElementById("btn-refresh-all")?.addEventListener("click", () => {
    refreshAllData();
  });

  document.getElementById("btn-trigger-sla")?.addEventListener("click", () => {
    triggerSlaCheck();
  });

  document.getElementById("btn-escalations-run-sweep")?.addEventListener("click", () => {
    triggerSlaCheck();
  });
}

function switchView(viewId) {
  state.activeView = viewId;
  document.querySelectorAll(".gov-nav-btn").forEach(b => {
    b.classList.toggle("active", b.getAttribute("data-view") === viewId);
  });
  document.querySelectorAll(".view-section").forEach(sec => {
    sec.classList.toggle("active", sec.id === viewId);
  });

  // View specific refreshes
  if (viewId === "view-console") loadConsoleComplaints();
  if (viewId === "view-triage") loadTriageQueue();
  if (viewId === "view-escalations") loadEscalationsView();
  if (viewId === "view-analytics") loadAnalyticsView();
  if (viewId === "view-simulator" && state.simulationPresets.length === 0) loadSimulationPresets();
  if (viewId === "view-city-dashboard") loadRoleDashboard("city");
  if (viewId === "view-state-dashboard") loadRoleDashboard("state");
}

// Master Refresh
async function refreshAllData() {
  await Promise.all([
    fetchSystemConfig(),
    fetchSummaryMetrics(),
    fetchDepartments(),
    loadConsoleComplaints()
  ]);
  
  if (state.activeView === "view-triage") loadTriageQueue();
  if (state.activeView === "view-escalations") loadEscalationsView();
  if (state.activeView === "view-analytics") loadAnalyticsView();
}

async function fetchSystemConfig() {
  try {
    const response = await fetch(`${API_BASE}/api/system/config`);
    if (!response.ok) return;
    state.systemConfig = await response.json();
    populateCitySelectors(state.systemConfig.cities || ["Pune"]);
    const percent = Math.round(state.systemConfig.confidence_threshold * 100);
    document.getElementById("kpi-threshold-label").textContent = `Confidence below ${percent}% threshold`;
    document.getElementById("triage-threshold-label").textContent = `Confidence fallback: complaints below the ${percent}% threshold or ambiguity margin`;
    document.getElementById("footer-threshold-label").textContent = `Confidence Fallback Threshold: ${state.systemConfig.confidence_threshold}`;
    const range = document.getElementById("sim-threshold");
    if (range && !state.simulationResult) {
      range.value = percent;
      document.getElementById("sim-threshold-value").textContent = `${percent}%`;
    }
  } catch (error) {
    console.error("System configuration error:", error);
  }
}

function initRoleWorkspaces() {
  const roleSelector = document.getElementById("role-selector");
  const citySelector = document.getElementById("role-city-selector");
  roleSelector?.addEventListener("change", () => applyRoleWorkspace(roleSelector.value));
  citySelector?.addEventListener("change", async () => {
    state.selectedCity = citySelector.value;
    document.getElementById("input-city").value = state.selectedCity;
    document.getElementById("city-dashboard-title").textContent = `${state.selectedCity} Municipal Command`;
    document.getElementById("city-scope-chip").textContent = `${state.selectedCity} · Maharashtra`;
    await refreshAllData();
    if (state.role === "city") loadRoleDashboard("city");
  });
  applyRoleWorkspace("citizen", false);
}

function populateCitySelectors(cities) {
  const options = cities.map(city => `<option value="${escapeHtml(city)}">${escapeHtml(city)}</option>`).join("");
  const roleCity = document.getElementById("role-city-selector");
  const inputCity = document.getElementById("input-city");
  const simCity = document.getElementById("sim-city-scope");
  if (roleCity) roleCity.innerHTML = options;
  if (inputCity) inputCity.innerHTML = options;
  if (simCity) simCity.innerHTML = `<option value="">All Maharashtra cities</option>${options}`;
  state.selectedCity = cities.includes(state.selectedCity) ? state.selectedCity : cities[0];
  if (roleCity) roleCity.value = state.selectedCity;
  if (inputCity) inputCity.value = state.selectedCity;
}

function applyRoleWorkspace(role, navigate = true) {
  state.role = role;
  document.body.classList.remove("role-citizen", "role-city", "role-state");
  document.body.classList.add(`role-${role}`);
  const citySelector = document.getElementById("role-city-selector");
  citySelector.hidden = role !== "city";
  const simulationCity = document.getElementById("sim-city-scope");
  if (simulationCity) simulationCity.value = role === "city" ? state.selectedCity : "";

  const allowedViews = {
    citizen: new Set(["view-submit", "view-track"]),
    city: new Set(["view-city-dashboard", "view-console", "view-triage", "view-escalations", "view-analytics", "view-simulator", "view-sandbox"]),
    state: new Set(["view-state-dashboard", "view-console", "view-escalations", "view-analytics", "view-simulator", "view-sandbox"])
  }[role];
  document.querySelectorAll(".gov-nav-btn").forEach(button => {
    button.hidden = !allowedViews.has(button.dataset.view);
  });

  if (navigate) {
    const target = role === "citizen" ? "view-submit" : role === "city" ? "view-city-dashboard" : "view-state-dashboard";
    switchView(target);
    refreshAllData();
    initQuickTokens();
  }
}

// Fetch Summary KPI Metrics
async function fetchSummaryMetrics() {
  try {
    const cityQuery = state.role === "city" ? `?city=${encodeURIComponent(state.selectedCity)}` : "";
    const res = await fetch(`${API_BASE}/api/analytics/summary${cityQuery}`);
    if (!res.ok) throw new Error("Failed to load summary");
    const data = await res.json();
    state.summary = data;

    // Update KPI Tiles
    document.getElementById("kpi-total").textContent = data.total_complaints.toLocaleString();
    document.getElementById("kpi-auto-routed").textContent = data.auto_routed_count.toLocaleString();
    document.getElementById("kpi-auto-pct").textContent = `${data.auto_routed_percentage}% of total volume`;
    document.getElementById("kpi-manual-pending").textContent = data.manual_review_pending.toLocaleString();
    document.getElementById("kpi-escalated").textContent = data.escalated_active.toLocaleString();
    document.getElementById("kpi-escalation-split").textContent = `${data.level1_escalations} Level 1 / ${data.level2_escalations} Level 2`;
    document.getElementById("kpi-sla-compliance").textContent = `${data.sla_compliance_rate}%`;

    // Update Nav Badges
    document.getElementById("nav-count-total").textContent = data.total_complaints;
    document.getElementById("nav-count-triage").textContent = data.manual_review_pending;
    document.getElementById("nav-count-escalated").textContent = data.escalated_active;
  } catch (err) {
    console.error("Error fetching summary metrics:", err);
  }
}

// Fetch Departments
async function fetchDepartments() {
  try {
    const res = await fetch(`${API_BASE}/api/departments`);
    if (!res.ok) throw new Error("Failed to load departments");
    state.departments = await res.json();
  } catch (err) {
    console.error("Error fetching departments:", err);
  }
}

// Form Handlers & Sample Chips
function initFormListeners() {
  // Sample chips
  document.querySelectorAll(".sample-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const sampleKey = chip.getAttribute("data-sample");
      const sample = DEMO_SAMPLES[sampleKey];
      if (!sample) return;

      document.getElementById("input-citizen-name").value = sample.name;
      document.getElementById("input-citizen-phone").value = sample.phone;
      document.getElementById("input-citizen-email").value = sample.email;
      document.getElementById("input-ward").value = sample.ward;
      document.getElementById("input-locality").value = sample.locality;
      document.getElementById("input-complaint-text").value = sample.text;

      // Trigger NLP preview
      runNlpPreview(sample.text);
    });
  });

  // Real-time typing analysis preview
  const textArea = document.getElementById("input-complaint-text");
  textArea.addEventListener("input", (e) => {
    clearTimeout(state.previewDebounceTimer);
    clearTimeout(state.duplicateDebounceTimer);
    const text = e.target.value.trim();
    if (text.length >= 15) {
      state.previewDebounceTimer = setTimeout(() => {
        runNlpPreview(text);
      }, 500);
      state.duplicateDebounceTimer = setTimeout(() => checkForDuplicateComplaints(text), 850);
    } else {
      document.getElementById("classifier-preview-box").style.display = "none";
      document.getElementById("duplicate-alert").hidden = true;
    }
  });

  document.getElementById("btn-use-location")?.addEventListener("click", attachCitizenLocation);
  document.getElementById("btn-voice-input")?.addEventListener("click", startVoiceInput);

  document.getElementById("btn-preview-nlp")?.addEventListener("click", () => {
    const text = textArea.value.trim();
    if (text) runNlpPreview(text);
  });

  // Complaint Submission
  const form = document.getElementById("form-complaint");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    await submitComplaint();
  });

  // Citizen Tracking Form
  const trackForm = document.getElementById("form-track");
  trackForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const token = document.getElementById("input-track-token").value.trim();
    if (token) trackComplaint(token);
  });

  // Classifier Sandbox
  document.getElementById("btn-sandbox-classify")?.addEventListener("click", () => {
    const text = document.getElementById("sandbox-input-text").value.trim();
    if (text) runSandboxClassify(text);
  });

  document.getElementById("btn-sandbox-clear")?.addEventListener("click", () => {
    document.getElementById("sandbox-input-text").value = "";
    document.getElementById("sandbox-results-panel").style.display = "none";
  });
}

async function checkForDuplicateComplaints(text) {
  const alertBox = document.getElementById("duplicate-alert");
  const ward = document.getElementById("input-ward")?.value || "";
  const city = document.getElementById("input-city")?.value || "Pune";
  if (!alertBox || text.length < 10) return;
  try {
    const response = await fetch(`${API_BASE}/api/complaints/similar/search?text=${encodeURIComponent(text)}&ward=${encodeURIComponent(ward)}&city=${encodeURIComponent(city)}&limit=3`);
    if (!response.ok) return;
    const data = await response.json();
    if (!data.matches?.length) {
      alertBox.hidden = true;
      return;
    }
    alertBox.innerHTML = `<strong>Possible existing issue${data.matches.length > 1 ? 's' : ''} found — avoid duplicate field work</strong>` + data.matches.map(match => `
      <div class="duplicate-match">
        <span>${escapeHtml(match.tracking_token)} · ${escapeHtml(match.locality)} · ${Math.round(match.similarity * 100)}% similar</span>
        <button type="button" data-track-token="${escapeHtml(match.tracking_token)}">View status</button>
      </div>
    `).join("");
    alertBox.querySelectorAll("[data-track-token]").forEach(button => button.addEventListener("click", () => trackFromReceipt(button.dataset.trackToken)));
    alertBox.hidden = false;
  } catch (error) {
    console.error("Duplicate search error:", error);
  }
}

function attachCitizenLocation() {
  const status = document.getElementById("location-status");
  if (!navigator.geolocation) {
    showToast("Location unavailable", "This browser does not provide geolocation.", "error");
    return;
  }
  status.textContent = "Requesting location…";
  navigator.geolocation.getCurrentPosition(position => {
    const latitude = position.coords.latitude.toFixed(6);
    const longitude = position.coords.longitude.toFixed(6);
    document.getElementById("input-latitude").value = latitude;
    document.getElementById("input-longitude").value = longitude;
    status.textContent = `GPS attached · ${latitude}, ${longitude}`;
    status.classList.add("active");
    showToast("Location attached", "Coordinates will be available to the responding department.", "success");
  }, error => {
    status.textContent = "No GPS attached";
    showToast("Location permission denied", error.message, "error");
  }, { enableHighAccuracy: true, timeout: 8000 });
}

function startVoiceInput() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    showToast("Voice input unavailable", "Use a Chromium-based browser with speech recognition support.", "error");
    return;
  }
  const recognition = new SpeechRecognition();
  const language = document.getElementById("input-language").value;
  recognition.lang = language === "Hindi" ? "hi-IN" : language === "Marathi" ? "mr-IN" : "en-IN";
  recognition.interimResults = false;
  recognition.onstart = () => showToast("Listening…", "Describe the civic issue clearly.");
  recognition.onerror = event => showToast("Voice input stopped", event.error, "error");
  recognition.onresult = event => {
    const textarea = document.getElementById("input-complaint-text");
    textarea.value = `${textarea.value} ${event.results[0][0].transcript}`.trim();
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
  };
  recognition.start();
}

// Real-Time NLP Preview
async function runNlpPreview(text) {
  try {
    const res = await fetch(`${API_BASE}/api/complaints/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    if (!res.ok) return;
    const data = await res.json();

    const box = document.getElementById("classifier-preview-box");
    box.style.display = "block";

    document.getElementById("preview-dept-name").textContent = data.department_name;
    document.getElementById("preview-confidence").textContent = `${Math.round(data.confidence_score * 100)}%`;

    const badge = document.getElementById("preview-routing-badge");
    if (data.routing_type === "AUTO") {
      badge.textContent = "Direct Auto-Dispatch";
      badge.className = "status-badge auto-routed";
    } else {
      badge.textContent = "Manual Review Queue";
      badge.className = "status-badge manual-review";
    }

    const urgencyTag = document.getElementById("preview-urgency-tag");
    urgencyTag.textContent = `${data.urgency} Urgency`;
    urgencyTag.className = `urgency-pill ${data.urgency.toLowerCase()}`;

    document.getElementById("preview-reasoning").textContent = data.reasoning;

    // Render Probability Meters
    const metersContainer = document.getElementById("preview-prob-meters");
    metersContainer.innerHTML = "";
    const sortedProbs = Object.entries(data.probabilities).sort((a, b) => b[1] - a[1]);

    sortedProbs.forEach(([dept, prob], idx) => {
      const pct = Math.round(prob * 100);
      const isTop = idx === 0;
      const row = document.createElement("div");
      row.className = "prob-meter-row";
      row.innerHTML = `
        <div class="prob-label">${DEPT_NAMES[dept] || dept}</div>
        <div class="prob-bar-track">
          <div class="prob-bar-fill ${isTop ? 'lead' : ''}" style="width: ${pct}%"></div>
        </div>
        <div class="prob-value">${pct}%</div>
      `;
      metersContainer.appendChild(row);
    });
  } catch (err) {
    console.error("Preview error:", err);
  }
}

// Submit Complaint
async function submitComplaint() {
  const submitBtn = document.getElementById("btn-submit-complaint");
  submitBtn.disabled = true;
  submitBtn.textContent = "Processing and Routing...";

  const payload = {
    citizen_name: document.getElementById("input-citizen-name").value.trim(),
    citizen_phone: document.getElementById("input-citizen-phone").value.trim(),
    citizen_email: document.getElementById("input-citizen-email").value.trim(),
    ward_number: document.getElementById("input-ward").value,
    city: document.getElementById("input-city").value,
    locality: document.getElementById("input-locality").value.trim(),
    complaint_text: document.getElementById("input-complaint-text").value.trim(),
    language: document.getElementById("input-language").value === "Auto detect" ? null : document.getElementById("input-language").value,
    latitude: document.getElementById("input-latitude").value ? Number(document.getElementById("input-latitude").value) : null,
    longitude: document.getElementById("input-longitude").value ? Number(document.getElementById("input-longitude").value) : null
  };

  try {
    const res = await fetch(`${API_BASE}/api/complaints/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Submission failed");
    }

    const data = await res.json();

    // Render Receipt
    const receiptBox = document.getElementById("receipt-container");
    receiptBox.style.display = "block";
    receiptBox.innerHTML = `
      <div class="receipt-card">
        <div class="receipt-header">
          <div class="receipt-title">Official Grievance Registration Receipt</div>
          <span class="status-badge ${data.routing_type === 'AUTO' ? 'auto-routed' : 'manual-review'}">
            ${data.routing_type === 'AUTO' ? 'Auto-Routed to Department' : 'Awaiting Triage Confirmation'}
          </span>
        </div>
        <div class="receipt-grid">
          <div class="receipt-item">
            <div class="item-label">Tracking Token</div>
            <div class="item-value" style="color: var(--gov-blue); font-size: 16px;">${data.tracking_token}</div>
          </div>
          <div class="receipt-item">
            <div class="item-label">Responsible Department</div>
            <div class="item-value">${data.department_name}</div>
          </div>
          <div class="receipt-item">
            <div class="item-label">Model Confidence</div>
            <div class="item-value">${Math.round(data.confidence_score * 100)}%</div>
          </div>
          <div class="receipt-item">
            <div class="item-label">Statutory Resolution SLA</div>
            <div class="item-value">${data.sla_deadline_hours} Hours</div>
          </div>
          <div class="receipt-item">
            <div class="item-label">SLA Due Date and Time</div>
            <div class="item-value">${new Date(data.sla_due_at).toLocaleString()}</div>
          </div>
          <div class="receipt-item">
            <div class="item-label">Assigned Urgency</div>
            <div class="item-value"><span class="urgency-pill ${data.urgency.toLowerCase()}">${data.urgency}</span></div>
          </div>
        </div>
        <p style="font-size: 12px; color: var(--gov-text-muted); margin-bottom: 16px;">
          ${data.reasoning}
        </p>
        <div style="display: flex; gap: 10px;">
          <button type="button" class="btn btn-action-blue btn-sm" onclick="trackFromReceipt('${data.tracking_token}')">
            Track Grievance Status
          </button>
          <button type="button" class="btn btn-secondary btn-sm" onclick="resetComplaintForm()">
            Lodge Another Grievance
          </button>
        </div>
      </div>
    `;

    // Refresh metrics and tables
    await refreshAllData();
    initQuickTokens();

    // Scroll to receipt
    receiptBox.scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    alert(`Error submitting grievance: ${err.message}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `
      <svg class="icon" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
      <span>Submit Grievance to Municipal Portal</span>
    `;
  }
}

function resetComplaintForm() {
  document.getElementById("form-complaint").reset();
  document.getElementById("classifier-preview-box").style.display = "none";
  document.getElementById("receipt-container").style.display = "none";
  document.getElementById("duplicate-alert").hidden = true;
  const locationStatus = document.getElementById("location-status");
  locationStatus.textContent = "No GPS attached";
  locationStatus.classList.remove("active");
}

function trackFromReceipt(token) {
  switchView("view-track");
  document.getElementById("input-track-token").value = token;
  trackComplaint(token);
}

// Track Grievance
async function trackComplaint(token) {
  const container = document.getElementById("track-result-container");
  container.style.display = "block";
  container.innerHTML = `<div style="padding: 20px; text-align: center;">Retrieving complaint records for <strong>${token}</strong>...</div>`;

  try {
    const res = await fetch(`${API_BASE}/api/complaints/track/${encodeURIComponent(token)}`);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Grievance record not found.");
    }
    const data = await res.json();

    // Time remaining / Overdue calculation
    const now = new Date();
    const dueDate = new Date(data.sla_due_at);
    const diffHours = (dueDate - now) / (1000 * 60 * 60);

    let slaStatusHtml = "";
    if (data.status === "RESOLVED") {
      slaStatusHtml = `<span class="status-badge resolved">Resolved on ${new Date(data.resolved_at).toLocaleString()}</span>`;
    } else if (diffHours < 0) {
      const overdueHours = Math.abs(diffHours).toFixed(1);
      slaStatusHtml = `<span class="status-badge ${data.escalation_level === 2 ? 'escalated-l2' : 'escalated-l1'}">Overdue by ${overdueHours} Hours (Escalated Level ${data.escalation_level})</span>`;
    } else {
      slaStatusHtml = `<span class="status-badge routed">${Math.round(diffHours)} Hours Remaining in SLA</span>`;
    }

    // Build timeline items
    const timelineHtml = (data.audit_logs || []).map(log => {
      const isAlert = log.action.includes("ESCALAT");
      const isSuccess = log.action === "RESOLVED";
      const markerClass = isAlert ? "danger" : isSuccess ? "success" : "";

      return `
        <div class="timeline-item">
          <div class="timeline-marker ${markerClass}"></div>
          <div class="timeline-content">
            <div class="timeline-header">
              <span class="timeline-action">${log.action.replace(/_/g, ' ')}</span>
              <span class="timeline-time">${new Date(log.timestamp).toLocaleString()}</span>
            </div>
            <div class="timeline-actor">Actor: ${escapeHtml(log.performed_by)}</div>
            <div class="timeline-notes">${escapeHtml(log.notes)}</div>
          </div>
        </div>
      `;
    }).join("");

    container.innerHTML = `
      <div class="gov-card">
        <div class="gov-card-header">
          <div>
            <h3 style="font-size: 16px;">Grievance Dossier: <span style="color: var(--gov-blue);">${data.tracking_token}</span></h3>
            <span class="header-meta">Lodged on ${new Date(data.created_at).toLocaleString()} by ${escapeHtml(data.citizen_name)}</span>
          </div>
          <div>
            <span class="status-badge ${data.status.toLowerCase().replace('_', '-')}">${data.status.replace('_', ' ')}</span>
          </div>
        </div>
        <div class="gov-card-body">
          <div class="receipt-grid" style="margin-bottom: 16px;">
            <div class="receipt-item">
              <div class="item-label">Ward and Locality</div>
              <div class="item-value">${escapeHtml(data.city || 'Pune')} · ${escapeHtml(data.ward_number)} (${escapeHtml(data.locality)})</div>
            </div>
            <div class="receipt-item">
              <div class="item-label">Assigned Department</div>
              <div class="item-value">${data.department_name || DEPT_NAMES[data.assigned_department] || data.assigned_department}</div>
            </div>
            <div class="receipt-item">
              <div class="item-label">Statutory SLA Target</div>
              <div class="item-value">${data.sla_deadline_hours} Hours</div>
            </div>
            <div class="receipt-item">
              <div class="item-label">SLA Redressal Status</div>
              <div class="item-value">${slaStatusHtml}</div>
            </div>
            <div class="receipt-item">
              <div class="item-label">Department Head</div>
              <div class="item-value">${data.head_officer || "Pending Assignment"}</div>
            </div>
            <div class="receipt-item">
              <div class="item-label">Routing Pathway</div>
              <div class="item-value">
                <span class="status-badge ${data.routing_type === 'AUTO' ? 'auto-routed' : 'manual-review'}">
                  ${data.routing_type === 'AUTO' ? 'Auto-Routed (NLP)' : 'Manual Triage'}
                </span>
                (${Math.round(data.confidence_score * 100)}% Confidence)
              </div>
            </div>
          </div>

          <div style="background-color: #f8fafc; border: 1px solid var(--gov-border); padding: 12px; border-radius: var(--gov-radius); margin-bottom: 20px;">
            <div style="font-size: 11px; font-weight: 700; color: var(--gov-navy); text-transform: uppercase; margin-bottom: 4px;">Original Grievance Text</div>
            <p style="font-size: 13px; color: var(--gov-text);">${escapeHtml(data.complaint_text)}</p>
          </div>

          ${data.resolution_notes ? `
            <div style="background-color: var(--gov-success-bg); border: 1px solid #bbf7d0; padding: 12px; border-radius: var(--gov-radius); margin-bottom: 20px;">
              <div style="font-size: 11px; font-weight: 700; color: var(--gov-success); text-transform: uppercase; margin-bottom: 4px;">Resolution Remarks by ${escapeHtml(data.assigned_officer || 'Officer')}</div>
              <p style="font-size: 13px; color: #14532d;">${escapeHtml(data.resolution_notes)}</p>
            </div>
          ` : ''}

          ${data.status === 'RESOLVED' ? `
            <div class="citizen-verification">
              <div><strong>Was this issue actually resolved?</strong><span>Your verification closes the accountability loop. An unresolved report reopens the case.</span></div>
              <div class="verification-actions">
                <select id="citizen-rating" class="form-control" aria-label="Resolution rating"><option value="5">5 — Excellent</option><option value="4">4 — Good</option><option value="3">3 — Acceptable</option><option value="2">2 — Poor</option><option value="1">1 — Very poor</option></select>
                <button type="button" class="btn btn-primary btn-sm" onclick="submitCitizenVerification('${escapeHtml(data.tracking_token)}', true)">Confirm resolved</button>
                <button type="button" class="btn btn-secondary btn-sm" onclick="submitCitizenVerification('${escapeHtml(data.tracking_token)}', false)">Still unresolved</button>
              </div>
            </div>
          ` : data.citizen_feedback ? `<div class="citizen-feedback-record">Citizen rating: ${data.citizen_feedback.rating}/5</div>` : ''}

          <h4 style="font-size: 14px; color: var(--gov-navy); margin-bottom: 12px; border-bottom: 1px solid var(--gov-border); padding-bottom: 6px;">
            Official Chain of Custody and Audit Timeline
          </h4>
          <div class="timeline-list">
            ${timelineHtml}
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `
      <div class="gov-card" style="border-left: 4px solid var(--gov-danger);">
        <div class="gov-card-body">
          <h4 style="color: var(--gov-danger); font-size: 14px;">Record Not Found</h4>
          <p style="font-size: 13px; color: var(--gov-text); margin-top: 4px;">${err.message}</p>
        </div>
      </div>
    `;
  }
}

async function submitCitizenVerification(token, verified) {
  const rating = Number(document.getElementById("citizen-rating")?.value || (verified ? 5 : 1));
  const comments = verified ? "Citizen confirmed that the field resolution is satisfactory." : "The reported issue is still present and requires another inspection.";
  try {
    const response = await fetch(`${API_BASE}/api/complaints/track/${encodeURIComponent(token)}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating, resolution_verified: verified, comments })
    });
    if (!response.ok) throw new Error("Could not record citizen verification");
    const result = await response.json();
    showToast(result.reopened ? "Grievance reopened" : "Feedback recorded", result.reopened ? "The department has been notified for another inspection." : "Thank you for verifying the resolution.", "success");
    await trackComplaint(token);
    await refreshAllData();
  } catch (error) {
    showToast("Verification failed", error.message, "error");
  }
}

// Quick tokens in track view
async function initQuickTokens() {
  const container = document.getElementById("track-quick-tokens");
  if (!container) return;

  if (state.role === "citizen") {
    container.innerHTML = '<span class="samples-label">For privacy, enter the tracking token issued on your registration receipt.</span>';
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/complaints?limit=6`);
    if (!res.ok) return;
    const data = await res.json();
    
    container.innerHTML = '<span class="samples-label">Recent Trackable Tokens:</span>';
    data.complaints.forEach(c => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "sample-chip";
      btn.textContent = `${c.tracking_token} (${c.status})`;
      btn.addEventListener("click", () => {
        document.getElementById("input-track-token").value = c.tracking_token;
        trackComplaint(c.tracking_token);
      });
      container.appendChild(btn);
    });
  } catch (err) {
    console.error("Quick tokens error:", err);
  }
}

// Operations Console & Filters
function initConsoleFilters() {
  ["filter-dept", "filter-status", "filter-routing", "filter-escalated"].forEach(id => {
    document.getElementById(id)?.addEventListener("change", () => loadConsoleComplaints());
  });

  let searchTimeout;
  document.getElementById("filter-search")?.addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => loadConsoleComplaints(), 400);
  });

  document.getElementById("btn-export-csv")?.addEventListener("click", () => {
    exportConsoleDataToCsv();
  });
}

async function loadConsoleComplaints() {
  const dept = document.getElementById("filter-dept")?.value || "ALL";
  const status = document.getElementById("filter-status")?.value || "ALL";
  const routing = document.getElementById("filter-routing")?.value || "ALL";
  const escalated = document.getElementById("filter-escalated")?.value || "ALL";
  const search = document.getElementById("filter-search")?.value || "";

  let url = `${API_BASE}/api/complaints?limit=200`;
  if (state.role === "city") url += `&city=${encodeURIComponent(state.selectedCity)}`;
  if (dept !== "ALL") url += `&department=${encodeURIComponent(dept)}`;
  if (status !== "ALL") url += `&status=${encodeURIComponent(status)}`;
  if (routing !== "ALL") url += `&routing_type=${encodeURIComponent(routing)}`;
  if (escalated !== "ALL") url += `&escalated=${encodeURIComponent(escalated)}`;
  if (search.trim()) url += `&search=${encodeURIComponent(search.trim())}`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to load complaints");
    const data = await res.json();
    state.complaints = data.complaints;

    document.getElementById("console-table-count").textContent = data.complaints.length;
    renderConsoleTable(data.complaints);
  } catch (err) {
    console.error("Console error:", err);
  }
}

function renderConsoleTable(complaints) {
  const tbody = document.getElementById("console-tbody");
  tbody.innerHTML = "";

  if (complaints.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 24px; color: var(--gov-text-muted);">No complaints match the specified filters.</td></tr>`;
    return;
  }

  const now = new Date();

  complaints.forEach(c => {
    const tr = document.createElement("tr");

    const dueDate = new Date(c.sla_due_at);
    const diffHours = (dueDate - now) / (1000 * 60 * 60);

    let slaText = "";
    if (c.status === "RESOLVED") {
      slaText = `<span style="color: var(--gov-success); font-weight: 600;">Resolved</span>`;
    } else if (diffHours < 0) {
      slaText = `<span style="color: var(--gov-danger); font-weight: 700;">Overdue (${Math.abs(diffHours).toFixed(0)}h)</span>`;
    } else {
      slaText = `<span>${Math.round(diffHours)}h remaining</span>`;
    }

    let escBadge = "---";
    if (c.is_escalated === 1 && c.status !== "RESOLVED") {
      escBadge = `<span class="status-badge ${c.escalation_level === 2 ? 'escalated-l2' : 'escalated-l1'}">Level ${c.escalation_level}</span>`;
    }

    const deptLabel = c.department_name || DEPT_NAMES[c.assigned_department] || c.assigned_department;

    tr.innerHTML = `
      <td><span class="token-link" onclick="openInspectorModal(${Number(c.id)})">${escapeHtml(c.tracking_token)}</span></td>
      <td>
        <div style="font-weight: 600;">${escapeHtml(c.citizen_name)}</div>
        <div style="font-size: 11px; color: var(--gov-text-muted);">${escapeHtml(c.city || 'Pune')} · ${escapeHtml(c.ward_number)}</div>
      </td>
      <td><strong>${deptLabel}</strong></td>
      <td>
        <span class="status-badge ${c.routing_type === 'AUTO' ? 'auto-routed' : 'manual-review'}">
          ${c.routing_type === 'AUTO' ? 'Auto' : 'Manual'}
        </span>
      </td>
      <td><span class="urgency-pill ${c.urgency.toLowerCase()}">${c.urgency}</span></td>
      <td>${Math.round(c.confidence_score * 100)}%</td>
      <td><span class="status-badge ${c.status.toLowerCase().replace('_', '-')}">${c.status.replace('_', ' ')}</span></td>
      <td>${slaText}</td>
      <td>${escBadge}</td>
      <td>
        <button type="button" class="btn btn-secondary btn-sm" onclick="openInspectorModal(${Number(c.id)})">
          Inspect
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// Triage Review Queue (Confidence Fallback)
async function loadTriageQueue() {
  try {
    const cityQuery = state.role === "city" ? `&city=${encodeURIComponent(state.selectedCity)}` : "";
    const res = await fetch(`${API_BASE}/api/complaints?routing_type=MANUAL_REVIEW&status=RECEIVED${cityQuery}`);
    if (!res.ok) throw new Error("Failed to load triage queue");
    const data = await res.json();

    document.getElementById("triage-table-count").textContent = data.complaints.length;
    renderTriageTable(data.complaints);
  } catch (err) {
    console.error("Triage queue error:", err);
  }
}

function renderTriageTable(complaints) {
  const tbody = document.getElementById("triage-tbody");
  tbody.innerHTML = "";

  if (complaints.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px; color: var(--gov-success); font-weight: 600;">Zero pending complaints in manual review queue. All complaints auto-routed successfully!</td></tr>`;
    return;
  }

  complaints.forEach(c => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong style="color: var(--gov-blue);">${escapeHtml(c.tracking_token)}</strong></td>
      <td>
        <div style="font-weight: 600;">${escapeHtml(c.citizen_name)}</div>
        <div style="font-size: 11px; color: var(--gov-text-muted);">${escapeHtml(c.ward_number)} - ${escapeHtml(c.locality)}</div>
      </td>
      <td style="max-width: 320px; font-size: 12px; color: var(--gov-slate);">${escapeHtml(c.complaint_text)}</td>
      <td><strong>${DEPT_NAMES[c.predicted_department] || c.predicted_department}</strong></td>
      <td><span style="color: var(--gov-warning); font-weight: 700;">${Math.round(c.confidence_score * 100)}%</span></td>
      <td><span class="urgency-pill ${c.urgency.toLowerCase()}">${c.urgency}</span></td>
      <td>
        <button type="button" class="btn btn-action-blue btn-sm triage-action">
          Assign &amp; Route
        </button>
      </td>
    `;
    tr.querySelector(".triage-action").addEventListener("click", () => openTriageModal(c.id, c.tracking_token, c.complaint_text, c.predicted_department));
    tbody.appendChild(tr);
  });
}

// SLA & Escalations View
async function loadEscalationsView() {
  await Promise.all([
    renderDeptSlaTable(),
    renderEscalatedTable()
  ]);
}

async function renderDeptSlaTable() {
  const tbody = document.getElementById("dept-sla-tbody");
  if (!tbody || state.departments.length === 0) return;

  tbody.innerHTML = state.departments.map(d => `
    <tr>
      <td><strong>${d.name}</strong></td>
      <td><strong>${d.sla_default_hours} Hours</strong></td>
      <td>Overdue > ${d.sla_default_hours}h</td>
      <td>Overdue > ${d.sla_default_hours + 24}h</td>
      <td>${d.active_staff_count} Field Staff</td>
      <td>${d.head_officer}</td>
    </tr>
  `).join("");
}

async function renderEscalatedTable() {
  const tbody = document.getElementById("escalations-tbody");
  tbody.innerHTML = "";

  try {
    const cityQuery = state.role === "city" ? `&city=${encodeURIComponent(state.selectedCity)}` : "";
    const res = await fetch(`${API_BASE}/api/complaints?escalated=1${cityQuery}`);
    if (!res.ok) throw new Error("Failed to load escalations");
    const data = await res.json();
    const activeEscalations = data.complaints.filter(c => c.status !== "RESOLVED" && c.status !== "REJECTED");

    document.getElementById("escalations-table-count").textContent = activeEscalations.length;

    if (activeEscalations.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 24px; color: var(--gov-success); font-weight: 600;">No active overdue escalations. All complaints are within their statutory SLA deadlines.</td></tr>`;
      return;
    }

    const now = new Date();

    activeEscalations.forEach(c => {
      const dueDate = new Date(c.sla_due_at);
      const overdueHours = ((now - dueDate) / (1000 * 60 * 60)).toFixed(1);
      const authority = c.escalation_level === 2
        ? "Municipal Commissioner & Grievance Cell Director"
        : "Superintending / Executive Engineer";

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><span class="token-link" onclick="openInspectorModal(${Number(c.id)})">${escapeHtml(c.tracking_token)}</span></td>
        <td>
          <div style="font-weight: 600;">${escapeHtml(c.citizen_name)}</div>
          <div style="font-size: 11px; color: var(--gov-text-muted);">${escapeHtml(c.ward_number)}</div>
        </td>
        <td><strong>${c.department_name || DEPT_NAMES[c.assigned_department] || c.assigned_department}</strong></td>
        <td><span class="status-badge ${c.status.toLowerCase().replace('_', '-')}">${c.status.replace('_', ' ')}</span></td>
        <td>${new Date(c.sla_due_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} (${new Date(c.sla_due_at).toLocaleDateString()})</td>
        <td><strong style="color: var(--gov-danger);">${overdueHours}h</strong></td>
        <td><span class="status-badge ${c.escalation_level === 2 ? 'escalated-l2' : 'escalated-l1'}">Level ${c.escalation_level}</span></td>
        <td style="font-size: 12px; font-weight: 600;">${authority}</td>
        <td>
          <button type="button" class="btn btn-primary btn-sm" onclick="openInspectorModal(${Number(c.id)})">
            Resolve Urgently
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Escalations load error:", err);
  }
}

// Trigger SLA Check Daemon
async function triggerSlaCheck() {
  try {
    const res = await fetch(`${API_BASE}/api/sla/trigger-check`, { method: "POST" });
    if (!res.ok) throw new Error("SLA check execution failed");
    const data = await res.json();
    alert(`SLA Sweep Completed:\nChecked ${data.total_active_checked} active grievances.\n${data.newly_escalated} complaints newly escalated due to SLA deadline breaches.`);
    await refreshAllData();
  } catch (err) {
    alert(`Error running SLA sweep: ${err.message}`);
  }
}

// Analytics and Model Evaluation View
async function loadAnalyticsView() {
  await Promise.all([
    renderModelEvaluationReport(),
    renderAnalyticsBreakdown()
  ]);
}

async function renderModelEvaluationReport() {
  try {
    const res = await fetch(`${API_BASE}/api/analytics/model`);
    if (!res.ok) throw new Error("Failed to load model evaluation");
    const data = await res.json();
    state.modelEval = data;

    document.getElementById("eval-model-type").textContent = data.model_type;
    document.getElementById("eval-accuracy").textContent = `${(data.overall_accuracy * 100).toFixed(2)}%`;
    document.getElementById("eval-split").textContent = `${data.training_samples} Training / ${data.test_samples} Held-Out Test`;
    document.getElementById("eval-threshold").textContent = data.confidence_threshold;
    document.getElementById("eval-fallback-rate").textContent = `${(data.test_fallback_rate * 100).toFixed(2)}% (${Math.round(data.test_fallback_rate * data.test_samples)} instances)`;
    document.getElementById("eval-protocol").textContent = data.evaluation_protocol || "Held-out evaluation split.";

    // Per-department report table
    const tbody = document.getElementById("eval-metrics-tbody");
    tbody.innerHTML = "";

    const report = data.classification_report;
    const classes = data.classes;

    classes.forEach(c => {
      const metrics = report[c];
      if (!metrics) return;
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${DEPT_NAMES[c] || c}</strong></td>
        <td>${(metrics.precision * 100).toFixed(1)}%</td>
        <td>${(metrics.recall * 100).toFixed(1)}%</td>
        <td><strong>${(metrics.f1_score * 100).toFixed(1)}%</strong></td>
        <td>${metrics.support}</td>
      `;
      tbody.appendChild(tr);
    });

    // Summary row
    if (report["macro avg"]) {
      const tr = document.createElement("tr");
      tr.style.backgroundColor = "#f8fafc";
      tr.style.fontWeight = "700";
      tr.innerHTML = `
        <td>Macro Average</td>
        <td>${(report["macro avg"].precision * 100).toFixed(1)}%</td>
        <td>${(report["macro avg"].recall * 100).toFixed(1)}%</td>
        <td>${(report["macro avg"].f1_score * 100).toFixed(1)}%</td>
        <td>${report["macro avg"].support}</td>
      `;
      tbody.appendChild(tr);
    }

    // Confusion Matrix Table
    const cmTable = document.getElementById("confusion-matrix-table");
    cmTable.innerHTML = "";

    // Header row
    let headerHtml = "<tr><th>True \\ Pred</th>";
    data.class_labels.forEach(lbl => {
      headerHtml += `<th title="${lbl}">${lbl.split('&')[0].trim()}</th>`;
    });
    headerHtml += "</tr>";

    let rowsHtml = "";
    data.confusion_matrix.forEach((row, rIdx) => {
      const trueLabel = data.class_labels[rIdx];
      rowsHtml += `<tr><th title="${trueLabel}">${trueLabel.split('&')[0].trim()}</th>`;
      row.forEach((cellVal, cIdx) => {
        const isDiagonal = rIdx === cIdx;
        const cellClass = isDiagonal ? "cm-diagonal" : (cellVal > 0 ? "cm-misclassified" : "");
        rowsHtml += `<td class="${cellClass}">${cellVal}</td>`;
      });
      rowsHtml += "</tr>";
    });

    cmTable.innerHTML = headerHtml + rowsHtml;
  } catch (err) {
    console.error("Model eval load error:", err);
  }
}

async function renderAnalyticsBreakdown() {
  if (!state.summary) return;

  // Department breakdown
  const deptTbody = document.getElementById("analytics-dept-tbody");
  deptTbody.innerHTML = state.summary.department_breakdown.map(d => `
    <tr>
      <td><strong>${d.name}</strong></td>
      <td><strong>${d.total_count}</strong></td>
      <td>${d.in_progress_count}</td>
      <td>${d.resolved_count}</td>
      <td><span style="color: ${d.escalated_count > 0 ? 'var(--gov-danger)' : 'inherit'}; font-weight: ${d.escalated_count > 0 ? '700' : '400'};">${d.escalated_count}</span></td>
      <td>${d.sla_default_hours}h</td>
    </tr>
  `).join("");

  // Ward breakdown
  const wardTbody = document.getElementById("analytics-ward-tbody");
  wardTbody.innerHTML = state.summary.ward_breakdown.map(w => `
    <tr>
      <td><strong>${w.ward_number}</strong></td>
      <td>${w.count}</td>
      <td><span style="color: ${w.escalated_count > 0 ? 'var(--gov-danger)' : 'inherit'};">${w.escalated_count}</span></td>
    </tr>
  `).join("");
}

// Role-scoped Maharashtra command dashboards
async function loadRoleDashboard(role) {
  const city = role === "city" ? state.selectedCity : null;
  const query = city ? `?city=${encodeURIComponent(city)}` : "";
  try {
    const [summaryResponse, intelligenceResponse] = await Promise.all([
      fetch(`${API_BASE}/api/analytics/summary${query}`),
      fetch(`${API_BASE}/api/analytics/intelligence${query}`)
    ]);
    if (!summaryResponse.ok || !intelligenceResponse.ok) throw new Error("Dashboard intelligence could not be loaded");
    const summary = await summaryResponse.json();
    const intelligence = await intelligenceResponse.json();
    renderCommandKpis(role, summary, intelligence);
    renderTopIssues(document.getElementById(`${role}-top-issues`), intelligence.top_issues);
    renderPriorityComplaints(document.getElementById(`${role}-priority-list`), intelligence.top_complaints);
    if (role === "state") renderStateCityMatrix(summary.city_breakdown || []);
  } catch (error) {
    showToast("Command dashboard unavailable", error.message, "error");
  }
}

function renderCommandKpis(role, summary, intelligence) {
  const container = document.getElementById(`${role}-command-kpis`);
  if (!container) return;
  const unresolved = Math.max(0, summary.total_complaints - summary.resolved_count);
  const scope = role === "city" ? state.selectedCity : "Maharashtra";
  const cards = [
    ["Total grievances", summary.total_complaints, `${scope} received`],
    ["Open workload", unresolved, `${summary.in_progress_count} in progress`],
    ["SLA compliance", `${summary.sla_compliance_rate}%`, `${summary.escalated_active} active escalations`],
    ["AI top issue", intelligence.top_issues?.[0]?.name || "No data", `${intelligence.top_issues?.[0]?.count || 0} related cases`],
    [role === "state" ? "Cities monitored" : "Manual triage", role === "state" ? summary.city_breakdown.length : summary.manual_review_pending, role === "state" ? "Maharashtra network" : "awaiting confirmation"]
  ];
  container.innerHTML = cards.map(([label, value, detail]) => `
    <article class="command-kpi"><span>${escapeHtml(label)}</span><strong title="${escapeHtml(String(value))}">${escapeHtml(String(value))}</strong><small>${escapeHtml(detail)}</small></article>
  `).join("");
}

function renderTopIssues(container, issues) {
  if (!container) return;
  if (!issues?.length) {
    container.innerHTML = `<div class="empty-intelligence">No complaint clusters available for this scope.</div>`;
    return;
  }
  container.innerHTML = issues.slice(0, 6).map((issue, index) => `
    <div class="issue-row">
      <span class="issue-rank">${index + 1}</span>
      <div class="issue-copy"><strong>${escapeHtml(issue.name)}</strong><span>${escapeHtml((issue.representative_terms || []).join(" · ") || "Operational complaint cluster")}</span></div>
      <div class="issue-volume"><strong>${issue.count}</strong><small>${issue.share}% share · ${issue.active_escalations} escalated</small></div>
    </div>
  `).join("");
}

function renderPriorityComplaints(container, complaints) {
  if (!container) return;
  if (!complaints?.length) {
    container.innerHTML = `<div class="empty-intelligence">No priority complaints in this scope.</div>`;
    return;
  }
  container.innerHTML = complaints.slice(0, 8).map(complaint => `
    <article class="priority-case ${complaint.priority_score >= 60 ? 'critical' : ''}" data-priority-token="${escapeHtml(complaint.tracking_token)}">
      <div><strong>${escapeHtml(complaint.tracking_token)}</strong><span class="priority-score">${complaint.priority_score} risk</span></div>
      <p>${escapeHtml(complaint.summary)}</p>
      <small>${escapeHtml(complaint.city)} · ${escapeHtml(complaint.ward)} · ${escapeHtml(complaint.urgency)} · ${escapeHtml(complaint.status.replaceAll('_', ' '))}</small>
    </article>
  `).join("");
  container.querySelectorAll("[data-priority-token]").forEach(card => card.addEventListener("click", () => openPriorityComplaint(card.dataset.priorityToken)));
}

function renderStateCityMatrix(cities) {
  const tbody = document.getElementById("state-city-tbody");
  if (!tbody) return;
  const maxTotal = Math.max(1, ...cities.map(city => city.total_count));
  tbody.innerHTML = cities.map(city => {
    const pressure = Math.min(100, Math.round((city.total_count / maxTotal) * 55 + city.escalated_count * 12 + city.triage_count * 7));
    return `<tr><td><strong>${escapeHtml(city.city)}</strong></td><td>${city.total_count}</td><td>${city.resolved_count}</td><td>${city.escalated_count}</td><td>${city.triage_count}</td><td><div class="pressure-meter" title="${pressure}% pressure"><span style="width:${pressure}%"></span></div></td></tr>`;
  }).join("");
}

async function openPriorityComplaint(token) {
  try {
    const response = await fetch(`${API_BASE}/api/complaints?search=${encodeURIComponent(token)}&limit=1`);
    if (!response.ok) throw new Error("Complaint lookup failed");
    const data = await response.json();
    if (!data.complaints?.length) throw new Error("Complaint no longer exists");
    openInspectorModal(data.complaints[0].id);
  } catch (error) {
    showToast("Complaint unavailable", error.message, "error");
  }
}

// Classifier Sandbox
async function runSandboxClassify(text) {
  try {
    const res = await fetch(`${API_BASE}/api/complaints/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    if (!res.ok) throw new Error("Sandbox classification error");
    const data = await res.json();

    const panel = document.getElementById("sandbox-results-panel");
    panel.style.display = "block";

    document.getElementById("sandbox-res-dept").textContent = data.department_name;
    document.getElementById("sandbox-res-conf").textContent = `${Math.round(data.confidence_score * 100)}%`;

    const routingElem = document.getElementById("sandbox-res-routing");
    routingElem.innerHTML = data.routing_type === "AUTO"
      ? `<span class="status-badge auto-routed">Direct Auto-Dispatch (Above ${Math.round(state.systemConfig.confidence_threshold * 100)}% Threshold)</span>`
      : `<span class="status-badge manual-review">Manual Review Fallback (Below ${Math.round(state.systemConfig.confidence_threshold * 100)}% Threshold)</span>`;

    document.getElementById("sandbox-res-urgency").innerHTML = `<span class="urgency-pill ${data.urgency.toLowerCase()}">${data.urgency}</span>`;
    document.getElementById("sandbox-res-reasoning").textContent = data.reasoning;

    const salientDiv = document.getElementById("sandbox-res-salient");
    if (data.top_features && data.top_features.length > 0) {
      salientDiv.innerHTML = `<strong>Detected Keywords:</strong> ${data.top_features.join(", ")}`;
    } else {
      salientDiv.innerHTML = "";
    }

    // Probability Bars
    const barsContainer = document.getElementById("sandbox-prob-bars");
    barsContainer.innerHTML = "";
    const sorted = Object.entries(data.probabilities).sort((a, b) => b[1] - a[1]);

    sorted.forEach(([dept, prob], idx) => {
      const pct = Math.round(prob * 100);
      const isTop = idx === 0;
      const row = document.createElement("div");
      row.className = "prob-meter-row";
      row.innerHTML = `
        <div class="prob-label">${DEPT_NAMES[dept] || dept}</div>
        <div class="prob-bar-track">
          <div class="prob-bar-fill ${isTop ? 'lead' : ''}" style="width: ${pct}%"></div>
        </div>
        <div class="prob-value">${pct}%</div>
      `;
      barsContainer.appendChild(row);
    });
  } catch (err) {
    alert(`Sandbox classification error: ${err.message}`);
  }
}

// Modals Handling
function initModals() {
  document.querySelectorAll(".modal-close-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("active"));
    });
  });

  // Triage Confirm Button
  document.getElementById("btn-triage-modal-confirm")?.addEventListener("click", async () => {
    const cId = document.getElementById("triage-modal-complaint-id").value;
    const dept = document.getElementById("triage-modal-select-dept").value;
    const operator = document.getElementById("triage-modal-operator").value.trim();
    const notes = document.getElementById("triage-modal-notes").value.trim();

    try {
      const res = await fetch(`${API_BASE}/api/complaints/${cId}/triage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          assigned_department: dept,
          operator_name: operator || "Triage Desk Operator",
          notes: notes || "Department confirmed upon manual triage review."
        })
      });
      if (!res.ok) throw new Error("Triage assignment failed");
      
      document.getElementById("modal-triage").classList.remove("active");
      alert("Complaint successfully triaged and dispatched to selected department!");
      await refreshAllData();
      loadTriageQueue();
    } catch (err) {
      alert(`Error assigning department: ${err.message}`);
    }
  });
}

// Open Inspector Modal
async function openInspectorModal(complaintId) {
  try {
    const res = await fetch(`${API_BASE}/api/complaints/${complaintId}`);
    if (!res.ok) throw new Error("Failed to load complaint");
    const data = await res.json();
    state.selectedComplaint = data;

    const modal = document.getElementById("modal-inspector");
    document.getElementById("modal-inspector-title").textContent = `Complaint Details: ${data.tracking_token}`;

    const body = document.getElementById("modal-inspector-body");
    body.innerHTML = `
      <div class="receipt-grid" style="margin-bottom: 14px;">
        <div class="receipt-item">
          <div class="item-label">Citizen Name</div>
          <div class="item-value">${escapeHtml(data.citizen_name)} (${escapeHtml(data.citizen_phone)})</div>
        </div>
        <div class="receipt-item">
          <div class="item-label">Ward Zone</div>
          <div class="item-value">${escapeHtml(data.ward_number)} - ${escapeHtml(data.locality)}</div>
        </div>
        <div class="receipt-item">
          <div class="item-label">Department</div>
          <div class="item-value">${data.department_name || DEPT_NAMES[data.assigned_department] || data.assigned_department}</div>
        </div>
        <div class="receipt-item">
          <div class="item-label">Current Status</div>
          <div class="item-value"><span class="status-badge ${data.status.toLowerCase().replace('_', '-')}">${data.status.replace('_', ' ')}</span></div>
        </div>
        <div class="receipt-item">
          <div class="item-label">Confidence Score</div>
          <div class="item-value">${Math.round(data.confidence_score * 100)}% (${data.routing_type})</div>
        </div>
        <div class="receipt-item">
          <div class="item-label">SLA Due At</div>
          <div class="item-value">${new Date(data.sla_due_at).toLocaleString()}</div>
        </div>
      </div>

      <div style="background-color: #f8fafc; border: 1px solid var(--gov-border); padding: 10px; border-radius: var(--gov-radius); margin-bottom: 16px;">
        <div style="font-size: 11px; font-weight: 700; color: var(--gov-navy); text-transform: uppercase; margin-bottom: 2px;">Complaint Text</div>
        <p style="font-size: 13px;">${escapeHtml(data.complaint_text)}</p>
      </div>

      <!-- Ground Action & Status Update Form -->
      <div style="border-top: 1px solid var(--gov-border); padding-top: 14px; margin-top: 14px;">
        <h4 style="font-size: 13px; color: var(--gov-navy); margin-bottom: 8px;">Department Ground Action &amp; Redressal Update</h4>
        
        <div class="form-grid" style="margin-bottom: 10px;">
          <div class="form-group">
            <label for="inspector-update-status">Update Status:</label>
            <select id="inspector-update-status" class="form-control">
              <option value="IN_PROGRESS" ${data.status === 'IN_PROGRESS' ? 'selected' : ''}>In Progress</option>
              <option value="RESOLVED" ${data.status === 'RESOLVED' ? 'selected' : ''}>Resolved</option>
              <option value="REJECTED" ${data.status === 'REJECTED' ? 'selected' : ''}>Rejected</option>
            </select>
          </div>
          <div class="form-group">
            <label for="inspector-update-officer">Assigned Officer / Inspector:</label>
            <input type="text" id="inspector-update-officer" class="form-control" value="${escapeHtml(data.assigned_officer || '')}" placeholder="e.g. Er. Sunil Rao">
          </div>
          <div class="form-group full-width">
            <label for="inspector-update-notes">Inspection / Redressal Verification Notes:</label>
            <textarea id="inspector-update-notes" class="form-control" rows="2" placeholder="Record physical site action, materials deployed, or verification remarks...">${escapeHtml(data.resolution_notes || '')}</textarea>
          </div>
        </div>
        
        <button type="button" class="btn btn-primary btn-sm" onclick="saveStatusUpdate(${data.id})">
          Save Action Update
        </button>
      </div>

      <!-- Misrouting Reroute Tool -->
      <div style="border-top: 1px solid var(--gov-border); padding-top: 14px; margin-top: 14px;">
        <h4 style="font-size: 13px; color: var(--gov-navy); margin-bottom: 4px;">Misrouting Correction (Transfer Department)</h4>
        <p style="font-size: 12px; color: var(--gov-text-muted); margin-bottom: 8px;">If this complaint was incorrectly assigned, transfer it with justification.</p>
        
        <div class="form-grid" style="margin-bottom: 10px;">
          <div class="form-group">
            <label for="inspector-reassign-dept">Target Department:</label>
            <select id="inspector-reassign-dept" class="form-control">
              <option value="roads">Roads &amp; Footpaths</option>
              <option value="water_supply">Water Supply &amp; Pipelines</option>
              <option value="electricity">Electricity &amp; Streetlighting</option>
              <option value="sanitation">Solid Waste &amp; Sanitation</option>
              <option value="drainage">Drainage &amp; Sewerage</option>
              <option value="public_health">Public Health &amp; Pest Control</option>
              <option value="encroachment">Encroachments &amp; Town Planning</option>
            </select>
          </div>
          <div class="form-group">
            <label for="inspector-reassign-reason">Transfer Justification:</label>
            <input type="text" id="inspector-reassign-reason" class="form-control" placeholder="e.g. Involves open sewer line, not drinking water">
          </div>
        </div>

        <button type="button" class="btn btn-secondary btn-sm" onclick="saveDepartmentReassignment(${data.id})">
          Transfer Complaint
        </button>
      </div>
    `;

    modal.classList.add("active");
  } catch (err) {
    alert(`Error viewing complaint: ${err.message}`);
  }
}

async function saveStatusUpdate(complaintId) {
  const status = document.getElementById("inspector-update-status").value;
  const officer = document.getElementById("inspector-update-officer").value.trim();
  const notes = document.getElementById("inspector-update-notes").value.trim();

  try {
    const res = await fetch(`${API_BASE}/api/complaints/${complaintId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status,
        officer_name: officer,
        notes: notes || `Status updated to ${status}.`
      })
    });
    if (!res.ok) throw new Error("Status update failed");
    
    document.getElementById("modal-inspector").classList.remove("active");
    alert("Complaint status successfully updated!");
    await refreshAllData();
  } catch (err) {
    alert(`Update failed: ${err.message}`);
  }
}

async function saveDepartmentReassignment(complaintId) {
  const newDept = document.getElementById("inspector-reassign-dept").value;
  const reason = document.getElementById("inspector-reassign-reason").value.trim();

  if (!reason) {
    alert("Please enter a transfer justification.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/complaints/${complaintId}/reassign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        new_department: newDept,
        reason
      })
    });
    if (!res.ok) throw new Error("Reassignment failed");

    document.getElementById("modal-inspector").classList.remove("active");
    alert("Complaint transferred to target department successfully!");
    await refreshAllData();
  } catch (err) {
    alert(`Reassignment failed: ${err.message}`);
  }
}

function openTriageModal(id, token, text, predictedDept) {
  document.getElementById("triage-modal-complaint-id").value = id;
  document.getElementById("triage-modal-token").textContent = token;
  document.getElementById("triage-modal-text").textContent = text;
  document.getElementById("triage-modal-select-dept").value = predictedDept;
  document.getElementById("modal-triage").classList.add("active");
}

// City Digital Twin Simulator
const SIM_DEFAULT_STAFF = {
  roads: 9,
  water_supply: 8,
  electricity: 7,
  sanitation: 10,
  drainage: 7,
  public_health: 6,
  encroachment: 5
};

function initSimulation() {
  const runButton = document.getElementById("btn-sim-run");
  if (!runButton) return;

  loadSimulationPresets();
  renderStaffingControls();

  ["threshold", "ambiguity", "urgency"].forEach(name => {
    const input = document.getElementById(`sim-${name}`);
    const output = document.getElementById(`sim-${name}-value`);
    input?.addEventListener("input", () => { output.textContent = `${input.value}%`; });
  });

  document.getElementById("sim-preset")?.addEventListener("change", applySimulationPreset);
  runButton.addEventListener("click", runCitySimulation);
  document.getElementById("btn-sim-reset")?.addEventListener("click", resetSimulation);
  window.addEventListener("resize", () => {
    if (state.simulationResult && state.activeView === "view-simulator") {
      drawSimulationTimeline(state.simulationResult.timeline);
    }
  });
}

async function loadSimulationPresets() {
  try {
    const response = await fetch(`${API_BASE}/api/simulation/presets`);
    if (!response.ok) throw new Error("Could not load simulator presets");
    const data = await response.json();
    state.simulationPresets = data.presets || [];
    const select = document.getElementById("sim-preset");
    if (!select) return;
    select.innerHTML = state.simulationPresets.map(preset =>
      `<option value="${escapeHtml(preset.key)}">${escapeHtml(preset.name)}</option>`
    ).join("");
    applySimulationPreset();
  } catch (error) {
    showToast("Simulator unavailable", error.message, "error");
  }
}

function applySimulationPreset() {
  const key = document.getElementById("sim-preset")?.value || "normal";
  const preset = state.simulationPresets.find(item => item.key === key);
  if (!preset) return;
  document.getElementById("sim-preset-description").textContent = preset.description;
  document.getElementById("sim-duration").value = preset.duration_hours;
  document.getElementById("sim-rate").value = preset.arrival_rate;
  document.getElementById("sim-ambiguity").value = Math.round(preset.ambiguity_rate * 100);
  document.getElementById("sim-urgency").value = Math.round(preset.high_urgency_rate * 100);
  document.getElementById("sim-ambiguity-value").textContent = `${Math.round(preset.ambiguity_rate * 100)}%`;
  document.getElementById("sim-urgency-value").textContent = `${Math.round(preset.high_urgency_rate * 100)}%`;

  Object.entries(SIM_DEFAULT_STAFF).forEach(([department, value]) => {
    const input = document.getElementById(`sim-staff-${department}`);
    if (input) input.value = Math.max(1, Math.round(value * (preset.staff_factor || 1)));
  });
}

function renderStaffingControls() {
  const container = document.getElementById("sim-staffing-controls");
  if (!container) return;
  container.innerHTML = Object.entries(SIM_DEFAULT_STAFF).map(([code, count]) => `
    <div class="staffing-row">
      <label for="sim-staff-${code}">${escapeHtml(DEPT_NAMES[code] || code)}</label>
      <input id="sim-staff-${code}" class="form-control" type="number" min="1" max="100" value="${count}">
    </div>
  `).join("");
}

function getSimulationPayload() {
  const staffing = {};
  Object.keys(SIM_DEFAULT_STAFF).forEach(code => {
    staffing[code] = Number(document.getElementById(`sim-staff-${code}`).value);
  });
  return {
    preset: document.getElementById("sim-preset").value,
    seed: Number(document.getElementById("sim-seed").value),
    duration_hours: Number(document.getElementById("sim-duration").value),
    arrival_rate: Number(document.getElementById("sim-rate").value),
    triage_staff: Number(document.getElementById("sim-triage").value),
    confidence_threshold: Number(document.getElementById("sim-threshold").value) / 100,
    ambiguity_rate: Number(document.getElementById("sim-ambiguity").value) / 100,
    high_urgency_rate: Number(document.getElementById("sim-urgency").value) / 100,
    city_scope: document.getElementById("sim-city-scope").value || null,
    staffing
  };
}

async function runCitySimulation() {
  const button = document.getElementById("btn-sim-run");
  const original = button.innerHTML;
  button.disabled = true;
  button.innerHTML = `<span class="live-dot"></span> Simulating city operations...`;
  try {
    const response = await fetch(`${API_BASE}/api/simulation/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(getSimulationPayload())
    });
    if (!response.ok) {
      const details = await response.json();
      throw new Error(details.detail?.[0]?.msg || details.detail || "Simulation failed");
    }
    const data = await response.json();
    state.simulationResult = data;
    renderSimulationResults(data);
    showToast("Simulation complete", `${data.summary.total_complaints} complaints processed using seed ${data.configuration.seed}.`, "success");
  } catch (error) {
    showToast("Simulation failed", error.message, "error");
  } finally {
    button.disabled = false;
    button.innerHTML = original;
  }
}

function renderSimulationResults(data) {
  document.getElementById("sim-empty-state").hidden = true;
  document.getElementById("sim-results").hidden = false;
  const summary = data.summary;
  document.getElementById("sim-kpi-total").textContent = summary.total_complaints.toLocaleString();
  document.getElementById("sim-kpi-scenario").textContent = data.scenario.name;
  document.getElementById("sim-kpi-auto").textContent = `${summary.auto_routing_rate}%`;
  document.getElementById("sim-kpi-manual").textContent = `${summary.manual_review.toLocaleString()} manual reviews`;
  document.getElementById("sim-kpi-sla").textContent = `${summary.sla_compliance}%`;
  document.getElementById("sim-kpi-breaches").textContent = `${summary.sla_breaches.toLocaleString()} SLA breaches`;
  document.getElementById("sim-kpi-p95").textContent = `${summary.p95_resolution_hours}h`;
  document.getElementById("sim-kpi-median").textContent = `${summary.median_resolution_hours}h median`;
  document.getElementById("sim-kpi-bottleneck").textContent = summary.bottleneck_department;
  document.getElementById("sim-kpi-escalations").textContent = `${summary.level1_escalations} L1 · ${summary.level2_escalations} L2`;

  const tbody = document.getElementById("sim-dept-tbody");
  tbody.innerHTML = data.department_metrics.map(department => `
    <tr>
      <td><strong>${escapeHtml(department.name)}</strong></td>
      <td>${department.received}</td>
      <td>${department.staff}</td>
      <td><strong>${department.utilization}%</strong><div class="util-track"><span style="width:${Math.min(100, department.utilization)}%"></span></div></td>
      <td>${department.avg_wait_hours}h</td>
      <td><span class="status-badge ${department.sla_compliance < 75 ? 'escalated-l2' : department.sla_compliance < 95 ? 'manual-review' : 'resolved'}">${department.sla_compliance}%</span></td>
    </tr>
  `).join("");

  const maxWard = Math.max(...data.ward_activity.map(item => item.count), 1);
  document.getElementById("sim-ward-grid").innerHTML = data.ward_activity.map(item => {
    const pressure = item.count / maxWard;
    const level = item.breaches > 0 && pressure > .65 ? "critical" : pressure > .55 ? "hot" : "";
    return `<div class="ward-cell ${level}" title="${item.count} complaints; ${item.breaches} breaches"><strong>${escapeHtml(item.ward.replace('Ward ', 'W'))}</strong><span>${item.count}</span><small>${item.breaches ? `${item.breaches} breach${item.breaches === 1 ? '' : 'es'}` : 'within SLA'}</small></div>`;
  }).join("");

  document.getElementById("sim-event-count").textContent = data.events.length;
  document.getElementById("sim-event-feed").innerHTML = data.events.map(event => `
    <div class="sim-event ${escapeHtml(event.type)}"><p>${escapeHtml(event.message)}</p><small>T+${event.at.toFixed(1)}h · ${escapeHtml(event.city || '')} · ${escapeHtml(event.ward)}</small></div>
  `).join("") || `<div class="sim-event"><p>No exceptional events generated.</p></div>`;

  document.getElementById("sim-top-issues").innerHTML = (data.top_issues || []).map(issue => `
    <article class="sim-issue ${issue.severity === 'CRITICAL' ? 'critical' : ''}"><strong>${escapeHtml(issue.name)}</strong><span>${issue.count}</span><small>${issue.share}% of intake · ${issue.sla_breaches} breaches · ${escapeHtml(issue.severity)}</small></article>
  `).join("");

  requestAnimationFrame(() => drawSimulationTimeline(data.timeline));
}

function drawSimulationTimeline(timeline) {
  const canvas = document.getElementById("sim-timeline-chart");
  if (!canvas || !timeline?.length) return;
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 700;
  const height = 230;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  const context = canvas.getContext("2d");
  context.scale(ratio, ratio);
  context.clearRect(0, 0, width, height);

  const padding = { left: 34, right: 12, top: 12, bottom: 24 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const maxValue = Math.max(1, ...timeline.flatMap(point => [point.arrivals, point.resolved, point.breached]));
  context.font = "9px system-ui";
  context.strokeStyle = "#e2e8f0";
  context.fillStyle = "#64748b";
  context.lineWidth = 1;
  for (let i = 0; i <= 4; i += 1) {
    const y = padding.top + chartHeight * i / 4;
    context.beginPath(); context.moveTo(padding.left, y); context.lineTo(width - padding.right, y); context.stroke();
    context.fillText(Math.round(maxValue * (1 - i / 4)), 3, y + 3);
  }

  const drawLine = (key, color) => {
    context.beginPath();
    context.strokeStyle = color;
    context.lineWidth = 2;
    timeline.forEach((point, index) => {
      const x = padding.left + chartWidth * index / Math.max(1, timeline.length - 1);
      const y = padding.top + chartHeight * (1 - point[key] / maxValue);
      if (index === 0) context.moveTo(x, y); else context.lineTo(x, y);
    });
    context.stroke();
  };
  drawLine("arrivals", "#0891b2");
  drawLine("resolved", "#16a34a");
  drawLine("breached", "#dc2626");
  context.fillStyle = "#64748b";
  context.fillText("0h", padding.left, height - 5);
  context.fillText(`${timeline.length - 1}h`, width - padding.right - 22, height - 5);
}

function resetSimulation() {
  document.getElementById("sim-preset").value = "normal";
  const threshold = Math.round(state.systemConfig.confidence_threshold * 100);
  document.getElementById("sim-threshold").value = threshold;
  document.getElementById("sim-threshold-value").textContent = `${threshold}%`;
  document.getElementById("sim-seed").value = 42;
  applySimulationPreset();
  state.simulationResult = null;
  document.getElementById("sim-empty-state").hidden = false;
  document.getElementById("sim-results").hidden = true;
}

function showToast(title, message, type = "info") {
  const region = document.getElementById("toast-region");
  if (!region) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  const heading = document.createElement("strong");
  heading.textContent = title;
  const copy = document.createElement("span");
  copy.textContent = message;
  toast.append(heading, copy);
  region.appendChild(toast);
  window.setTimeout(() => toast.remove(), 4500);
}

function exportConsoleDataToCsv() {
  if (state.complaints.length === 0) {
    alert("No records to export.");
    return;
  }

  const headers = ["Token", "Citizen", "Ward", "Department", "Urgency", "Confidence", "Status", "SLA Due", "Escalated"];
  const rows = state.complaints.map(c => [
    c.tracking_token,
    `"${c.citizen_name}"`,
    `"${c.ward_number}"`,
    `"${c.department_name || c.assigned_department}"`,
    c.urgency,
    c.confidence_score,
    c.status,
    `"${c.sla_due_at}"`,
    c.is_escalated
  ]);

  const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `grievance_ledger_${new Date().toISOString().split('T')[0]}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function escapeHtml(string) {
  return String(string)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
