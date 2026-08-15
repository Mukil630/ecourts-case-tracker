document.addEventListener("DOMContentLoaded", () => {
  const caseForm = document.getElementById("case-form");
  const cnrInput = document.getElementById("cnr-input");
  const clientNameInput = document.getElementById("client-name");
  const clientPhoneInput = document.getElementById("client-phone");
  const engineModeSelect = document.getElementById("engine-mode-select");
  const btnFetch = document.getElementById("btn-fetch");
  const btnDemo = document.getElementById("btn-demo");
  const btnSyncAll = document.getElementById("btn-sync-all");
  const btnOpenHistory = document.getElementById("btn-open-history");
  const cardHistoryStat = document.getElementById("card-history-stat");
  const filterInput = document.getElementById("filter-input");
  const caseResultContent = document.getElementById("case-result-content");
  const casesTbody = document.getElementById("cases-tbody");
  const casesCount = document.getElementById("cases-count");
  const historyCount = document.getElementById("history-count");
  const statTotalCases = document.getElementById("stat-total-cases");
  const statPendingCases = document.getElementById("stat-pending-cases");
  const statDateChanges = document.getElementById("stat-date-changes");
  const apiKeyInput = document.getElementById("api-key-input");
  const btnSaveKey = document.getElementById("btn-save-key");
  const btnToggleView = document.getElementById("btn-toggle-view");
  const currentKeyDisplay = document.getElementById("current-key-display");
  const apiStatusText = document.getElementById("api-status-text");
  const statusDot = document.getElementById("status-dot");
  const historyModal = document.getElementById("history-modal");
  const btnCloseModal = document.getElementById("btn-close-modal");
  const historyLogsContent = document.getElementById("history-logs-content");

  let isKeyVisible = true;
  let allTrackedCases = [];

  // Toggle View Button
  if (btnToggleView) {
    btnToggleView.addEventListener("click", () => {
      isKeyVisible = !isKeyVisible;
      apiKeyInput.type = isKeyVisible ? "text" : "password";
      btnToggleView.innerText = isKeyVisible ? "👁️ Hide" : "👁️ View";
    });
  }

  // Check key & system status on startup
  checkKeyStatus();
  loadTrackedCases();
  loadHistoryLogsCount();

  // Save Key Handler
  btnSaveKey.addEventListener("click", async () => {
    const key = apiKeyInput.value.trim();
    if (!key) return;
    btnSaveKey.disabled = true;
    btnSaveKey.innerText = "Saving...";

    try {
      const res = await fetch("/api/save-key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: key })
      });
      const data = await res.json();
      if (data.success) {
        currentKeyDisplay.innerText = key;
        apiStatusText.innerText = `API Key Active (${data.masked_key})`;
        statusDot.style.backgroundColor = "var(--accent-emerald)";
        alert("✅ API Key saved successfully! Live eCourts Partner API is active.");
      }
    } catch (e) {
      alert("Failed to save key: " + e.message);
    } finally {
      btnSaveKey.disabled = false;
      btnSaveKey.innerText = "💾 Save Key";
    }
  });

  async function checkKeyStatus() {
    try {
      const res = await fetch("/api/key-status");
      const data = await res.json();
      if (data.configured) {
        apiStatusText.innerText = `API Active (${data.masked_key})`;
        currentKeyDisplay.innerText = data.full_key || data.masked_key;
        apiKeyInput.value = data.full_key || "";
        statusDot.style.backgroundColor = "var(--accent-emerald)";
      } else {
        apiStatusText.innerText = "Demo Mode (No API Key)";
        currentKeyDisplay.innerText = "Not Configured (Demo Mode)";
        statusDot.style.backgroundColor = "var(--accent-amber)";
      }
    } catch (e) {}
  }

  // Handle Form Submit
  caseForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const cnr = cnrInput.value.trim().toUpperCase();
    const name = clientNameInput.value.trim();
    const phone = clientPhoneInput.value.trim();
    const mode = engineModeSelect.value;

    if (!cnr) return;

    btnFetch.disabled = true;
    btnFetch.innerText = mode === "agent" ? "🤖 Vision Agent Solving..." : "⏳ Querying eCourts...";
    caseResultContent.innerHTML = `
      <div class="empty-state">
        <p><strong>[${mode === 'agent' ? 'Autonomous AI Vision Agent' : 'Partner API'}]</strong> Executing case lookup for <code>${cnr}</code>...</p>
      </div>
    `;

    try {
      const endpoint = mode === "agent" ? "/api/run-agent" : "/api/check-case";
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cnr, client_name: name, client_phone: phone })
      });

      const data = await response.json();
      renderCaseResult(data, phone);
      loadTrackedCases();
      loadHistoryLogsCount();
    } catch (err) {
      caseResultContent.innerHTML = `
        <div class="empty-state" style="color: var(--accent-rose);">
          <p>Failed to reach server: ${err.message}</p>
        </div>
      `;
    } finally {
      btnFetch.disabled = false;
      btnFetch.innerText = "⚡ Execute Tracking";
    }
  });

  // Demo Case Button
  btnDemo.addEventListener("click", () => {
    cnrInput.value = "DLND020047882015";
    clientNameInput.value = "Arun Jaitley";
    clientPhoneInput.value = "+919876543210";
    caseForm.dispatchEvent(new Event("submit"));
  });

  // Sync All Cases Button
  btnSyncAll.addEventListener("click", async () => {
    btnSyncAll.disabled = true;
    btnSyncAll.innerText = "🔄 Syncing Cases...";
    try {
      const res = await fetch("/api/sync-all", { method: "POST" });
      const data = await res.json();
      alert(`✅ Sync Complete!\n• Total Checked: ${data.total_checked}\n• Date Shifts Detected: ${data.date_changes_count}`);
      loadTrackedCases();
      loadHistoryLogsCount();
    } catch (e) {
      alert("Sync failed: " + e.message);
    } finally {
      btnSyncAll.disabled = false;
      btnSyncAll.innerText = "🔄 Sync All Cases Now";
    }
  });

  // Search Filter Handler
  if (filterInput) {
    filterInput.addEventListener("input", (e) => {
      const term = e.target.value.toLowerCase();
      const filtered = allTrackedCases.filter(c => 
        (c.cnr_number || "").toLowerCase().includes(term) ||
        (c.case_title || "").toLowerCase().includes(term) ||
        (c.court_name || "").toLowerCase().includes(term) ||
        (c.client_name || "").toLowerCase().includes(term)
      );
      renderTableRows(filtered);
    });
  }

  // History Modal Triggers
  btnOpenHistory.addEventListener("click", openHistoryModal);
  if (cardHistoryStat) {
    cardHistoryStat.addEventListener("click", openHistoryModal);
  }
  btnCloseModal.addEventListener("click", () => historyModal.style.display = "none");
  window.addEventListener("click", (e) => {
    if (e.target === historyModal) historyModal.style.display = "none";
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
  function renderCaseResult(data, phone) {
    if (!data.success && data.error) {
      caseResultContent.innerHTML = `
        <div class="empty-state" style="color: var(--accent-rose);">
          <p><strong>[${data.error_type || 'API Notice'}]</strong> ${data.error}</p>
        </div>
      `;
      return;
    }

    const c = data.case_data || data;
    const statusClass = (c.case_status || "").toLowerCase().includes("dispose") ? "tag-disposed" : "tag-pending";
    const nextDate = c.next_hearing_date || "Not Scheduled / Disposed";
    const waText = formatWhatsAppText(c);
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
          <div class="data-label">Next Hearing Date</div>
          <div class="hearing-date">${escapeHtml(nextDate)}</div>
        </div>
        <div style="text-align: right;">
          <div class="data-label">Total Hearings</div>
          <div style="font-weight: 700; font-size: 1.1rem; color: #fff;">${c.hearing_count || 25}</div>
        </div>
      </div>

      <div class="data-grid">
        <div class="data-item">
          <div class="data-label">Court</div>
          <div class="data-val">${escapeHtml(c.court_name || 'Chief Metropolitan Magistrate')}</div>
        </div>
        <div class="data-item">
          <div class="data-label">State / District</div>
          <div class="data-val">${escapeHtml(c.state || 'DL')} / ${escapeHtml(c.district || 'New Delhi')}</div>
        </div>
      </div>

      <div class="whatsapp-card">
        <div style="font-size: 0.8rem; font-weight: 600; color: #8696a0; margin-bottom: 8px;">
          💬 WhatsApp Notification Preview:
        </div>
        <div class="whatsapp-bubble">${escapeHtml(waText)}</div>
        <div style="display: flex; gap: 8px;">
          <a href="${waLink}" target="_blank" class="btn btn-whatsapp" style="flex: 1;">
            📲 Open in WhatsApp Web
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
          <td colspan="7" class="empty-state">No matching case records found in database.</td>
        </tr>
      `;
      return;
    }

    casesTbody.innerHTML = cases.map(item => `
      <tr>
        <td><code style="color: var(--accent-blue); font-family: var(--font-mono);">${escapeHtml(item.cnr_number)}</code></td>
        <td><strong>${escapeHtml(item.case_title || 'N/A')}</strong></td>
        <td style="font-size: 0.85rem; color: var(--text-secondary);">${escapeHtml(item.court_name || 'District Court')}</td>
        <td><span class="tag ${item.case_status && item.case_status.includes('DISP') ? 'tag-disposed' : 'tag-pending'}">${escapeHtml(item.case_status || 'PENDING')}</span></td>
        <td style="font-weight: 700; color: var(--accent-blue);">${escapeHtml(item.next_hearing_date || 'N/A')}</td>
        <td>${escapeHtml(item.client_phone || '-')}</td>
        <td>
          <div class="action-btn-group">
            <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;" onclick="recheckCase('${item.cnr_number}')" title="Recheck Case">
              ⚡ Check
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
    cnrInput.value = cnr;
    caseForm.dispatchEvent(new Event("submit"));
  };

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

  function formatWhatsAppText(c) {
    return `⚖️ *LEGAL CASE HEARING UPDATE*
---------------------------------------
*Case:* ${c.case_title || 'Case'}
*CNR:* ${c.cnr_number}
*Status:* ${c.case_status || 'Pending'}
*Court:* ${c.court_name || 'Court'}
*Next Hearing Date:* *${c.next_hearing_date || 'Disposed / Awaiting Date'}*
---------------------------------------
*Advocate Office Update*`;
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
