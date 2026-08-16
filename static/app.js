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

function getSelectedOrTodayDate() {
  const picker = document.getElementById("dashboard-date-picker");
  if (picker && picker.value) return picker.value;
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

// =========================================================================
// 0. SIMPLE & ELEGANT STARTUP SPLASH / VIDEO INTRO CONTROLLER
// =========================================================================
let splashDismissed = false;

window.dismissStartupSplash = function() {
  if (splashDismissed) return;
  splashDismissed = true;
  const splash = document.getElementById("app-startup-splash");
  if (splash) {
    splash.classList.add("splash-dismissed");
    setTimeout(() => {
      splash.style.display = "none";
    }, 650);
  }
};

function runStartupSequence() {
  const video = document.getElementById("splash-video");
  const simpleContent = document.getElementById("splash-simple-content");

  // Check if custom video file is available and playable
  if (video) {
    video.onloadeddata = function() {
      video.style.display = "block";
      if (simpleContent) simpleContent.style.display = "none";
      video.play().catch(() => {});
    };

    video.onended = function() {
      window.dismissStartupSplash();
    };

    video.onerror = function() {
      if (video) video.style.display = "none";
      if (simpleContent) simpleContent.style.display = "flex";
    };
  }

  // Smooth fallback dismissal
  setTimeout(() => {
    window.dismissStartupSplash();
  }, 2000);
}

// =========================================================================
// 1. GLOBAL NAVIGATION & VIEW SWITCHER
// =========================================================================
window.switchView = function(viewId) {
  try {
    const navItems = document.querySelectorAll(".nav-item[data-view]");
    const viewSections = document.querySelectorAll(".view-section");

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
        sec.style.display = "block";
      } else {
        sec.classList.remove("active");
        sec.style.display = "none";
      }
    });

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
      <div class="drawer-section-card" style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.35); border-left: 4px solid var(--success);">
        <div class="drawer-section-title" style="color: #34d399; border-color: rgba(16, 185, 129, 0.2); display:flex; justify-content:space-between; align-items:center;">
          <span>💡 SIMPLE CASE EXPLANATION & ACTION</span>
          <span style="font-size:0.68rem; background:rgba(16, 185, 129, 0.2); color:#34d399; padding:2px 8px; border-radius:4px; font-weight:800;">PLAIN TAMIL/ENG</span>
        </div>
        <div style="font-size: 0.88rem; font-weight: 800; color: #ffffff; margin-bottom: 6px;">
          ${escapeHtml(plainInfo.category)}
        </div>
        <div style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.5; margin-bottom: 10px;">
          <strong style="color: #ffffff;">📖 Case Summary:</strong> ${escapeHtml(plainInfo.meaning)}
        </div>
        <div style="font-size: 0.82rem; color: #34d399; line-height: 1.5; background: #04070e; border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 6px; padding: 10px 12px;">
          ⚡ <strong style="color: #ffffff;">Today's Court Action:</strong> ${escapeHtml(plainInfo.todayAction)}
        </div>
      </div>

      <!-- 0.5 SMART SLEEP & MONITORING STATUS CARD -->
      <div class="drawer-section-card" style="background: #080c15; border: 1px solid var(--border-gold);">
        <div class="drawer-section-title">🧠 SMART SLEEP & AUTO-SYNC RADAR</div>
        <div style="display:flex; align-items:center; gap:12px;">
          <span style="font-size:1.4rem;">${c.next_hearing_date === getSelectedOrTodayDate() ? '🔔' : '😴'}</span>
          <div>
            <div style="font-size:0.88rem; font-weight:800; color:#ffffff;">
              ${c.next_hearing_date === getSelectedOrTodayDate() ? 'Active In Court Today (Item #' + (c.item_number || '-') + ')' : 'Smart Sleeping until ' + (c.next_hearing_date || 'Schedule')}
            </div>
            <div style="font-size:0.78rem; color:var(--text-muted); margin-top:3px; line-height:1.4;">
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
          <span class="drawer-field-val" style="color:var(--text-gold); font-weight:800;">${escapeHtml(c.court_room || '-')}</span>
        </div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Item Number:</span>
          <span class="drawer-field-val" style="font-size:0.95rem; color:#38bdf8; font-weight:800;">#${escapeHtml(c.item_number || '-')}</span>
        </div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Presiding Judge:</span>
          <span class="drawer-field-val">${escapeHtml(c.judge_name || '-')}</span>
        </div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">16-Digit CNR:</span>
          <span class="drawer-field-val"><code style="font-family:var(--font-mono); font-size:0.75rem; color:var(--text-gold); background:rgba(245,158,11,0.1); padding:2px 6px; border-radius:4px; border:1px solid rgba(245,158,11,0.25);">${escapeHtml(c.cnr_number)}</code></span>
        </div>
      </div>


      <!-- 2. Client & Litigant Card -->
      <div class="drawer-section-card">
        <div class="drawer-section-title">👤 Client Contact & Role</div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Client Name:</span>
          <span class="drawer-field-val" style="color:#ffffff; font-weight:700;">${escapeHtml(c.client_name || 'Client')}</span>
        </div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Litigant Role:</span>
          <span class="drawer-field-val"><span class="badge badge-evidence">${escapeHtml(c.litigant_role || 'Petitioner')}</span></span>
        </div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">WhatsApp Phone:</span>
          <span class="drawer-field-val"><strong style="color:var(--text-gold);">${escapeHtml(c.client_phone || '-')}</strong></span>
        </div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Parties:</span>
          <span class="drawer-field-val" style="font-size:0.78rem; color:var(--text-secondary);">${escapeHtml(c.parties || c.case_title)}</span>
        </div>
      </div>

      <!-- 3. Stage & Next Hearing Card -->
      <div class="drawer-section-card">
        <div class="drawer-section-title">📅 Hearing Status & Stage</div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Next Hearing Date:</span>
          <span class="drawer-field-val" style="color:var(--text-gold); font-size:0.92rem; font-weight:800;">${escapeHtml(c.next_hearing_date || 'Awaiting Date')}</span>
        </div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Hearing Stage:</span>
          <span class="drawer-field-val"><span class="badge ${getBadgeClass(c.case_stage)}">${escapeHtml(c.case_stage || 'Evidence')}</span></span>
        </div>
        <div class="drawer-field-row">
          <span class="drawer-field-label">Advocate Notes:</span>
          <span class="drawer-field-val" style="color:var(--text-gold); font-weight:600;">${escapeHtml(c.notes || 'None')}</span>
        </div>
      </div>

      <!-- 4. Quick Actions -->
      <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 6px;">
        <a href="${getWhatsAppUrl(c)}" target="_blank" class="btn-ui btn-ui-wa" style="text-align:center; padding:10px; font-weight:800; font-size:0.85rem;">
          📲 Send WhatsApp Hearing Notice
        </a>
        <div style="display:flex; gap:8px;">
          <a href="/api/export-case/${encodeURIComponent(c.cnr_number)}" target="_blank" class="btn-ui btn-ui-secondary" style="flex:1; text-align:center; padding:8px; font-size:0.75rem;">
            🖨️ Print Case Brief
          </a>
          <button onclick="syncSingleCase('${escapeHtml(c.cnr_number)}')" class="btn-ui btn-ui-secondary" style="flex:1; padding:8px; font-size:0.75rem;">
            🔄 Sync eCourts
          </button>
        </div>
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
        <span style="font-size:0.72rem; color:var(--success); font-weight:700;">✓ Synced in Vault</span>
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
  } catch (err) {
    container.innerHTML = `<p style="color: var(--danger); text-align: center;">Search failed: ${escapeHtml(err.message)}</p>`;
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
  const picker = document.getElementById("dashboard-date-picker");
  if (picker && picker.value !== targetDate) {
    picker.value = targetDate;
  }
  const dayLabel = document.getElementById("header-current-date-day");
  if (dayLabel) {
    try {
      dayLabel.innerText = new Date(targetDate + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
    } catch(e) {
      dayLabel.innerText = targetDate;
    }
  }
  const hExp = document.getElementById("header-export-btn");
  if (hExp) hExp.href = `/api/export-cause-list?date=${encodeURIComponent(targetDate)}`;
  const mExp = document.getElementById("main-export-btn");
  if (mExp) mExp.href = `/api/export-cause-list?date=${encodeURIComponent(targetDate)}`;

  const container = document.getElementById("hearing-board-list-container");
  if (container) {
    container.innerHTML = `<p style="padding: 24px; text-align: center; color: var(--text-muted);">Loading Daily Court Hearing Board for ${targetDate}...</p>`;
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

    if (kpiTodayHearings) kpiTodayHearings.innerText = count;
    if (badgeTodayHearings) badgeTodayHearings.innerText = count;
    if (allCourtsTabBadge) allCourtsTabBadge.innerText = count;
    if (btnBulkWa) btnBulkWa.innerText = `📲 Send Notice to All (${count}) Clients`;
    if (kpiTodayHearingsSub) {
      kpiTodayHearingsSub.innerText = count > 0 ? `Across ${courtsCount} Courts in Karur` : "No hearings scheduled";
    }

    renderHearingBoard(data, selectedCourtFilter);
    setupCourtChips(data);
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

  if (!data || !data.court_summaries || data.court_summaries.length === 0) {
    container.innerHTML = `
      <div style="padding: 36px 20px; text-align: center; color: var(--text-muted);">
        <div style="font-size: 2rem; margin-bottom: 8px;">📋</div>
        <strong style="font-size: 0.95rem; color: var(--text-main);">No Hearings Scheduled for This Date</strong>
        <p style="font-size: 0.78rem; margin-top: 4px;">Click <strong>"+ Add New Case"</strong> in the sidebar to add your first client.</p>
      </div>
    `;
    return;
  }

  let summaryHeaderHtml = "";
  if (filterCourt === "ALL" && data.court_summaries && data.court_summaries.length > 0) {
    const courtsCount = data.total_courts || data.court_summaries.length;
    summaryHeaderHtml = `
      <div style="background: #080c15; border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 18px 22px; margin: 18px 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 12px; margin-bottom: 14px; flex-wrap: wrap; gap: 10px;">
          <div>
            <span style="background: linear-gradient(135deg, #fbbf24, #d97706); color: #090d16; font-size: 0.72rem; padding: 3px 10px; border-radius: 4px; font-weight: 800; text-transform: uppercase;">Hearings for ${escapeHtml(data.target_date || 'Today')}</span>
            <div style="font-weight: 800; font-size: 1.05rem; color: #ffffff; margin-top: 6px;">
              You have <span style="color: var(--text-gold);">${data.total_hearings}</span> confirmed hearings scheduled across ${courtsCount} Karur Court${courtsCount > 1 ? 's' : ''}
            </div>
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <button onclick="openBulkWhatsAppModal()" class="btn-ui btn-ui-wa" style="font-size: 0.78rem; padding: 6px 14px; font-weight: 800;">
              📲 Send Notice to All (${data.total_hearings || 0}) Clients
            </button>
            <a href="/api/export-cause-list?date=${encodeURIComponent(data.target_date || getSelectedOrTodayDate())}" target="_blank" class="btn-ui btn-ui-secondary" style="font-size: 0.78rem; padding: 6px 12px;">
              🖨️ A4 Cause List
            </a>
          </div>
        </div>

        <div style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; font-size: 0.84rem;">
            <thead>
              <tr style="background: #0e1526; border-bottom: 1px solid var(--border-color);">
                <th style="width: 50px; padding: 8px 12px; text-align: left; font-weight: 700; color: var(--text-gold);">S.NO</th>
                <th style="padding: 8px 12px; text-align: left; font-weight: 700; color: var(--text-gold);">COURT NAME</th>
                <th style="width: 120px; padding: 8px 12px; text-align: right; font-weight: 700; color: var(--text-gold);">CONFIRMED</th>
              </tr>
            </thead>
            <tbody>
              ${data.court_summaries.map((c, i) => `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.04);">
                  <td style="padding: 8px 12px; font-weight: 700; color: var(--text-muted);">${i + 1}</td>
                  <td style="padding: 8px 12px; font-weight: 600; color: var(--text-secondary);">${escapeHtml(c.court_name)}</td>
                  <td style="padding: 8px 12px; text-align: right; font-weight: 800; color: var(--text-gold);">${c.hearings_count}</td>
                </tr>
              `).join("")}
              <tr style="background: #0e1526; font-weight: 800;">
                <td colspan="2" style="padding: 10px 12px; text-align: right; color: #ffffff;">TOTAL CONFIRMED HEARINGS:</td>
                <td style="padding: 10px 12px; text-align: right; color: var(--text-gold); font-size: 0.95rem;">${data.total_hearings}</td>
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
              <th style="width: 50px; text-align: center;">Item</th>
              <th>Case Details (Click to View Side Details)</th>
              <th>Client</th>
              <th>Status</th>
              <th>Room & Judge</th>
              <th style="text-align: right;">WhatsApp</th>
            </tr>
          </thead>
          <tbody>
            ${court.cases.map(c => `
              <tr class="clickable-case-row">
                <td style="text-align: center; width: 60px;" onclick="openCaseDrawer('${escapeHtml(c.cnr_number)}')">
                  <div class="item-badge-cell" style="cursor: pointer;">${escapeHtml(c.item_number || '-')}</div>
                </td>
                <td class="clickable-case-cell" onclick="openCaseDrawer('${escapeHtml(c.cnr_number)}')" style="max-width: 400px;">
                  <div class="case-title-text" style="font-size: 0.95rem; margin-bottom: 4px; color: #ffffff;">${escapeHtml(c.case_title)}</div>
                  <div class="case-sub-text" style="font-size: 0.8rem;">
                    <strong style="color: var(--text-gold); font-family: var(--font-mono); font-weight: 800; font-size: 0.88rem;">${escapeHtml(c.case_number_formatted || c.cnr_number)}</strong>
                    ${c.notes ? ` &bull; <span style="color: #fef08a; font-weight: 600; background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.3); padding: 2px 8px; border-radius: 4px; font-size: 0.72rem;">Note: ${escapeHtml(c.notes)}</span>` : ''}
                  </div>
                </td>
                <td style="min-width: 140px;">
                  <strong style="color: #ffffff; font-size: 0.9rem; display: block; margin-bottom: 2px;">${escapeHtml(c.client_name || 'Client')}</strong>
                  <div style="font-size: 0.78rem; color: var(--text-gold); font-family: var(--font-mono); font-weight: 600;">${escapeHtml(c.client_phone || '-')}</div>
                </td>
                <td>
                  <span class="badge ${getBadgeClass(c.case_stage)}">${escapeHtml(c.case_stage || 'Evidence')}</span>
                </td>
                <td style="min-width: 160px;">
                  <div class="room-badge" style="color: #ffffff; font-weight: 800;">${escapeHtml(c.court_room || '-')}</div>
                  <div style="font-size: 0.78rem; color: var(--text-secondary); line-height: 1.35;">${escapeHtml(c.judge_name || '-')}</div>
                </td>
                <td style="text-align: right; min-width: 130px;">
                  <a href="${getWhatsAppUrl(c)}" target="_blank" class="btn-ui btn-ui-wa" style="padding: 7px 14px; font-size: 0.8rem; font-weight: 800;">
                    📲 Send Notice
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


async function loadTrackedCases() {
  try {
    const res = await fetch("/api/cases");
    const data = await res.json();
    allCases = data || [];

    const kpiActiveCases = document.getElementById("kpi-active-cases");
    const badgeTotalCases = document.getElementById("badge-total-cases");
    const kpiDisposedCases = document.getElementById("kpi-disposed-cases");
    const kpiUpcoming7d = document.getElementById("kpi-upcoming-7d");

    const activeCount = allCases.filter(c => (c.case_status || "").toUpperCase() !== "DISPOSED").length;
    const disposedCount = allCases.filter(c => (c.case_status || "").toUpperCase() === "DISPOSED").length;

    if (kpiActiveCases) kpiActiveCases.innerText = activeCount;
    if (badgeTotalCases) badgeTotalCases.innerText = allCases.length;
    if (kpiDisposedCases) kpiDisposedCases.innerText = disposedCount;

    const todayStr = getSelectedOrTodayDate();
    const futureCasesCount = allCases.filter(c => c.next_hearing_date && c.next_hearing_date >= todayStr).length;
    if (kpiUpcoming7d) kpiUpcoming7d.innerText = futureCasesCount;

    renderAllCasesTable(allCases);
    renderClientsTable(allCases);
    renderWhatsAppDockets(allCases);
  } catch (e) {
    console.error("loadTrackedCases error:", e);
  }
}

function renderAllCasesTable(cases) {
  const tbody = document.getElementById("all-cases-tbody");
  if (!tbody) return;

  if (!cases || cases.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="padding: 32px; text-align: center; color: var(--text-muted);">
          <div style="font-size: 1.8rem; margin-bottom: 6px;">📁</div>
          <strong>No Cases in Portfolio</strong>
        </td>
      </tr>
    `;
    return;
  }

  const todayStr = getSelectedOrTodayDate();
  tbody.innerHTML = cases.map(c => `
    <tr class="clickable-case-row">
      <td class="clickable-case-cell" onclick="openCaseDrawer('${escapeHtml(c.cnr_number)}')">
        <strong style="font-size: 0.92rem; color: #ffffff; display: block; margin-bottom: 2px; font-weight: 700;">${escapeHtml(c.client_name || 'Client')}</strong>
        <div style="font-size: 0.76rem; color: var(--text-gold); font-weight: 600;">${escapeHtml(c.litigant_role || 'Litigant')}</div>
      </td>
      <td class="clickable-case-cell" onclick="openCaseDrawer('${escapeHtml(c.cnr_number)}')" style="max-width: 320px;">
        <div class="case-title-text" style="font-size: 0.92rem; margin-bottom: 3px; color: #ffffff;">${escapeHtml(c.case_title)}</div>
        <div style="font-size: 0.78rem; color: var(--text-secondary); line-height: 1.35; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;" title="${escapeHtml(c.parties || '')}">
          ${escapeHtml(c.parties || '')}
        </div>
      </td>
      <td onclick="openCaseDrawer('${escapeHtml(c.cnr_number)}')">
        <strong style="font-size: 0.9rem; color: #ffffff; font-weight: 800;">${escapeHtml(c.case_number_formatted || '-')}</strong>
      </td>
      <td onclick="openCaseDrawer('${escapeHtml(c.cnr_number)}')">
        <code style="font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-gold); font-weight: 700; background: rgba(245,158,11,0.1); padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(245,158,11,0.25);">${escapeHtml(c.cnr_number)}</code>
      </td>
      <td style="font-size: 0.86rem; color: var(--text-secondary); max-width: 220px;">
        ${escapeHtml(c.court_name || 'District Court')}
      </td>
      <td>
        <strong style="color: var(--text-gold); font-size: 0.9rem; display: block; font-weight: 800;">${escapeHtml(c.next_hearing_date || 'Awaiting Date')}</strong>
        <div style="margin-top: 4px;">
          ${c.next_hearing_date === todayStr 
            ? '<span style="background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.35); padding: 3px 10px; border-radius: 12px; font-size: 0.72rem; font-weight: 800; display: inline-block;">🔔 Hearing Today</span>'
            : (c.case_status === 'DISPOSED' 
                ? '<span style="background: rgba(100, 116, 139, 0.15); color: #94a3b8; border: 1px solid rgba(100, 116, 139, 0.3); padding: 3px 10px; border-radius: 12px; font-size: 0.72rem; font-weight: 600; display: inline-block;">🏁 Disposed</span>'
                : '<span style="background: rgba(255, 255, 255, 0.04); color: var(--text-muted); border: 1px solid rgba(255, 255, 255, 0.08); padding: 3px 10px; border-radius: 12px; font-size: 0.72rem; font-weight: 600; display: inline-block;">😴 Sleeping until ' + (c.next_hearing_date || 'date') + '</span>')}
        </div>
      </td>
      <td>
        <span class="badge ${c.case_status === 'DISPOSED' ? 'badge-disposed' : 'badge-evidence'}">${escapeHtml(c.case_status || 'PENDING')}</span>
      </td>

      <td style="text-align: right;">
        <div style="display: flex; gap: 6px; justify-content: flex-end; align-items: center;">
          <a href="${getWhatsAppUrl(c)}" target="_blank" class="table-action-btn" style="background: rgba(16, 185, 129, 0.15); color: #34d399; border-color: rgba(16, 185, 129, 0.3);" title="Send WhatsApp Notice">💬</a>
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
      <td><strong>${escapeHtml(cl.name)}</strong></td>
      <td><code style="font-family: var(--font-mono); font-size:0.78rem;">${escapeHtml(cl.phone)}</code></td>
      <td><span class="badge badge-evidence">${escapeHtml(cl.role)}</span></td>
      <td><strong>${cl.count} Active Matter${cl.count > 1 ? 's' : ''}</strong></td>
      <td><strong style="color:var(--primary);">${escapeHtml(cl.nextDate)}</strong></td>
      <td><span style="color:var(--success); font-weight:700; font-size:0.76rem;">✓ Active</span></td>
      <td style="text-align: right;">
        <a href="${getWhatsAppUrl(cl.caseObj)}" target="_blank" class="btn-ui btn-ui-wa" style="padding:4px 10px; font-size:0.72rem;">
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
        <td><strong>${escapeHtml(l.client_name)}</strong></td>
        <td><code>${escapeHtml(l.client_phone)}</code></td>
        <td><span class="badge badge-evidence">${escapeHtml(l.matter_type)}</span></td>
        <td>${escapeHtml(l.expected_court)}</td>
        <td><span class="badge badge-steps">${escapeHtml(l.status)}</span></td>
        <td><span style="font-size:0.72rem; color:var(--text-muted);">${escapeHtml(l.notes || '-')}</span></td>
        <td style="text-align: right;">
          <a href="https://wa.me/${(l.client_phone || '').replace(/[^0-9]/g, '')}?text=Hello%20${encodeURIComponent(l.client_name)}%2C%20Advocate%20R.%20Anbaiya%20Office%20Notice" target="_blank" class="btn-ui btn-ui-wa" style="padding:3px 8px; font-size:0.7rem;">
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
    <div style="background: #0e1526; border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px 20px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; box-shadow: var(--shadow-sm);">
      <div>
        <div style="font-weight: 800; font-size: 0.95rem; color: #ffffff;">${escapeHtml(c.client_name || 'Client')} <span style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-gold); font-weight: 600;">(${escapeHtml(c.client_phone || '-')})</span></div>
        <div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 4px;">
          Case: <strong style="color: #ffffff;">${escapeHtml(c.case_title)}</strong> &bull; Item: <strong style="color: var(--text-gold);">#${escapeHtml(c.item_number || '-')}</strong> (${escapeHtml(c.court_room || '-')}) &bull; Stage: <strong>${escapeHtml(c.case_stage || 'Evidence')}</strong>
        </div>
      </div>
      <a href="${getWhatsAppUrl(c)}" target="_blank" class="btn-ui btn-ui-wa" style="padding: 8px 16px;">
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

  // Date picker change listener
  const datePicker = document.getElementById("dashboard-date-picker");
  if (datePicker) {
    if (!datePicker.value) {
      datePicker.value = "2026-08-14"; // Default to loaded board date
    }
    datePicker.addEventListener("change", () => {
      loadDailyCauseList(datePicker.value);
    });
  }

  // Initial Loads & Start Live Sync Loop
  async function initApp() {
    runStartupSequence();
    await loadAdvocateSettings();
    await loadMetaConfig();
    await loadTrackedCases();
    await loadDailyCauseList(getSelectedOrTodayDate());
    await loadLeads();
    renderCalendar(currentCalendarDate);
    startLiveSyncLoop();
  }
  initApp();
});

// =========================================================================
// 7. OFFICIAL META WHATSAPP CLOUD API INTEGRATION
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

