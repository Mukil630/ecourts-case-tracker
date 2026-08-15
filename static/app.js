/**
 * R. ANBAIYA & ASSOCIATES • Advocates & Legal Consultants
 * eCourts Automation & Case Management Platform
 * Complete Multi-Module Frontend Controller
 */

document.addEventListener("DOMContentLoaded", () => {
  // Global State
  let allCases = [];
  let causeListData = null;
  let currentAdvocateSettings = {};
  let selectedCourtFilter = "ALL";
  let currentCalendarDate = new Date();

  // Navigation & Core Elements
  const navItems = document.querySelectorAll(".nav-item[data-view]");
  const viewSections = document.querySelectorAll(".view-section");
  const dashboardDatePicker = document.getElementById("dashboard-date-picker");
  const hearingBoardListContainer = document.getElementById("hearing-board-list-container");
  const fullHearingsContainer = document.getElementById("full-hearings-container");
  const allCasesTbody = document.getElementById("all-cases-tbody");
  const allCasesSearch = document.getElementById("all-cases-search");
  const clientsTbody = document.getElementById("clients-tbody");
  const clientSearchInput = document.getElementById("client-search-input");
  const whatsappDocketsList = document.getElementById("whatsapp-dockets-list");
  const alertsAuditList = document.getElementById("alerts-audit-list");

  // KPI Elements
  const kpiTodayHearings = document.getElementById("kpi-today-hearings");
  const kpiTodayHearingsSub = document.getElementById("kpi-today-hearings-sub");
  const kpiActiveCases = document.getElementById("kpi-active-cases");
  const kpiUpcoming7d = document.getElementById("kpi-upcoming-7d");
  const kpiDisposedCases = document.getElementById("kpi-disposed-cases");
  const badgeTodayHearings = document.getElementById("badge-today-hearings");
  const badgeTotalCases = document.getElementById("badge-total-cases");
  const badgeAlertsCount = document.getElementById("badge-alerts-count");

  // Case Intake Wizard Elements
  const caseIntakeModal = document.getElementById("case-intake-modal");
  const btnNavCaseIntake = document.getElementById("btn-nav-case-intake");
  const btnCloseIntakeModal = document.getElementById("btn-close-intake-modal");
  const wizardForm = document.getElementById("wizard-form");
  const wizClientName = document.getElementById("wiz-client-name");
  const wizLitigantRole = document.getElementById("wiz-litigant-role");
  const wizClientPhone = document.getElementById("wiz-client-phone");
  const wizClientEmail = document.getElementById("wiz-client-email");
  const wizCnr = document.getElementById("wiz-cnr");
  const wizCaseNo = document.getElementById("wiz-case-no");
  const wizStage = document.getElementById("wiz-stage");
  const wizRoom = document.getElementById("wiz-room");
  const wizItem = document.getElementById("wiz-item");
  const wizNotes = document.getElementById("wiz-notes");
  const intakeVerificationPreview = document.getElementById("intake-verification-preview");

  // Calendar Elements
  const calendarMonthTitle = document.getElementById("calendar-month-title");
  const calendarGridContainer = document.getElementById("calendar-grid-container");
  const btnPrevMonth = document.getElementById("btn-prev-month");
  const btnNextMonth = document.getElementById("btn-next-month");
  const calendarSelectedDayHeading = document.getElementById("calendar-selected-day-heading");
  const calendarSelectedDayList = document.getElementById("calendar-selected-day-list");

  // Settings Elements
  const firmSettingsForm = document.getElementById("firm-settings-form");
  const cfgFirmName = document.getElementById("cfg-firm-name");
  const cfgLawyerName = document.getElementById("cfg-lawyer-name");
  const cfgLawyerPhone = document.getElementById("cfg-lawyer-phone");
  const cfgFooter = document.getElementById("cfg-footer");
  const cfgApiKey = document.getElementById("cfg-api-key");

  // Initialize Application
  initNavigation();
  loadAdvocateSettings();
  const initialDate = dashboardDatePicker ? dashboardDatePicker.value : "2026-08-14";
  loadDailyCauseList(initialDate);
  loadTrackedCases();
  loadAlertsAudit();
  renderCalendar(currentCalendarDate);

  // =========================================================================
  // 1. NAVIGATION & ROUTING
  // =========================================================================
  function initNavigation() {
    navItems.forEach(item => {
      item.addEventListener("click", () => {
        const targetViewId = item.getAttribute("data-view");
        switchView(targetViewId);
      });
    });

    if (btnNavCaseIntake) {
      btnNavCaseIntake.addEventListener("click", openCaseIntakeModal);
    }
    if (btnCloseIntakeModal) {
      btnCloseIntakeModal.addEventListener("click", () => caseIntakeModal.style.display = "none");
    }
  }

  window.switchView = (viewId) => {
    navItems.forEach(item => {
      if (item.getAttribute("data-view") === viewId) {
        item.classList.add("active");
      } else {
        item.classList.remove("active");
      }
    });

    viewSections.forEach(sec => {
      if (sec.id === viewId) {
        sec.classList.add("active");
      } else {
        sec.classList.remove("active");
      }
    });

    if (viewId === "view-hearings") renderFullHearingsView();
    if (viewId === "view-cases") renderAllCasesTable(allCases);
    if (viewId === "view-clients") renderClientsTable(allCases);
    if (viewId === "view-whatsapp") renderWhatsAppDockets(allCases);
    if (viewId === "view-calendar") renderCalendar(currentCalendarDate);
    if (viewId === "view-reports") updateReportsView();
    if (viewId === "view-alerts") loadAlertsAudit();
  };

  // =========================================================================
  // 2. DASHBOARD & TODAY'S HEARINGS CAUSE LIST
  // =========================================================================
  if (dashboardDatePicker) {
    dashboardDatePicker.addEventListener("change", () => {
      const selected = dashboardDatePicker.value;
      const printLink = document.getElementById("btn-print-docket-link");
      if (printLink) printLink.href = `/api/export-cause-list?date=${selected}`;
      loadDailyCauseList(selected);
    });
  }

  const btnMorningDocket = document.getElementById("btn-generate-morning-docket");
  if (btnMorningDocket) {
    btnMorningDocket.addEventListener("click", generateMorningDocket);
  }

  const btnDispatchAllDockets = document.getElementById("btn-dispatch-all-dockets");
  if (btnDispatchAllDockets) {
    btnDispatchAllDockets.addEventListener("click", generateMorningDocket);
  }

  async function generateMorningDocket() {
    const targetDate = dashboardDatePicker ? dashboardDatePicker.value : "2026-08-14";
    try {
      const res = await fetch("/api/cause-list/generate-whatsapp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date: targetDate })
      });
      const data = await res.json();
      if (data.text) {
        const rawPhone = currentAdvocateSettings.lawyer_phone || "+919842112233";
        const cleanPhone = rawPhone.replace(/[^0-9]/g, "");
        const waUrl = `https://wa.me/${cleanPhone}?text=${encodeURIComponent(data.text)}`;
        window.open(waUrl, "_blank");
      }
    } catch (e) {
      alert("Failed to generate WhatsApp Docket: " + e.message);
    }
  }

  async function loadDailyCauseList(targetDate = "2026-08-14") {
    if (hearingBoardListContainer) {
      hearingBoardListContainer.innerHTML = `<p style="padding: 24px; text-align: center; color: var(--text-muted);">Loading Daily Court Hearing Board for ${targetDate}...</p>`;
    }
    try {
      const res = await fetch(`/api/cause-list?date=${targetDate}`);
      const data = await res.json();
      causeListData = data;

      const count = data.total_hearings || 0;
      const courtsCount = data.total_courts || 0;

      if (kpiTodayHearings) kpiTodayHearings.innerText = count;
      if (badgeTodayHearings) badgeTodayHearings.innerText = count;
      if (kpiTodayHearingsSub) {
        kpiTodayHearingsSub.innerText = count > 0 ? `Across ${courtsCount} Court${courtsCount > 1 ? 's' : ''}` : "No hearings today";
      }

      renderHearingBoard(data, selectedCourtFilter);
      setupCourtChips(data);
    } catch (e) {
      if (hearingBoardListContainer) {
        hearingBoardListContainer.innerHTML = `<p style="padding: 24px; color: var(--danger);">Failed to load hearing board: ${e.message}</p>`;
      }
    }
  }

  function setupCourtChips(data) {
    const chipsRow = document.getElementById("court-chips-row");
    if (!chipsRow) return;

    const summaries = data.court_summaries || [];
    chipsRow.innerHTML = `
      <button class="court-chip-btn ${selectedCourtFilter === 'ALL' ? 'active' : ''}" data-court="ALL">
        All Courts <span class="chip-count">${data.total_hearings || 0}</span>
      </button>
      ${summaries.map(c => `
        <button class="court-chip-btn ${selectedCourtFilter === c.court_name ? 'active' : ''}" data-court="${escapeHtml(c.court_name)}">
          ${escapeHtml(c.court_name.replace(' Court, Karur', '').replace(' at Magisterial Level', ''))}
          <span class="chip-count">${c.hearings_count}</span>
        </button>
      `).join("")}
    `;

    chipsRow.querySelectorAll(".court-chip-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        chipsRow.querySelectorAll(".court-chip-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        selectedCourtFilter = btn.getAttribute("data-court");
        renderHearingBoard(causeListData, selectedCourtFilter);
      });
    });
  }

  function renderHearingBoard(data, filterCourt = "ALL") {
    if (!hearingBoardListContainer) return;
    if (!data || !data.court_summaries || data.court_summaries.length === 0) {
      hearingBoardListContainer.innerHTML = `
        <div style="padding: 36px 20px; text-align: center; color: var(--text-muted);">
          <div style="font-size: 2rem; margin-bottom: 8px;">📋</div>
          <strong style="font-size: 0.95rem; color: var(--text-main);">No Hearings Scheduled for This Date</strong>
          <p style="font-size: 0.78rem; margin-top: 4px;">You can add client cases using <strong>"+ Case Intake"</strong> in the sidebar.</p>
        </div>
      `;
      return;
    }

    let courtsToRender = data.court_summaries;
    if (filterCourt !== "ALL") {
      courtsToRender = courtsToRender.filter(c => c.court_name === filterCourt);
    }

    hearingBoardListContainer.innerHTML = courtsToRender.map(court => `
      <div class="court-group-block">
        <div class="court-group-header">
          <span>🏛️ ${escapeHtml(court.court_name)}</span>
          <span class="court-group-count">${court.hearings_count} Case${court.hearings_count > 1 ? 's' : ''}</span>
        </div>
        <div class="hearing-table-wrapper">
          <table class="hearing-table">
            <thead>
              <tr>
                <th style="width: 55px; text-align: center;">Item</th>
                <th>Case Details</th>
                <th>Client</th>
                <th>Status</th>
                <th>Court Room</th>
                <th style="text-align: right;">Actions</th>
              </tr>
            </thead>
            <tbody>
              ${court.cases.map(c => `
                <tr>
                  <td style="text-align: center;">
                    <span class="item-number-cell">${escapeHtml(c.item_number || '-')}</span>
                  </td>
                  <td>
                    <div class="case-title-bold">${escapeHtml(c.case_title)}</div>
                    <div class="case-meta-line">
                      <span class="case-no-pill">${escapeHtml(c.case_number_formatted || c.cnr_number)}</span>
                      ${c.notes ? `&bull; <span style="color: var(--warning);">${escapeHtml(c.notes)}</span>` : ''}
                    </div>
                    ${c.judge_name ? `<div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 2px;">⚖️ Presiding: ${escapeHtml(c.judge_name)}</div>` : ''}
                  </td>
                  <td>
                    <strong>${escapeHtml(c.client_name || 'Client')}</strong>
                    <div style="font-size: 0.72rem; color: var(--text-muted);">${escapeHtml(c.client_phone || '-')}</div>
                  </td>
                  <td>
                    <span class="badge ${getBadgeClass(c.case_stage)}">${escapeHtml(c.case_stage || 'Evidence')}</span>
                  </td>
                  <td>
                    <strong style="color: var(--text-main);">${escapeHtml(c.court_room || '-')}</strong>
                  </td>
                  <td style="text-align: right;">
                    <a href="${getWhatsAppUrl(c)}" target="_blank" class="btn-ui btn-ui-wa" style="padding: 4px 8px; font-size: 0.72rem;">
                      💬 WhatsApp
                    </a>
                  </td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      </div>
    `).join("");
  }

  function renderFullHearingsView() {
    if (!fullHearingsContainer || !causeListData) return;
    renderHearingBoard(causeListData, "ALL");
    fullHearingsContainer.innerHTML = hearingBoardListContainer.innerHTML;
  }

  // =========================================================================
  // 3. ALL CASES & PORTFOLIO MANAGEMENT
  // =========================================================================
  async function loadTrackedCases() {
    try {
      const res = await fetch("/api/cases");
      const data = await res.json();
      allCases = data || [];

      // Dynamic KPI updates
      const activeCasesCount = allCases.filter(c => (c.case_status || "").toUpperCase() !== "DISPOSED").length;
      const disposedCasesCount = allCases.filter(c => (c.case_status || "").toUpperCase() === "DISPOSED").length;

      if (kpiActiveCases) kpiActiveCases.innerText = activeCasesCount;
      if (badgeTotalCases) badgeTotalCases.innerText = allCases.length;
      if (kpiDisposedCases) kpiDisposedCases.innerText = disposedCasesCount;

      const todayStr = new Date().toISOString().split("T")[0];
      const future7d = new Date(Date.now() + 7 * 86400000).toISOString().split("T")[0];
      const upcoming7dCount = allCases.filter(c => c.next_hearing_date && c.next_hearing_date >= todayStr && c.next_hearing_date <= future7d).length;
      if (kpiUpcoming7d) kpiUpcoming7d.innerText = upcoming7dCount;

      renderUpcomingHearingsWidget(allCases);
      renderAlertsWidget(allCases);
      renderAllCasesTable(allCases);
      renderClientsTable(allCases);
      renderWhatsAppDockets(allCases);
      updateReportsView();
    } catch (e) {
      console.error("loadTrackedCases error:", e);
    }
  }

  function renderUpcomingHearingsWidget(cases) {
    const container = document.getElementById("upcoming-hearings-widget-list");
    if (!container) return;

    const todayStr = dashboardDatePicker ? dashboardDatePicker.value : "2026-08-14";
    const futureCases = (cases || []).filter(c => c.next_hearing_date && c.next_hearing_date > todayStr);
    
    // Sort by hearing date ascending
    futureCases.sort((a, b) => a.next_hearing_date.localeCompare(b.next_hearing_date));

    if (futureCases.length === 0) {
      container.innerHTML = `
        <div style="padding: 16px; text-align: center; color: var(--text-muted); font-size: 0.78rem;">
          No upcoming hearings scheduled. Enroll new matters using <strong>+ Case Intake</strong>.
        </div>
      `;
      return;
    }

    container.innerHTML = futureCases.slice(0, 4).map(c => {
      const parts = (c.next_hearing_date || "").split("-");
      const day = parts[2] || "15";
      const monthNum = parseInt(parts[1] || "8", 10);
      const monthNamesShort = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
      const month = monthNamesShort[monthNum - 1] || "AUG";

      return `
        <div class="upcoming-item">
          <div class="upcoming-date-box">
            <span class="upcoming-date-day">${day}</span>
            <span class="upcoming-date-month">${month}</span>
          </div>
          <div class="upcoming-details">
            <div class="upcoming-title">${escapeHtml(c.case_title)}</div>
            <div class="upcoming-meta">${escapeHtml(c.case_number_formatted || c.cnr_number)} &bull; ${escapeHtml(c.case_stage || 'Hearing')}</div>
            <div class="upcoming-court">${escapeHtml(c.court_name || '')} &bull; ${escapeHtml(c.court_room || '-')}</div>
          </div>
        </div>
      `;
    }).join("");
  }

  function renderAlertsWidget(cases) {
    const container = document.getElementById("alerts-widget-list");
    if (!container) return;

    fetch("/api/history")
      .then(res => res.json())
      .then(logs => {
        if (!logs || logs.length === 0) {
          container.innerHTML = `
            <div style="padding: 14px; text-align: center; color: var(--text-muted); font-size: 0.78rem;">
              ✓ No active judicial alerts.
            </div>
          `;
          return;
        }

        if (badgeAlertsCount) badgeAlertsCount.innerText = logs.length;

        container.innerHTML = logs.slice(0, 3).map(l => `
          <div class="alert-card-item alert-orange" style="margin-bottom: 8px; padding: 8px 10px;">
            <div class="alert-icon" style="font-size: 1rem;">⚠️</div>
            <div style="flex: 1;">
              <strong style="font-size: 0.78rem; color: #92400e;">${escapeHtml(l.details || 'Hearing Date Updated')}</strong>
              <div style="font-size: 0.7rem; color: #b45309;">CNR: ${escapeHtml(l.cnr_number)} &bull; New Date: ${escapeHtml(l.new_hearing_date)}</div>
            </div>
          </div>
        `).join("");
      })
      .catch(() => {
        container.innerHTML = `<div style="padding: 10px; color: var(--text-muted); font-size: 0.78rem;">No active judicial alerts.</div>`;
      });
  }


  if (allCasesSearch) {
    allCasesSearch.addEventListener("input", () => {
      const q = allCasesSearch.value.trim().toLowerCase();
      const filtered = allCases.filter(c => 
        (c.client_name || "").toLowerCase().includes(q) ||
        (c.case_title || "").toLowerCase().includes(q) ||
        (c.cnr_number || "").toLowerCase().includes(q) ||
        (c.case_number_formatted || "").toLowerCase().includes(q)
      );
      renderAllCasesTable(filtered);
    });
  }

  function renderAllCasesTable(cases) {
    if (!allCasesTbody) return;
    if (!cases || cases.length === 0) {
      allCasesTbody.innerHTML = `
        <tr>
          <td colspan="8" style="padding: 32px; text-align: center; color: var(--text-muted);">
            <div style="font-size: 1.8rem; margin-bottom: 6px;">📁</div>
            <strong style="color: var(--text-main);">No Cases in Portfolio</strong>
            <p style="font-size: 0.78rem; margin-top: 4px;">Click <strong>"+ Add New Case"</strong> above to register your first client matter.</p>
          </td>
        </tr>
      `;
      return;
    }

    allCasesTbody.innerHTML = cases.map(c => `
      <tr>
        <td>
          <strong>${escapeHtml(c.client_name || 'Client')}</strong>
          <div style="font-size: 0.7rem; color: var(--text-muted);">${escapeHtml(c.litigant_role || 'Litigant')}</div>
        </td>
        <td>
          <div class="case-title-bold">${escapeHtml(c.case_title)}</div>
          <div style="font-size:0.72rem; color:var(--text-muted);">${escapeHtml(c.parties || '')}</div>
        </td>
        <td><span class="case-no-pill">${escapeHtml(c.case_number_formatted || '-')}</span></td>
        <td><code style="font-family: var(--font-mono); font-size:0.75rem; color:var(--primary);">${escapeHtml(c.cnr_number)}</code></td>
        <td>${escapeHtml(c.court_name || 'District Court')}</td>
        <td><strong style="color:var(--primary);">${escapeHtml(c.next_hearing_date || 'Awaiting Date')}</strong></td>
        <td><span class="badge ${c.case_status === 'DISPOSED' ? 'badge-disposed' : 'badge-pending'}">${escapeHtml(c.case_status || 'PENDING')}</span></td>
        <td>
          <div style="display:flex; gap:6px;">
            <a href="${getWhatsAppUrl(c)}" target="_blank" class="btn-ui btn-ui-wa" style="padding:3px 6px; font-size:0.7rem;" title="Send WhatsApp">💬</a>
            <button onclick="syncSingleCase('${escapeHtml(c.cnr_number)}')" class="btn-ui btn-ui-secondary" style="padding:3px 6px; font-size:0.7rem;" title="Check Live eCourts">🔄</button>
            <a href="/api/export-case/${encodeURIComponent(c.cnr_number)}" target="_blank" class="btn-ui btn-ui-secondary" style="padding:3px 6px; font-size:0.7rem;" title="Print Case Sheet">🖨️</a>
            <button onclick="deleteSingleCase('${escapeHtml(c.cnr_number)}')" class="btn-ui btn-ui-danger" style="padding:3px 6px; font-size:0.7rem;" title="Delete Case">🗑️</button>
          </div>
        </td>
      </tr>
    `).join("");
  }

  window.syncSingleCase = async (cnr) => {
    try {
      const res = await fetch("/api/check-case", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cnr: cnr, force_live: true })
      });
      const data = await res.json();
      alert(`✅ eCourts Sync Complete for ${cnr}!\nNext Hearing: ${data.case_data.next_hearing_date || 'N/A'}\nStage: ${data.case_data.case_stage || 'N/A'}`);
      loadTrackedCases();
      loadDailyCauseList(dashboardDatePicker ? dashboardDatePicker.value : "2026-08-14");
    } catch (e) {
      alert("Sync failed: " + e.message);
    }
  };

  window.deleteSingleCase = async (cnr) => {
    if (!confirm(`Are you sure you want to remove case ${cnr} from tracking?`)) return;
    try {
      const res = await fetch(`/api/cases/${encodeURIComponent(cnr)}`, { method: "DELETE" });
      const data = await res.json();
      alert(data.message || "Case removed.");
      loadTrackedCases();
      loadDailyCauseList(dashboardDatePicker ? dashboardDatePicker.value : "2026-08-14");
    } catch (e) {
      alert("Delete failed: " + e.message);
    }
  };

  const btnQuickSync = document.getElementById("btn-quick-sync-portfolio");
  if (btnQuickSync) {
    btnQuickSync.addEventListener("click", async () => {
      btnQuickSync.disabled = true;
      btnQuickSync.innerText = "⚡ Syncing...";
      try {
        const res = await fetch("/api/scheduler/smart-sync", { method: "POST" });
        const data = await res.json();
        alert(`🎯 Smart Predictive Sync Complete!\n• Active Checked: ${data.checked_cases}\n• Sleeping Cases: ${data.sleeping_cases}\n• Date Shifts Detected: ${data.date_changes_count}`);
        loadTrackedCases();
        loadDailyCauseList(dashboardDatePicker ? dashboardDatePicker.value : "2026-08-14");
      } catch (e) {
        alert("Sync failed: " + e.message);
      } finally {
        btnQuickSync.disabled = false;
        btnQuickSync.innerText = "🔄 Sync Portfolio";
      }
    });
  }

  // =========================================================================
  // 4. CLIENT DIRECTORY
  // =========================================================================
  if (clientSearchInput) {
    clientSearchInput.addEventListener("input", () => {
      const q = clientSearchInput.value.trim().toLowerCase();
      const filtered = allCases.filter(c => 
        (c.client_name || "").toLowerCase().includes(q) ||
        (c.client_phone || "").toLowerCase().includes(q)
      );
      renderClientsTable(filtered);
    });
  }

  function renderClientsTable(cases) {
    if (!clientsTbody) return;
    const clientMap = {};
    cases.forEach(c => {
      const name = c.client_name || "Client";
      if (!clientMap[name]) {
        clientMap[name] = {
          name: name,
          phone: c.client_phone || "-",
          role: c.litigant_role || "Petitioner / Complainant",
          count: 0,
          nextDate: c.next_hearing_date || "Awaiting Schedule",
          caseObj: c
        };
      }
      clientMap[name].count += 1;
    });

    const clientList = Object.values(clientMap);
    if (clientList.length === 0) {
      clientsTbody.innerHTML = `
        <tr>
          <td colspan="7" style="padding: 32px; text-align: center; color: var(--text-muted);">
            <div style="font-size: 1.8rem; margin-bottom: 6px;">👥</div>
            <strong style="color: var(--text-main);">No Clients Registered Yet</strong>
            <p style="font-size: 0.78rem; margin-top: 4px;">Use <strong>"+ Add Client"</strong> to enroll your clients and track their matters.</p>
          </td>
        </tr>
      `;
      return;
    }

    clientsTbody.innerHTML = clientList.map(cl => `
      <tr>
        <td><strong>${escapeHtml(cl.name)}</strong></td>
        <td><code style="font-family: var(--font-mono); font-size:0.78rem;">${escapeHtml(cl.phone)}</code></td>
        <td><span class="badge badge-evidence">${escapeHtml(cl.role)}</span></td>
        <td><strong>${cl.count} Active Matter${cl.count > 1 ? 's' : ''}</strong></td>
        <td><strong style="color:var(--primary);">${escapeHtml(cl.nextDate)}</strong></td>
        <td><span style="color:var(--success); font-weight:700; font-size:0.76rem;">✓ WhatsApp Active</span></td>
        <td>
          <a href="${getWhatsAppUrl(cl.caseObj)}" target="_blank" class="btn-ui btn-ui-wa" style="padding:4px 10px; font-size:0.72rem;">
            💬 Send Notice
          </a>
        </td>
      </tr>
    `).join("");
  }

  // =========================================================================
  // 5. WHATSAPP DOCKETS VIEW
  // =========================================================================
  function renderWhatsAppDockets(cases) {
    if (!whatsappDocketsList) return;
    const bannerTitle = document.getElementById("wa-banner-title");
    const bannerDesc = document.getElementById("wa-banner-desc");

    if (!cases || cases.length === 0) {
      if (bannerTitle) bannerTitle.innerText = "No WhatsApp Notices Pending";
      if (bannerDesc) bannerDesc.innerText = "When client cases are enrolled, individual WhatsApp dispatch cards will appear here.";

      whatsappDocketsList.innerHTML = `
        <div style="text-align: center; padding: 36px 20px; color: var(--text-muted); background: #ffffff; border: 1px solid var(--border-color); border-radius: var(--radius-sm);">
          <div style="font-size: 2rem; margin-bottom: 6px;">📲</div>
          <strong style="color: var(--text-main); font-size: 0.95rem;">No Notices Ready to Dispatch</strong>
          <p style="font-size: 0.78rem; margin-top: 4px;">Enroll client cases with hearing dates using <strong>"+ Case Intake"</strong>.</p>
        </div>
      `;
      return;
    }

    if (bannerTitle) bannerTitle.innerText = `Today's Docket: ${cases.length} Client Notice${cases.length > 1 ? 's' : ''} Ready`;
    if (bannerDesc) bannerDesc.innerText = "Review and dispatch pre-formatted hearing notices directly to your clients on WhatsApp.";

    whatsappDocketsList.innerHTML = cases.map(c => `
      <div style="background: #ffffff; border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 14px 18px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; gap: 14px; flex-wrap: wrap;">
        <div>
          <div style="font-weight: 800; font-size: 0.92rem; color: var(--text-main);">${escapeHtml(c.client_name || 'Client')} (${escapeHtml(c.client_phone || '-')})</div>
          <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 2px;">
            Case: <strong>${escapeHtml(c.case_title)}</strong> &bull; Item: <strong>#${escapeHtml(c.item_number || '-')}</strong> (${escapeHtml(c.court_room || '-')}) &bull; Stage: <strong>${escapeHtml(c.case_stage || 'Evidence')}</strong>
          </div>
          <div style="font-size: 0.74rem; color: var(--text-muted); margin-top: 2px;">
            🏛️ ${escapeHtml(c.court_name || '')} &bull; Next Hearing: <strong style="color: var(--primary);">${escapeHtml(c.next_hearing_date || 'Awaiting Schedule')}</strong>
          </div>
        </div>
        <a href="${getWhatsAppUrl(c)}" target="_blank" class="btn-ui btn-ui-wa" style="flex-shrink: 0;">
          📲 Send WhatsApp
        </a>
      </div>
    `).join("");
  }

  // =========================================================================
  // 6. INTERACTIVE CALENDAR ENGINE
  // =========================================================================
  if (btnPrevMonth) {
    btnPrevMonth.addEventListener("click", () => {
      currentCalendarDate.setMonth(currentCalendarDate.getMonth() - 1);
      renderCalendar(currentCalendarDate);
    });
  }
  if (btnNextMonth) {
    btnNextMonth.addEventListener("click", () => {
      currentCalendarDate.setMonth(currentCalendarDate.getMonth() + 1);
      renderCalendar(currentCalendarDate);
    });
  }

  function renderCalendar(dateObj) {
    if (!calendarGridContainer) return;

    const year = dateObj.getFullYear();
    const month = dateObj.getMonth();
    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    
    if (calendarMonthTitle) {
      calendarMonthTitle.innerText = `📅 Hearing Calendar • ${monthNames[month]} ${year}`;
    }

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    let html = `
      <div style="font-weight: 700; color: var(--text-muted); font-size: 0.74rem; padding: 6px;">SUN</div>
      <div style="font-weight: 700; color: var(--text-muted); font-size: 0.74rem; padding: 6px;">MON</div>
      <div style="font-weight: 700; color: var(--text-muted); font-size: 0.74rem; padding: 6px;">TUE</div>
      <div style="font-weight: 700; color: var(--text-muted); font-size: 0.74rem; padding: 6px;">WED</div>
      <div style="font-weight: 700; color: var(--text-muted); font-size: 0.74rem; padding: 6px;">THU</div>
      <div style="font-weight: 700; color: var(--text-muted); font-size: 0.74rem; padding: 6px;">FRI</div>
      <div style="font-weight: 700; color: var(--text-muted); font-size: 0.74rem; padding: 6px;">SAT</div>
    `;

    // Blank cells before first day
    for (let i = 0; i < firstDay; i++) {
      html += `<div style="padding: 12px; background: #fafafa; border: 1px solid #f1f5f9; border-radius: var(--radius-sm);"></div>`;
    }

    // Days in current month
    for (let day = 1; day <= daysInMonth; day++) {
      const monthStr = String(month + 1).padStart(2, '0');
      const dayStr = String(day).padStart(2, '0');
      const fullDateStr = `${year}-${monthStr}-${dayStr}`;

      const matchedCases = allCases.filter(c => c.next_hearing_date === fullDateStr);
      const hasHearings = matchedCases.length > 0;

      html += `
        <div onclick="selectCalendarDate('${fullDateStr}')" style="padding: 10px 6px; cursor: pointer; background: ${hasHearings ? 'var(--primary-light)' : '#ffffff'}; border: 1px solid ${hasHearings ? 'var(--primary)' : 'var(--border-color)'}; border-radius: var(--radius-sm); transition: var(--transition);" title="View hearings on ${fullDateStr}">
          <div style="font-weight: 800; font-size: 0.85rem; color: ${hasHearings ? 'var(--primary)' : 'var(--text-main)'};">${day}</div>
          ${hasHearings ? `<div style="background: var(--primary); color: #fff; font-size: 0.65rem; padding: 1px 4px; border-radius: 3px; margin-top: 4px; font-weight: 700;">${matchedCases.length} Case${matchedCases.length > 1 ? 's' : ''}</div>` : ''}
        </div>
      `;
    }

    calendarGridContainer.innerHTML = html;
  }

  window.selectCalendarDate = (dateStr) => {
    if (!calendarSelectedDayHeading || !calendarSelectedDayList) return;
    calendarSelectedDayHeading.innerText = `Scheduled Hearings for ${dateStr}`;

    const matched = allCases.filter(c => c.next_hearing_date === dateStr);
    if (matched.length === 0) {
      calendarSelectedDayList.innerHTML = `<p style="color: var(--text-muted); font-size: 0.8rem;">No hearings scheduled on ${dateStr}.</p>`;
      return;
    }

    calendarSelectedDayList.innerHTML = matched.map(c => `
      <div style="background: #f8fafc; border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 10px 14px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <strong>${escapeHtml(c.case_title)}</strong> (${escapeHtml(c.client_name || 'Client')})<br>
          <span style="font-size: 0.74rem; color: var(--text-muted);">${escapeHtml(c.court_name || '')} &bull; Item #${escapeHtml(c.item_number || '-')} &bull; ${escapeHtml(c.case_stage || 'Hearing')}</span>
        </div>
        <a href="${getWhatsAppUrl(c)}" target="_blank" class="btn-ui btn-ui-wa" style="padding: 3px 8px; font-size: 0.72rem;">💬 WhatsApp</a>
      </div>
    `).join("");
  };

  // =========================================================================
  // 7. ALERTS AUDIT TRAIL
  // =========================================================================
  async function loadAlertsAudit() {
    if (!alertsAuditList) return;
    try {
      const res = await fetch("/api/history");
      const logs = await res.json();

      if (!logs || logs.length === 0) {
        alertsAuditList.innerHTML = `
          <div style="text-align: center; padding: 32px 20px; color: var(--text-muted);">
            <div style="font-size: 2rem; margin-bottom: 6px;">🔔</div>
            <strong style="color: var(--text-main);">Audit Trail Clean</strong>
            <p style="font-size: 0.78rem; margin-top: 4px;">When court date changes occur, automatic audit entries will be recorded here.</p>
          </div>
        `;
        return;
      }

      alertsAuditList.innerHTML = logs.map(l => `
        <div class="alert-card-item alert-orange" style="margin-bottom: 10px;">
          <div class="alert-icon">📅</div>
          <div style="flex: 1;">
            <strong>Hearing Date Shift Detected</strong> &bull; CNR: <code>${escapeHtml(l.cnr_number)}</code><br>
            Previous Date: <span style="text-decoration: line-through;">${escapeHtml(l.previous_hearing_date || 'None')}</span> ➡️ New Date: <strong>${escapeHtml(l.new_hearing_date)}</strong><br>
            <span style="font-size: 0.7rem; color: #92400e;">Logged at: ${escapeHtml(l.detected_at)}</span>
          </div>
        </div>
      `).join("");
    } catch (e) {}
  }

  // =========================================================================
  // 8. PRACTICE REPORTS & ANALYTICS
  // =========================================================================
  function updateReportsView() {
    const repActive = document.getElementById("rep-active-matters");
    const repTotal = document.getElementById("rep-total-hearings");
    const repDisposed = document.getElementById("rep-disposed-cases");
    const repCredits = document.getElementById("rep-credits-remaining");

    if (repActive) repActive.innerText = allCases.filter(c => c.case_status !== 'DISPOSED').length;
    if (repTotal) repTotal.innerText = allCases.filter(c => c.next_hearing_date).length;
    if (repDisposed) repDisposed.innerText = allCases.filter(c => c.case_status === 'DISPOSED').length;
    if (repCredits) repCredits.innerText = "176.0";
  }

  // =========================================================================
  // 9. ADVOCATE & FIRM SETTINGS
  // =========================================================================
  async function loadAdvocateSettings() {
    try {
      const res = await fetch("/api/advocate-settings");
      const data = await res.json();
      currentAdvocateSettings = data || {};
      
      const firm = data.firm_name || "R. ANBAIYA & ASSOCIATES";
      const lawyer = data.lawyer_name || "Advocate R. Anbaiya";
      const phone = data.lawyer_phone || "+919842112233";

      if (cfgFirmName) cfgFirmName.value = firm;
      if (cfgLawyerName) cfgLawyerName.value = lawyer;
      if (cfgLawyerPhone) cfgLawyerPhone.value = phone;
      if (cfgFooter) cfgFooter.value = data.default_whatsapp_footer || "Sent on behalf of R. Anbaiya & Associates, Advocates & Legal Consultants, Karur";

      const sidebarBrandTitle = document.getElementById("sidebar-brand-title");
      if (sidebarBrandTitle) sidebarBrandTitle.innerText = firm;

      const sidebarAdvocateName = document.getElementById("sidebar-advocate-name");
      if (sidebarAdvocateName) sidebarAdvocateName.innerText = lawyer;

      const headerGreeting = document.getElementById("header-advocate-greeting");
      if (headerGreeting) headerGreeting.innerText = `Good Evening, ${lawyer}`;

      const avatarInitials = document.getElementById("sidebar-avatar-initials");
      if (avatarInitials) {
        const initials = lawyer.split(" ").map(w => w[0]).filter(Boolean).slice(-2).join("").toUpperCase();
        avatarInitials.innerText = initials || "RA";
      }
    } catch (e) {}
  }

  if (firmSettingsForm) {
    firmSettingsForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await fetch("/api/advocate-settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            firm_name: cfgFirmName.value.trim(),
            lawyer_name: cfgLawyerName.value.trim(),
            lawyer_phone: cfgLawyerPhone.value.trim(),
            default_whatsapp_footer: cfgFooter.value.trim()
          })
        });
        alert("✅ Advocate & Firm Settings saved successfully!");
        loadAdvocateSettings();
      } catch (err) {
        alert("Failed to save: " + err.message);
      }
    });
  }

  // =========================================================================
  // 10. 3-STEP CASE INTAKE WIZARD
  // =========================================================================
  window.openCaseIntakeModal = () => {
    caseIntakeModal.style.display = "flex";
    goToStep(1);
  };

  window.goToStep = async (stepNum) => {
    const step1 = document.getElementById("wizard-step-1");
    const step2 = document.getElementById("wizard-step-2");
    const step3 = document.getElementById("wizard-step-3");
    const ind1 = document.getElementById("step-ind-1");
    const ind2 = document.getElementById("step-ind-2");
    const ind3 = document.getElementById("step-ind-3");

    [step1, step2, step3].forEach(s => s.style.display = "none");
    [ind1, ind2, ind3].forEach(i => i.classList.remove("active"));

    if (stepNum === 1) {
      step1.style.display = "block";
      ind1.classList.add("active");
    } else if (stepNum === 2) {
      if (!wizClientName.value.trim() || !wizClientPhone.value.trim()) {
        alert("Please enter the client name and WhatsApp number.");
        step1.style.display = "block";
        ind1.classList.add("active");
        return;
      }
      step2.style.display = "block";
      ind2.classList.add("active");
    } else if (stepNum === 3) {
      const cnr = wizCnr.value.trim().toUpperCase();
      if (!cnr) {
        alert("Please enter the 16-digit CNR number.");
        step2.style.display = "block";
        ind2.classList.add("active");
        return;
      }
      step3.style.display = "block";
      ind3.classList.add("active");
      
      intakeVerificationPreview.innerHTML = `
        <div style="text-align: center; padding: 16px;">
          <p style="font-weight: 700; color: var(--primary);">⚡ Checking judicial records for CNR ${cnr}...</p>
        </div>
      `;

      try {
        const res = await fetch("/api/check-case", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            cnr: cnr,
            client_name: wizClientName.value.trim(),
            client_phone: wizClientPhone.value.trim(),
            client_email: wizClientEmail.value.trim(),
            litigant_role: wizLitigantRole.value,
            case_number_formatted: wizCaseNo.value.trim(),
            case_stage: wizStage.value.trim(),
            court_room: wizRoom.value.trim(),
            item_number: wizItem.value.trim(),
            notes: wizNotes.value.trim(),
            force_live: false
          })
        });

        const data = await res.json();
        const c = data.case_data || data;

        intakeVerificationPreview.innerHTML = `
          <div style="font-size: 0.85rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
              <strong style="color:var(--text-main); font-size:0.95rem;">${escapeHtml(c.case_title || 'Case Title')}</strong>
              <span class="badge badge-evidence">✓ Verified Record</span>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:10px;">
              <div><strong>CNR:</strong> <code style="font-family:var(--font-mono); color:var(--primary);">${escapeHtml(c.cnr_number)}</code></div>
              <div><strong>Court:</strong> ${escapeHtml(c.court_name || 'District Court')}</div>
              <div><strong>Status:</strong> ${escapeHtml(c.case_status || 'PENDING')}</div>
              <div><strong>Next Hearing:</strong> <strong style="color:var(--primary);">${escapeHtml(c.next_hearing_date || 'Awaiting Schedule')}</strong></div>
            </div>
            <div style="background:#ecfdf5; border:1px solid #a7f3d0; padding:8px 12px; border-radius:4px; font-size:0.78rem; color:#065f46;">
              Client: <strong>${escapeHtml(wizClientName.value)}</strong> (${escapeHtml(wizClientPhone.value)}) enrolled as <strong>${escapeHtml(wizLitigantRole.value)}</strong>.
            </div>
          </div>
        `;
      } catch (err) {
        intakeVerificationPreview.innerHTML = `<p style="color:var(--danger);">Verification notice: ${err.message}</p>`;
      }
    }
  };

  window.autoFillSampleClient = () => {
    wizClientName.value = "Shobika Impex Private LTD";
    wizLitigantRole.value = "Financial Institution / Bank";
    wizClientPhone.value = "+919843011223";
    wizClientEmail.value = "accounts@shobikaimpex.com";
    wizCnr.value = "TNKR060000692024";
    wizCaseNo.value = "COS/69/2024";
    wizStage.value = "Evidence";
    wizRoom.value = "Room 3";
    wizItem.value = "1";
    wizNotes.value = "Commercial dispute trial & evidence documents marking";
    goToStep(2);
  };

  wizardForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btnSubmit = document.getElementById("btn-confirm-intake");
    if (btnSubmit) {
      btnSubmit.disabled = true;
      btnSubmit.innerText = "⏳ Enrolling Case...";
    }

    try {
      const res = await fetch("/api/check-case", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cnr: wizCnr.value.trim().toUpperCase(),
          client_name: wizClientName.value.trim(),
          client_phone: wizClientPhone.value.trim(),
          client_email: wizClientEmail.value.trim(),
          litigant_role: wizLitigantRole.value,
          case_number_formatted: wizCaseNo.value.trim(),
          case_stage: wizStage.value.trim(),
          court_room: wizRoom.value.trim(),
          item_number: wizItem.value.trim(),
          notes: wizNotes.value.trim(),
          next_hearing_date: dashboardDatePicker ? dashboardDatePicker.value : "2026-08-14",
          force_live: false
        })
      });

      const data = await res.json();
      caseIntakeModal.style.display = "none";
      alert("✅ Case successfully enrolled and added to your Private Chamber Tracking!");
      
      await loadTrackedCases();
      await loadDailyCauseList(dashboardDatePicker ? dashboardDatePicker.value : "2026-08-14");
      switchView("view-cases");
    } catch (err) {
      alert("Failed to enroll case: " + err.message);
    } finally {
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.innerText = "✓ Confirm & Track Case";
      }
    }
  });


  // Helpers
  function getBadgeClass(stage) {
    if (!stage) return "badge-evidence";
    const s = stage.toLowerCase();
    if (s.includes("trial")) return "badge-trial";
    if (s.includes("ia")) return "badge-ia";
    if (s.includes("warrant") || s.includes("arrest")) return "badge-warrant";
    if (s.includes("step")) return "badge-steps";
    if (s.includes("dispose")) return "badge-disposed";
    return "badge-evidence";
  }

  function getWhatsAppUrl(c) {
    if (!c) return "#";
    const lawyer = currentAdvocateSettings.lawyer_name || "Advocate R. Anbaiya";
    const firm = currentAdvocateSettings.firm_name || "R. ANBAIYA & ASSOCIATES";
    const footer = currentAdvocateSettings.default_whatsapp_footer || "Sent on behalf of R. Anbaiya & Associates, Advocates & Legal Consultants, Karur";

    const text = `⚖️ *${firm}*
*HEARING UPDATE NOTICE*
---------------------------------------
Dear *${c.client_name || 'Client'}*,

Your court hearing details have been confirmed:
• *Case:* ${c.case_title || 'Case Title'}
• *Court:* ${c.court_name || 'Court'}
• *Item No:* ${c.item_number || '-'} (${c.court_room || '-'})
• *Stage:* *${c.case_stage || 'Evidence'}*
• *Next Hearing Date:* *${c.next_hearing_date || 'Awaiting Date'}*
${c.notes ? `• *Advocate Note:* ${c.notes}` : ''}
---------------------------------------
${footer}
*Advocate:* ${lawyer}`;

    const cleanPhone = (c.client_phone || "").replace(/[^0-9]/g, "");
    return `https://wa.me/${cleanPhone}?text=${encodeURIComponent(text)}`;
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
