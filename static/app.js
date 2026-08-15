/**
 * LEX CHAMBERS • eCourts Automation Platform
 * Frontend Controller for Advocate R. Anbaiya
 */

document.addEventListener("DOMContentLoaded", () => {
  // State
  let allCases = [];
  let causeListData = null;
  let currentAdvocateSettings = {};
  let selectedCourtFilter = "ALL";

  // Elements
  const navItems = document.querySelectorAll(".nav-item[data-view]");
  const viewSections = document.querySelectorAll(".view-section");
  const dashboardDatePicker = document.getElementById("dashboard-date-picker");
  const hearingBoardListContainer = document.getElementById("hearing-board-list-container");
  const fullHearingsContainer = document.getElementById("full-hearings-container");
  const allCasesTbody = document.getElementById("all-cases-tbody");
  const clientsTbody = document.getElementById("clients-tbody");
  const whatsappDocketsList = document.getElementById("whatsapp-dockets-list");
  const alertsAuditList = document.getElementById("alerts-audit-list");

  // KPI Elements
  const kpiTodayHearings = document.getElementById("kpi-today-hearings");
  const kpiActiveCases = document.getElementById("kpi-active-cases");
  const badgeTodayHearings = document.getElementById("badge-today-hearings");
  const badgeTotalCases = document.getElementById("badge-total-cases");

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

  // Settings
  const firmSettingsForm = document.getElementById("firm-settings-form");
  const cfgFirmName = document.getElementById("cfg-firm-name");
  const cfgLawyerName = document.getElementById("cfg-lawyer-name");
  const cfgLawyerPhone = document.getElementById("cfg-lawyer-phone");
  const cfgFooter = document.getElementById("cfg-footer");
  const cfgApiKey = document.getElementById("cfg-api-key");

  // Initialize
  initNavigation();
  loadAdvocateSettings();
  loadDailyCauseList("2026-08-14");
  loadTrackedCases();
  loadAlertsAudit();

  // Navigation Logic
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
  };

  // Date Picker Change
  if (dashboardDatePicker) {
    dashboardDatePicker.addEventListener("change", () => {
      const selected = dashboardDatePicker.value;
      const printLink = document.getElementById("btn-print-docket-link");
      if (printLink) printLink.href = `/api/export-cause-list?date=${selected}`;
      loadDailyCauseList(selected);
    });
  }

  // Generate Morning WhatsApp Docket
  const btnMorningDocket = document.getElementById("btn-generate-morning-docket");
  if (btnMorningDocket) {
    btnMorningDocket.addEventListener("click", async () => {
      const targetDate = dashboardDatePicker.value || "2026-08-14";
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
    });
  }

  // Load Daily Cause List
  async function loadDailyCauseList(targetDate = "2026-08-14") {
    hearingBoardListContainer.innerHTML = `<p style="padding: 24px; text-align: center; color: var(--text-muted);">Loading Daily Court Hearing Board for ${targetDate}...</p>`;
    try {
      const res = await fetch(`/api/cause-list?date=${targetDate}`);
      const data = await res.json();
      causeListData = data;

      if (kpiTodayHearings) kpiTodayHearings.innerText = data.total_hearings || 0;
      if (badgeTodayHearings) badgeTodayHearings.innerText = data.total_hearings || 0;

      renderHearingBoard(data, selectedCourtFilter);
      setupCourtChips(data);
    } catch (e) {
      hearingBoardListContainer.innerHTML = `<p style="padding: 24px; color: var(--danger);">Failed to load hearing board: ${e.message}</p>`;
    }
  }

  // Setup Court Chips Filter
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

  // Render Hearing Board
  function renderHearingBoard(data, filterCourt = "ALL") {
    if (!data || !data.court_summaries || data.court_summaries.length === 0) {
      hearingBoardListContainer.innerHTML = `
        <div style="padding: 30px; text-align: center; color: var(--text-muted);">
          <p>No confirmed court hearings scheduled for this date.</p>
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
        <table class="hearing-table">
          <thead>
            <tr>
              <th style="width: 70px; text-align: center;">Item No</th>
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
                  <a href="${getWhatsAppUrl(c)}" target="_blank" class="btn-ui btn-ui-wa" style="padding: 4px 10px; font-size: 0.72rem;">
                    💬 WhatsApp
                  </a>
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `).join("");
  }

  // Load All Stored Cases
  async function loadTrackedCases() {
    try {
      const res = await fetch("/api/cases");
      const data = await res.json();
      allCases = data || [];

      if (kpiActiveCases) kpiActiveCases.innerText = allCases.length;
      if (badgeTotalCases) badgeTotalCases.innerText = allCases.length;

      renderAllCasesTable(allCases);
      renderClientsTable(allCases);
      renderWhatsAppDockets(allCases);
    } catch (e) {
      console.error(e);
    }
  }

  // Render All Cases Table
  function renderAllCasesTable(cases) {
    if (!allCasesTbody) return;
    if (!cases || cases.length === 0) {
      allCasesTbody.innerHTML = `<tr><td colspan="8" style="padding: 24px; text-align: center; color: var(--text-muted);">No cases found in database.</td></tr>`;
      return;
    }

    allCasesTbody.innerHTML = cases.map(c => `
      <tr>
        <td><strong>${escapeHtml(c.client_name || 'Client')}</strong></td>
        <td>
          <div class="case-title-bold">${escapeHtml(c.case_title)}</div>
          <div style="font-size:0.72rem; color:var(--text-muted);">${escapeHtml(c.parties || '')}</div>
        </td>
        <td><span class="case-no-pill">${escapeHtml(c.case_number_formatted || '-')}</span></td>
        <td><code style="font-family: var(--font-mono); font-size:0.75rem; color:var(--primary);">${escapeHtml(c.cnr_number)}</code></td>
        <td>${escapeHtml(c.court_name || 'Karur Court')}</td>
        <td><strong style="color:var(--primary);">${escapeHtml(c.next_hearing_date || 'Awaiting Date')}</strong></td>
        <td><span class="badge ${c.case_status === 'DISPOSED' ? 'badge-disposed' : 'badge-pending'}">${escapeHtml(c.case_status || 'PENDING')}</span></td>
        <td>
          <div style="display:flex; gap:6px;">
            <a href="${getWhatsAppUrl(c)}" target="_blank" class="btn-ui btn-ui-wa" style="padding:3px 6px; font-size:0.7rem;">💬</a>
            <a href="/api/export-case/${encodeURIComponent(c.cnr_number)}" target="_blank" class="btn-ui btn-ui-secondary" style="padding:3px 6px; font-size:0.7rem;">🖨️</a>
          </div>
        </td>
      </tr>
    `).join("");
  }

  // Render Clients Table
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
          nextDate: c.next_hearing_date || "Awaiting Date",
          caseObj: c
        };
      }
      clientMap[name].count += 1;
    });

    const clientList = Object.values(clientMap);
    clientsTbody.innerHTML = clientList.map(cl => `
      <tr>
        <td><strong>${escapeHtml(cl.name)}</strong></td>
        <td><code style="font-family: var(--font-mono); font-size:0.78rem;">${escapeHtml(cl.phone)}</code></td>
        <td><span class="badge badge-evidence">${escapeHtml(cl.role)}</span></td>
        <td><strong>${cl.count} Active Case${cl.count > 1 ? 's' : ''}</strong></td>
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

  // Render WhatsApp Dockets Page
  function renderWhatsAppDockets(cases) {
    if (!whatsappDocketsList) return;
    whatsappDocketsList.innerHTML = cases.map(c => `
      <div style="background: #ffffff; border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 14px 18px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; gap: 14px;">
        <div>
          <div style="font-weight: 800; font-size: 0.92rem; color: var(--text-main);">${escapeHtml(c.client_name || 'Client')} (${escapeHtml(c.client_phone || '-')})</div>
          <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 2px;">
            Case: <strong>${escapeHtml(c.case_title)}</strong> &bull; Item: <strong>#${escapeHtml(c.item_number || '-')}</strong> (${escapeHtml(c.court_room || '-')}) &bull; Stage: <strong>${escapeHtml(c.case_stage || 'Evidence')}</strong>
          </div>
          <div style="font-size: 0.74rem; color: var(--text-muted); margin-top: 2px;">
            🏛️ ${escapeHtml(c.court_name || '')} &bull; Next Hearing: <strong style="color: var(--primary);">${escapeHtml(c.next_hearing_date || '14-08-2026')}</strong>
          </div>
        </div>
        <a href="${getWhatsAppUrl(c)}" target="_blank" class="btn-ui btn-ui-wa" style="flex-shrink: 0;">
          📲 Send WhatsApp
        </a>
      </div>
    `).join("");
  }

  // Full Hearings View
  function renderFullHearingsView() {
    if (!fullHearingsContainer || !causeListData) return;
    renderHearingBoard(causeListData, "ALL");
    fullHearingsContainer.innerHTML = hearingBoardListContainer.innerHTML;
  }

  // Load Alerts Audit
  async function loadAlertsAudit() {
    if (!alertsAuditList) return;
    try {
      const res = await fetch("/api/history");
      const logs = await res.json();
      if (!logs || logs.length === 0) {
        alertsAuditList.innerHTML = `<p style="padding:20px; text-align:center; color:var(--text-muted);">No hearing date changes detected recently.</p>`;
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

  // Load Advocate Settings
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


  // Save Settings
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

  // Case Intake Wizard Functions
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

  // Submit Intake Form
  wizardForm.addEventListener("submit", (e) => {
    e.preventDefault();
    caseIntakeModal.style.display = "none";
    alert("✅ Case successfully added to tracking!");
    loadTrackedCases();
    loadDailyCauseList("2026-08-14");
    switchView("view-cases");
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
