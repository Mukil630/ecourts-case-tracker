document.addEventListener("DOMContentLoaded", () => {
  const caseForm = document.getElementById("case-form");
  const cnrInput = document.getElementById("cnr-input");
  const clientNameInput = document.getElementById("client-name");
  const clientPhoneInput = document.getElementById("client-phone");
  const btnFetch = document.getElementById("btn-fetch");
  const btnDemo = document.getElementById("btn-demo");
  const btnRefreshList = document.getElementById("btn-refresh-list");
  const caseResultContent = document.getElementById("case-result-content");
  const casesTbody = document.getElementById("cases-tbody");
  const casesCount = document.getElementById("cases-count");
  const apiKeyInput = document.getElementById("api-key-input");
  const btnSaveKey = document.getElementById("btn-save-key");
  const btnToggleView = document.getElementById("btn-toggle-view");
  const currentKeyDisplay = document.getElementById("current-key-display");
  const apiStatusText = document.getElementById("api-status-text");
  const statusDot = document.getElementById("status-dot");

  let isKeyVisible = true;

  // Toggle View Button
  if (btnToggleView) {
    btnToggleView.addEventListener("click", () => {
      isKeyVisible = !isKeyVisible;
      apiKeyInput.type = isKeyVisible ? "text" : "password";
      btnToggleView.innerText = isKeyVisible ? "👁️ Hide" : "👁️ View";
    });
  }

  // Check key status on startup
  checkKeyStatus();

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
        alert("✅ API Key saved successfully! Live eCourts API is active.");
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
        apiStatusText.innerText = `API Key Active (${data.masked_key})`;
        currentKeyDisplay.innerText = data.full_key || data.masked_key;
        apiKeyInput.value = data.full_key || "";
        statusDot.style.backgroundColor = "var(--accent-emerald)";
      } else {
        apiStatusText.innerText = "No API Key (Demo Mode)";
        currentKeyDisplay.innerText = "Not Configured (Demo Mode)";
        statusDot.style.backgroundColor = "var(--accent-amber)";
      }
    } catch (e) {}
  }

  // Load initial cases list
  loadTrackedCases();

  // Handle Form Submit
  caseForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const cnr = cnrInput.value.trim().toUpperCase();
    const name = clientNameInput.value.trim();
    const phone = clientPhoneInput.value.trim();

    if (!cnr) return;

    btnFetch.disabled = true;
    btnFetch.innerText = "⏳ Fetching from eCourts...";
    caseResultContent.innerHTML = `
      <div class="empty-state">
        <p>Connecting to eCourtsIndia API for CNR <strong>${cnr}</strong>...</p>
      </div>
    `;

    try {
      const response = await fetch("/api/check-case", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cnr, client_name: name, client_phone: phone })
      });

      const data = await response.json();
      renderCaseResult(data, phone);
      loadTrackedCases();
    } catch (err) {
      caseResultContent.innerHTML = `
        <div class="empty-state" style="color: var(--accent-rose);">
          <p>Failed to reach server: ${err.message}</p>
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
    caseForm.dispatchEvent(new Event("submit"));
  });

  btnRefreshList.addEventListener("click", loadTrackedCases);

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
        <a href="${waLink}" target="_blank" class="btn btn-whatsapp" style="width: 100%;">
          📲 Open in WhatsApp Web / App
        </a>
      </div>
    `;
  }

  // Load Database Tracked Cases
  async function loadTrackedCases() {
    try {
      const res = await fetch("/api/cases");
      const cases = await res.json();
      casesCount.innerText = cases.length;

      if (!cases || cases.length === 0) {
        casesTbody.innerHTML = `
          <tr>
            <td colspan="7" class="empty-state">No cases tracked in database yet.</td>
          </tr>
        `;
        return;
      }

      casesTbody.innerHTML = cases.map(item => `
        <tr>
          <td><code style="color: var(--accent-blue);">${escapeHtml(item.cnr_number)}</code></td>
          <td><strong>${escapeHtml(item.case_title || 'N/A')}</strong></td>
          <td style="font-size: 0.85rem; color: var(--text-secondary);">${escapeHtml(item.court_name || 'District Court')}</td>
          <td><span class="tag ${item.case_status && item.case_status.includes('DISP') ? 'tag-disposed' : 'tag-pending'}">${escapeHtml(item.case_status || 'PENDING')}</span></td>
          <td style="font-weight: 700; color: var(--accent-blue);">${escapeHtml(item.next_hearing_date || 'N/A')}</td>
          <td>${escapeHtml(item.client_phone || '-')}</td>
          <td>
            <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.75rem;" onclick="recheckCase('${item.cnr_number}')">
              ⚡ Check
            </button>
          </td>
        </tr>
      `).join("");
    } catch (e) {
      console.error(e);
    }
  }

  window.recheckCase = (cnr) => {
    cnrInput.value = cnr;
    caseForm.dispatchEvent(new Event("submit"));
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
