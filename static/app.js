document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const caseForm = document.getElementById("case-form");
  const cnrInput = document.getElementById("cnr-input");
  const clientNameInput = document.getElementById("client-name");
  const clientPhoneInput = document.getElementById("client-phone");
  const caseNotesInput = document.getElementById("case-notes");
  const ruleTrackHearing = document.getElementById("rule-track-hearing");
  const ruleTrackOrders = document.getElementById("rule-track-orders");
  const ruleTrackStatus = document.getElementById("rule-track-status");
  const ruleAutoWa = document.getElementById("rule-auto-wa");
  const forceLiveToggle = document.getElementById("force-live-toggle");

  const btnFetch = document.getElementById("btn-fetch");
  const btnDemo = document.getElementById("btn-demo");
  const btnSyncAll = document.getElementById("btn-sync-all");
  const btnOpenHistory = document.getElementById("btn-open-history");
  const cardHistoryStat = document.getElementById("card-history-stat");
  const filterInput = document.getElementById("filter-input");
  const caseResultContent = document.getElementById("case-result-content");
  const cacheBadge = document.getElementById("cache-badge");
  const casesTbody = document.getElementById("cases-tbody");
  const casesCount = document.getElementById("cases-count");
  const historyCount = document.getElementById("history-count");
  const statTotalCases = document.getElementById("stat-total-cases");
  const statPendingCases = document.getElementById("stat-pending-cases");
  const statDateChanges = document.getElementById("stat-date-changes");
  const statCreditsSaved = document.getElementById("stat-credits-saved");
  const headerFirmName = document.getElementById("header-firm-name");
  const apiStatusText = document.getElementById("api-status-text");
  const statusDot = document.getElementById("status-dot");
  const creditGuardText = document.getElementById("credit-guard-text");

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
  const editNotes = document.getElementById("edit-notes");
  const editRuleHearing = document.getElementById("edit-rule-hearing");
  const editRuleOrders = document.getElementById("edit-rule-orders");
  const editRuleStatus = document.getElementById("edit-rule-status");
  const editRuleWa = document.getElementById("edit-rule-wa");

  const historyModal = document.getElementById("history-modal");
  const btnCloseHistory = document.getElementById("btn-close-history");
  const historyLogsContent = document.getElementById("history-logs-content");

  let allTrackedCases = [];
  let currentAdvocateSettings = {};

  // Initialize
  checkKeyStatus();
  loadAdvocateSettings();
  loadTrackedCases();
  loadHistoryLogsCount();
  loadSyncStatus();

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

  async function loadSyncStatus() {
    try {
      const res = await fetch("/api/sync-status");
      const data = await res.json();
      statCreditsSaved.innerText = data.total_credits_saved || 0;
    } catch (e) {}
  }

  // Handle Form Submit (Add New Case & Client)
  caseForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const cnr = cnrInput.value.trim().toUpperCase();
    const name = clientNameInput.value.trim();
    const phone = clientPhoneInput.value.trim();
    const notes = caseNotesInput.value.trim();
    const forceLive = forceLiveToggle.checked;

    if (!cnr) return;

    btnFetch.disabled = true;
    btnFetch.innerText = forceLive ? "⚡ Live Querying eCourts (1.5 credits)..." : "⚡ Loading Case...";
    caseResultContent.innerHTML = `
      <div class="empty-state">
        <p>Fetching case intelligence for CNR <code>${cnr}</code> for client <strong>${escapeHtml(name)}</strong>...</p>
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
          notes: notes,
          force_live: forceLive,
          track_next_hearing: ruleTrackHearing.checked,
          track_orders: ruleTrackOrders.checked,
          track_case_status: ruleTrackStatus.checked,
          auto_whatsapp_enabled: ruleAutoWa.checked
        })
      });

      const data = await response.json();
      renderCaseResult(data, name, phone, notes);
      loadTrackedCases();
      loadHistoryLogsCount();
      loadSyncStatus();
    } catch (err) {
      caseResultContent.innerHTML = `
        <div class="empty-state" style="color: var(--accent-rose);">
          <p>Failed to track case: ${err.message}</p>
        </div>
      `;
    } finally {
      btnFetch.disabled = false;
      btnFetch.innerText = "⚡ Fetch & Track Case";
    }
  });

  // Demo Case Button
  btnDemo.addEventListener("click", () => {
    cnrInput.value = "DLND020047882015";
    clientNameInput.value = "Arun Jaitley";
    clientPhoneInput.value = "+919876543210";
    caseNotesInput.value = "Criminal defamation trial & 65B evidence review";
    caseForm.dispatchEvent(new Event("submit"));
  });

  // Sync All Cases Button
  btnSyncAll.addEventListener("click", async () => {
    btnSyncAll.disabled = true;
    btnSyncAll.innerText = "🔄 Syncing All Cases...";
    try {
      const res = await fetch("/api/sync-all", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force_live: false })
      });
      const data = await res.json();
      alert(`✅ Portfolio Sync Complete!\n• Total Checked: ${data.total_checked}\n• Cached (0 credits): ${data.cached_count}\n• Date Shifts Detected: ${data.date_changes_count}`);
      loadTrackedCases();
      loadHistoryLogsCount();
      loadSyncStatus();
    } catch (e) {
      alert("Sync failed: " + e.message);
    } finally {
      btnSyncAll.disabled = false;
      btnSyncAll.innerText = "🔄 Sync All Cases Now";
    }
  });

  // Live Filter Handler
  if (filterInput) {
    filterInput.addEventListener("input", (e) => {
      const term = e.target.value.toLowerCase();
      const filtered = allTrackedCases.filter(c => 
        (c.cnr_number || "").toLowerCase().includes(term) ||
        (c.case_title || "").toLowerCase().includes(term) ||
        (c.court_name || "").toLowerCase().includes(term) ||
        (c.client_name || "").toLowerCase().includes(term) ||
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

  // Render Result Function
  function renderCaseResult(data, clientName, phone, notes) {
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
        </div>
        <span class="tag ${statusClass}">${escapeHtml(c.case_status || 'PENDING')}</span>
      </div>

      <div class="hearing-box">
        <div>
          <div class="data-label">Next Scheduled Hearing Date</div>
          <div class="hearing-date">${escapeHtml(nextDate)}</div>
        </div>
        <div style="text-align: right;">
          <div class="data-label">Total Hearings</div>
          <div style="font-weight: 700; font-size: 1.1rem; color: #fff;">${c.hearing_count || 25}</div>
        </div>
      </div>

      <div class="data-grid">
        <div class="data-item">
          <div class="data-label">Court & District</div>
          <div class="data-val">${escapeHtml(c.court_name || 'Chief Metropolitan Magistrate')}</div>
        </div>
        <div class="data-item">
          <div class="data-label">Assigned Client</div>
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
          <span>💬 Prepared WhatsApp Notice:</span>
          <span>Client: <strong>${escapeHtml(phone || '')}</strong></span>
        </div>
        <div class="whatsapp-bubble">${escapeHtml(waText)}</div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <a href="${waLink}" target="_blank" class="btn btn-whatsapp" style="flex: 1;">
            📲 Dispatch to Client WhatsApp
          </a>
          <a href="/api/export-case/${encodeURIComponent(c.cnr_number)}" target="_blank" class="btn btn-secondary" style="flex: none; padding: 10px 16px;">
            🖨️ Print Brief
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
      
      const pending = allTrackedCases.filter(c => !((c.case_status || "").toLowerCase().includes("disp"))).length;
      statPendingCases.innerText = pending;

      renderTableRows(allTrackedCases);
    } catch (e) {
      console.error(e);
    }
  }

  function renderTableRows(cases) {
    if (!cases || cases.length === 0) {
      casesTbody.innerHTML = `
        <tr>
          <td colspan="7" class="empty-state">No matching client cases found in database.</td>
        </tr>
      `;
      return;
    }

    casesTbody.innerHTML = cases.map(item => `
      <tr>
        <td>
          <strong>${escapeHtml(item.client_name || 'Litigant')}</strong>
          <div style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(item.client_phone || '-')}</div>
        </td>
        <td><code style="color: var(--accent-blue); font-family: var(--font-mono);">${escapeHtml(item.cnr_number)}</code></td>
        <td>
          <div style="font-weight: 600;">${escapeHtml(item.case_title || 'N/A')}</div>
          <div style="font-size: 0.8rem; color: var(--text-secondary);">${escapeHtml(item.court_name || 'District Court')}</div>
        </td>
        <td><span class="tag ${item.case_status && item.case_status.includes('DISP') ? 'tag-disposed' : 'tag-pending'}">${escapeHtml(item.case_status || 'PENDING')}</span></td>
        <td style="font-weight: 700; color: var(--accent-blue);">${escapeHtml(item.next_hearing_date || 'N/A')}</td>
        <td>
          <div>
            ${item.track_next_hearing ? '<span class="rule-chip">📅 Date</span>' : ''}
            ${item.track_orders ? '<span class="rule-chip">📜 Orders</span>' : ''}
            ${item.auto_whatsapp_enabled ? '<span class="rule-chip" style="color: var(--accent-emerald);">💬 WhatsApp</span>' : ''}
          </div>
        </td>
        <td>
          <div class="action-btn-group">
            <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;" onclick="recheckCase('${item.cnr_number}')" title="Recheck Case (Cached/Free)">
              ⚡ Check
            </button>
            <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;" onclick="openEditRulesModal('${item.cnr_number}')" title="Edit Automation Rules">
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
      clientPhoneInput.value = item.client_phone || "";
      caseNotesInput.value = item.notes || "";
    }
    caseForm.dispatchEvent(new Event("submit"));
  };

  // Edit Rules Modal
  window.openEditRulesModal = (cnr) => {
    const item = allTrackedCases.find(c => c.cnr_number === cnr);
    if (!item) return;

    editRuleCnr.value = cnr;
    editClientName.value = item.client_name || "";
    editClientPhone.value = item.client_phone || "";
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
    } catch (err) {
      alert("Failed to update rules: " + err.message);
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
• *CNR:* \`${c.cnr_number}\`
• *Court:* ${c.court_name || 'Court'}
• *Status:* ${c.case_status || 'Pending'}
• *Next Hearing Date:* *${c.next_hearing_date || 'Awaiting Schedule / Disposed'}*
${c.latest_order_date ? `• *Latest Order Date:* ${c.latest_order_date}` : ''}
${notes ? `• *Note:* ${notes}` : ''}
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
