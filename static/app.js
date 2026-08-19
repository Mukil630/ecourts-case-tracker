/**
 * R. ANBAIYA & ASSOCIATES • Legal Practice Management Platform
 * Live Real-Time Auto-Sync Engine & JARVIS Agentic Legal AI Co-Pilot
 */

// Global State
let allCases = [];
let allLeads = [];
let causeListData = null;
let currentAdvocateSettings = {};
let selectedCourtFilter = "ALL";
let currentCalendarDate = new Date();
let lastSyncTimestamp = 0;
let isJarvisOpen = false;

function getRealTodayDate() {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function getSelectedOrTodayDate() {
  const picker = document.getElementById("dashboard-date-picker");
  if (picker && picker.value) return picker.value;
  return getRealTodayDate();
}

window.switchDashboardDate = function(dateStr) {
  const picker = document.getElementById("dashboard-date-picker");
  if (picker) picker.value = dateStr;
  loadDailyCauseList(dateStr);
};

// =========================================================================
// 0. STARTUP CONTROLLER
// =========================================================================
window.dismissStartupSplash = function() {
  const splash = document.getElementById("app-startup-splash");
  if (splash) splash.style.display = "none";
};

// =========================================================================
// 1. GLOBAL NAVIGATION & VIEW SWITCHER
// =========================================================================
window.toggleMobileSidebar = function(forceState) {
  const sidebar = document.getElementById("app-sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  if (!sidebar) return;
  
  const isOpen = sidebar.classList.contains("mobile-open");
  const targetState = forceState !== undefined ? forceState : !isOpen;
  
  if (targetState) {
    sidebar.classList.add("mobile-open");
    if (backdrop) backdrop.classList.add("active");
  } else {
    sidebar.classList.remove("mobile-open");
    if (backdrop) backdrop.classList.remove("active");
  }
};

window.switchView = function(viewId) {
  try {
    const navItems = document.querySelectorAll(".nav-item[data-view]");
    const mobileNavItems = document.querySelectorAll(".mobile-nav-btn[data-mobile-view]");
    const viewSections = document.querySelectorAll(".view-section");

    navItems.forEach(item => {
      if (item.getAttribute("data-view") === viewId) {
        item.classList.add("active");
      } else {
        item.classList.remove("active");
      }
    });

    mobileNavItems.forEach(item => {
      if (item.getAttribute("data-mobile-view") === viewId) {
        item.classList.add("active");
      } else {
        item.classList.remove("active");
      }
    });

    viewSections.forEach(sec => {
      if (sec.id === viewId) {
        sec.classList.add("active");
        sec.style.display = "block";
      } else {
        sec.classList.remove("active");
        sec.style.display = "none";
      }
    });

    // Automatically close mobile sidebar if opened
    window.toggleMobileSidebar(false);

    if (viewId === "view-cases") renderAllCasesTable(allCases);
    if (viewId === "view-clients") renderClientsTable(allCases);
    if (viewId === "view-leads") loadLeads();
    if (viewId === "view-whatsapp") renderWhatsAppDockets(allCases);
    if (viewId === "view-calendar") renderCalendar(currentCalendarDate);
    if (viewId === "view-dashboard") {
      loadDailyCauseList(getSelectedOrTodayDate());
    }
  } catch (err) {
    console.error("switchView error:", err);
  }
};

// =========================================================================
// 2. CLIENT INTAKE, ADVOCATE SEARCH & CASE DRAWER
// =========================================================================
window.openCaseIntakeModal = function() {
  const modal = document.getElementById("case-intake-modal");
  if (modal) modal.style.display = "flex";
};

window.openAdvocateSearchModal = function() {
  const modal = document.getElementById("advocate-search-modal");
  if (modal) modal.style.display = "flex";
};

function getCasePlainExplanation(c) {
  const caseNo = (c.case_number_formatted || c.cnr_number || "").toUpperCase();
  const title = (c.case_title || "").toLowerCase();
  const stage = (c.case_stage || "").toLowerCase();
  const notes = (c.notes || "").toLowerCase();

  // 1. Cheque Bounce / 138 NI Act (STC 1035/2023)
  if (caseNo.includes("1035") || title.includes("palanisamy") || title.includes("velmurugan")) {
    return {
      category: "💸 Cheque Bounce Suit (Section 138 Negotiable Instruments Act)",
      meaning: "M. Palanisamy (Petitioner) gave money or goods; respondent M. Velmurugan gave a bank cheque that bounced due to insufficient funds.",
      todayAction: "M. Palanisamy is in the witness box giving oral evidence (PW1). Advocate R. Anbaiya will guide his testimony and face cross-examination from the accused's lawyer."
    };
  }

  // 2. Warrant Matter (STC 383/2025)
  if (caseNo.includes("383") || title.includes("eniyavan") || "warrant" in stage || notes.includes("warrant")) {
    return {
      category: "🚨 Criminal Case with Non-Bailable Arrest Warrant (NBW)",
      meaning: "G. Eniyavan filed criminal proceedings against D. Jeevanandham for non-compliance. The accused repeatedly skipped court hearings.",
      todayAction: "Court issued Non-Bailable Warrant (NBW) to Karur Police to arrest and produce the accused in Room 10 before Magistrate R. Mahesh."
    };
  }

  // 3. Accident Compensation EP (EP 25/2025)
  if (caseNo.includes("25/2025") || title.includes("shalini") || title.includes("tnstc")) {
    return {
      category: "🚌 Motor Accident Claims Compensation Execution Petition (EP)",
      meaning: "Court already ordered government transport (TNSTC) to pay accident compensation money to Shalini.",
      todayAction: "Execution Hearing: Court is checking if TNSTC deposited the compensation money into court treasury, or if bus attachment/warrant is required."
    };
  }

  // 4. Injunction / Property Dispute (OS 361/2025)
  if (caseNo.includes("361/2025") || title.includes("nirmala") || stage.includes("ia")) {
    return {
      category: "🏡 Property Ownership & Urgent Injunction Application (IA)",
      meaning: "S. Nirmala is disputing property rights against C. Velusamy & 10 others regarding ancestral/purchased land.",
      todayAction: "Interim Injunction Hearing: Advocate R. Anbaiya is requesting the District Judge to grant a stay order stopping the other party from selling or altering the land."
    };
  }

  // 5. Commercial Suit (COS 69/2024)
  if (caseNo.includes("69/2024") || title.includes("shobika")) {
    return {
      category: "🏭 Commercial Business Contract & Invoice Recovery Suit",
      meaning: "Shobika Impex Private Ltd supplied textile goods, but payment of invoices was withheld by Sundarapandiyan.",
      todayAction: "Commercial Evidence Trial: Shobika Impex authorized officer is proving invoices, delivery challans, and ledger balance before Sub Judge Priyanga."
    };
  }

  // 6. Bank Loan Recovery Suits (Bank of Baroda & SBI)
  if (title.includes("bank") || title.includes("sbi") || title.includes("baroda")) {
    return {
      category: "🏦 Institutional Bank Loan Recovery & Mortgage Suit",
      meaning: "Bank filed recovery suit against borrower/guarantors for defaulted agricultural/business loan balance.",
      todayAction: stage.includes("ex-parte") 
        ? "Borrower failed to appear in court. Advocate R. Anbaiya is submitting Bank Proof Affidavit to obtain an Ex-Parte Decree order."
        : "Bank branch manager is giving witness evidence with original loan sanction and promissory note documents."
    };
  }

  // 7. Partition & Title Suits (Palaniyappan / Shankar / Lakshmi)
  if (title.includes("palaniyappan") || caseNo.includes("139/2021")) {
    return {
      category: "📜 5-Year Civil Land Ownership Trial & Final Arguments",
      meaning: "Long-standing land title dispute between A. Palaniyappan and R. Manokaran & 5 others since 2021.",
      todayAction: "Final Trial Arguments: Witness examination is complete. Advocate R. Anbaiya is presenting final legal citations for judgment."
    };
  }

  // General Fallback
  return {
    category: `⚖️ Civil / Criminal Court Proceeding (${c.court_name || 'District Court'})`,
    meaning: `Matters between ${c.parties || c.case_title || 'Litigants'}. Represented by ${c.advocates || 'Advocate R. Anbaiya'}.`,
    todayAction: `Scheduled for "${c.case_stage || 'Hearing'}" before ${c.judge_name || 'Presiding Judge'} in ${c.court_room || 'Court Hall'}.`
  };
}

window.openCaseDrawer = function(cnrNumber) {
  if (!cnrNumber) return;

  // Find case in allCases or causeListData
  let c = allCases.find(item => item.cnr_number === cnrNumber);
  if (!c && causeListData && causeListData.court_summaries) {
    for (const court of causeListData.court_summaries) {
      const match = court.cases.find(item => item.cnr_number === cnrNumber);
      if (match) {
        c = match;
        break;
      }
    }
  }

  if (!c) {
    alert("Case details not found for " + cnrNumber);
    return;
  }

  const badgeElem = document.getElementById("drawer-case-no-badge");
  const titleElem = document.getElementById("drawer-case-header-title");
  const bodyContent = document.getElementById("case-drawer-body-content");
  const overlay = document.getElementById("case-drawer-overlay");
  const panel = document.getElementById("case-detail-drawer");

  if (badgeElem) badgeElem.innerText = c.case_number_formatted || c.cnr_number;
  if (titleElem) titleElem.innerText = c.case_title || "Case Details";

  const plainInfo = getCasePlainExplanation(c);

  if (bodyContent) {
    bodyContent.innerHTML = `
      <!-- 0. SIMPLE CASE MEANING & TODAY'S COURT ACTION (Plain Language) -->
      <div class="drawer-section-card" style="background: rgba(16, 185, 129, 0.12); border: 1.5px solid rgba(16, 185, 129, 0.4); border-left: 5px solid #10b981;">
        <div class="drawer-section-title" style="color: #34d399; border-color: rgba(16, 185, 129, 0.3); display:flex; justify-content:space-between; align-items:center;">
          <span>💡 SIMPLE CASE EXPLANATION & ACTION</span>
          <span style="font-size:0.75rem; background:rgba(16, 185, 129, 0.25); color:#34d399; padding:3px 10px; border-radius:4px; font-weight:800; border: 1px solid rgba(16,185,129,0.4);">PLAIN TAMIL/ENG</span>
        </div>
        <div style="font-size: 0.95rem; font-weight: 800; color: #ffffff; margin-bottom: 8px;">
          ${escapeHtml(plainInfo.category)}
        </div>
        <div style="font-size: 0.88rem; color: #e2e8f0; line-height: 1.55; margin-bottom: 12px;">
          <strong style="color: #ffffff;">📖 Case Summary:</strong> ${escapeHtml(plainInfo.meaning)}
        </div>
        <div style="font-size: 0.88rem; color: #a7f3d0; line-height: 1.55; background: #04070e; border: 1.5px solid rgba(16, 185, 129, 0.4); border-radius: 8px; padding: 12px 14px;">
          ⚡ <strong style="color: #ffffff;">Today's Court Action:</strong> ${escapeHtml(plainInfo.todayAction)}
        </div>
      </div>

      <!-- 0.5 SMART SLEEP & MONITORING STATUS CARD -->
      <div class="drawer-section-card" style="background: #080c15; border: 1.5px solid var(--border-gold);">
        <div class="drawer-section-title">🧠 SMART SLEEP & AUTO-SYNC RADAR</div>
        <div style="display:flex; align-items:center; gap:14px;">
          <span style="font-size:1.6rem;">${c.next_hearing_date === getSelectedOrTodayDate() ? '🔔' : '😴'}</span>
          <div>
            <div style="font-size:0.95rem; font-weight:800; color:#ffffff;">
              ${c.next_hearing_date === getSelectedOrTodayDate() ? 'Active In Court Today (Item #' + (c.item_number || '-') + ')' : 'Smart Sleeping until ' + (c.next_hearing_date || 'Schedule')}
            </div>
            <div style="font-size:0.82rem; color:#cbd5e1; margin-top:4px; line-height:1.45;">
              ${c.next_hearing_date === getSelectedOrTodayDate() ? 'Currently listed on today\'s hearing board.' : 'Zero credits wasted daily. System will automatically wake up 2 days before ' + (c.next_hearing_date || 'date') + ' to scan tomorrow\'s cause list!'}
            </div>
          </div>
        </div>
      </div>


      <!-- 1. Case Identity Card -->
      <div class="drawer-section-card">
        <div class="drawer-section-title">🏛️ Court & Hearing Identity</div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Court Complex:</span>
          <span class="drawer-field-val">${escapeHtml(c.court_name || 'Karur District Court')}</span>
        </div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Court Room:</span>
          <span class="drawer-field-val"><span class="room-badge">${escapeHtml(c.court_room || '-')}</span></span>
        </div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Item Number:</span>
          <span class="drawer-field-val" style="font-size:1rem; color:#fbbf24; font-weight:800;">#${escapeHtml(c.item_number || '-')}</span>
        </div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Presiding Judge:</span>
          <span class="drawer-field-val" style="color: #cbd5e1;">${escapeHtml(c.judge_name || '-')}</span>
        </div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">16-Digit CNR:</span>
          <span class="drawer-field-val"><span class="cnr-number-pill">${escapeHtml(c.cnr_number)}</span></span>
        </div>
      </div>


      <!-- 2. Client & Litigant Card -->
      <div class="drawer-section-card">
        <div class="drawer-section-title">👤 Client Contact & Role</div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Client Name:</span>
          <span class="drawer-field-val" style="color:#ffffff; font-weight:800; font-size: 0.95rem;">${escapeHtml(c.client_name || 'Client')}</span>
        </div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Litigant Role:</span>
          <span class="drawer-field-val"><span class="badge badge-evidence">${escapeHtml(c.litigant_role || 'Petitioner')}</span></span>
        </div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">WhatsApp Phone:</span>
          <span class="drawer-field-val"><div class="client-phone-pill">📞 ${escapeHtml(c.client_phone || '-')}</div></span>
        </div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Parties:</span>
          <span class="drawer-field-val" style="font-size:0.84rem; color:#cbd5e1;">${escapeHtml(c.parties || c.case_title)}</span>
        </div>
      </div>

      <!-- 3. Stage & Next Hearing Card -->
      <div class="drawer-section-card">
        <div class="drawer-section-title">📅 Hearing Status & Stage</div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Next Hearing Date:</span>
          <span class="drawer-field-val" style="color:var(--text-gold); font-size:0.98rem; font-weight:800; font-family: var(--font-mono);">${escapeHtml(c.next_hearing_date || 'Awaiting Date')}</span>
        </div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Hearing Stage:</span>
          <span class="drawer-field-val"><span class="badge ${getBadgeClass(c.case_stage)}">${escapeHtml(c.case_stage || 'Evidence')}</span></span>
        </div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Advocate Notes:</span>
          <span class="drawer-field-val"><span class="notes-badge-pill">${escapeHtml(c.notes || 'None')}</span></span>
        </div>
      </div>

      <!-- 4. Quick Actions -->
      <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 8px;">
        <a href="${getWhatsAppUrl(c)}" target="_blank" class="btn-ui btn-ui-wa" style="text-align:center; padding:12px; font-weight:800; font-size:0.9rem; box-shadow: 0 4px 16px rgba(16, 185, 129, 0.4);">
          📲 Send WhatsApp Hearing Notice
        </a>
        <div style="display:flex; gap:10px;">
          <a href="/api/export-case/${encodeURIComponent(c.cnr_number)}" target="_blank" class="btn-ui btn-ui-secondary" style="flex:1; text-align:center; padding:10px; font-size:0.8rem; font-weight: 700;">
            🖨️ Print Case Brief
          </a>
          <button onclick="syncSingleCase('${escapeHtml(c.cnr_number)}')" class="btn-ui btn-ui-secondary" style="flex:1; padding:10px; font-size:0.8rem; font-weight: 700;">
            🔄 Sync eCourts
          </button>
        </div>
        <button onclick="toggleCaseDisposed('${escapeHtml(c.cnr_number)}', '${escapeHtml(c.case_status || 'PENDING')}'); closeCaseDrawer();" class="btn-ui btn-ui-secondary" style="width:100%; text-align:center; padding:9px; font-size:0.78rem; font-weight:700; ${((c.case_status || '').toUpperCase() === 'DISPOSED') ? 'border-color:#10b981; color:#34d399; background:rgba(16,185,129,0.1);' : 'border-color:#ef4444; color:#f87171; background:rgba(239,68,68,0.08);'}">
          ${((c.case_status || '').toUpperCase() === 'DISPOSED') ? '🔓 Reopen / Move to Active Cases' : '🏁 Mark Case as Disposed / Closed'}
        </button>
      </div>
    `;
  }

  if (overlay) overlay.style.display = "block";
  if (panel) panel.style.right = "0px";
};

window.closeCaseDrawer = function() {
  const overlay = document.getElementById("case-drawer-overlay");
  const panel = document.getElementById("case-detail-drawer");
  if (overlay) overlay.style.display = "none";
  if (panel) panel.style.right = "-480px";
};

window.openBulkWhatsAppModal = function() {
  const modal = document.getElementById("bulk-whatsapp-modal");
  const tbody = document.getElementById("bulk-wa-tbody");
  if (!modal || !tbody) return;

  const todayCases = [];
  if (causeListData && causeListData.court_summaries) {
    for (const court of causeListData.court_summaries) {
      todayCases.push(...(court.cases || []));
    }
  }

  if (todayCases.length === 0) {
    alert("No hearings scheduled for this date to dispatch notices.");
    return;
  }

  const title = document.getElementById("bulk-wa-modal-title");
  if (title) title.innerText = `📲 Dispatch WhatsApp Notices (${todayCases.length} Clients)`;

  const subtitle = document.getElementById("bulk-wa-modal-subtitle");
  if (subtitle) subtitle.innerText = `Send personalized hearing docket notices to all clients scheduled for ${causeListData?.target_date || getSelectedOrTodayDate()}.`;

  const readyLbl = document.getElementById("bulk-wa-notices-ready-label");
  if (readyLbl) readyLbl.innerText = `${todayCases.length} Notice${todayCases.length > 1 ? 's' : ''} Ready for Instant Send`;

  const metaBtn = document.getElementById("btn-meta-dispatch-all");
  if (metaBtn) metaBtn.innerText = `🛡️ Official Meta Cloud Auto-Dispatch (${todayCases.length})`;

  tbody.innerHTML = todayCases.map(c => `
    <tr>
      <td style="text-align: center; font-weight: 800; color: var(--primary);">#${escapeHtml(c.item_number || '-')}</td>
      <td>
        <strong>${escapeHtml(c.client_name || 'Client')}</strong><br>
        <code style="font-size:0.72rem; color:var(--text-muted);">${escapeHtml(c.client_phone || '-')}</code>
      </td>
      <td>
        <span style="font-weight:600;">${escapeHtml(c.case_number_formatted || c.cnr_number)}</span><br>
        <span style="font-size:0.7rem; color:var(--text-muted);">${escapeHtml(c.court_name)} (${escapeHtml(c.court_room || '-')})</span>
      </td>
      <td style="text-align: right;">
        <a href="${getWhatsAppUrl(c)}" target="_blank" class="btn-ui btn-ui-wa" style="padding:4px 8px; font-size:0.7rem;">
          📲 Send Notice
        </a>
      </td>
    </tr>
  `).join("");

  modal.style.display = "flex";
};

window.sendAllQueuedNotices = function() {
  const todayCases = [];
  if (causeListData && causeListData.court_summaries) {
    for (const court of causeListData.court_summaries) {
      todayCases.push(...(court.cases || []));
    }
  }

  if (todayCases.length === 0) {
    alert("No hearings scheduled for this date.");
    return;
  }

  // Open WhatsApp Web links sequentially with delay to prevent browser popup block
  todayCases.forEach((c, idx) => {
    setTimeout(() => {
      window.open(getWhatsAppUrl(c), "_blank");
    }, idx * 600);
  });
  alert(`🚀 Opened WhatsApp notices for ${todayCases.length} scheduled client${todayCases.length > 1 ? 's' : ''}!`);
};


window.autoFillSampleClient = function() {
  const nameInput = document.getElementById("wiz-client-name");
  const caseNoInput = document.getElementById("wiz-case-no");
  const phoneInput = document.getElementById("wiz-client-phone");
  const courtSelect = document.getElementById("wiz-court-name");
  const dateInput = document.getElementById("wiz-hearing-date");
  const stageInput = document.getElementById("wiz-stage");
  const roomInput = document.getElementById("wiz-room");
  const itemInput = document.getElementById("wiz-item");
  const notesInput = document.getElementById("wiz-notes");

  if (nameInput) nameInput.value = "M. Palanisamy";
  if (caseNoInput) caseNoInput.value = "STC/1035/2023";
  if (phoneInput) phoneInput.value = "9443322110";
  if (courtSelect) courtSelect.value = "Chief Judicial Magistrate Court, Karur";
  if (dateInput) dateInput.value = getSelectedOrTodayDate();
  if (stageInput) stageInput.value = "Evidence";
  if (roomInput) roomInput.value = "Room 8";
  if (itemInput) itemInput.value = "4";
  if (notesInput) notesInput.value = "Complainant evidence cross examination";
};

window.performAdvocateSearch = async function() {
  const nameInput = document.getElementById("adv-search-name");
  const distSelect = document.getElementById("adv-search-district");
  const container = document.getElementById("adv-search-results-container");

  const advocateName = nameInput ? nameInput.value.trim() : "Advocate R. Anbaiya";
  const district = distSelect ? distSelect.value : "Karur";

  if (!container) return;
  container.innerHTML = `<p style="text-align: center; color: var(--primary); padding: 16px 0;">⚡ Searching eCourts for <strong>${escapeHtml(advocateName)}</strong> in <strong>${escapeHtml(district)}</strong>...</p>`;

  try {
    const res = await fetch(`/api/search-advocate-cases?name=${encodeURIComponent(advocateName)}&district=${encodeURIComponent(district)}`);
    const data = await res.json();
    const cases = data.cases || [];

    if (cases.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 20px; color: var(--text-muted);">
          <strong>No cases found under "${escapeHtml(advocateName)}"</strong>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
        <strong style="font-size:0.88rem; color:var(--text-main);">Found ${cases.length} Confirmed Matter${cases.length > 1 ? 's' : ''}</strong>
        <button type="button" class="btn-ui btn-ui-primary" onclick="bulkImportDiscoveredCases()" style="font-size: 0.72rem; padding: 4px 10px; font-weight: 800;">
          📥 Import All (${cases.length}) to Vault
        </button>
      </div>

      <div style="max-height: 250px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: var(--radius-sm);">
        <table class="hearing-table" style="font-size: 0.78rem;">
          <thead>
            <tr>
              <th style="width: 45px; text-align: center;">Item</th>
              <th>Case Number / Title</th>
              <th>Court & Room</th>
              <th>Stage</th>
            </tr>
          </thead>
          <tbody>
            ${cases.map(c => `
              <tr>
                <td style="font-weight: 800; color: var(--primary); text-align: center;">${escapeHtml(c.item_number || '-')}</td>
                <td>
                  <strong>${escapeHtml(c.case_number_formatted || c.cnr_number)}</strong><br>
                  <span style="font-size: 0.7rem; color: var(--text-muted);">${escapeHtml(c.case_title)}</span>
                </td>
                <td>${escapeHtml(c.court_name || 'Karur Court')} (${escapeHtml(c.court_room || '-')})</td>
                <td><span class="badge badge-evidence" style="font-size:0.68rem;">${escapeHtml(c.case_stage || 'Evidence')}</span></td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;
    window._lastDiscoveredCases = cases;
  } catch (err) {
    container.innerHTML = `<p style="color: var(--danger); text-align: center;">Search failed: ${escapeHtml(err.message)}</p>`;
  }
};

window.bulkImportDiscoveredCases = async function() {
  const cases = window._lastDiscoveredCases || [];
  if (cases.length === 0) return;

  try {
    const res = await fetch("/api/cause-list/import-karur", { method: "POST" });
    const data = await res.json();
    alert(`✅ Successfully imported ${cases.length} cases into Chamber Vault!`);
    const modal = document.getElementById("advocate-search-modal");
    if (modal) modal.style.display = "none";
    await loadTrackedCases();
    await loadDailyCauseList(getSelectedOrTodayDate());
    window.switchView("view-dashboard");
  } catch (e) {
    alert("Import failed: " + e.message);
  }
};

window.loadKarurDemoPractice = async function() {
  try {
    const res = await fetch("/api/cause-list/import-karur", { method: "POST" });
    const data = await res.json();
    alert("✅ Loaded Advocate R. Anbaiya Chamber Cases into Vault!");
    await loadTrackedCases();
    await loadDailyCauseList(getSelectedOrTodayDate());
  } catch (e) {
    alert("Failed to load cases: " + e.message);
  }
};

// =========================================================================
// 3. JARVIS AGENTIC LEGAL AI CO-PILOT
// =========================================================================
window.toggleJarvisDrawer = function() {
  const drawer = document.getElementById("jarvis-ai-drawer");
  if (!drawer) return;
  isJarvisOpen = !isJarvisOpen;
  drawer.style.right = isJarvisOpen ? "0px" : "-420px";
  if (isJarvisOpen) {
    loadAiBriefing();
  }
};

window.sendAiPrompt = function(promptText) {
  const input = document.getElementById("ai-prompt-input");
  if (input) {
    input.value = promptText;
    window.sendAiMessage();
  }
};

window.sendAiMessage = async function() {
  const input = document.getElementById("ai-prompt-input");
  const history = document.getElementById("ai-chat-history");
  if (!input || !history) return;

  const text = input.value.trim();
  if (!text) return;

  // Append user message
  history.innerHTML += `
    <div style="background: #17233f; border: 1px solid var(--border-gold); border-radius: var(--radius-sm); padding: 10px 14px; align-self: flex-end; max-width: 85%; font-size: 0.84rem; color: #ffffff;">
      <strong style="color: var(--text-gold);">You:</strong> ${escapeHtml(text)}
    </div>
  `;
  input.value = "";
  history.scrollTop = history.scrollHeight;

  // Add Thinking indicator
  const thinkingId = "thinking-" + Date.now();
  history.innerHTML += `
    <div id="${thinkingId}" style="background: rgba(245, 158, 11, 0.1); border: 1px solid var(--border-gold); border-radius: var(--radius-sm); padding: 10px 14px; color: var(--text-gold); font-size: 0.82rem;">
      🤖 <em>JARVIS is analyzing cases vault & legal strategies...</em>
    </div>
  `;
  history.scrollTop = history.scrollHeight;

  try {
    const res = await fetch("/api/ai-assistant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: text })
    });
    const data = await res.json();
    const thinkElem = document.getElementById(thinkingId);
    if (thinkElem) thinkElem.remove();

    const formattedReply = (data.reply || "Ready to assist.")
      .replace(/\n/g, "<br>")
      .replace(/\*\*(.*?)\*\*/g, "<strong style='color:#ffffff;'>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>");

    history.innerHTML += `
      <div style="background: #080c15; border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 14px 16px; font-size: 0.84rem; line-height: 1.5; color: var(--text-secondary);">
        ${formattedReply}
      </div>
    `;
    history.scrollTop = history.scrollHeight;
  } catch (e) {
    const thinkElem = document.getElementById(thinkingId);
    if (thinkElem) thinkElem.innerHTML = `<span style="color:var(--danger);">Error: ${escapeHtml(e.message)}</span>`;
  }
};

async function loadAiBriefing() {
  try {
    const res = await fetch(`/api/ai-briefing?date=${encodeURIComponent(getSelectedOrTodayDate())}`);
    const data = await res.json();
    const history = document.getElementById("ai-chat-history");
    if (!history) return;

    if (data.briefing_text && !history.innerHTML.includes("Morning Legal Briefing")) {
      const formatted = data.briefing_text
        .replace(/\n/g, "<br>")
        .replace(/\*\*(.*?)\*\*/g, "<strong style='color:#ffffff;'>$1</strong>");

      history.innerHTML += `
        <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: var(--radius-sm); padding: 14px 16px; color: #34d399; font-size: 0.82rem; line-height: 1.5;">
          ${formatted}
        </div>
      `;
      history.scrollTop = history.scrollHeight;
    }
  } catch (e) {}
}

// =========================================================================
// 4. REAL-TIME ZERO-REFRESH LIVE SYNC LOOP
// =========================================================================
function startLiveSyncLoop() {
  setInterval(async () => {
    try {
      const res = await fetch("/api/live-status");
      const status = await res.json();

      const liveIndicator = document.getElementById("live-sync-indicator");
      if (liveIndicator) {
        liveIndicator.innerHTML = `<span style="width:6px; height:6px; border-radius:50%; background:#10b981;"></span> Live Auto-Sync Active (${status.last_updated})`;
      }

      // If case count changed or initial portfolio was empty, sync immediately
      if (status.total_cases !== allCases.length || allCases.length === 0) {
        await loadTrackedCases();
        await loadDailyCauseList(getSelectedOrTodayDate());
      }
      lastSyncTimestamp = status.timestamp;
    } catch (e) {}
  }, 4000);
}

// =========================================================================
// 5. DATA LOADERS & RENDERERS
// =========================================================================
async function loadDailyCauseList(targetDate) {
  if (!targetDate) {
    targetDate = getSelectedOrTodayDate();
  }
  const realToday = getRealTodayDate();
  const isToday = (targetDate === realToday);

  const picker = document.getElementById("dashboard-date-picker");
  if (picker && picker.value !== targetDate) {
    picker.value = targetDate;
  }

  const dayLabel = document.getElementById("header-current-date-day");
  if (dayLabel) {
    try {
      const dObj = new Date(targetDate + "T00:00:00");
      const formatted = dObj.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
      dayLabel.innerText = isToday ? `Today (${formatted})` : formatted;
    } catch(e) {
      dayLabel.innerText = targetDate;
    }
  }

  const hExp = document.getElementById("header-export-btn");
  if (hExp) hExp.href = `/api/export-cause-list?date=${encodeURIComponent(targetDate)}`;
  const mExp = document.getElementById("main-export-btn");
  if (mExp) mExp.href = `/api/export-cause-list?date=${encodeURIComponent(targetDate)}`;

  const mainTitle = document.getElementById("hearing-board-main-title");
  const mainSub = document.getElementById("hearing-board-main-sub");

  if (mainTitle) {
    mainTitle.innerText = isToday ? "⚖️ Today's Court Hearing Board" : `⚖️ Court Hearing Board • ${targetDate}`;
  }
  if (mainSub) {
    mainSub.innerHTML = isToday
      ? `Live Daily Court Docket &bull; Grouped by Court Complex, Presiding Judge, Court Room & Item Number`
      : `Viewing Scheduled Cause List for <strong style="color:var(--text-gold);">${targetDate}</strong> &bull; Grouped by Court, Room & Item Number`;
  }

  const container = document.getElementById("hearing-board-list-container");
  if (container) {
    container.innerHTML = `<p style="padding: 24px; text-align: center; color: var(--text-muted);">Loading Court Hearing Board for ${targetDate}...</p>`;
  }

  try {
    const res = await fetch(`/api/cause-list?date=${encodeURIComponent(targetDate)}`);
    const data = await res.json();
    causeListData = data;

    const count = data.total_hearings || 0;
    const courtsCount = data.total_courts || (data.court_summaries ? data.court_summaries.length : 0);

    const kpiTodayHearings = document.getElementById("kpi-today-hearings");
    const badgeTodayHearings = document.getElementById("badge-today-hearings");
    const kpiTodayHearingsSub = document.getElementById("kpi-today-hearings-sub");
    const allCourtsTabBadge = document.getElementById("all-courts-tab-badge");
    const btnBulkWa = document.getElementById("btn-bulk-wa-header");

    if (kpiTodayHearings) kpiTodayHearings.innerText = isToday ? count : (allCases ? allCases.filter(c => c.next_hearing_date === realToday && (c.case_status || '').toUpperCase() !== 'DISPOSED').length : count);
    if (badgeTodayHearings) badgeTodayHearings.innerText = isToday ? count : (allCases ? allCases.filter(c => c.next_hearing_date === realToday && (c.case_status || '').toUpperCase() !== 'DISPOSED').length : count);
    if (allCourtsTabBadge) allCourtsTabBadge.innerText = count;
    if (btnBulkWa) btnBulkWa.innerText = `📲 Send Notice to All (${count}) Clients`;
    if (kpiTodayHearingsSub) {
      if (isToday) {
        kpiTodayHearingsSub.innerText = count > 0 ? `Across ${courtsCount} Courts in Karur` : "No hearings scheduled today";
      } else {
        kpiTodayHearingsSub.innerText = `Today has ${allCases ? allCases.filter(c => c.next_hearing_date === realToday && (c.case_status || '').toUpperCase() !== 'DISPOSED').length : 0} hearings`;
      }
    }

    renderHearingBoard(data, selectedCourtFilter);
    setupCourtChips(data);
    await renderTomorrowEveningDocket(targetDate);
    renderUpcomingHearingsPipeline();
    renderRescheduledHearingsSection();
  } catch (e) {
    if (container) {
      container.innerHTML = `<p style="padding: 24px; color: var(--danger);">Failed to load hearing board: ${e.message}</p>`;
    }
  }
}

function setupCourtChips(data) {
  const chipsRow = document.getElementById("court-chips-row");
  if (!chipsRow) return;

  const summaries = data.court_summaries || [];
  chipsRow.innerHTML = `
    <button class="court-tab-btn ${selectedCourtFilter === 'ALL' ? 'active' : ''}" data-court="ALL">
      All Courts <span class="tab-badge">${data.total_hearings || 0}</span>
    </button>
    ${summaries.map(c => `
      <button class="court-tab-btn ${selectedCourtFilter === c.court_name ? 'active' : ''}" data-court="${escapeHtml(c.court_name)}">
        ${escapeHtml(c.court_name.replace(' Court, Karur', '').replace(' at Magisterial Level', ''))}
        <span class="tab-badge">${c.hearings_count}</span>
      </button>
    `).join("")}
  `;

  chipsRow.querySelectorAll(".court-tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      chipsRow.querySelectorAll(".court-tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      selectedCourtFilter = btn.getAttribute("data-court");
      renderHearingBoard(causeListData, selectedCourtFilter);
    });
  });
}

function renderHearingBoard(data, filterCourt = "ALL") {
  const container = document.getElementById("hearing-board-list-container");
  if (!container) return;

  const realToday = getRealTodayDate();
  const isToday = (!data || !data.target_date || data.target_date === realToday);
  const targetDateStr = data ? (data.target_date || realToday) : realToday;

  let targetDateFormatted = targetDateStr;
  try {
    targetDateFormatted = new Date(targetDateStr + "T00:00:00").toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "short", year: "numeric" });
  } catch(e) {}

  if (!data || !data.court_summaries || data.court_summaries.length === 0) {
    // Find next upcoming hearing date from allCases
    const futureCases = (allCases || [])
      .filter(c => c.next_hearing_date && c.next_hearing_date > targetDateStr && (c.case_status || '').toUpperCase() !== "DISPOSED")
      .sort((a, b) => (a.next_hearing_date || "").localeCompare(b.next_hearing_date || ""));

    let nextDateHtml = "";
    if (futureCases.length > 0) {
      const nextDate = futureCases[0].next_hearing_date;
      const casesOnNextDate = futureCases.filter(c => c.next_hearing_date === nextDate);
      
      let nextDateFormatted = nextDate;
      try {
        nextDateFormatted = new Date(nextDate + "T00:00:00").toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "short", year: "numeric" });
      } catch(e) {}

      const tom = new Date();
      tom.setDate(tom.getDate() + 1);
      const tomStr = tom.toISOString().split("T")[0];
      const isNextTomorrow = (nextDate === tomStr);

      nextDateHtml = `
        <div style="background: rgba(59, 130, 246, 0.1); border: 1.5px solid rgba(59, 130, 246, 0.35); border-radius: var(--radius-md); padding: 18px 20px; margin: 20px auto 0 auto; max-width: 600px; text-align: left; box-shadow: 0 4px 16px rgba(0,0,0,0.3);">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <span style="font-size: 0.76rem; font-weight: 800; color: #60a5fa; text-transform: uppercase; background: rgba(59,130,246,0.2); padding: 3px 10px; border-radius: 12px; border: 1px solid rgba(59,130,246,0.4);">
              📅 Next Scheduled Court Session
            </span>
            <span style="font-size: 0.8rem; color: var(--text-gold); font-weight: 700;">
              ${casesOnNextDate.length} Confirmed Hearing${casesOnNextDate.length > 1 ? 's' : ''}
            </span>
          </div>
          <div style="font-size: 1.15rem; font-weight: 800; color: #ffffff; margin-top: 8px;">
            🏛️ ${isNextTomorrow ? 'Tomorrow • ' : ''}${escapeHtml(nextDateFormatted)}
          </div>
          <div style="margin-top: 10px; font-size: 0.82rem; color: #cbd5e1; line-height: 1.45;">
            ${casesOnNextDate.slice(0, 3).map(c => `
              <div style="margin-top: 4px;">• <strong>${escapeHtml(c.case_title)}</strong> (${escapeHtml(c.case_number_formatted || c.cnr_number)}) in <em>${escapeHtml(c.court_name)}</em> (Item #${escapeHtml(c.item_number || '-')})</div>
            `).join("")}
            ${casesOnNextDate.length > 3 ? `<div style="color:var(--text-muted); margin-top:2px;">...and ${casesOnNextDate.length - 3} more cases</div>` : ''}
          </div>
          <div style="margin-top: 14px; display:flex; gap:10px;">
            <button type="button" class="btn-ui btn-ui-primary" onclick="switchDashboardDate('${escapeHtml(nextDate)}')" style="font-size: 0.8rem; font-weight: 800; padding: 7px 16px;">
              👉 Switch to ${escapeHtml(nextDate)} Board
            </button>
          </div>
        </div>
      `;
    }

    container.innerHTML = `
      <div style="padding: 36px 20px; text-align: center; color: var(--text-muted);">
        <div style="font-size: 2.5rem; margin-bottom: 8px;">📋</div>
        <strong style="font-size: 1.15rem; color: var(--text-main); display: block;">
          No Hearings Scheduled for ${isToday ? 'Today (' + targetDateFormatted + ')' : targetDateFormatted}
        </strong>
        <p style="font-size: 0.85rem; margin-top: 6px; color: var(--text-muted); max-width: 560px; margin-left: auto; margin-right: auto; line-height: 1.5;">
          ${isToday 
            ? 'Advocate R. Anbaiya has <strong>0 court appearances or cause list listings</strong> allocated for today. All pending matters in the chamber vault are in good standing.' 
            : 'No cases are listed on the official court diary for this specific date.'}
        </p>
        ${nextDateHtml}
        <div style="display: flex; gap: 10px; justify-content: center; margin-top: 20px; flex-wrap: wrap;">
          ${!isToday ? `<button type="button" class="btn-ui btn-ui-secondary" onclick="switchDashboardDate('${getRealTodayDate()}')" style="font-size: 0.78rem; font-weight: 700; padding: 7px 14px;">👈 Back to Today (${getRealTodayDate()})</button>` : ''}
          <button type="button" class="btn-ui btn-ui-secondary" onclick="openAdvocateSearchModal()" style="font-size: 0.78rem; font-weight: 700; padding: 7px 14px;">
            🔍 Search eCourts Live
          </button>
          <button type="button" class="btn-ui btn-ui-secondary" onclick="openCaseIntakeModal()" style="font-size: 0.78rem; font-weight: 700; padding: 7px 14px;">
            ➕ Add New Case
          </button>
        </div>
      </div>
    `;
    return;
  }

  let summaryHeaderHtml = "";
  if (filterCourt === "ALL" && data.court_summaries && data.court_summaries.length > 0) {
    const courtsCount = data.total_courts || data.court_summaries.length;
    summaryHeaderHtml = `
      <div class="hearing-board-summary-box">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 14px; margin-bottom: 14px; flex-wrap: wrap; gap: 10px;">
          <div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="background: rgba(245, 158, 11, 0.15); color: var(--text-gold); border: 1px solid rgba(245, 158, 11, 0.3); font-size: 0.74rem; padding: 3px 10px; border-radius: 12px; font-weight: 700; text-transform: uppercase;">
                ${isToday ? '⚡ Today\'s Scheduled Board' : '📅 Cause List for ' + targetDateFormatted}
              </span>
              ${!isToday ? `<button onclick="switchDashboardDate('${getRealTodayDate()}')" class="btn-ui btn-ui-secondary" style="padding: 2px 8px; font-size: 0.7rem; font-weight: 700;">👈 Back to Today</button>` : ''}
            </div>
            <div style="font-weight: 800; font-size: 1.05rem; color: #ffffff; margin-top: 6px;">
              Advocate R. Anbaiya has <span style="color: var(--text-gold); font-weight: 800;">${data.total_hearings}</span> confirmed hearings scheduled across ${courtsCount} Karur Court${courtsCount > 1 ? 's' : ''}
            </div>
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <button onclick="openBulkWhatsAppModal()" class="btn-ui btn-ui-wa" style="font-size: 0.8rem; padding: 7px 14px; font-weight: 800;">
              📲 Send Notice to All (${data.total_hearings || 0}) Clients
            </button>
            <a href="/api/export-cause-list?date=${encodeURIComponent(data.target_date || getSelectedOrTodayDate())}" target="_blank" class="btn-ui btn-ui-secondary" style="font-size: 0.8rem; padding: 7px 14px;">
              🖨️ A4 Cause List
            </a>
          </div>
        </div>

        <div style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; font-size: 0.86rem; background: #080c15; border-radius: var(--radius-sm); overflow: hidden;">
            <thead>
              <tr style="background: #0f172a; border-bottom: 1px solid var(--border-color);">
                <th style="width: 60px; padding: 10px 14px; text-align: left; font-weight: 700; color: var(--text-muted); font-size: 0.76rem;">S.NO</th>
                <th style="padding: 10px 14px; text-align: left; font-weight: 700; color: var(--text-muted); font-size: 0.76rem;">COURT NAME</th>
                <th style="width: 130px; padding: 10px 14px; text-align: right; font-weight: 700; color: var(--text-muted); font-size: 0.76rem;">CONFIRMED</th>
              </tr>
            </thead>
            <tbody>
              ${data.court_summaries.map((c, i) => `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.04);">
                  <td style="padding: 10px 14px; font-weight: 600; color: var(--text-muted);">${i + 1}</td>
                  <td style="padding: 10px 14px; font-weight: 600; color: #ffffff;">${escapeHtml(c.court_name)}</td>
                  <td style="padding: 10px 14px; text-align: right; font-weight: 800; color: var(--text-gold); font-family: var(--font-mono);">${c.hearings_count}</td>
                </tr>
              `).join("")}
              <tr style="background: #111a2e; font-weight: 800;">
                <td colspan="2" style="padding: 11px 14px; text-align: right; color: #ffffff;">TOTAL CONFIRMED HEARINGS:</td>
                <td style="padding: 11px 14px; text-align: right; color: var(--text-gold); font-size: 0.95rem; font-family: var(--font-mono);">${data.total_hearings}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  let courtsToRender = data.court_summaries;
  if (filterCourt !== "ALL") {
    courtsToRender = courtsToRender.filter(c => c.court_name === filterCourt);
  }

  container.innerHTML = summaryHeaderHtml + courtsToRender.map(court => `
    <div class="court-block">
      <div class="court-block-header">
        <span>🏛️ ${escapeHtml(court.court_name)}</span>
        <span class="court-block-count">${court.hearings_count} Case${court.hearings_count > 1 ? 's' : ''}</span>
      </div>
      <div style="overflow-x: auto;">
        <table class="hearing-table">
          <thead>
            <tr>
              <th style="width: 60px; text-align: center;">Item</th>
              <th style="min-width: 320px;">Case Details (Click to View Side Details)</th>
              <th style="min-width: 170px;">Client</th>
              <th style="min-width: 130px;">Status</th>
              <th style="min-width: 180px;">Room & Judge</th>
              <th style="text-align: right; min-width: 140px;">WhatsApp</th>
            </tr>
          </thead>
          <tbody>
            ${court.cases.map(c => {
              const isNewFiling = (c.case_number_formatted || c.cnr_number || '').includes('2026');
              const filingBadge = isNewFiling 
                ? '<span style="font-size:0.68rem; background:rgba(59,130,246,0.18); color:#60a5fa; border:1px solid rgba(59,130,246,0.35); padding:1px 6px; border-radius:4px; font-weight:700;">🆕 New Filing (2026)</span>'
                : '<span style="font-size:0.68rem; background:rgba(148,163,184,0.12); color:#94a3b8; border:1px solid rgba(148,163,184,0.25); padding:1px 6px; border-radius:4px; font-weight:600;">📜 Ongoing Matter</span>';

              let hearingDateFormatted = c.next_hearing_date || '-';
              try {
                const dObj = new Date(c.next_hearing_date + "T00:00:00");
                hearingDateFormatted = dObj.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
              } catch(e) {}

              return `
                <tr class="clickable-case-row">
                  <td style="text-align: center; width: 60px;" onclick="openCaseDrawer('${escapeHtml(c.cnr_number)}')">
                    <div class="item-badge-cell" style="cursor: pointer;">${escapeHtml(c.item_number || '-')}</div>
                  </td>
                  <td class="clickable-case-cell" onclick="openCaseDrawer('${escapeHtml(c.cnr_number)}')" style="max-width: 420px;">
                    <div class="case-title-text" style="display:flex; align-items:center; justify-content:space-between; gap:8px;">
                      <span>${escapeHtml(c.case_title)}</span>
                      <span style="font-size:0.72rem; background:rgba(245,158,11,0.15); color:#fbbf24; border:1px solid rgba(245,158,11,0.35); padding:2px 7px; border-radius:5px; font-weight:800; font-family:var(--font-mono); white-space:nowrap;">📅 ${escapeHtml(hearingDateFormatted)}</span>
                    </div>
                    <div class="case-sub-text" style="display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin-top:4px;">
                      <span class="case-number-pill">${escapeHtml(c.case_number_formatted || c.cnr_number)}</span>
                      ${filingBadge}
                      ${c.notes ? `<span class="notes-badge-pill">📌 Note: ${escapeHtml(c.notes)}</span>` : ''}
                    </div>
                  </td>
                  <td style="min-width: 170px;">
                    <strong style="color: #ffffff; font-size: 0.95rem; display: block; font-weight: 800;">${escapeHtml(c.client_name || 'Client')}</strong>
                    <div class="client-phone-pill">📞 ${escapeHtml(c.client_phone || '-')}</div>
                  </td>
                  <td>
                    <span class="badge ${getBadgeClass(c.case_stage)}">${escapeHtml(c.case_stage || 'Evidence')}</span>
                  </td>
                  <td style="min-width: 180px;">
                    <div class="room-badge">${escapeHtml(c.court_room || '-')}</div>
                    <div class="judge-text">${escapeHtml(c.judge_name || '-')}</div>
                  </td>
                  <td style="text-align: right; min-width: 140px;">
                    <a href="${getWhatsAppUrl(c)}" target="_blank" class="btn-ui btn-ui-wa" style="padding: 8px 14px; font-size: 0.82rem; font-weight: 800;">
                      📲 Send Notice
                    </a>
                  </td>
                </tr>
              `;
            }).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `).join("");
}

function getTomorrowDate() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

async function renderTomorrowEveningDocket(currentTargetDate) {
  const container = document.getElementById("tomorrow-evening-docket-container");
  if (!container) return;

  const realToday = getRealTodayDate();
  const tomorrowStr = getTomorrowDate();
  
  // If user is ALREADY viewing tomorrow's board directly, clear this advance container
  if (currentTargetDate === tomorrowStr) {
    container.innerHTML = "";
    return;
  }

  try {
    const res = await fetch(`/api/cause-list?date=${encodeURIComponent(tomorrowStr)}`);
    const tomorrowData = await res.json();

    if (!tomorrowData || !tomorrowData.total_hearings || tomorrowData.total_hearings === 0) {
      container.innerHTML = "";
      return;
    }

    let tomorrowFormatted = tomorrowStr;
    try {
      tomorrowFormatted = new Date(tomorrowStr + "T00:00:00").toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "short", year: "numeric" });
    } catch(e) {}

    container.innerHTML = `
      <div style="background: #060a14; border: 2px solid #f59e0b; border-radius: var(--radius-md); padding: 22px 24px; margin-top: 24px; box-shadow: 0 8px 32px rgba(245, 158, 11, 0.15);">
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 1.5px solid rgba(245, 158, 11, 0.3); padding-bottom: 14px; margin-bottom: 16px; flex-wrap:wrap; gap:12px;">
          <div>
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1.5px solid rgba(245, 158, 11, 0.5); font-size: 0.76rem; padding: 4px 12px; border-radius: 14px; font-weight: 800; text-transform: uppercase;">
                🌙 Evening Advance Docket for Tomorrow
              </span>
              <span style="color:#94a3b8; font-size:0.75rem;">(Auto-prepared for Advocate R. Anbaiya)</span>
            </div>
            <div style="font-weight: 800; font-size: 1.15rem; color: #ffffff; margin-top: 8px;">
              🏛️ ${escapeHtml(tomorrowFormatted)} &bull; <span style="color: #fbbf24;">${tomorrowData.total_hearings} Confirmed Hearings</span> across ${tomorrowData.total_courts} Courts
            </div>
          </div>
          <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
            <a href="/api/export-cause-list?date=${encodeURIComponent(tomorrowStr)}" target="_blank" class="btn-ui btn-ui-secondary" style="font-size: 0.8rem; padding: 8px 14px; font-weight: 800; border-color: var(--border-gold); color: var(--text-gold);">
              🖨️ A4 Cause List (PDF)
            </a>
            <button onclick="switchDashboardDate('${tomorrowStr}')" class="btn-ui btn-ui-primary" style="font-size: 0.8rem; padding: 8px 16px; font-weight: 800; background: linear-gradient(135deg, #f59e0b, #d97706); color: #000000; box-shadow: 0 4px 14px rgba(245,158,11,0.4);">
              👉 Open Tomorrow's Full Board
            </button>
          </div>
        </div>

        <!-- 1. SUMMARY TABLE (S.NO | COURT NAME | CONFIRMED) -->
        <div style="font-size: 0.85rem; font-weight: 800; color: #ffffff; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">
          📊 Court Summary Breakdown
        </div>
        <div style="overflow-x: auto; margin-bottom: 20px;">
          <table style="width: 100%; border-collapse: collapse; font-size: 0.84rem; background: #0c1322; border-radius: var(--radius-sm); border: 1px solid var(--border-color); overflow: hidden;">
            <thead>
              <tr style="background: #111b2f; border-bottom: 1px solid var(--border-color);">
                <th style="width: 55px; padding: 9px 14px; text-align: left; font-weight: 800; color: var(--text-muted); font-size: 0.74rem;">S.NO</th>
                <th style="padding: 9px 14px; text-align: left; font-weight: 800; color: var(--text-muted); font-size: 0.74rem;">COURT NAME</th>
                <th style="width: 130px; padding: 9px 14px; text-align: right; font-weight: 800; color: var(--text-muted); font-size: 0.74rem;">CONFIRMED</th>
              </tr>
            </thead>
            <tbody>
              ${tomorrowData.court_summaries.map((c, i) => `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.04);">
                  <td style="padding: 9px 14px; color: var(--text-muted); font-weight: 700;">${i + 1}</td>
                  <td style="padding: 9px 14px; color: #ffffff; font-weight: 600;">${escapeHtml(c.court_name)}</td>
                  <td style="padding: 9px 14px; text-align: right; font-weight: 800; color: #fbbf24; font-family: var(--font-mono);">${c.hearings_count}</td>
                </tr>
              `).join("")}
              <tr style="background: #17243e; font-weight: 800;">
                <td colspan="2" style="padding: 10px 14px; text-align: right; color: #ffffff;">TOTAL CONFIRMED HEARINGS:</td>
                <td style="padding: 10px 14px; text-align: right; color: #fbbf24; font-size: 0.98rem; font-family: var(--font-mono);">${tomorrowData.total_hearings}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 2. DETAILED ITEM-WISE COURT LISTINGS (Exact match to Court Dossier) -->
        <div style="font-size: 0.85rem; font-weight: 800; color: #ffffff; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px;">
          📋 Courtroom Item-wise Schedule
        </div>
        ${tomorrowData.court_summaries.map(court => `
          <div style="background: #0a101d; border: 1px solid rgba(255,255,255,0.08); border-radius: var(--radius-sm); padding: 14px 16px; margin-bottom: 14px;">
            <div style="font-weight: 800; color: #38bdf8; font-size: 0.92rem; margin-bottom: 10px; display:flex; justify-content:space-between; align-items:center;">
              <span>🏛️ ${escapeHtml(court.court_name.toUpperCase())}</span>
              <span style="font-size:0.75rem; background:rgba(56,189,248,0.15); border:1px solid rgba(56,189,248,0.3); padding:2px 8px; border-radius:4px; color:#38bdf8; font-weight:700;">${court.hearings_count} Case${court.hearings_count > 1 ? 's' : ''}</span>
            </div>
            <div style="overflow-x: auto;">
              <table class="hearing-table" style="font-size: 0.82rem;">
                <thead>
                  <tr>
                    <th style="width: 55px; text-align: center;">Item</th>
                    <th style="width: 160px;">Room & Judge</th>
                    <th>Case Title & Number</th>
                    <th style="width: 140px;">Stage</th>
                    <th style="width: 90px; text-align: center;">Status</th>
                    <th style="width: 130px; text-align: right;">Action</th>
                  </tr>
                </thead>
                <tbody>
                  ${court.cases.map(c => {
                    const isNewFiling = (c.case_number_formatted || c.cnr_number || '').includes('2026');
                    const filingTag = isNewFiling ? '<span style="font-size:0.68rem; background:rgba(59,130,246,0.18); color:#60a5fa; padding:1px 5px; border-radius:3px;">🆕 New</span>' : '<span style="font-size:0.68rem; background:rgba(148,163,184,0.12); color:#94a3b8; padding:1px 5px; border-radius:3px;">📜 Ongoing</span>';

                    return `
                      <tr>
                        <td style="text-align: center; font-weight: 800; color: var(--primary);">#${escapeHtml(c.item_number || '-')}</td>
                        <td>
                          <div class="room-badge" style="font-size: 0.72rem; padding: 1px 6px;">${escapeHtml(c.court_room || '-')}</div>
                          <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 3px;">${escapeHtml(c.judge_name || '-')}</div>
                        </td>
                        <td class="clickable-case-cell" onclick="openCaseDrawer('${escapeHtml(c.cnr_number)}')">
                          <strong style="color: #ffffff; font-size: 0.88rem;">${escapeHtml(c.case_title)}</strong>
                          <div style="font-size: 0.74rem; color: #fbbf24; margin-top: 2px; font-family: var(--font-mono); display:flex; align-items:center; gap:6px;">
                            <span>${escapeHtml(c.case_number_formatted || c.cnr_number)}</span>
                            ${filingTag}
                          </div>
                        </td>
                        <td><span class="badge ${getBadgeClass(c.case_stage)}" style="font-size: 0.72rem;">${escapeHtml(c.case_stage || 'Hearing')}</span></td>
                        <td style="text-align: center;"><span style="color: #34d399; font-weight: 800; font-size: 0.75rem;">✓ Confirmed</span></td>
                        <td style="text-align: right;">
                          <a href="${getWhatsAppUrl(c)}" target="_blank" class="btn-ui btn-ui-wa" style="padding: 5px 10px; font-size: 0.75rem; font-weight: 800;">📲 Notice</a>
                        </td>
                      </tr>
                    `;
                  }).join("")}
                </tbody>
              </table>
            </div>
          </div>
        `).join("")}
      </div>
    `;
  } catch(err) {
    console.error("renderTomorrowEveningDocket error:", err);
  }
}

function renderUpcomingHearingsPipeline() {
  const container = document.getElementById("upcoming-pipeline-table-container");
  const countBadge = document.getElementById("upcoming-pipeline-count-badge");
  if (!container) return;

  const realToday = getRealTodayDate();
  
  // Filter cases with next_hearing_date STRICTLY in future (> realToday) and NOT disposed
  const upcomingCases = (allCases || []).filter(c => {
    const d = c.next_hearing_date;
    return d && d > realToday && (c.case_status || '').toUpperCase() !== "DISPOSED";
  });

  // Sort chronologically
  upcomingCases.sort((a, b) => {
    if (a.next_hearing_date === b.next_hearing_date) {
      const numA = parseInt(a.item_number) || 999;
      const numB = parseInt(b.item_number) || 999;
      return numA - numB;
    }
    return (a.next_hearing_date || "").localeCompare(b.next_hearing_date || "");
  });

  if (countBadge) countBadge.innerText = upcomingCases.length;

  if (upcomingCases.length === 0) {
    container.innerHTML = `
      <div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 0.82rem;">
        No upcoming scheduled hearings found in the next 14 days.
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <table class="hearing-table" style="font-size: 0.84rem;">
      <thead>
        <tr>
          <th style="width: 140px;">Hearing Date</th>
          <th style="width: 50px; text-align: center;">Item</th>
          <th>Case Number / Parties</th>
          <th>Court & Room</th>
          <th>Stage</th>
          <th style="text-align: right; width: 140px;">Advance Action</th>
        </tr>
      </thead>
      <tbody>
        ${upcomingCases.map(c => {
          let dateFormatted = c.next_hearing_date || '-';
          try {
            const dateObj = new Date(c.next_hearing_date + "T00:00:00");
            dateFormatted = dateObj.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", year: "numeric" });
          } catch(e) {}

          return `
            <tr>
              <td>
                <span style="display: inline-block; background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); font-size: 0.74rem; padding: 4px 8px; border-radius: 6px; font-weight: 800;">
                  📅 ${escapeHtml(dateFormatted)}
                </span>
              </td>
              <td style="text-align: center; font-weight: 800; color: var(--primary);">
                ${escapeHtml(c.item_number || '-')}
              </td>
              <td class="clickable-case-cell" onclick="openCaseDrawer('${escapeHtml(c.cnr_number)}')">
                <strong style="color: #ffffff; font-size: 0.88rem;">${escapeHtml(c.case_title)}</strong>
                <div style="margin-top: 3px;">
                  <span class="case-number-pill" style="font-size: 0.72rem;">${escapeHtml(c.case_number_formatted || c.cnr_number)}</span>
                  ${c.client_name ? `<span style="font-size: 0.72rem; color: var(--text-muted); margin-left: 6px;">Client: ${escapeHtml(c.client_name)}</span>` : ''}
                </div>
              </td>
              <td>
                <div style="font-weight: 700; color: var(--text-main); font-size: 0.82rem;">${escapeHtml(c.court_name || 'Karur Court')}</div>
                <div style="font-size: 0.72rem; color: var(--text-muted);">${escapeHtml(c.court_room || '-')} &bull; ${escapeHtml(c.judge_name || '-')}</div>
              </td>
              <td>
                <span class="badge ${getBadgeClass(c.case_stage)}" style="font-size: 0.7rem;">${escapeHtml(c.case_stage || 'Hearing')}</span>
              </td>
              <td style="text-align: right;">
                <a href="${getWhatsAppUrl(c)}" target="_blank" class="btn-ui btn-ui-wa" style="padding: 5px 10px; font-size: 0.74rem; font-weight: 800;">
                  📲 WhatsApp
                </a>
              </td>
            </tr>
          `;
        }).join("")}
      </tbody>
    </table>
  `;
}

async function renderRescheduledHearingsSection() {
  const container = document.getElementById("rescheduled-table-container");
  const countBadge = document.getElementById("rescheduled-count-badge");
  if (!container) return;

  try {
    const res = await fetch("/api/history");
    const logs = await res.json();

    if (countBadge) countBadge.innerText = logs.length || 0;

    if (!logs || logs.length === 0) {
      container.innerHTML = `
        <div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 0.82rem;">
          No recent hearing date changes or adjournments recorded yet.
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <table class="hearing-table" style="font-size: 0.84rem;">
        <thead>
          <tr>
            <th style="width: 140px;">Detected Date</th>
            <th>Case Title / Number</th>
            <th>Client</th>
            <th>Previous Date</th>
            <th>New Rescheduled Date</th>
            <th style="text-align: right; width: 150px;">WhatsApp Client Alert</th>
          </tr>
        </thead>
        <tbody>
          ${logs.slice(0, 10).map(log => {
            const waText = encodeURIComponent(
              `*LEGAL NOTICE - CASE ADJOURNMENT / RE-SCHEDULING*\n\n` +
              `Dear ${log.client_name || 'Client'},\n\n` +
              `This is an official update from Advocate R. Anbaiya & Associates regarding your matter: *${log.case_title || log.cnr_number}*.\n\n` +
              `• *Previous Hearing:* ${log.previous_hearing_date || 'N/A'}\n` +
              `• *NEW ADJOURNED DATE:* *${log.new_hearing_date || 'Upcoming'}*\n\n` +
              `Please take note of the new hearing schedule. For queries, contact our chamber.\n\n` +
              `*Advocate R. Anbaiya & Associates*\nKarur District Court Complex`
            );
            const cleanPhone = (log.client_phone || '9842112233').replace(/[^0-9]/g, '');
            const waUrl = `https://wa.me/${cleanPhone}?text=${waText}`;

            return `
              <tr>
                <td style="font-size: 0.76rem; color: var(--text-muted); font-family: var(--font-mono);">
                  ${escapeHtml(log.detected_at || '-')}
                </td>
                <td class="clickable-case-cell" onclick="openCaseDrawer('${escapeHtml(log.cnr_number)}')">
                  <strong style="color: #ffffff; font-size: 0.88rem;">${escapeHtml(log.case_title || log.cnr_number)}</strong>
                  <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 2px;">
                    CNR: ${escapeHtml(log.cnr_number)}
                  </div>
                </td>
                <td>
                  <span style="font-weight: 700; color: var(--text-main);">${escapeHtml(log.client_name || 'Client')}</span><br>
                  <span style="font-size: 0.72rem; color: var(--text-muted);">📞 ${escapeHtml(log.client_phone || '-')}</span>
                </td>
                <td>
                  <span style="text-decoration: line-through; color: #ef4444; font-weight: 700; font-size: 0.78rem;">
                    ${escapeHtml(log.previous_hearing_date || 'None')}
                  </span>
                </td>
                <td>
                  <span style="background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); font-size: 0.78rem; padding: 3px 8px; border-radius: 6px; font-weight: 800;">
                    ➔ ${escapeHtml(log.new_hearing_date || '-')}
                  </span>
                </td>
                <td style="text-align: right;">
                  <a href="${waUrl}" target="_blank" class="btn-ui btn-ui-wa" style="padding: 5px 10px; font-size: 0.74rem; font-weight: 800;">
                    📲 Send New Date
                  </a>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    `;
  } catch(err) {
    console.error("renderRescheduledHearingsSection error:", err);
  }
}

async function loadTrackedCases() {
  try {
    const res = await fetch("/api/cases");
    const data = await res.json();
    allCases = data || [];
    renderUpcomingHearingsPipeline();
    renderRescheduledHearingsSection();

    const kpiActiveCases = document.getElementById("kpi-active-cases");
    const badgeTotalCases = document.getElementById("badge-total-cases");
    const kpiDisposedCases = document.getElementById("kpi-disposed-cases");
    const kpiUpcoming7d = document.getElementById("kpi-upcoming-7d");

    const realToday = getRealTodayDate();
    const activeCount = allCases.filter(c => (c.case_status || "").toUpperCase() !== "DISPOSED").length;
    const disposedCount = allCases.filter(c => (c.case_status || "").toUpperCase() === "DISPOSED").length;

    if (kpiActiveCases) kpiActiveCases.innerText = activeCount;
    if (badgeTotalCases) badgeTotalCases.innerText = allCases.length;
    if (kpiDisposedCases) kpiDisposedCases.innerText = disposedCount;

    const futureCasesCount = allCases.filter(c => c.next_hearing_date && c.next_hearing_date > realToday && (c.case_status || '').toUpperCase() !== 'DISPOSED').length;
    const awaitingCasesCount = allCases.filter(c => c.next_hearing_date && c.next_hearing_date <= realToday && (c.case_status || '').toUpperCase() !== 'DISPOSED').length;
    if (kpiUpcoming7d) kpiUpcoming7d.innerText = futureCasesCount;

    // Update Filter Tab Badges
    const bActive = document.getElementById("badge-active-tab-count");
    const bUpcoming = document.getElementById("badge-upcoming-tab-count");
    const bAwaiting = document.getElementById("badge-awaiting-tab-count");
    const bDisposed = document.getElementById("badge-disposed-tab-count");
    const bAll = document.getElementById("badge-all-tab-count");

    if (bActive) bActive.innerText = activeCount;
    if (bUpcoming) bUpcoming.innerText = futureCasesCount;
    if (bAwaiting) bAwaiting.innerText = awaitingCasesCount;
    if (bDisposed) bDisposed.innerText = disposedCount;
    if (bAll) bAll.innerText = allCases.length;

    filterAllCasesView(currentCaseFilterTab || "ACTIVE");
    renderClientsTable(allCases.filter(c => (c.case_status || '').toUpperCase() !== 'DISPOSED'));
    renderWhatsAppDockets(allCases.filter(c => (c.case_status || '').toUpperCase() !== 'DISPOSED'));
  } catch (e) {
    console.error("loadTrackedCases error:", e);
  }
}

let currentCaseFilterTab = "ACTIVE";

window.filterAllCasesView = function(category) {
  currentCaseFilterTab = category;
  document.querySelectorAll("#all-cases-filter-tabs .court-tab-btn").forEach(b => b.classList.remove("active"));
  const activeBtn = document.getElementById(`filter-btn-${category.toLowerCase()}`);
  if (activeBtn) activeBtn.classList.add("active");

  const realToday = getRealTodayDate();
  let filtered = allCases || [];

  if (category === "ACTIVE") {
    filtered = filtered.filter(c => (c.case_status || '').toUpperCase() !== 'DISPOSED');
  } else if (category === "UPCOMING") {
    filtered = filtered.filter(c => c.next_hearing_date && c.next_hearing_date > realToday && (c.case_status || '').toUpperCase() !== 'DISPOSED');
  } else if (category === "AWAITING") {
    filtered = filtered.filter(c => c.next_hearing_date && c.next_hearing_date <= realToday && (c.case_status || '').toUpperCase() !== 'DISPOSED');
  } else if (category === "DISPOSED") {
    filtered = filtered.filter(c => (c.case_status || '').toUpperCase() === 'DISPOSED');
  }

  const query = (document.getElementById("all-cases-search")?.value || "").toLowerCase();
  if (query) {
    filtered = filtered.filter(c => 
      (c.case_title || '').toLowerCase().includes(query) ||
      (c.client_name || '').toLowerCase().includes(query) ||
      (c.cnr_number || '').toLowerCase().includes(query) ||
      (c.case_number_formatted || '').toLowerCase().includes(query)
    );
  }

  renderAllCasesTable(filtered);
};

function renderAllCasesTable(cases) {
  const tbody = document.getElementById("all-cases-tbody");
  if (!tbody) return;

  if (!cases || cases.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="padding: 32px; text-align: center; color: var(--text-muted);">
          <div style="font-size: 1.8rem; margin-bottom: 6px;">📁</div>
          <strong>No Cases Found in this Category</strong>
        </td>
      </tr>
    `;
    return;
  }

  const realToday = getRealTodayDate();
  tbody.innerHTML = cases.map(c => {
    const isDisposed = (c.case_status || "").toUpperCase() === "DISPOSED";
    const isHearingToday = !isDisposed && c.next_hearing_date === realToday;
    const isUpcoming = !isDisposed && c.next_hearing_date && c.next_hearing_date > realToday;
    const isAwaiting = !isDisposed && (!c.next_hearing_date || c.next_hearing_date < realToday);

    let statusTag = '';
    if (isDisposed) {
      statusTag = '<span style="background: #334155; color: #f1f5f9; padding: 2px 8px; border-radius: 10px; font-size: 0.72rem; font-weight: 700; display: inline-block;">🏁 Disposed</span>';
    } else if (isHearingToday) {
      statusTag = '<span style="background: #059669; color: #ffffff; padding: 2px 8px; border-radius: 10px; font-size: 0.72rem; font-weight: 800; display: inline-block;">🔔 Hearing Today</span>';
    } else if (isUpcoming) {
      statusTag = '<span style="background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); padding: 2px 8px; border-radius: 10px; font-size: 0.72rem; font-weight: 700; display: inline-block;">📅 Upcoming</span>';
    } else {
      statusTag = '<span style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); padding: 2px 8px; border-radius: 10px; font-size: 0.72rem; font-weight: 600; display: inline-block;" title="Past hearing date. Awaiting court adjourned date posting.">⏳ Awaiting Next Date</span>';
    }

    return `
    <tr class="clickable-case-row">
      <td class="clickable-case-cell" onclick="openCaseDrawer('${escapeHtml(c.cnr_number)}')">
        <div style="margin-bottom: 4px;">
          <span class="case-number-pill">${escapeHtml(c.case_number_formatted || '-')}</span>
        </div>
        <strong style="font-size: 0.95rem; color: #ffffff; display: block; margin-bottom: 3px; font-weight: 800;">${escapeHtml(c.client_name || 'Client')}</strong>
        <div class="client-phone-pill">📞 ${escapeHtml(c.client_phone || '-')}</div>
      </td>
      <td class="clickable-case-cell" onclick="openCaseDrawer('${escapeHtml(c.cnr_number)}')" style="max-width: 380px;">
        <div class="case-title-text" style="font-size: 0.96rem; margin-bottom: 4px;">${escapeHtml(c.case_title)}</div>
        <div style="font-size: 0.8rem; color: #94a3b8; line-height: 1.35; margin-bottom: 5px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;" title="${escapeHtml(c.parties || '')}">
          ${escapeHtml(c.parties || '')}
        </div>
        <div>
          <span class="cnr-number-pill" style="font-size: 0.74rem;">${escapeHtml(c.cnr_number)}</span>
          ${c.notes ? `<span class="notes-badge-pill" style="font-size: 0.74rem; margin-left: 4px;">📌 ${escapeHtml(c.notes)}</span>` : ''}
        </div>
      </td>
      <td onclick="openCaseDrawer('${escapeHtml(c.cnr_number)}')">
        <div style="font-size: 0.9rem; color: #ffffff; font-weight: 700;">${escapeHtml(c.court_name || 'District Court')}</div>
        <div class="judge-text" style="margin-top: 3px;">
          ${c.court_room ? `<span class="room-badge" style="font-size:0.75rem; padding: 1px 6px;">${escapeHtml(c.court_room)}</span> ` : ''}
          ${escapeHtml(c.judge_name || '-')}
        </div>
      </td>
      <td>
        <strong style="color: var(--text-gold); font-size: 0.92rem; display: block; font-weight: 800; font-family: var(--font-mono);">${escapeHtml(c.next_hearing_date || 'Awaiting Date')}</strong>
        <div style="margin-top: 4px; display: flex; gap: 4px; flex-wrap: wrap;">
          ${statusTag}
          <span class="badge ${getBadgeClass(c.case_stage)}" style="font-size: 0.72rem; padding: 2px 6px;">${escapeHtml(c.case_stage || 'Evidence')}</span>
        </div>
      </td>

      <td style="text-align: right;">
        <div style="display: flex; gap: 6px; justify-content: flex-end; align-items: center;">
          <a href="${getWhatsAppUrl(c)}" target="_blank" class="table-action-btn" style="background: rgba(16, 185, 129, 0.2); color: #34d399; border-color: rgba(16, 185, 129, 0.4); font-weight: 800;" title="Send WhatsApp Notice">💬</a>
          <button onclick="toggleCaseDisposed('${escapeHtml(c.cnr_number)}', '${escapeHtml(c.case_status || 'PENDING')}')" class="table-action-btn" title="${c.case_status === 'DISPOSED' ? 'Reopen Case (Active)' : 'Mark Case Disposed / Closed (Freeze API)'}">${c.case_status === 'DISPOSED' ? '🔓' : '🏁'}</button>
          <button onclick="syncSingleCase('${escapeHtml(c.cnr_number)}')" class="table-action-btn" title="Check Live eCourts">🔄</button>
          <a href="/api/export-case/${encodeURIComponent(c.cnr_number)}" target="_blank" class="table-action-btn" title="Print Case Sheet">🖨️</a>
          <button onclick="deleteSingleCase('${escapeHtml(c.cnr_number)}')" class="table-action-btn" style="color: #f87171;" title="Remove Case">🗑️</button>
        </div>
      </td>
    </tr>
  `).join("");
}

function renderClientsTable(cases) {
  const tbody = document.getElementById("clients-tbody");
  if (!tbody) return;

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
  tbody.innerHTML = clientList.map(cl => `
    <tr>
      <td><strong style="color: #ffffff; font-size: 0.95rem; font-weight: 800;">${escapeHtml(cl.name)}</strong></td>
      <td><div class="client-phone-pill">📞 ${escapeHtml(cl.phone)}</div></td>
      <td><span class="badge badge-evidence">${escapeHtml(cl.role)}</span></td>
      <td><strong style="color: #ffffff; font-size: 0.9rem;">${cl.count} Active Matter${cl.count > 1 ? 's' : ''}</strong></td>
      <td>
        <strong style="color: var(--text-gold); font-family: var(--font-mono); font-weight: 800; font-size: 0.92rem;">${escapeHtml(cl.nextDate)}</strong>
        <div style="margin-top: 3px;"><span style="color: #34d399; font-weight: 700; font-size: 0.72rem; background: rgba(16, 185, 129, 0.15); padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(16, 185, 129, 0.3);">✓ Active</span></div>
      </td>
      <td style="text-align: right;">
        <a href="${getWhatsAppUrl(cl.caseObj)}" target="_blank" class="btn-ui btn-ui-wa" style="padding: 6px 12px; font-size: 0.78rem; font-weight: 800;">
          📲 Send Notice
        </a>
      </td>
    </tr>
  `).join("");
}

async function loadLeads() {
  try {
    const res = await fetch("/api/leads");
    const data = await res.json();
    allLeads = data || [];

    const badgeLeads = document.getElementById("badge-leads-count");
    if (badgeLeads) badgeLeads.innerText = allLeads.length;

    const tbody = document.getElementById("leads-tbody");
    if (!tbody) return;

    if (allLeads.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" style="padding: 24px; text-align: center; color: var(--text-muted);">
            No prospective inquiries in pipeline. Click <strong>"+ Add New Inquiry"</strong>.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = allLeads.map(l => `
      <tr>
        <td><strong style="color: #ffffff; font-size: 0.95rem; font-weight: 800;">${escapeHtml(l.client_name)}</strong></td>
        <td><div class="client-phone-pill">${escapeHtml(l.client_phone)}</div></td>
        <td><span class="badge badge-evidence">${escapeHtml(l.matter_type)}</span></td>
        <td style="color: #e2e8f0; font-weight: 600;">${escapeHtml(l.expected_court)}</td>
        <td><span class="badge badge-steps">${escapeHtml(l.status)}</span></td>
        <td><span style="font-size: 0.82rem; color: #cbd5e1; font-weight: 600;">${escapeHtml(l.notes || '-')}</span></td>
        <td style="text-align: right;">
          <a href="https://wa.me/${(l.client_phone || '').replace(/[^0-9]/g, '')}?text=Hello%20${encodeURIComponent(l.client_name)}%2C%20Advocate%20R.%20Anbaiya%20Office%20Notice" target="_blank" class="btn-ui btn-ui-wa" style="padding: 6px 12px; font-size: 0.78rem; font-weight: 800;">
            💬 WhatsApp
          </a>
        </td>
      </tr>
    `).join("");
  } catch (e) {}
}

function renderWhatsAppDockets(cases) {
  const container = document.getElementById("whatsapp-dockets-list");
  if (!container) return;

  if (!cases || cases.length === 0) {
    container.innerHTML = `<p style="text-align: center; color: var(--text-muted); padding: 24px;">No notices ready.</p>`;
    return;
  }

  container.innerHTML = cases.map(c => `
    <div style="background: #090e1a; border: 1.5px solid var(--border-color); border-radius: var(--radius-md); padding: 18px 22px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 16px rgba(0,0,0,0.3);">
      <div>
        <div style="font-weight: 800; font-size: 1.02rem; color: #ffffff; display: flex; align-items: center; gap: 10px;">
          <span>${escapeHtml(c.client_name || 'Client')}</span>
          <span class="client-phone-pill">📞 ${escapeHtml(c.client_phone || '-')}</span>
        </div>
        <div style="font-size: 0.88rem; color: #cbd5e1; margin-top: 6px; display: flex; align-items: center; flex-wrap: wrap; gap: 8px;">
          <span>Case: <strong style="color: #ffffff;">${escapeHtml(c.case_title)}</strong></span>
          <span class="case-number-pill" style="font-size: 0.8rem; padding: 2px 8px;">${escapeHtml(c.case_number_formatted || c.cnr_number)}</span>
          <span class="room-badge" style="font-size: 0.8rem; margin: 0; padding: 2px 8px;">Item #${escapeHtml(c.item_number || '-')} &bull; ${escapeHtml(c.court_room || '-')}</span>
          <span class="badge ${getBadgeClass(c.case_stage)}" style="font-size: 0.74rem; padding: 2px 8px;">${escapeHtml(c.case_stage || 'Evidence')}</span>
        </div>
      </div>
      <a href="${getWhatsAppUrl(c)}" target="_blank" class="btn-ui btn-ui-wa" style="padding: 10px 18px; font-weight: 800; font-size: 0.85rem; box-shadow: 0 4px 14px rgba(16, 185, 129, 0.4);">
        📲 Send WhatsApp
      </a>
    </div>
  `).join("");
}

function renderCalendar(dateObj) {
  const container = document.getElementById("calendar-grid-container");
  if (!container) return;

  const year = dateObj.getFullYear();
  const month = dateObj.getMonth();
  const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  
  const title = document.getElementById("calendar-month-title");
  if (title) {
    title.innerText = `📅 Hearing Calendar • ${monthNames[month]} ${year}`;
  }

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  let html = `
    <div style="font-weight: 800; color: var(--text-gold); font-size: 0.76rem; padding: 6px;">SUN</div>
    <div style="font-weight: 800; color: var(--text-gold); font-size: 0.76rem; padding: 6px;">MON</div>
    <div style="font-weight: 800; color: var(--text-gold); font-size: 0.76rem; padding: 6px;">TUE</div>
    <div style="font-weight: 800; color: var(--text-gold); font-size: 0.76rem; padding: 6px;">WED</div>
    <div style="font-weight: 800; color: var(--text-gold); font-size: 0.76rem; padding: 6px;">THU</div>
    <div style="font-weight: 800; color: var(--text-gold); font-size: 0.76rem; padding: 6px;">FRI</div>
    <div style="font-weight: 800; color: var(--text-gold); font-size: 0.76rem; padding: 6px;">SAT</div>
  `;

  for (let i = 0; i < firstDay; i++) {
    html += `<div style="padding: 12px; background: rgba(255,255,255,0.01); border: 1px solid var(--border-light); border-radius: var(--radius-sm);"></div>`;
  }

  for (let day = 1; day <= daysInMonth; day++) {
    const monthStr = String(month + 1).padStart(2, '0');
    const dayStr = String(day).padStart(2, '0');
    const fullDateStr = `${year}-${monthStr}-${dayStr}`;

    const matchedCases = allCases.filter(c => c.next_hearing_date === fullDateStr);
    const hasHearings = matchedCases.length > 0;

    html += `
      <div onclick="selectCalendarDate('${fullDateStr}')" style="padding: 10px 6px; cursor: pointer; background: ${hasHearings ? 'rgba(245, 158, 11, 0.15)' : '#0e1526'}; border: 1px solid ${hasHearings ? 'var(--border-gold)' : 'var(--border-color)'}; border-radius: var(--radius-sm); transition: var(--transition);" title="View hearings on ${fullDateStr}">
        <div style="font-weight: 800; font-size: 0.88rem; color: ${hasHearings ? 'var(--text-gold)' : '#ffffff'};">${day}</div>
        ${hasHearings ? `<div style="background: linear-gradient(135deg, #fbbf24, #d97706); color: #090d16; font-size: 0.65rem; padding: 2px 4px; border-radius: 4px; margin-top: 4px; font-weight: 800;">${matchedCases.length} Cases</div>` : ''}
      </div>
    `;
  }

  container.innerHTML = html;
}

window.selectCalendarDate = function(dateStr) {
  const heading = document.getElementById("calendar-selected-day-heading");
  const list = document.getElementById("calendar-selected-day-list");
  if (!heading || !list) return;

  heading.innerText = `Scheduled Hearings for ${dateStr}`;
  const matched = allCases.filter(c => c.next_hearing_date === dateStr);

  if (matched.length === 0) {
    list.innerHTML = `<p style="color: var(--text-muted); font-size: 0.78rem; padding: 8px 0;">No hearings scheduled on ${dateStr}.</p>`;
    return;
  }

  list.innerHTML = matched.map(c => `
    <div style="background: #080c15; border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 12px 16px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
      <div>
        <strong style="color: #ffffff; font-size: 0.9rem;">${escapeHtml(c.case_title)}</strong> <span style="color: var(--text-gold); font-weight: 700;">(${escapeHtml(c.client_name || 'Client')})</span><br>
        <span style="font-size: 0.78rem; color: var(--text-secondary); margin-top: 2px; display: inline-block;">${escapeHtml(c.court_name || '')} &bull; Item #${escapeHtml(c.item_number || '-')} &bull; <span style="color: #38bdf8;">${escapeHtml(c.case_stage || 'Hearing')}</span></span>
      </div>
      <a href="${getWhatsAppUrl(c)}" target="_blank" class="btn-ui btn-ui-wa" style="padding: 5px 12px; font-size: 0.76rem; font-weight: 800;">💬 WhatsApp</a>
    </div>
  `).join("");
};

async function loadAdvocateSettings() {
  try {
    const res = await fetch("/api/advocate-settings");
    const data = await res.json();
    currentAdvocateSettings = data || {};
    
    const firm = data.firm_name || "R. ANBAIYA & ASSOCIATES";
    const lawyer = data.lawyer_name || "Advocate R. Anbaiya";

    const sidebarBrandTitle = document.getElementById("sidebar-brand-title");
    if (sidebarBrandTitle) sidebarBrandTitle.innerText = firm;

    const sidebarAdvocateName = document.getElementById("sidebar-advocate-name");
    if (sidebarAdvocateName) sidebarAdvocateName.innerText = lawyer;

    const headerGreeting = document.getElementById("header-advocate-greeting");
    if (headerGreeting) headerGreeting.innerText = `Good Morning, ${lawyer}`;
  } catch (e) {}
}

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

// =========================================================================
// 6. APPLICATION STARTUP & FORM LISTENERS
// =========================================================================
document.addEventListener("DOMContentLoaded", () => {
  // Search listeners
  const allCasesSearch = document.getElementById("all-cases-search");
  if (allCasesSearch) {
    allCasesSearch.addEventListener("input", () => {
      filterAllCasesView(currentCaseFilterTab || "ACTIVE");
    });
  }

  const dashboardDatePicker = document.getElementById("dashboard-date-picker");
  if (dashboardDatePicker) {
    dashboardDatePicker.addEventListener("change", () => {
      loadDailyCauseList(dashboardDatePicker.value);
    });
  }

  const btnPrevMonth = document.getElementById("btn-prev-month");
  if (btnPrevMonth) {
    btnPrevMonth.addEventListener("click", () => {
      currentCalendarDate.setMonth(currentCalendarDate.getMonth() - 1);
      renderCalendar(currentCalendarDate);
    });
  }

  const btnNextMonth = document.getElementById("btn-next-month");
  if (btnNextMonth) {
    btnNextMonth.addEventListener("click", () => {
      currentCalendarDate.setMonth(currentCalendarDate.getMonth() + 1);
      renderCalendar(currentCalendarDate);
    });
  }

  // Fast Direct Intake Form Handler
  const intakeForm = document.getElementById("direct-intake-form");
  if (intakeForm) {
    intakeForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btnSubmit = document.getElementById("btn-confirm-intake");
      if (btnSubmit) {
        btnSubmit.disabled = true;
        btnSubmit.innerText = "⏳ Adding Client...";
      }

      const nameInput = document.getElementById("wiz-client-name");
      const caseNoInput = document.getElementById("wiz-case-no");
      const phoneInput = document.getElementById("wiz-client-phone");
      const courtSelect = document.getElementById("wiz-court-name");
      const dateInput = document.getElementById("wiz-hearing-date");
      const stageInput = document.getElementById("wiz-stage");
      const roomInput = document.getElementById("wiz-room");
      const itemInput = document.getElementById("wiz-item");
      const notesInput = document.getElementById("wiz-notes");

      try {
        await fetch("/api/check-case", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            client_name: nameInput ? nameInput.value.trim() : "",
            case_number: caseNoInput ? caseNoInput.value.trim() : "",
            case_number_formatted: caseNoInput ? caseNoInput.value.trim() : "",
            cnr: caseNoInput ? caseNoInput.value.trim().toUpperCase() : "",
            client_phone: phoneInput ? phoneInput.value.trim() : "",
            court_name: courtSelect ? courtSelect.value : "Principal Sub Court, Karur",
            next_hearing_date: (dateInput && dateInput.value) ? dateInput.value : getSelectedOrTodayDate(),
            case_stage: stageInput ? stageInput.value.trim() : "Evidence",
            court_room: roomInput ? roomInput.value.trim() : "Room 1",
            item_number: itemInput ? itemInput.value.trim() : "1",
            notes: notesInput ? notesInput.value.trim() : "",
            force_live: false
          })
        });

        const modal = document.getElementById("case-intake-modal");
        if (modal) modal.style.display = "none";
        
        alert(`✅ Client "${nameInput ? nameInput.value : 'Client'}" successfully added to tracking!`);
        intakeForm.reset();
        await loadTrackedCases();
        await loadDailyCauseList(getSelectedOrTodayDate());
        window.switchView("view-cases");
      } catch (err) {
        alert("Failed to add client: " + err.message);
      } finally {
        if (btnSubmit) {
          btnSubmit.disabled = false;
          btnSubmit.innerText = "➕ Add & Track Client";
        }
      }
    });
  }

  // Meta WhatsApp Form Listener
  const metaWaForm = document.getElementById("meta-wa-form");
  if (metaWaForm) {
    metaWaForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const phoneIdInput = document.getElementById("meta-phone-id");
      const tokenInput = document.getElementById("meta-access-token");
      const wabaIdInput = document.getElementById("meta-waba-id");

      try {
        const res = await fetch("/api/whatsapp/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            phone_number_id: phoneIdInput ? phoneIdInput.value.trim() : "",
            access_token: tokenInput ? tokenInput.value.trim() : "",
            waba_id: wabaIdInput ? wabaIdInput.value.trim() : "",
            auto_dispatch: true
          })
        });
        const data = await res.json();
        if (data.success) {
          alert("✅ Official Meta WhatsApp Cloud API Credentials Saved Successfully!");
          loadMetaConfig();
        }
      } catch (err) {
        alert("Failed to save Meta WhatsApp credentials: " + err.message);
      }
    });
  }

  // eCourts API Key Form Listener
  const apiKeyForm = document.getElementById("ecourts-api-key-form");
  if (apiKeyForm) {
    apiKeyForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const keyInput = document.getElementById("cfg-ecourts-api-key");
      const keyVal = keyInput ? keyInput.value.trim() : "";
      if (!keyVal) {
        alert("Please enter a valid eCourts API Key.");
        return;
      }

      try {
        const res = await fetch("/api/save-key", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ api_key: keyVal })
        });
        const data = await res.json();
        if (data.success) {
          alert(`✅ eCourts API Key Saved & Verified!\nMasked Key: ${data.masked_key}`);
          keyInput.value = "";
          await loadApiKeyStatus();
          await loadSchedulerEvaluation();
        } else {
          alert("❌ Failed to save key: " + (data.error || "Unknown error"));
        }
      } catch (err) {
        alert("Error saving API key: " + err.message);
      }
    });
  }

  // Telegram Form Listener
  const telegramForm = document.getElementById("telegram-config-form");
  if (telegramForm) {
    telegramForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const tokenInput = document.getElementById("cfg-telegram-token");
      const chatIdInput = document.getElementById("cfg-telegram-chat-id");

      try {
        const res = await fetch("/api/telegram/save-config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            bot_token: tokenInput ? tokenInput.value.trim() : "",
            chat_id: chatIdInput ? chatIdInput.value.trim() : ""
          })
        });
        const data = await res.json();
        if (data.success) {
          alert("✅ Telegram Bot Configuration Saved Successfully!");
          loadTelegramConfig();
        } else {
          alert("❌ Failed: " + (data.error || "Unknown error"));
        }
      } catch (err) {
        alert("Error saving Telegram config: " + err.message);
      }
    });
  }

  // Date picker change listener
  const datePicker = document.getElementById("dashboard-date-picker");
  if (datePicker) {
    const todayStr = getSelectedOrTodayDate();
    datePicker.value = todayStr;
    datePicker.addEventListener("change", () => {
      loadDailyCauseList(datePicker.value);
    });
  }

  // Initial Loads & Start Live Sync Loop
  async function initApp() {
    window.dismissStartupSplash();
    try { await loadAdvocateSettings(); } catch (e) { console.warn("loadAdvocateSettings error:", e); }
    try { await loadApiKeyStatus(); } catch (e) { console.warn("loadApiKeyStatus error:", e); }
    try { await loadSchedulerEvaluation(); } catch (e) { console.warn("loadSchedulerEvaluation error:", e); }
    try { await loadHearingChangeLogs(); } catch (e) { console.warn("loadHearingChangeLogs error:", e); }
    try { await loadMetaConfig(); } catch (e) { console.warn("loadMetaConfig error:", e); }
    try { await loadTelegramConfig(); } catch (e) { console.warn("loadTelegramConfig error:", e); }
    try { await loadTrackedCases(); } catch (e) { console.warn("loadTrackedCases error:", e); }
    try { await loadDailyCauseList(getSelectedOrTodayDate()); } catch (e) { console.warn("loadDailyCauseList error:", e); }
    try { await loadLeads(); } catch (e) { console.warn("loadLeads error:", e); }
    try { renderCalendar(currentCalendarDate); } catch (e) { console.warn("renderCalendar error:", e); }
    try { startLiveSyncLoop(); } catch (e) { console.warn("startLiveSyncLoop error:", e); }
  }
  initApp();
});

// =========================================================================
// 7. eCOURTS API KEY & CREDIT SHIELD MANAGEMENT
// =========================================================================
async function loadApiKeyStatus() {
  try {
    const res = await fetch("/api/key-status");
    const data = await res.json();
    const keyInput = document.getElementById("cfg-ecourts-api-key");
    const badge = document.getElementById("ecourts-api-status-badge");
    const guardLabel = document.getElementById("credit-guard-label");
    const topGuardLabel = document.getElementById("credits-balance-label");

    if (keyInput && data.masked_key) {
      keyInput.placeholder = `Saved: ${data.masked_key}`;
    }

    if (badge) {
      if (data.configured) {
        badge.innerText = "✓ Active & Guarded";
        badge.style.background = "rgba(16, 185, 129, 0.15)";
        badge.style.color = "#34d399";
        badge.style.borderColor = "rgba(16, 185, 129, 0.35)";
      } else {
        badge.innerText = "Chamber Vault Mode";
        badge.style.background = "rgba(56, 189, 248, 0.15)";
        badge.style.color = "#38bdf8";
        badge.style.borderColor = "rgba(56, 189, 248, 0.35)";
      }
    }

    if (guardLabel && data.credit_guard) {
      guardLabel.innerText = data.credit_guard.message || "🛡️ Credit Guard: Zero-Credit Chamber Vault Active";
    }

    if (topGuardLabel) {
      topGuardLabel.innerText = data.configured ? "Guarded (Live)" : "Vault Mode (0 Credits)";
    }
  } catch (e) {}
}

window.toggleApiKeyVisibility = function() {
  const keyInput = document.getElementById("cfg-ecourts-api-key");
  if (!keyInput) return;
  if (keyInput.type === "password") {
    keyInput.type = "text";
  } else {
    keyInput.type = "password";
  }
};

window.loadSchedulerEvaluation = async function() {
  try {
    const res = await fetch("/api/scheduler/evaluation");
    const data = await res.json();

    const elTotal = document.getElementById("shield-total-cases");
    const elSleeping = document.getElementById("shield-sleeping-cases");
    const elDisposed = document.getElementById("shield-disposed-cases");
    const elSaved = document.getElementById("shield-saved-amount");

    if (elTotal) elTotal.innerText = data.total_cases || 0;
    if (elSleeping) elSleeping.innerText = data.sleeping_cases || 0;
    if (elDisposed) elDisposed.innerText = data.disposed_cases || 0;
    if (elSaved) elSaved.innerText = `₹${(data.credits_saved_today || 0).toFixed(2)}`;
  } catch (e) {}
};

window.triggerSmartSyncNow = async function() {
  try {
    const res = await fetch("/api/scheduler/smart-sync", { method: "POST" });
    const data = await res.json();
    alert(`⚡ Smart Predictive Sync Complete!\n\n• Monitored Cases: ${data.total_monitored}\n• Checked Due Cases: ${data.checked_count}\n• Sleeping Cases (0 Credits): ${data.sleeping_count}\n• Updated Next Hearings: ${data.updated_count}\n• Estimated Rupees Saved: ₹${data.credits_saved_rupees}`);
    await loadTrackedCases();
    await loadDailyCauseList(getSelectedOrTodayDate());
    await loadSchedulerEvaluation();
    await loadHearingChangeLogs();
  } catch (err) {
    alert("Smart sync error: " + err.message);
  }
};

window.loadHearingChangeLogs = async function() {
  const container = document.getElementById("hearing-change-logs-container");
  if (!container) return;

  try {
    const res = await fetch("/api/history");
    const logs = await res.json();

    if (!logs || logs.length === 0) {
      container.innerHTML = `<p style="text-align: center; color: var(--text-muted); font-size: 0.8rem; padding: 12px 0;">No hearing date changes recorded yet. When judges adjourn attended cases, they will appear here automatically.</p>`;
      return;
    }

    container.innerHTML = `
      <div style="overflow-x: auto;">
        <table class="hearing-table" style="font-size: 0.82rem;">
          <thead>
            <tr>
              <th style="width: 25%;">Case / Client</th>
              <th style="width: 25%;">Previous Date</th>
              <th style="width: 25%;">New Hearing Date</th>
              <th style="width: 25%; text-align: right;">Action</th>
            </tr>
          </thead>
          <tbody>
            ${logs.map(l => `
              <tr>
                <td>
                  <strong>${escapeHtml(l.case_title || l.cnr_number)}</strong>
                  <div style="font-size: 0.72rem; color: var(--text-muted);">${escapeHtml(l.client_name || '')} (${escapeHtml(l.client_phone || '-')})</div>
                </td>
                <td style="color: #94a3b8; font-family: var(--font-mono);">${escapeHtml(l.previous_hearing_date || 'N/A')}</td>
                <td style="color: #34d399; font-weight: 800; font-family: var(--font-mono);">${escapeHtml(l.new_hearing_date || '-')}</td>
                <td style="text-align: right;">
                  <a href="https://wa.me/${(l.client_phone || '').replace(/[^0-9]/g, '')}?text=${encodeURIComponent(`⚖️ Court Hearing Update for ${l.case_title}: Your hearing has been adjourned to ${l.new_hearing_date}.`)}" target="_blank" class="btn-ui btn-ui-wa" style="font-size: 0.7rem; padding: 3px 8px;">📲 Send Notice</a>
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<p style="color: #f87171; font-size: 0.8rem;">Failed to load history logs: ${err.message}</p>`;
  }
};

window.toggleCaseDisposed = async function(cnr, currentStatus) {
  const isDisposed = (currentStatus || "").toUpperCase() === "DISPOSED";
  const targetStatus = isDisposed ? "PENDING" : "DISPOSED";
  const actionName = isDisposed ? "Reopen Case" : "Mark as Disposed (Freeze API Checks)";

  if (!confirm(`Are you sure you want to ${actionName} for case ${cnr}?`)) return;

  try {
    const res = await fetch(`/api/cases/${encodeURIComponent(cnr)}/status`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: targetStatus })
    });
    const data = await res.json();
    if (data.success) {
      alert(`✅ Case status updated to "${targetStatus}"!\n${targetStatus === 'DISPOSED' ? '❄️ Case is now frozen in Chamber Vault (0 API credits used forever).' : '⚡ Case reactivated for hearing monitoring.'}`);
      await loadTrackedCases();
      await loadDailyCauseList(getSelectedOrTodayDate());
      await loadSchedulerEvaluation();
    } else {
      alert("❌ Failed to update case status.");
    }
  } catch (err) {
    alert("Error: " + err.message);
  }
};

// =========================================================================
// 8. OFFICIAL META WHATSAPP CLOUD API INTEGRATION
// =========================================================================
async function loadMetaConfig() {
  try {
    const res = await fetch("/api/whatsapp/config");
    const data = await res.json();
    
    const phoneInput = document.getElementById("meta-phone-id");
    const tokenInput = document.getElementById("meta-access-token");
    const wabaInput = document.getElementById("meta-waba-id");
    const badge = document.getElementById("meta-status-badge");

    if (phoneInput && data.phone_number_id) phoneInput.value = data.phone_number_id;
    if (wabaInput && data.waba_id) wabaInput.value = data.waba_id;
    if (tokenInput && data.masked_token) tokenInput.placeholder = `Saved: ${data.masked_token}`;

    if (badge) {
      if (data.configured) {
        badge.innerText = "✓ Meta API Active";
        badge.style.background = "#ecfdf5";
        badge.style.color = "#065f46";
      } else {
        badge.innerText = "Unconfigured";
        badge.style.background = "#f1f5f9";
        badge.style.color = "#64748b";
      }
    }
  } catch (e) {}
}

window.testMetaWhatsApp = async function() {
  const phone = prompt("Enter your 10-digit WhatsApp phone number to receive the test notice (e.g. 9842112233):");
  if (!phone) return;

  try {
    const res = await fetch("/api/whatsapp/test-send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone: phone.trim() })
    });
    const result = await res.json();

    if (result.success) {
      alert(`✅ Official Meta WhatsApp Message Sent Successfully to +${result.recipient}!\nMessage ID: ${result.message_id}`);
    } else {
      alert(`❌ Meta WhatsApp Send Failed:\n${result.error}`);
    }
  } catch (err) {
    alert("Test failed: " + err.message);
  }
};

window.dispatchAllViaMetaCloud = async function() {
  const btn = document.getElementById("btn-meta-dispatch-all");
  if (btn) {
    btn.disabled = true;
    btn.innerText = "⏳ Dispatching via Meta Cloud API...";
  }

  const targetDate = (causeListData && causeListData.target_date) || getSelectedOrTodayDate();
  try {
    const res = await fetch("/api/whatsapp/dispatch-all", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: targetDate })
    });
    const result = await res.json();

    if (result.success) {
      alert(`✅ Official Meta WhatsApp Dispatch Complete!\n\n• Successfully Sent: ${result.sent} Notices\n• Failed: ${result.failed}\n• Total: ${result.total}`);
      const modal = document.getElementById("bulk-whatsapp-modal");
      if (modal) modal.style.display = "none";
    } else {
      alert(`❌ Dispatch Failed:\n${result.error || 'Check Meta Cloud API configuration in Settings.'}`);
    }
  } catch (err) {
    alert("Dispatch error: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      const count = (causeListData && causeListData.total_hearings) || '';
      btn.innerText = `🛡️ Official Meta Cloud Auto-Dispatch${count ? ` (${count})` : ''}`;
    }
  }
};

window.dispatchSingleViaMeta = async function(cnr) {
  try {
    const res = await fetch("/api/whatsapp/dispatch-single", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cnr_number: cnr })
    });
    const result = await res.json();

    if (result.success) {
      alert(`✅ Official Meta Notice sent to client (+${result.recipient})!`);
    } else {
      alert(`❌ Failed to send via Meta Cloud API: ${result.error}\nFalling back to 1-Click WhatsApp link.`);
    }
  } catch (err) {
    alert("Error: " + err.message);
  }
};

// =========================================================================
// 8. TELEGRAM AUTONOMOUS BOT DISPATCH & CHAT ID AUTO-DETECTOR
// =========================================================================
async function loadTelegramConfig() {
  try {
    const res = await fetch("/api/telegram/status");
    const data = await res.json();
    const tokenInput = document.getElementById("cfg-telegram-token");
    const chatIdInput = document.getElementById("cfg-telegram-chat-id");
    const badge = document.getElementById("telegram-status-badge");

    if (data.chat_id && chatIdInput && !chatIdInput.value) {
      chatIdInput.value = data.chat_id;
    }
    if (badge) {
      badge.innerText = data.configured ? "Connected" : (data.has_token ? "Token Active" : "Unconfigured");
      badge.style.background = data.configured ? "#15803d" : "#0369a1";
    }
  } catch (e) {
    console.error("loadTelegramConfig error:", e);
  }
}

window.autoDetectTelegramChatId = async function() {
  const tokenInput = document.getElementById("cfg-telegram-token");
  const tok = tokenInput ? tokenInput.value.trim() : "";
  try {
    const res = await fetch("/api/telegram/sync-chat-id", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bot_token: tok })
    });
    const data = await res.json();
    if (data.success) {
      const chatIdInput = document.getElementById("cfg-telegram-chat-id");
      if (chatIdInput) chatIdInput.value = data.chat_id;
      alert(`🎉 Connected Successfully!\nDetected Chat ID: ${data.chat_id}`);
      await loadTelegramConfig();
    } else {
      alert(`⚠️ ${data.error || "No messages found. Please open @jarvis_prime_remote_bot on Telegram, press START (or send a message), and try again."}`);
    }
  } catch (e) {
    alert("Error detecting Telegram Chat ID: " + e.message);
  }
};

window.sendTelegramTestAlert = async function() {
  const chatIdInput = document.getElementById("cfg-telegram-chat-id");
  const chatId = chatIdInput ? chatIdInput.value.trim() : "";
  try {
    const res = await fetch("/api/telegram/send-test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chatId })
    });
    const data = await res.json();
    if (data.success) {
      alert("✅ Test Alert sent to your Telegram successfully! Check @jarvis_prime_remote_bot on your phone.");
    } else {
      alert(`❌ Telegram Dispatch Failed: ${data.error || "Ensure you have pressed /start in @jarvis_prime_remote_bot"}`);
    }
  } catch (e) {
    alert("Error sending Telegram test alert: " + e.message);
  }
};

window.dispatchTelegramDocket = async function() {
  const targetDate = getSelectedOrTodayDate();
  try {
    const res = await fetch("/api/telegram/dispatch-docket", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: targetDate })
    });
    const data = await res.json();
    if (data.success) {
      alert(`✈️ Hearing Board Docket for ${targetDate} dispatched to Telegram (@jarvis_prime_remote_bot)!`);
    } else {
      alert(`⚠️ ${data.error || "Failed to dispatch. Ensure Chat ID is configured in Settings."}`);
    }
  } catch (e) {
    alert("Error dispatching Telegram docket: " + e.message);
  }
};


