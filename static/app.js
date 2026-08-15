document.addEventListener("DOMContentLoaded", () => {
  // Navigation Tabs
  const navTabs = document.querySelectorAll(".nav-tab");
  const tabPanes = document.querySelectorAll(".tab-pane");

  navTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      navTabs.forEach(t => t.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));

      tab.classList.add("active");
      const targetId = tab.getAttribute("data-tab");
      const pane = document.getElementById(targetId);
      if (pane) pane.classList.add("active");

      if (targetId === "tab-cause-list") {
        loadDailyCauseList();
      } else if (targetId === "tab-portfolio") {
        loadTrackedCases();
      }
    });
  });

  // Cause List Elements
  const causeListDatePicker = document.getElementById("cause-list-date-picker");
  const causeListContainer = document.getElementById("cause-list-container");
  const courtSummaryChips = document.getElementById("court-summary-chips");
  const btnLoadKarurSample = document.getElementById("btn-load-karur-sample");
  const btnSendMorningDocket = document.getElementById("btn-send-morning-docket");
  const btnPrintBoard = document.getElementById("btn-print-board");
  const statBoardCount = document.getElementById("stat-board-count");

  // Client Intake Form Elements
  const caseForm = document.getElementById("case-form");
  const cnrInput = document.getElementById("cnr-input");
  const clientNameInput = document.getElementById("client-name");
  const litigantRoleInput = document.getElementById("litigant-role");
  const clientPhoneInput = document.getElementById("client-phone");
  const clientEmailInput = document.getElementById("client-email");
  const caseNumberInput = document.getElementById("case-number-input");
  const caseStageInput = document.getElementById("case-stage-input");
  const courtRoomInput = document.getElementById("court-room-input");
  const itemNumberInput = document.getElementById("item-number-input");
  const caseNotesInput = document.getElementById("case-notes");
  const ruleTrackHearing = document.getElementById("rule-track-hearing");
  const ruleTrackOrders = document.getElementById("rule-track-orders");
  const ruleTrackStatus = document.getElementById("rule-track-status");
  const ruleAutoWa = document.getElementById("rule-auto-wa");
  const forceLiveToggle = document.getElementById("force-live-toggle");

  const btnFetch = document.getElementById("btn-fetch");
  const btnDemo = document.getElementById("btn-demo");
  const btnClearForm = document.getElementById("btn-clear-form");
  const btnClearAll = document.getElementById("btn-clear-all");
  const btnSmartSync = document.getElementById("btn-smart-sync");
  const btnOpenSchedulerMonitor = document.getElementById("btn-open-scheduler-monitor");
  const btnOpenHistory = document.getElementById("btn-open-history");

  const cardHistoryStat = document.getElementById("card-history-stat");
  const filterInput = document.getElementById("filter-input");
  const caseResultContent = document.getElementById("case-result-content");
  const cacheBadge = document.getElementById("cache-badge");
  const casesTbody = document.getElementById("cases-tbody");
  const casesCount = document.getElementById("cases-count");
  const historyCount = document.getElementById("history-count");
  const statTotalCases = document.getElementById("stat-total-cases");
  const statDateChanges = document.getElementById("stat-date-changes");
  const headerFirmName = document.getElementById("header-firm-name");
  const apiStatusText = document.getElementById("api-status-text");
  const statusDot = document.getElementById("status-dot");

  // Modals
  const settingsModal = document.getElementById("settings-modal");
  const btnOpenSettings = document.getElementById("btn-open-settings");
  const btnCloseSettings = document.getElementById("btn-close-settings");
  const btnCancelSettings = document.getElementById("btn-cancel-settings");
  const settingsForm = document.getElementById("settings-form");
  const settingFirmName = document.getElementById("setting-firm-name");
  const settingLawyerName = document.getElementById("setting-lawyer-name");
  const settingLawyerPhone = document.getElementById("setting-lawyer-phone");
  const settingFooter = document.getElementById("setting-footer");
  const apiKeyInput = document.getElementById("api-key-input");

  const rulesModal = document.getElementById("rules-modal");
  const btnCloseRules = document.getElementById("btn-close-rules");
  const btnCancelRules = document.getElementById("btn-cancel-rules");
  const rulesForm = document.getElementById("rules-form");
  const editRuleCnr = document.getElementById("edit-rule-cnr");
  const editClientName = document.getElementById("edit-client-name");
  const editClientPhone = document.getElementById("edit-client-phone");
  const editRoom = document.getElementById("edit-room");
  const editItem = document.getElementById("edit-item");
  const editStage = document.getElementById("edit-stage");
  const editJudge = document.getElementById("edit-judge");
  const editNotes = document.getElementById("edit-notes");
  const editRuleHearing = document.getElementById("edit-rule-hearing");
  const editRuleOrders = document.getElementById("edit-rule-orders");
  const editRuleStatus = document.getElementById("edit-rule-status");
  const editRuleWa = document.getElementById("edit-rule-wa");

  const schedulerModal = document.getElementById("scheduler-modal");
  const btnCloseScheduler = document.getElementById("btn-close-scheduler");
  const schedulerSummaryBanner = document.getElementById("scheduler-summary-banner");
  const schedulerEvaluationsList = document.getElementById("scheduler-evaluations-list");

  const historyModal = document.getElementById("history-modal");
  const btnCloseHistory = document.getElementById("btn-close-history");
  const historyLogsContent = document.getElementById("history-logs-content");

  let allTrackedCases = [];
  let currentAdvocateSettings = {};

  // Initialize
  checkKeyStatus();
  loadAdvocateSettings();
  loadDailyCauseList();
  loadTrackedCases();
  loadHistoryLogsCount();

  // Load Daily Cause List
  causeListDatePicker.addEventListener("change", () => {
    const selected = causeListDatePicker.value;
    btnPrintBoard.href = `/api/export-cause-list?date=${selected}`;
    loadDailyCauseList(selected);
  });

  btnLoadKarurSample.addEventListener("click", async () => {
    btnLoadKarurSample.disabled = true;
    btnLoadKarurSample.innerText = "⏳ Loading Karur Board...";
    try {
      const res = await fetch("/api/cause-list/import-karur", { method: "POST" });
      const data = await res.json();
      causeListDatePicker.value = "2026-08-14";
      btnPrintBoard.href = `/api/export-cause-list?date=2026-08-14`;
      loadDailyCauseList("2026-08-14");
      loadTrackedCases();
      alert("✅ " + data.message);
    } catch (e) {
      alert("Failed to load sample: " + e.message);
    } finally {
      btnLoadKarurSample.disabled = false;
      btnLoadKarurSample.innerText = "📥 Load Karur Board (14)";
    }
  });

  btnSendMorningDocket.addEventListener("click", async () => {
    const selected = causeListDatePicker.value;
    btnSendMorningDocket.disabled = true;
    btnSendMorningDocket.innerText = "⏳ Generating...";
    try {
      const res = await fetch("/api/cause-list/generate-whatsapp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date: selected })
      });
      const data = await res.json();
      if (data.text) {
        const url = `https://wa.me/${(currentAdvocateSettings.lawyer_phone || '').replace(/[^0-9]/g, '')}?text=${encodeURIComponent(data.text)}`;
        window.open(url, "_blank");
      }
    } catch (e) {
      alert("Failed to generate WhatsApp Docket: " + e.message);
    } finally {
      btnSendMorningDocket.disabled = false;
      btnSendMorningDocket.innerText = "📲 WhatsApp Daily Docket";
    }
  });

  async function loadDailyCauseList(targetDate = "") {
    const dateQuery = targetDate || causeListDatePicker.value || "";
    causeListContainer.innerHTML = `<p class="empty-state">Loading court hearing board for ${dateQuery || 'all dates'}...</p>`;
    try {
      const res = await fetch(`/api/cause-list?date=${dateQuery}`);
      const data = await res.json();

      statBoardCount.innerText = data.total_hearings || 0;

      // Render Court Summary Chips
      if (data.court_summaries && data.court_summaries.length > 0) {
        courtSummaryChips.innerHTML = data.court_summaries.map(court => `
          <div class="court-chip">
            <span class="court-chip-name" title="${escapeHtml(court.court_name)}">${escapeHtml(court.court_name)}</span>
            <span class="court-chip-count">${court.hearings_count}</span>
          </div>
        `).join("");
      } else {
        courtSummaryChips.innerHTML = "";
      }

      if (!data.court_summaries || data.court_summaries.length === 0) {
        causeListContainer.innerHTML = `
          <div class="empty-state">
            <p>No hearings found for <strong>${escapeHtml(data.target_date)}</strong>.</p>
            <button class="btn btn-secondary" style="margin-top: 10px;" onclick="document.getElementById('btn-load-karur-sample').click()">
              📥 Click to Load Karur Sample (14 Hearings)
            </button>
          </div>
        `;
        return;
      }

      causeListContainer.innerHTML = data.court_summaries.map(court => `
        <div class="court-board-card">
          <div class="court-board-title">
            <span style="font-weight: 800; font-size: 1rem; color: #fff;">🏛️ ${escapeHtml(court.court_name)}</span>
            <span class="badge-subtle">${court.hearings_count} Cases Confirmed</span>
          </div>
          <div>
            ${court.cases.map(c => `
              <div class="hearing-item-card">
                <div>
                  <div class="data-label" style="font-size: 0.68rem;">ITEM NO</div>
                  <div class="item-badge">${escapeHtml(c.item_number || '-')}</div>
                </div>
                <div>
                  <div class="data-label" style="font-size: 0.68rem;">COURT ROOM</div>
                  <div style="font-weight: 700; color: #fff;">${escapeHtml(c.court_room || 'Room -')}</div>
                  <div style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);">${escapeHtml(c.case_number_formatted || c.cnr_number)}</div>
                </div>
                <div>
                  <div style="font-weight: 700; font-size: 0.95rem; color: #fff;">${escapeHtml(c.case_title)}</div>
                  <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 2px;">
                    👤 Client: <strong>${escapeHtml(c.client_name || 'Client')}</strong> (${escapeHtml(c.client_phone || '-')})
                    ${c.litigant_role ? `&bull; <span style="color: var(--accent-blue); font-size: 0.75rem;">${escapeHtml(c.litigant_role)}</span>` : ''}
                    ${c.notes ? `&bull; <span style="color: var(--accent-amber);">📝 ${escapeHtml(c.notes)}</span>` : ''}
                  </div>
                  ${c.judge_name ? `<div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;">⚖️ Presiding: ${escapeHtml(c.judge_name)}</div>` : ''}
                </div>
                <div style="text-align: right;">
                  <span class="stage-badge">${escapeHtml(c.case_stage || 'Evidence')}</span>
                  <div style="margin-top: 6px;">
                    <a href="https://wa.me/${(c.client_phone || '').replace(/[^0-9]/g, '')}?text=${encodeURIComponent(formatWhatsAppText(c, c.client_name, c.notes))}" target="_blank" class="btn btn-whatsapp" style="padding: 4px 8px; font-size: 0.72rem; display: inline-flex;">
                      💬 Alert Client
                    </a>
                  </div>
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `).join("");

    } catch (e) {
      causeListContainer.innerHTML = `<p class="empty-state" style="color: var(--accent-rose);">Failed to load cause list: ${e.message}</p>`;
    }
  }

  // Load Advocate Settings
  async function loadAdvocateSettings() {
    try {
      const res = await fetch("/api/advocate-settings");
      const settings = await res.json();
      currentAdvocateSettings = settings || {};
      if (settings.firm_name) {
        headerFirmName.innerText = `⚖️ ${settings.firm_name}`;
        settingFirmName.value = settings.firm_name;
      }
      settingLawyerName.value = settings.lawyer_name || "";
      settingLawyerPhone.value = settings.lawyer_phone || "";
      settingFooter.value = settings.default_whatsapp_footer || "";
    } catch (e) {}
  }

  // Save Advocate Settings
  settingsForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      firm_name: settingFirmName.value.trim(),
      lawyer_name: settingLawyerName.value.trim(),
      lawyer_phone: settingLawyerPhone.value.trim(),
      default_whatsapp_footer: settingFooter.value.trim()
    };
    const newKey = apiKeyInput.value.trim();

    try {
      await fetch("/api/advocate-settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (newKey) {
        await fetch("/api/save-key", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ api_key: newKey })
        });
      }

      alert("✅ Advocate Firm settings updated successfully!");
      settingsModal.style.display = "none";
      loadAdvocateSettings();
      checkKeyStatus();
      loadDailyCauseList();
      loadTrackedCases();
    } catch (err) {
      alert("Failed to save settings: " + err.message);
    }
  });

  btnOpenSettings.addEventListener("click", () => settingsModal.style.display = "flex");
  btnCloseSettings.addEventListener("click", () => settingsModal.style.display = "none");
  btnCancelSettings.addEventListener("click", () => settingsModal.style.display = "none");

  // API Key Check
  async function checkKeyStatus() {
    try {
      const res = await fetch("/api/key-status");
      const data = await res.json();
      if (data.configured) {
        apiStatusText.innerText = `API Active (${data.masked_key})`;
        apiKeyInput.value = data.full_key || "";
        statusDot.style.backgroundColor = "var(--accent-emerald)";
      } else {
        apiStatusText.innerText = "Demo Mode (No API Key)";
        statusDot.style.backgroundColor = "var(--accent-amber)";
      }
    } catch (e) {}
  }

  // Handle Client Intake & Case Verification Form Submit
  caseForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const cnr = cnrInput.value.trim().toUpperCase();
    const name = clientNameInput.value.trim();
    const role = litigantRoleInput ? litigantRoleInput.value : "Petitioner / Complainant";
    const phone = clientPhoneInput.value.trim();
    const email = clientEmailInput ? clientEmailInput.value.trim() : "";
    const caseNumber = caseNumberInput ? caseNumberInput.value.trim() : "";
    const caseStage = caseStageInput ? caseStageInput.value.trim() : "";
    const courtRoom = courtRoomInput ? courtRoomInput.value.trim() : "";
    const itemNumber = itemNumberInput ? itemNumberInput.value.trim() : "";
    const notes = caseNotesInput.value.trim();
    const forceLive = forceLiveToggle.checked;

    if (!cnr) return;

    btnFetch.disabled = true;
    btnFetch.innerText = forceLive ? "⚡ Live Querying eCourts (1.5 credits)..." : "⚡ Verifying Case...";
    caseResultContent.innerHTML = `
      <div class="empty-state">
        <p>Verifying judicial records for CNR <code>${cnr}</code> & enrolling client <strong>${escapeHtml(name)}</strong>...</p>
      </div>
    `;

    try {
      const response = await fetch("/api/check-case", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cnr,
          client_name: name,
          client_phone: phone,
          client_email: email,
          litigant_role: role,
          case_number_formatted: caseNumber,
          case_stage: caseStage,
          court_room: courtRoom,
          item_number: itemNumber,
          notes: notes,
          force_live: forceLive,
          track_next_hearing: ruleTrackHearing.checked,
          track_orders: ruleTrackOrders.checked,
          track_case_status: ruleTrackStatus.checked,
          auto_whatsapp_enabled: ruleAutoWa.checked
        })
      });

      const data = await response.json();
      renderCaseResult(data, name, phone, notes, role, email);
      loadTrackedCases();
      loadHistoryLogsCount();
      loadDailyCauseList();
    } catch (err) {
      caseResultContent.innerHTML = `
        <div class="empty-state" style="color: var(--accent-rose);">
          <p>Failed to verify case: ${err.message}</p>
        </div>
      `;
    } finally {
      btnFetch.disabled = false;
      btnFetch.innerText = "⚡ Check & Verify Case Now";
    }
  });

  // Demo Case Button (Loads Karur Client)
  btnDemo.addEventListener("click", () => {
    cnrInput.value = "TNKR060000692024";
    clientNameInput.value = "Shobika Impex Private LTD";
    if (litigantRoleInput) litigantRoleInput.value = "Financial Institution / Bank";
    clientPhoneInput.value = "+919843011223";
    if (clientEmailInput) clientEmailInput.value = "accounts@shobikaimpex.com";
    if (caseNumberInput) caseNumberInput.value = "COS/69/2024";
    if (caseStageInput) caseStageInput.value = "Evidence";
    if (courtRoomInput) courtRoomInput.value = "Room 3";
    if (itemNumberInput) itemNumberInput.value = "1";
    caseNotesInput.value = "Commercial dispute trial & evidence documents marking";
    caseForm.dispatchEvent(new Event("submit"));
  });

  // Clear Form Handler
  if (btnClearForm) {

    btnClearForm.addEventListener("click", () => {
      caseForm.reset();
      cnrInput.value = "";
      clientNameInput.value = "";
      clientPhoneInput.value = "";
      if (clientEmailInput) clientEmailInput.value = "";
      if (caseNumberInput) caseNumberInput.value = "";
      if (caseStageInput) caseStageInput.value = "";
      if (courtRoomInput) courtRoomInput.value = "";
      if (itemNumberInput) itemNumberInput.value = "";
      caseNotesInput.value = "";
      caseResultContent.innerHTML = `
        <div class="empty-state">
          <p>Form cleared. Enter new client details on the left to verify a new case.</p>
        </div>
      `;
    });
  }

  // Clear All Cases & Reset Database Handler
  if (btnClearAll) {
    btnClearAll.addEventListener("click", async () => {
      if (!confirm("⚠️ Are you sure you want to delete ALL stored cases and history logs? This will reset the database to a clean state.")) {
        return;
      }
      try {
        const res = await fetch("/api/cases/clear-all", { method: "POST" });
        const data = await res.json();
        alert("✅ " + data.message);
        loadTrackedCases();
        loadHistoryLogsCount();
        loadDailyCauseList();
      } catch (e) {
        alert("Failed to clear database: " + e.message);
      }
    });
  }


  // Smart Schedule Sync Button (Hearing-Near vs Hearing-Far Optimizer)
  if (btnSmartSync) {
    btnSmartSync.addEventListener("click", async () => {
      btnSmartSync.disabled = true;
      btnSmartSync.innerText = "⚡ Running Smart Scheduler...";
      try {
        const res = await fetch("/api/scheduler/smart-sync", { method: "POST" });
        const data = await res.json();
        alert(`🎯 Smart Predictive Sync Complete!\n• Total Portfolio: ${data.total_portfolio}\n• 💤 Sleeping Cases (Far Away / Disposed): ${data.sleeping_cases + data.disposed_cases}\n• ⚡ Active Checked (Hearing Near): ${data.checked_cases}\n• 🛡️ Credits Saved this Run: ${data.credits_saved_this_run} credits\n• Date Shifts Detected: ${data.date_changes_count}`);
        loadTrackedCases();
        loadHistoryLogsCount();
        loadDailyCauseList();
      } catch (e) {
        alert("Smart Sync failed: " + e.message);
      } finally {
        btnSmartSync.disabled = false;
        btnSmartSync.innerText = "⚡ Smart Scheduler Sync (Save Credits)";
      }
    });
  }

  // Scheduler Monitor Modal Trigger
  if (btnOpenSchedulerMonitor) {
    btnOpenSchedulerMonitor.addEventListener("click", openSchedulerMonitorModal);
  }
  if (btnCloseScheduler) {
    btnCloseScheduler.addEventListener("click", () => schedulerModal.style.display = "none");
  }

  async function openSchedulerMonitorModal() {
    schedulerModal.style.display = "flex";
    schedulerSummaryBanner.innerHTML = `<p class="empty-state">Evaluating cases with Smart Scheduler...</p>`;
    schedulerEvaluationsList.innerHTML = "";

    try {
      const res = await fetch("/api/scheduler/evaluation");
      const data = await res.json();

      schedulerSummaryBanner.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; text-align: center;">
          <div>
            <div class="data-label">Total Cases</div>
            <div style="font-size: 1.3rem; font-weight: 800; color: #fff;">${data.total_cases}</div>
          </div>
          <div>
            <div class="data-label">💤 Sleeping (Far Away)</div>
            <div style="font-size: 1.3rem; font-weight: 800; color: var(--accent-blue);">${data.sleeping_cases}</div>
          </div>
          <div>
            <div class="data-label">⚡ Checking Today</div>
            <div style="font-size: 1.3rem; font-weight: 800; color: var(--accent-emerald);">${data.due_cases}</div>
          </div>
          <div>
            <div class="data-label">🛡️ Credits Saved Today</div>
            <div style="font-size: 1.3rem; font-weight: 800; color: var(--accent-emerald);">${data.credits_saved_today} Credits</div>
          </div>
        </div>
      `;

      schedulerEvaluationsList.innerHTML = (data.evaluations || []).map(ev => `
        <div class="history-item" style="border-left: 4px solid ${ev.should_check ? 'var(--accent-emerald)' : 'var(--border-color)'};">
          <div class="history-item-header">
            <span><strong>${escapeHtml(ev.case_title || 'Case')}</strong> &bull; <code style="color: var(--accent-blue);">${escapeHtml(ev.cnr)}</code></span>
            <span style="font-weight: 700; color: ${ev.should_check ? 'var(--accent-emerald)' : 'var(--text-muted)'};">
              ${ev.should_check ? '⚡ Active Query (1.5 Cr)' : '💤 Sleeping (0 Cr)'}
            </span>
          </div>
          <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 4px;">
            <span>Client: ${escapeHtml(ev.client_name || 'Client')} &bull; Next Hearing: <strong>${escapeHtml(ev.next_hearing_date || 'N/A')}</strong></span>
          </div>
          <div style="font-size: 0.8rem; color: var(--accent-blue); margin-top: 4px;">
            Decision Reason: ${escapeHtml(ev.reason)}
          </div>
        </div>
      `).join("");

    } catch (e) {
      schedulerSummaryBanner.innerHTML = `<p class="empty-state" style="color: var(--accent-rose);">Failed to evaluate scheduler: ${e.message}</p>`;
    }
  }

  // Live Filter Handler
  if (filterInput) {
    filterInput.addEventListener("input", (e) => {
      const term = e.target.value.toLowerCase();
      const filtered = allTrackedCases.filter(c => 
        (c.cnr_number || "").toLowerCase().includes(term) ||
        (c.case_title || "").toLowerCase().includes(term) ||
        (c.court_name || "").toLowerCase().includes(term) ||
        (c.client_name || "").toLowerCase().includes(term) ||
        (c.litigant_role || "").toLowerCase().includes(term) ||
        (c.case_stage || "").toLowerCase().includes(term) ||
        (c.case_number_formatted || "").toLowerCase().includes(term) ||
        (c.notes || "").toLowerCase().includes(term)
      );
      renderTableRows(filtered);
    });
  }

  // History Modal Triggers
  btnOpenHistory.addEventListener("click", openHistoryModal);
  if (cardHistoryStat) {
    cardHistoryStat.addEventListener("click", openHistoryModal);
  }
  btnCloseHistory.addEventListener("click", () => historyModal.style.display = "none");
  window.addEventListener("click", (e) => {
    if (e.target === historyModal) historyModal.style.display = "none";
    if (e.target === settingsModal) settingsModal.style.display = "none";
    if (e.target === rulesModal) rulesModal.style.display = "none";
    if (e.target === schedulerModal) schedulerModal.style.display = "none";
  });

  async function openHistoryModal() {
    historyModal.style.display = "flex";
    historyLogsContent.innerHTML = `<p class="empty-state">Fetching audit history logs...</p>`;
    try {
      const res = await fetch("/api/history");
      const logs = await res.json();
      if (!logs || logs.length === 0) {
        historyLogsContent.innerHTML = `<p class="empty-state">No hearing date changes detected yet. The background worker logs all shifts automatically.</p>`;
        return;
      }
      historyLogsContent.innerHTML = logs.map(l => `
        <div class="history-item">
          <div class="history-item-header">
            <span><strong>CNR:</strong> <code style="color: var(--accent-blue);">${escapeHtml(l.cnr_number)}</code> (${escapeHtml(l.case_title || 'Case')})</span>
            <span>⏱️ ${escapeHtml(l.detected_at)}</span>
          </div>
          <div class="history-shift">
            <span style="color: var(--text-muted); text-decoration: line-through;">${escapeHtml(l.previous_hearing_date || 'None')}</span>
            <span>➡️</span>
            <span style="color: var(--accent-emerald); font-size: 1.1rem;">${escapeHtml(l.new_hearing_date || 'Awaiting Date')}</span>
          </div>
          <div style="margin-top: 6px; font-size: 0.8rem; color: var(--text-secondary); display: flex; justify-content: space-between; align-items: center;">
            <span>Client: ${escapeHtml(l.client_name || 'N/A')} (${escapeHtml(l.client_phone || 'N/A')})</span>
            <span style="color: ${l.notified ? 'var(--accent-emerald)' : 'var(--accent-amber)'}; font-weight: 600;">
              ${l.notified ? '✓ Notification Dispatched' : '⏳ Ready for Dispatch'}
            </span>
          </div>
        </div>
      `).join("");
    } catch (e) {
      historyLogsContent.innerHTML = `<p class="empty-state" style="color: var(--accent-rose);">Error loading history: ${e.message}</p>`;
    }
  }

  async function loadHistoryLogsCount() {
    try {
      const res = await fetch("/api/history");
      const logs = await res.json();
      const count = logs ? logs.length : 0;
      historyCount.innerText = count;
      statDateChanges.innerText = count;
    } catch (e) {}
  }

  // Render Verification Result Function
  function renderCaseResult(data, clientName, phone, notes, role = "", email = "") {
    if (!data.success && data.error) {
      caseResultContent.innerHTML = `
        <div class="empty-state" style="color: var(--accent-rose);">
          <p><strong>[${data.error_type || 'API Notice'}]</strong> ${data.error}</p>
        </div>
      `;
      cacheBadge.style.display = "none";
      return;
    }

    const c = data.case_data || data;
    const isCached = data.is_cached;
    cacheBadge.style.display = isCached ? "inline-block" : "none";

    const statusClass = (c.case_status || "").toLowerCase().includes("dispose") ? "tag-disposed" : "tag-pending";
    const nextDate = c.next_hearing_date || "Not Scheduled / Disposed";
    const waText = formatWhatsAppText(c, clientName, notes);
    const cleanPhone = (phone || "").replace(/[^0-9]/g, "");
    const waLink = `https://wa.me/${cleanPhone}?text=${encodeURIComponent(waText)}`;

    caseResultContent.innerHTML = `
      <div class="case-header">
        <div>
          <div class="case-name">${escapeHtml(c.case_title || 'Case Title')}</div>
          <span class="case-cnr-badge">${escapeHtml(c.cnr_number)}</span>
          ${role ? `<span class="badge-subtle" style="margin-left: 6px;">${escapeHtml(role)}</span>` : ''}
        </div>
        <span class="tag ${statusClass}">${escapeHtml(c.case_status || 'PENDING')}</span>
      </div>

      <div class="hearing-box">
        <div>
          <div class="data-label">Next Scheduled Hearing Date</div>
          <div class="hearing-date">${escapeHtml(nextDate)}</div>
        </div>
        <div style="text-align: right;">
          <div class="data-label">Verification Status</div>
          <div style="font-weight: 800; font-size: 1rem; color: var(--accent-emerald);">✓ Record Verified</div>
        </div>
      </div>

      <div class="data-grid">
        <div class="data-item">
          <div class="data-label">Court & District</div>
          <div class="data-val">${escapeHtml(c.court_name || 'District Court')}</div>
        </div>
        <div class="data-item">
          <div class="data-label">Enrolled Client</div>
          <div class="data-val">${escapeHtml(clientName || 'Client')} (${escapeHtml(phone || '-')})</div>
        </div>
      </div>

      ${c.latest_order_date ? `
      <div class="data-item" style="margin-bottom: 14px; border-color: rgba(56, 189, 248, 0.3);">
        <div class="data-label">📜 Latest Court Order Passed</div>
        <div class="data-val" style="color: var(--accent-blue);">Order Date: ${escapeHtml(c.latest_order_date)} ${c.latest_order_pdf ? `&bull; <a href="${c.latest_order_pdf}" target="_blank" style="color: var(--accent-emerald);">Download Order PDF</a>` : ''}</div>
      </div>
      ` : ''}

      <div class="whatsapp-card">
        <div style="font-size: 0.8rem; font-weight: 600; color: #8696a0; margin-bottom: 8px; display: flex; justify-content: space-between;">
          <span>💬 Automated Client WhatsApp Notice:</span>
          <span>Target: <strong>${escapeHtml(phone || '')}</strong></span>
        </div>
        <div class="whatsapp-bubble">${escapeHtml(waText)}</div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <a href="${waLink}" target="_blank" class="btn btn-whatsapp" style="flex: 1;">
            📲 Dispatch Notice to Client WhatsApp
          </a>
          <a href="/api/export-case/${encodeURIComponent(c.cnr_number)}" target="_blank" class="btn btn-secondary" style="flex: none; padding: 10px 16px;">
            🖨️ Print Intake Brief
          </a>
        </div>
      </div>
    `;
  }

  // Load Database Tracked Cases
  async function loadTrackedCases() {
    try {
      const res = await fetch("/api/cases");
      const cases = await res.json();
      allTrackedCases = cases || [];
      casesCount.innerText = allTrackedCases.length;
      statTotalCases.innerText = allTrackedCases.length;

      renderTableRows(allTrackedCases);
    } catch (e) {
      console.error(e);
    }
  }

  function renderTableRows(cases) {
    if (!cases || cases.length === 0) {
      casesTbody.innerHTML = `
        <tr>
          <td colspan="8" class="empty-state">No matching client cases found in database.</td>
        </tr>
      `;
      return;
    }

    casesTbody.innerHTML = cases.map(item => `
      <tr>
        <td>
          <strong>${escapeHtml(item.client_name || 'Litigant')}</strong>
          ${item.litigant_role ? `<div style="font-size: 0.72rem; color: var(--accent-blue); font-weight: 600;">${escapeHtml(item.litigant_role)}</div>` : ''}
          <div style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(item.client_phone || '-')}</div>
        </td>
        <td>
          <span class="item-badge" style="font-size: 0.85rem; padding: 2px 6px;">#${escapeHtml(item.item_number || '-')}</span>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;">${escapeHtml(item.court_room || '-')}</div>
        </td>
        <td>
          <div style="font-weight: 700; color: #fff;">${escapeHtml(item.case_number_formatted || '-')}</div>
          <code style="color: var(--accent-blue); font-family: var(--font-mono); font-size: 0.75rem;">${escapeHtml(item.cnr_number)}</code>
        </td>
        <td>
          <div style="font-weight: 600;">${escapeHtml(item.case_title || 'N/A')}</div>
          <div style="font-size: 0.78rem; color: var(--text-secondary);">${escapeHtml(item.court_name || 'District Court')}</div>
        </td>
        <td><span class="stage-badge">${escapeHtml(item.case_stage || 'Evidence')}</span></td>
        <td style="font-weight: 700; color: var(--accent-blue);">${escapeHtml(item.next_hearing_date || 'N/A')}</td>
        <td>
          <div>
            ${item.track_next_hearing ? '<span class="rule-chip">📅 Date</span>' : ''}
            ${item.track_orders ? '<span class="rule-chip">📜 Orders</span>' : ''}
            ${item.auto_whatsapp_enabled ? '<span class="rule-chip" style="color: var(--accent-emerald);">💬 WA</span>' : ''}
          </div>
        </td>
        <td>
          <div class="action-btn-group">
            <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;" onclick="recheckCase('${item.cnr_number}')" title="Recheck Case (Cached/Free)">
              ⚡ Check
            </button>
            <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;" onclick="openEditRulesModal('${item.cnr_number}')" title="Edit Case Details & Rules">
              ⚙️
            </button>
            <a href="/api/export-case/${encodeURIComponent(item.cnr_number)}" target="_blank" class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;" title="Print / PDF Brief">
              🖨️
            </a>
            <button class="btn btn-danger" style="padding: 4px 8px; font-size: 0.75rem;" onclick="deleteTrackedCase('${item.cnr_number}')" title="Remove Case">
              🗑️
            </button>
          </div>
        </td>
      </tr>
    `).join("");
  }

  window.recheckCase = (cnr) => {
    const item = allTrackedCases.find(c => c.cnr_number === cnr);
    cnrInput.value = cnr;
    if (item) {
      clientNameInput.value = item.client_name || "";
      if (litigantRoleInput) litigantRoleInput.value = item.litigant_role || "Petitioner / Complainant";
      clientPhoneInput.value = item.client_phone || "";
      if (clientEmailInput) clientEmailInput.value = item.client_email || "";
      if (caseNumberInput) caseNumberInput.value = item.case_number_formatted || "";
      if (caseStageInput) caseStageInput.value = item.case_stage || "";
      if (courtRoomInput) courtRoomInput.value = item.court_room || "";
      if (itemNumberInput) itemNumberInput.value = item.item_number || "";
      caseNotesInput.value = item.notes || "";
    }
    // Switch to Add Client tab
    document.querySelector('.nav-tab[data-tab="tab-add-client"]').click();
    caseForm.dispatchEvent(new Event("submit"));
  };

  // Edit Rules Modal
  window.openEditRulesModal = (cnr) => {
    const item = allTrackedCases.find(c => c.cnr_number === cnr);
    if (!item) return;

    editRuleCnr.value = cnr;
    editClientName.value = item.client_name || "";
    editClientPhone.value = item.client_phone || "";
    editRoom.value = item.court_room || "";
    editItem.value = item.item_number || "";
    editStage.value = item.case_stage || "";
    editJudge.value = item.judge_name || "";
    editNotes.value = item.notes || "";
    editRuleHearing.checked = Boolean(item.track_next_hearing);
    editRuleOrders.checked = Boolean(item.track_orders);
    editRuleStatus.checked = Boolean(item.track_case_status);
    editRuleWa.checked = Boolean(item.auto_whatsapp_enabled);

    rulesModal.style.display = "flex";
  };

  rulesForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const cnr = editRuleCnr.value;
    const payload = {
      client_name: editClientName.value.trim(),
      client_phone: editClientPhone.value.trim(),
      court_room: editRoom.value.trim(),
      item_number: editItem.value.trim(),
      case_stage: editStage.value.trim(),
      judge_name: editJudge.value.trim(),
      notes: editNotes.value.trim(),
      track_next_hearing: editRuleHearing.checked,
      track_orders: editRuleOrders.checked,
      track_case_status: editRuleStatus.checked,
      auto_whatsapp_enabled: editRuleWa.checked
    };

    try {
      await fetch(`/api/cases/${encodeURIComponent(cnr)}/preferences`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      rulesModal.style.display = "none";
      loadTrackedCases();
      loadDailyCauseList();
    } catch (err) {
      alert("Failed to update case details: " + err.message);
    }
  });

  btnCloseRules.addEventListener("click", () => rulesModal.style.display = "none");
  btnCancelRules.addEventListener("click", () => rulesModal.style.display = "none");

  window.deleteTrackedCase = async (cnr) => {
    if (!confirm(`Are you sure you want to remove CNR: ${cnr} from tracking?`)) return;
    try {
      const res = await fetch(`/api/cases/${encodeURIComponent(cnr)}`, { method: "DELETE" });
      const data = await res.json();
      if (data.success) {
        loadTrackedCases();
        loadHistoryLogsCount();
        loadDailyCauseList();
      }
    } catch (e) {
      alert("Failed to delete case: " + e.message);
    }
  };

  function formatWhatsAppText(c, clientName, notes) {
    const firm = currentAdvocateSettings.firm_name || "Advocate Chambers";
    const lawyer = currentAdvocateSettings.lawyer_name || "Senior Advocate";
    const footer = currentAdvocateSettings.default_whatsapp_footer || "Sent on behalf of Advocate Office.";

    return `⚖️ *${firm.toUpperCase()}*
*HEARING UPDATE NOTICE*
---------------------------------------
Dear *${clientName || 'Client'}*,

Your court matter details have been updated:
• *Case:* ${c.case_title || 'Case Matter'}
• *Court:* ${c.court_name || 'Court'}
• *Item No:* ${c.item_number || '-'} (${c.court_room || '-'})
• *Stage:* *${c.case_stage || 'Evidence'}*
• *Next Hearing Date:* *${c.next_hearing_date || 'Awaiting Schedule / Disposed'}*
${c.notes ? `• *Advocate Note:* ${c.notes}` : ''}
---------------------------------------
${footer}
*Advocate:* ${lawyer}`;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
});
