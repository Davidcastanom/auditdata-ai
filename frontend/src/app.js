import { Store } from "./state.js";
import { Router } from "./router.js";
import { signInWithGoogle, signOut, getCurrentUser, authAvailable, saveToHistory, getHistory, getHistorySession } from "./auth.js";
import { NubeValidación } from "./nube.js";

const loginScreen = document.querySelector("#loginScreen");
const appContent = document.querySelector("#appContent");
const googleLoginButton = document.querySelector("#googleLoginButton");
const skipLoginButton = document.querySelector("#skipLoginButton");
const heroStartButton = document.querySelector("#heroStartButton");
const heroSkipButton = document.querySelector("#heroSkipButton");
const ctaStartButton = document.querySelector("#ctaStartButton");
const ctaGoogleButton = document.querySelector("#ctaGoogleButton");

let currentUser = null;

async function initAuth() {
  const isTest = new URLSearchParams(window.location.search).has("test");
  if (isTest) {
    showApp();
    return;
  }
  try {
    const user = await getCurrentUser();
    if (user) {
      currentUser = user;
      showApp();
    } else {
      showLogin();
    }
  } catch {
    showApp();
  }
}

function showLogin() {
  loginScreen.style.display = "grid";
  appContent.style.display = "none";
}

function showApp() {
  loginScreen.style.display = "none";
  appContent.style.display = "block";
  if (currentUser) {
    showUserBar();
    loadHistory();
  }
  init();
}

function showUserBar() {
  if (!currentUser) return;
  const userBar = document.querySelector("#userBar");
  const userAvatar = document.querySelector("#userAvatar");
  const userName = document.querySelector("#userName");
  const logoutButton = document.querySelector("#logoutButton");

  userBar.style.display = "flex";
  userName.textContent = currentUser.user_metadata?.full_name || currentUser.user_metadata?.name || currentUser.email;
  const avatar = currentUser.user_metadata?.avatar_url || currentUser.user_metadata?.picture;
  if (avatar) {
    userAvatar.src = avatar;
    userAvatar.alt = userName.textContent;
  }

  logoutButton.addEventListener("click", async () => {
    await signOut();
    currentUser = null;
    localStorage.clear();
    showLogin();
  });
}

googleLoginButton.addEventListener("click", async () => {
  try {
    await signInWithGoogle();
  } catch (e) {
    console.error("Login failed:", e);
  }
});

[skipLoginButton, heroStartButton, heroSkipButton, ctaStartButton].forEach((btn) => {
  if (btn) btn.addEventListener("click", () => showApp());
});

if (ctaGoogleButton) {
  ctaGoogleButton.addEventListener("click", async () => {
    try {
      await signInWithGoogle();
    } catch (e) {
      console.error("Login failed:", e);
    }
  });
}

const store = new Store();

const loadingOverlay = document.querySelector("#loadingOverlay");
const loadingText = document.querySelector("#loadingText");

function showLoading(text = "Procesando dataset...") {
  loadingText.textContent = text;
  loadingOverlay.style.display = "grid";
}

function hideLoading() {
  loadingOverlay.style.display = "none";
}

const els = {
  fileInput: document.querySelector("#fileInput"),
  dropzone: document.querySelector("#dropzone"),
  analyzeButton: document.querySelector("#analyzeButton"),
  loadSampleButton: document.querySelector("#loadSampleButton"),
  systemStatus: document.querySelector("#systemStatus"),
  datasetMeta: document.querySelector("#datasetMeta"),
  previousButton: document.querySelector("#previousButton"),
  nextButton: document.querySelector("#nextButton"),
  profileTitle: document.querySelector("#profileTitle"),
  metrics: document.querySelector("#metrics"),
  profileTable: document.querySelector("#profileTable"),
  rulesBoard: document.querySelector("#rulesBoard"),
  actionsLog: document.querySelector("#actionsLog"),
  undoButton: document.querySelector("#undoButton"),
  comparisonGrid: document.querySelector("#comparisonGrid"),
  validationTable: document.querySelector("#validationTable"),
  analystInput: document.querySelector("#analystInput"),
  versionInput: document.querySelector("#versionInput"),
  reportPreview: document.querySelector("#reportPreview"),
  downloadMarkdownButton: document.querySelector("#downloadMarkdownButton"),
  downloadPdfButton: document.querySelector("#downloadPdfButton"),
  downloadCsvButton: document.querySelector("#downloadCsvButton"),
  downloadAuditLogButton: document.querySelector("#downloadAuditLogButton"),
  saveToCloudButton: document.querySelector("#saveToCloudButton"),
  resetButton: document.querySelector("#resetButton"),
  advColSelect: document.querySelector("#advColSelect"),
  advActionSelect: document.querySelector("#advActionSelect"),
  advParam1Label: document.querySelector("#advParam1Label"),
  advParam1Input: document.querySelector("#advParam1Input"),
  advParam2Row: document.querySelector("#advParam2Row"),
  advParam2Label: document.querySelector("#advParam2Label"),
  advParam2Input: document.querySelector("#advParam2Input"),
  advReasonInput: document.querySelector("#advReasonInput"),
  applyAdvActionButton: document.querySelector("#applyAdvActionButton"),
  rowMeaningInput: document.querySelector("#rowMeaningInput"),
  objectiveInput: document.querySelector("#objectiveInput"),
  historyButton: document.querySelector("#historyButton"),
  historyPanel: document.querySelector("#historyPanel"),
  historyBackdrop: document.querySelector("#historyBackdrop"),
  historyCloseButton: document.querySelector("#historyCloseButton"),
  filePreviewModal: document.querySelector("#filePreviewModal"),
  filePreviewBackdrop: document.querySelector("#filePreviewBackdrop"),
  filePreviewClose: document.querySelector("#filePreviewClose"),
  filePreviewMeta: document.querySelector("#filePreviewMeta"),
  filePreviewTable: document.querySelector("#filePreviewTable"),
  filePreviewConfirm: document.querySelector("#filePreviewConfirm"),
  filePreviewCancel: document.querySelector("#filePreviewCancel"),
  previewDelimiter: document.querySelector("#previewDelimiter"),
  previewHeaderRow: document.querySelector("#previewHeaderRow"),
  historyList: document.querySelector("#historyList"),
  nubeContainer: document.querySelector("#nubeContainer"),
};

const router = new Router(goToStep);

// Inicializar Nube de Validación
const nube = new NubeValidación({
  container: els.nubeContainer,
  onActionReady: (actionOrList) => {
    const list = Array.isArray(actionOrList) ? actionOrList : [actionOrList];
    list.forEach(act => {
      if (act && act.kind) store.addAction(act);
    });
    renderLog();
    els.systemStatus.textContent = `Acciones registradas en bitácora: ${store.state.actions.length}`;
  },
  onAllReviewed: (actions) => {
    els.systemStatus.textContent = `${actions.length} acciones listas para depurar`;
    els.nextButton.disabled = false;
    enableStep(4);
  },
  onDiagnosticReady: (diagnostic) => {
    store.setDiagnostic(diagnostic);
  },
});

els.fileInput.addEventListener("change", () => {
  const file = els.fileInput.files[0];
  if (file) {
    fileToBase64(file).then(base64 => {
      showFilePreview(file.name, base64);
    });
  }
});

els.dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  els.dropzone.classList.add("is-dragging");
});

els.dropzone.addEventListener("dragleave", () => {
  els.dropzone.classList.remove("is-dragging");
});

els.dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  els.dropzone.classList.remove("is-dragging");
  const file = e.dataTransfer.files[0];
  if (file) {
    fileToBase64(file).then(base64 => {
      showFilePreview(file.name, base64);
    });
  }
});

els.analyzeButton.addEventListener("click", analyzeSelectedFile);
els.loadSampleButton.addEventListener("click", loadSample);
els.previousButton.addEventListener("click", () => router.navigate(store.state.step - 1));
els.nextButton.addEventListener("click", onNext);
els.downloadMarkdownButton.addEventListener("click", () => downloadReport("markdown"));
els.downloadPdfButton.addEventListener("click", () => downloadReport("pdf"));
els.downloadAuditLogButton.addEventListener("click", downloadAuditLog);
els.downloadCsvButton.addEventListener("click", downloadCleanCsv);
els.saveToCloudButton.addEventListener("click", saveToCloud);
els.undoButton.addEventListener("click", undoLastAction);
els.resetButton.addEventListener("click", resetProject);

const addNoteBtn = document.getElementById('addAnalystNoteBtn');
if (addNoteBtn) addNoteBtn.addEventListener('click', addAnalystNote);

document.querySelectorAll("[data-step-button]").forEach((button) => {
  button.addEventListener("click", () => router.navigate(Number(button.dataset.stepButton)));
});

function init() {
  if (store.state.filename) {
    els.systemStatus.textContent = `Sesión recuperada: ${store.state.filename}`;
    if (store.state.rowMeaning) els.rowMeaningInput.value = store.state.rowMeaning;
    if (store.state.analysisObjective) els.objectiveInput.value = store.state.analysisObjective;
    if (store.state.analysis) {
      renderProfile();
      renderRules();
      renderDepurationBoard();
      populateAdvancedColumns();
      renderLog();
      enableStep(1);
      enableStep(2);
      enableStep(3);
      els.datasetMeta.textContent = `${store.state.analysis.row_count} filas | ${store.state.analysis.column_count} columnas`;
    }
    if (store.state.cleaning) {
      renderValidation();
      renderReportPreview();
      enableStep(5);
      enableStep(6);
    }
  }
  router.init();
}

async function loadSample() {
  const sample = [
    "id,nombre,ciudad,edad,horas_sueno,litros_agua,completo_reto",
    "1,Ana,Bogota,28,7,2.1,si",
    "2,Juan,bogota,31,6,1.8,no",
    "3,Ana,Bogota,28,7,2.1,si",
    "4,Maria,Medellin,,8,2.4,si",
    "5,Luis,Medellin,450,2,,no",
  ].join("\n");
  
  const base64 = btoa(sample);
  store.setFile("moveup_sample.csv", base64);
  els.analyzeButton.disabled = false;
  await analyzeSelectedFile();
}

async function analyzeSelectedFile() {
  if (!store.state.fileBase64) return;
  els.systemStatus.textContent = "Perfilando dataset con Python...";
  els.analyzeButton.disabled = true;
  showLoading("Analizando tu dataset... Esto puede tardar unos segundos.");

  try {
    store.setContext(els.rowMeaningInput.value.trim(), els.objectiveInput.value.trim());
    const response = await postJson("/api/analyze", {
      filename: store.state.filename,
      content_base64: store.state.fileBase64,
    });
    store.setAnalysis(response.analysis);
    renderProfile();
    renderRules();
    renderDepurationBoard();
    populateAdvancedColumns();
    renderLog();
    enableStep(1);
    enableStep(2);
    enableStep(3);
    els.systemStatus.textContent = "Perfilado completado";
    els.datasetMeta.textContent = `${store.state.analysis.row_count} filas | ${store.state.analysis.column_count} columnas`;
    router.navigate(1);
  } catch (error) {
    els.systemStatus.textContent = `Error: ${error.message}`;
  } finally {
    els.analyzeButton.disabled = false;
    hideLoading();
  }
}

let _previewSettings = {};

async function showFilePreview(filename, base64) {
  store.setFile(filename, base64);
  els.filePreviewBackdrop.classList.add("is-active");
  els.filePreviewModal.classList.add("is-active");
  els.filePreviewMeta.innerHTML = '<span>Cargando vista previa...</span>';
  els.filePreviewTable.querySelector("thead").innerHTML = "";
  els.filePreviewTable.querySelector("tbody").innerHTML = "";

  try {
    const data = await postJson("/api/file/preview", { filename, content_base64: base64 });

    if (data.error) {
      els.filePreviewMeta.innerHTML = `<span style="color:var(--color-danger);">${escapeHtml(data.error)}</span>`;
      return;
    }

    _previewSettings = { encoding: data.encoding, delimiter: data.delimiter, headerRow: data.detected_header_row };

    els.filePreviewMeta.innerHTML = `
      <span><strong>Archivo:</strong> ${escapeHtml(filename)}</span>
      <span><strong>Formato:</strong> ${escapeHtml(data.format)}</span>
      <span><strong>Codificación:</strong> ${escapeHtml(data.encoding)}</span>
      <span><strong>Filas:</strong> ${data.total_rows}</span>
      <span><strong>Columnas:</strong> ${data.headers.length}</span>
    `;

    els.previewDelimiter.value = data.delimiter;

    els.previewHeaderRow.innerHTML = "";
    for (let i = 0; i < Math.min(5, (data.total_rows || 10) + 1); i++) {
      const opt = document.createElement("option");
      opt.value = i;
      opt.textContent = i === data.detected_header_row ? `Fila ${i + 1} (detectada como encabezado)` : `Fila ${i + 1}`;
      if (i === data.detected_header_row) opt.selected = true;
      els.previewHeaderRow.appendChild(opt);
    }

    const thead = els.filePreviewTable.querySelector("thead");
    const tbody = els.filePreviewTable.querySelector("tbody");
    thead.innerHTML = `<tr>${data.headers.map(h => `<th>${escapeHtml(h)}</th>`).join("")}</tr>`;
    tbody.innerHTML = data.preview.map(row =>
      `<tr>${data.headers.map(h => `<td>${escapeHtml(String(row[h] ?? ""))}</td>`).join("")}</tr>`
    ).join("");
  } catch (err) {
    els.filePreviewMeta.innerHTML = `<span style="color:var(--color-danger);">Error: ${escapeHtml(err.message)}</span>`;
  }
}

function hideFilePreview() {
  els.filePreviewBackdrop.classList.remove("is-active");
  els.filePreviewModal.classList.remove("is-active");
}

if (els.filePreviewClose) els.filePreviewClose.addEventListener("click", hideFilePreview);
if (els.filePreviewCancel) els.filePreviewCancel.addEventListener("click", hideFilePreview);
if (els.filePreviewBackdrop) els.filePreviewBackdrop.addEventListener("click", hideFilePreview);

if (els.filePreviewConfirm) {
  els.filePreviewConfirm.addEventListener("click", () => {
    hideFilePreview();
    analyzeSelectedFile();
  });
}

function renderProfile() {
  const analysis = store.state.analysis;
  if (!analysis) return;
  els.profileTitle.textContent = `Perfilado técnico - ${analysis.filename}`;

  const overall = analysis.scores.overall;
  const qualityClass = overall >= 90 ? 'status--ok' : overall >= 70 ? 'status--warn' : 'status--error';
  els.metrics.innerHTML = [
    metric("Filas", analysis.row_count),
    metric("Columnas", analysis.column_count),
    metric("Duplicados", analysis.duplicate_rows),
    metric("Calidad general", `<span class="status ${qualityClass}">${overall}%</span>`),
  ].join("");

  els.profileTable.innerHTML = analysis.columns
    .map(
      (column, idx) => {
        const dist = column.distribution_pct != null ? column.distribution_pct : '-';
        const distNum = typeof dist === 'number' ? dist : 0;
        const distClass = distNum >= 90 ? 'dist--ok' : distNum >= 70 ? 'dist--warn' : 'dist--error';
        const examples = (column.examples || []).slice(0, 4).join(', ');
        const hasStats = column.min_value != null || column.max_value != null;
        const hasFormatGroups = (column.format_groups || []).length > 0;

        let detailRows = '';
        if (hasStats) {
          detailRows += `<tr><td>Min</td><td>${valueOrDash(column.min_value)}</td></tr>`;
          detailRows += `<tr><td>Max</td><td>${valueOrDash(column.max_value)}</td></tr>`;
          detailRows += `<tr><td>Media</td><td>${valueOrDash(column.mean)}</td></tr>`;
          detailRows += `<tr><td>Mediana</td><td>${valueOrDash(column.median)}</td></tr>`;
          detailRows += `<tr><td>Outliers</td><td>${column.outliers || 0}</td></tr>`;
        }
        if (hasFormatGroups) {
          const groups = column.format_groups.slice(0, 3).map(g =>
            `"${g.canonical}" ← ${(g.variants || []).slice(0, 3).join(', ')}`
          ).join('<br>');
          detailRows += `<tr><td>Variantes</td><td>${groups}</td></tr>`;
        }

        const valDist = column.value_distribution || [];
        let freqHtml = '';
        if (valDist.length > 0 && column.detected_type !== 'number') {
          const maxPct = Math.max(...valDist.map(v => v.pct), 1);
          const freqRows = valDist.map(v => {
            const barW = Math.max((v.pct / maxPct) * 100, 2);
            return `<div class="freq-row">
              <span class="freq-val">${escapeHtml(v.value)}</span>
              <span class="freq-bar-wrap"><span class="freq-bar" style="width:${barW}%"></span></span>
              <span class="freq-pct">${v.pct}%</span>
              <span class="freq-count">${v.freq}</span>
            </div>`;
          }).join('');
          freqHtml = `<tr><td colspan="2">
            <div class="drawer-section drawer-section--collapsible is-open" style="margin-top:8px;">
              <button class="drawer-section__toggle" type="button" onclick="this.parentElement.classList.toggle('is-open')">
                Distribución de Frecuencias <span class="toggle-badge">${valDist.length} valores</span> <span class="toggle-arrow">▾</span>
              </button>
              <div class="drawer-section__body freq-scroll">
                <div class="freq-header"><span>Valor</span><span></span><span>%</span><span>Frec</span></div>
                ${freqRows}
              </div>
            </div>
          </td></tr>`;
        }

        if (!detailRows && !freqHtml) {
          detailRows = '<tr><td colspan="2" style="color:var(--color-muted);">Sin detalles adicionales</td></tr>';
        }

        return `
      <tr class="profile-row" data-profile-idx="${idx}">
        <td>${escapeHtml(column.name)}</td>
        <td><span class="tag">${escapeHtml(column.detected_type)}</span></td>
        <td>${column.unique_values}</td>
        <td>${column.missing}</td>
        <td><span class="${distClass}">${dist}%</span></td>
        <td>${escapeHtml(examples)}</td>
        <td><button class="button button--ghost button--sm profile-toggle" data-toggle-idx="${idx}" type="button">+</button></td>
      </tr>
      <tr class="profile-detail" id="profileDetail-${idx}" style="display:none;">
        <td colspan="7">
          <table class="detail-table">
            <tbody>${detailRows}${freqHtml}</tbody>
          </table>
        </td>
      </tr>`;
      }
    )
    .join("");

  els.profileTable.querySelectorAll('.profile-toggle').forEach(btn => {
    btn.onclick = () => {
      const idx = btn.dataset.toggleIdx;
      const detail = document.querySelector(`#profileDetail-${idx}`);
      if (detail) {
        const isOpen = detail.style.display !== 'none';
        detail.style.display = isOpen ? 'none' : '';
        btn.textContent = isOpen ? '+' : '-';
      }
    };
  });
}

function renderRules() {
  const analysis = store.state.analysis;
  if (!analysis) return;

  const deletedColumns = store.state.actions
    .filter(a => a.kind === "delete_column")
    .map(a => a.column);

  els.rulesBoard.innerHTML = `
    <div class="rules-intro">
      <p class="action-desc">Revisa cada columna del dataset. Si alguna no es necesaria para tu análisis, elimínala aquí con una justificación. Las columnas eliminadas no aparecerán en el reporte final.</p>
    </div>
  ` + analysis.columns
    .map(
      (column) => {
        const isDeleted = deletedColumns.includes(column.name);
        const reason = store.state.actions.find(a => a.kind === "delete_column" && a.column === column.name)?.reason || "";
        return `
      <article class="decisión-card ${isDeleted ? "decisión-card--disabled" : ""}">
        <div>
          <span class="tag">${escapeHtml(column.detected_type)}</span>
          <h3>${escapeHtml(column.name)}</h3>
          <p>${column.missing} faltantes | ${column.unique_values} valores únicos | ${column.outliers} outliers</p>
        </div>
        ${isDeleted ? `
          <div class="action-done">
            <span class="status status--warn">Columna eliminada</span>
          </div>
          <p class="action-done__reason">Justificación: ${escapeHtml(reason)}</p>
        ` : `
          <p class="action-desc">¿Esta columna aporta al objetivo de tu análisis? Si no, elimínala y documenta por qué.</p>
          <label>
            Justificación para eliminar
            <input type="text" data-delete-reason="${escapeAttr(column.name)}" placeholder="Ej. no aporta al objetivo del análisis" />
          </label>
          <button class="button button--ghost" type="button" data-delete-column="${escapeAttr(column.name)}">Eliminar columna</button>
        `}
      </article>`;
      }
    )
    .join("");

  document.querySelectorAll("[data-delete-column]").forEach((button) => {
    button.addEventListener("click", () => {
      const column = button.dataset.deleteColumn;
      const input = document.querySelector(`[data-delete-reason="${cssEscape(column)}"]`);
      const reason = input?.value || "Columna retirada por decisión del analista.";
      addAction({ kind: "delete_column", column, reason });
      renderRules();
    });
  });
}

// --- Step 4: Depuración Guiada con Chat Lateral ---

let depurChatHistory = {};

function renderDepurationBoard() {
  const diagnostic = store.state.diagnostic;
  if (!diagnostic) return;

  const datasetCard = document.getElementById('datasetSummaryCard');
  const columnGrid = document.getElementById('depurColumnGrid');
  if (!datasetCard || !columnGrid) return;

  const datasetCol = diagnostic.columns?.find(c => c.column === '__dataset__');
  if (datasetCol && datasetCol.issues?.length > 0) {
    const issue = datasetCol.issues[0];
    const rows = issue.affected_rows || [];
    const groupApplied = store.state.actions.some(a => a.kind === 'remove_duplicate_rows');
    datasetCard.innerHTML = `
      <div class="dataset-summary-card__info">
        <h3>Filas Duplicadas en Dataset</h3>
        <p>${escapeHtml(issue.description || `${rows.length} filas duplicadas detectadas`)}</p>
        ${!groupApplied && rows.length > 0 ? `
          <div class="depur-rows" style="margin-top: 8px;">
            <code>${escapeHtml(rows.slice(0, 15).join(', '))}${rows.length > 15 ? ` (+${rows.length - 15})` : ''}</code>
          </div>
        ` : ''}
      </div>
      <div>
        ${groupApplied ? '<span class="status status--ok">Duplicados eliminados</span>' :
          rows.length > 0 ? `<button class="button button--primary button--sm" id="dedupeButton" type="button">Eliminar duplicados</button>` :
          '<span class="status status--ok">Sin duplicados</span>'}
      </div>
    `;
    datasetCard.style.display = 'flex';
    if (!groupApplied && rows.length > 0) {
      datasetCard.querySelector('#dedupeButton')?.addEventListener('click', () => {
        addAction({
          kind: 'remove_duplicate_rows',
          column: 'Dataset',
          rows,
          reason: 'Eliminación de filas duplicadas documentada por el analista.',
        });
        renderDepurationBoard();
      });
    }
  } else {
    datasetCard.innerHTML = '<p class="empty-state">Sin filas duplicadas en el dataset.</p>';
    datasetCard.style.display = 'block';
  }

  const columns = diagnostic.columns?.filter(c => c.column !== '__dataset__') || [];
  const colCards = columns.map(col => {
    const issues = (col.issues || []).filter(i => i.count > 0);
    const issueCount = issues.length;
    const totalRows = issues.reduce((s, i) => s + (i.count || 0), 0);
    const domain = col.inferred_domain || 'general';
    let badgeClass = 'column-card__badge--ok';
    let badgeText = 'Limpia';
    if (issueCount > 2 || totalRows > 20) { badgeClass = 'column-card__badge--danger'; badgeText = `${issueCount} problemas`; }
    else if (issueCount > 0) { badgeClass = 'column-card__badge--warn'; badgeText = `${issueCount} problema${issueCount !== 1 ? 's' : ''}`; }

    return `
      <div class="column-card" data-depur-col="${escapeAttr(col.column)}" tabindex="0">
        <div class="column-card__header">
          <div>
            <p class="column-card__name">${escapeHtml(col.column)}</p>
            <p class="column-card__domain">${escapeHtml(domain)}</p>
          </div>
          <span class="column-card__badge ${badgeClass}">${badgeText}</span>
        </div>
        <div class="column-card__footer">
          <span>${totalRows} filas afectadas</span>
          <span>${issues.length} categorías</span>
        </div>
        <div class="column-card__actions">
          <button class="button button--primary button--sm" data-depur-open-col="${escapeAttr(col.column)}" type="button">Abrir Copiloto</button>
        </div>
      </div>
    `;
  }).join('');

  columnGrid.innerHTML = colCards || '<p class="empty-state">No hay columnas para depurar.</p>';

  columnGrid.querySelectorAll('[data-depur-open-col]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      openDepurDrawer(btn.dataset.depurOpenCol);
    });
  });

  columnGrid.querySelectorAll('.column-card').forEach(card => {
    card.addEventListener('click', () => {
      const col = card.dataset.depurCol;
      if (col) openDepurDrawer(col);
    });
  });

  bindCleaningActions();
  renderLog();
  renderAnalystNotes();
  populateAdvancedColumns();
}

function openDepurDrawer(columnName) {
  const drawer = document.querySelector('#aiColumnDrawer');
  const backdrop = document.querySelector('#aiColumnDrawerBackdrop');
  const badge = document.querySelector('#drawerColBadge');
  const title = document.querySelector('#drawerColTitle');
  const meta = document.querySelector('#drawerColMeta');
  const diagBox = document.querySelector('#drawerDiagnostics');
  const recsBox = document.querySelector('#drawerAIRecs');
  const chatFeed = document.querySelector('#drawerChatFeed');

  if (!drawer || !backdrop) return;

  nube.currentDrawerColumn = columnName;

  badge.textContent = 'Columna';
  title.textContent = columnName;
  meta.textContent = 'Copiloto de Depuración';

  const diagnostic = store.state.diagnostic;
  const colDiag = diagnostic?.columns?.find(c => c.column === columnName);
  const issues = colDiag?.issues || [];
  const profiler = colDiag?.profiler || {};

  let extraSections = '';

  const profileCol = (store.state.analysis?.columns || []).find(c => c.name === columnName);
  const pType = profiler.type || profileCol?.detected_type || '';

  if (['CATEGORICA', 'BOOLEANA', 'CONSTANTE', 'TEXTO_LIBRE'].includes(pType)) {
    const allVals = [
      ...(profiler.dominant_values || []),
      ...(profiler.suspicious_values || []),
    ].sort((a, b) => b.pct - a.pct);
    if (allVals.length > 0) {
      const maxPct = Math.max(...allVals.map(v => v.pct), 1);
      const rows = allVals.map(v => {
        const barW = Math.max((v.pct / maxPct) * 100, 2);
        const isSuspicious = (profiler.suspicious_values || []).some(s => s.value === v.value);
        return `<div class="freq-row${isSuspicious ? ' freq-row--suspicious' : ''}">
          <span class="freq-val">${escapeHtml(v.value)}</span>
          <span class="freq-bar-wrap"><span class="freq-bar" style="width:${barW}%"></span></span>
          <span class="freq-pct">${v.pct}%</span>
          <span class="freq-count">${v.freq}</span>
        </div>`;
      }).join('');
      extraSections += `
        <div class="drawer-section drawer-section--collapsible">
          <button class="drawer-section__toggle" type="button" onclick="this.parentElement.classList.toggle('is-open')">
            Distribución de Frecuencias <span class="toggle-badge">${allVals.length} valores</span> <span class="toggle-arrow">▾</span>
          </button>
          <div class="drawer-section__body freq-scroll">
            <div class="freq-header"><span>Valor</span><span></span><span>%</span><span>Frec</span></div>
            ${rows}
          </div>
        </div>`;
    }
  }

  if (pType === 'number' || profileCol?.detected_type === 'number') {
    const s = profileCol || {};
    const stats = [
      ['Mínimo', s.min_value],
      ['Máximo', s.max_value],
      ['Promedio', s.mean],
      ['Mediana', s.median],
      ['Outliers', s.outliers != null ? `${s.outliers} valores` : null],
    ].filter(([, v]) => v != null);
    if (stats.length > 0) {
      const rows = stats.map(([label, val]) =>
        `<div class="stat-row"><span class="stat-label">${label}</span><span class="stat-value">${typeof val === 'number' ? val.toLocaleString('es-CO') : escapeHtml(String(val))}</span></div>`
      ).join('');
      extraSections += `
        <div class="drawer-section drawer-section--collapsible">
          <button class="drawer-section__toggle" type="button" onclick="this.parentElement.classList.toggle('is-open')">
            Estadísticas de Columna <span class="toggle-arrow">▾</span>
          </button>
          <div class="drawer-section__body">
            ${rows}
          </div>
        </div>`;
    }
  }

  if (issues.length === 0 && !extraSections) {
    diagBox.innerHTML = `<p class="empty-state">No se detectaron problemas en esta columna.</p>`;
  } else {
    const issuesHtml = issues.map(iss => {
      const sevClass = iss.severity === 'CRITICA' ? 'severity--critica' : iss.severity === 'ALTA' ? 'severity--alta' : iss.severity === 'MEDIA' ? 'severity--media' : 'severity--baja';
      const exHtml = (iss.examples || []).slice(0, 3).map(e => `<div class="drawer-issue-example">${renderExample(e)}</div>`).join('');
      const rowsHtml = iss.affected_rows?.length > 0
        ? `<div class="drawer-issue-rows">Filas: <code>${escapeHtml(abbreviateRows(iss.affected_rows, 6))}</code></div>`
        : '';
      return `
        <div class="drawer-issue-item">
          <div class="drawer-issue-item__header">
            <strong>${escapeHtml(iss.category || iss.category_code)}</strong>
            <span class="drawer-issue-severity ${sevClass}">${escapeHtml(iss.severity || '')}</span>
            <span class="drawer-issue-count">${iss.count || 0} filas (${(iss.percentage || 0).toFixed(1)}%)</span>
          </div>
          <div class="drawer-issue-desc">${escapeHtml(iss.description || '')}</div>
          ${exHtml ? `<div class="drawer-issue-examples">${exHtml}</div>` : ''}
          ${rowsHtml}
        </div>`;
    }).join('');
    diagBox.innerHTML = extraSections + issuesHtml;
  }

  recsBox.innerHTML = '<div class="nube-loading" style="padding:var(--space-3);"><div class="nube-spinner"></div><p style="font-size:0.8rem;">Cargando recomendaciónes...</p></div>';

  const history = depurChatHistory[columnName] || [];
  chatFeed.innerHTML = '';
  history.forEach(msg => {
    const div = document.createElement('div');
    div.className = `chat-bubble chat-bubble--${msg.role === 'assistant' ? 'ai' : 'user'}`;
    div.innerHTML = `<strong>${msg.role === 'assistant' ? 'Copiloto' : 'Tu'}:</strong> ${escapeHtml(msg.content)}`;
    chatFeed.appendChild(div);
  });
  if (history.length === 0) {
    chatFeed.innerHTML = `
      <div class="chat-bubble chat-bubble--ai">
        <strong>Copiloto:</strong> Hola, estoy analizando la columna <code>${escapeHtml(columnName)}</code>.
        ${issues.length > 0 ? `Detecte <strong>${issues.length}</strong> problema(s): ${issues.map(i => i.category_code).join(', ')}.` : 'No hay problemas detectados.'}
        Preguntame lo que necesites o usa las recomendaciónes de abajo para depurar. Tu tienes el control.
      </div>
    `;
  }

  drawer.classList.add('is-active');
  backdrop.classList.add('is-active');

  if (!drawer._eventsBound) {
    const closeBtn = document.querySelector('#drawerCloseButton');
    if (closeBtn) closeBtn.onclick = () => { drawer.classList.remove('is-active'); backdrop.classList.remove('is-active'); };
    if (backdrop) backdrop.onclick = () => { drawer.classList.remove('is-active'); backdrop.classList.remove('is-active'); };

    const sendBtn = document.querySelector('#drawerChatSendButton');
    const input = document.querySelector('#drawerChatInput');
    if (sendBtn && input) {
      const handleSend = () => {
        const query = input.value.trim();
        if (!query || !nube.currentDrawerColumn) return;
        input.value = '';
        sendDepurChatMessage(nube.currentDrawerColumn, query);
      };
      sendBtn.onclick = handleSend;
      input.onkeydown = (e) => { if (e.key === 'Enter') handleSend(); };
    }
    drawer._eventsBound = true;
  }

  fetchDepurRecommendations(columnName, colDiag, recsBox);
}

async function fetchDepurRecommendations(columnName, colDiag, recsBox) {
  try {
    const response = await fetch('/api/ai/column-recommendations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: store.state.filename,
        content_base64: store.state.fileBase64,
        column: columnName
      })
    });

    if (!response.ok) throw new Error('Error al obtener recomendaciónes');

    const data = await response.json();
    const recs = data.recommendations || [];

    if (recs.length === 0) {
      recsBox.innerHTML = `<p class="empty-state">Sin recomendaciónes automaticas. Pregunta al Copiloto.</p>`;
      return;
    }

    recsBox.innerHTML = recs.map((rec, idx) => {
      const rows = rec.affected_rows || [];
      const rowsText = rows.length > 0 ? rows.slice(0, 5).join(', ') + (rows.length > 5 ? ` (+${rows.length - 5})` : '') : 'N/A';
      const actionKind = rec.action?.kind || 'flag_outliers';
      const actionMethod = rec.action?.method || rec.action?.value || '';
      const actionLabel = labelForAction(actionKind);
      const shortText = (rec.text || '').length > 80 ? (rec.text || '').substring(0, 80) + '...' : (rec.text || '');

      return `
      <div class="drawer-rec-card" data-rec-idx="${idx}">
        <div class="drawer-rec-header">
          <span class="tag tag--sm">${escapeHtml(rec.category || '')}</span>
          <span style="font-size:0.75rem;color:var(--color-muted);">${rows.length} fila(s)</span>
        </div>
        <p class="drawer-rec-text">${escapeHtml(shortText)}</p>
        <div class="drawer-rec-action-line">
          <span class="drawer-rec-action-badge">${escapeHtml(actionLabel)}</span>
          ${actionMethod ? `<span class="drawer-rec-method">→ ${escapeHtml(actionMethod)}</span>` : ''}
        </div>
        ${rows.length > 0 ? `<p class="drawer-rec-rows">Filas: <code>${escapeHtml(rowsText)}</code></p>` : ''}
        <div class="drawer-rec-reason">
          <textarea rows="1" placeholder="Justificación (opcional)..." data-rec-reason="${idx}"></textarea>
        </div>
        <div class="drawer-rec-actions">
          <button class="button button--primary button--sm" type="button" data-accept-rec="${idx}" data-col="${escapeAttr(columnName)}" data-kind="${escapeAttr(actionKind)}" data-method="${escapeAttr(actionMethod)}" data-rows="${escapeAttr(JSON.stringify(rows))}">Aceptar</button>
          <button class="button button--ghost button--sm" type="button" data-dismiss-rec="${idx}">Cancelar</button>
        </div>
        <div class="drawer-rec-validation" id="recValidation-${idx}" style="display:none;">
          <div class="rec-validation__summary">
            <div class="rec-validation__row"><span class="rec-validation__label">Acción:</span> <strong>${escapeHtml(actionLabel)}</strong></div>
            <div class="rec-validation__row"><span class="rec-validation__label">Columna:</span> ${escapeHtml(columnName)}</div>
            ${actionMethod ? `<div class="rec-validation__row"><span class="rec-validation__label">Metodo:</span> ${escapeHtml(actionMethod)}</div>` : ''}
            <div class="rec-validation__row"><span class="rec-validation__label">Filas:</span> <code>${escapeHtml(rowsText)}</code> (${rows.length})</div>
          </div>
          <div class="drawer-rec-actions" style="margin-top:var(--space-2);">
            <button class="button button--success button--sm" type="button" data-confirm-rec="${idx}">Confirmar y Documentar</button>
            <button class="button button--ghost button--sm" type="button" data-cancel-validation="${idx}">Volver</button>
          </div>
        </div>
      </div>`;
    }).join('');

    recsBox.querySelectorAll('[data-accept-rec]').forEach(btn => {
      btn.onclick = () => {
        const idx = Number(btn.dataset.acceptRec);
        const card = btn.closest('.drawer-rec-card');
        const validation = card.querySelector(`#recValidation-${idx}`);
        if (validation) {
          btn.style.display = 'none';
          validation.style.display = 'block';
        }
      };
    });

    recsBox.querySelectorAll('[data-cancel-validation]').forEach(btn => {
      btn.onclick = () => {
        const idx = Number(btn.dataset.cancelValidation);
        const card = btn.closest('.drawer-rec-card');
        const validation = card.querySelector(`#recValidation-${idx}`);
        const applyBtn = card.querySelector(`[data-accept-rec="${idx}"]`);
        if (validation) validation.style.display = 'none';
        if (applyBtn) applyBtn.style.display = '';
      };
    });

    recsBox.querySelectorAll('[data-confirm-rec]').forEach(btn => {
      btn.onclick = () => {
        const idx = Number(btn.dataset.confirmRec);
        const card = btn.closest('.drawer-rec-card');
        const applyBtn = card.querySelector(`[data-accept-rec="${idx}"]`);
        const kind = applyBtn.dataset.kind;
        const col = applyBtn.dataset.col;
        const method = applyBtn.dataset.method;
        const rows = JSON.parse(applyBtn.dataset.rows || '[]');
        const reasonTextarea = card.querySelector(`[data-rec-reason="${idx}"]`);
        const userReason = reasonTextarea?.value?.trim() || '';
        const autoReason = `Validado y confirmado desde Copiloto IA: ${card.querySelector('p')?.textContent || ''}`;
        addAction({
          kind,
          column: col,
          method,
          rows,
          _rowsKey: `${kind}_${rows.join(',')}`,
          reason: userReason || autoReason,
        });
        card.innerHTML = `<div class="rec-confirmed"><span class="status status--ok">Aplicada y documentada en bitácora</span></div>`;
        renderDepurationBoard();
      };
    });

    recsBox.querySelectorAll('[data-dismiss-rec]').forEach(btn => {
      btn.onclick = () => btn.closest('.drawer-rec-card')?.remove();
    });
  } catch (e) {
    recsBox.innerHTML = `
      <div class="empty-state" style="text-align:center;padding:var(--space-3);">
        <p style="margin:0 0 8px;">No se pudieron cargar las recomendaciónes.</p>
        <p style="margin:0 0 12px;font-size:0.8rem;color:var(--color-muted);">Verifica tu conexión y vuelve a intentar.</p>
        <button class="button button--primary button--sm retry-recommendations" type="button">
          Reintentar
        </button>
      </div>`;
    recsBox.querySelector('.retry-recommendations')?.addEventListener('click', () => {
      recsBox.innerHTML = '<div class="nube-loading" style="padding:var(--space-3);"><div class="nube-spinner"></div><p style="font-size:0.8rem;">Cargando recomendaciónes...</p></div>';
      fetchDepurRecommendations(columnName, colDiag, recsBox);
    });
  }
}

async function sendDepurChatMessage(columnName, query) {
  const chatFeed = document.querySelector('#drawerChatFeed');
  if (!chatFeed) return;

  const userDiv = document.createElement('div');
  userDiv.className = 'chat-bubble chat-bubble--user';
  userDiv.innerHTML = `<strong>Tu:</strong> ${escapeHtml(query)}`;
  chatFeed.appendChild(userDiv);

  if (!depurChatHistory[columnName]) depurChatHistory[columnName] = [];
  depurChatHistory[columnName].push({ role: 'user', content: query });

  const thinkingDiv = document.createElement('div');
  thinkingDiv.className = 'chat-bubble chat-bubble--ai';
  thinkingDiv.innerHTML = `<strong>Copiloto:</strong> <em>Analizando...</em>`;
  chatFeed.appendChild(thinkingDiv);
  chatFeed.scrollTop = chatFeed.scrollHeight;

  try {
    const response = await fetch('/api/ai/chat-column', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: store.state.filename,
        content_base64: store.state.fileBase64,
        column: columnName,
        user_query: query,
        chat_history: depurChatHistory[columnName].slice(-10)
      })
    });

    if (!response.ok) throw new Error('Error de conexión con la IA');

    const data = await response.json();
    const answer = data.response || 'Sin respuesta';
    thinkingDiv.innerHTML = `<strong>Copiloto:</strong> ${escapeHtml(answer)}`;
    depurChatHistory[columnName].push({ role: 'assistant', content: answer });
  } catch (e) {
    thinkingDiv.innerHTML = `<strong>Copiloto:</strong> Error: ${escapeHtml(e.message)}`;
  }
  chatFeed.scrollTop = chatFeed.scrollHeight;
}

function bindCleaningActions() {
  // Actions are now handled directly in renderDepurationBoard and openDepurDrawer
}

function addAction(action) {
  store.addAction(action);
  renderLog();
  renderAnalystNotes();
  els.systemStatus.textContent = `${store.state.actions.length} decisión(es) documentada(s)`;
}

function undoLastAction() {
  const undone = store.undoAction();
  if (undone) {
    renderLog();
    renderRules();
    renderDepurationBoard();
    populateAdvancedColumns();
    els.systemStatus.textContent = `${store.state.actions.length} decisión(es) documentada(s)`;
  }
}

function renderLog() {
  const actions = store.state.actions;
  els.undoButton.disabled = actions.length === 0;

  if (!actions.length) {
    els.actionsLog.innerHTML = `<p class="empty-state">Aún no hay acciones registradas.</p>`;
    return;
  }
  els.actionsLog.innerHTML = actions
    .map(
      (action, index) => {
        const isNote = action.kind === 'analyst_note';
        const itemClass = isNote ? 'log-item log-item--note' : 'log-item';
        const ts = action.timestamp ? new Date(action.timestamp).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' }) : '';
        return `
      <div class="${itemClass}">
        <div class="log-item__row">
          <div class="log-item__text">
            <strong>${index + 1}. ${labelForAction(action.kind)}</strong>
            ${action.column ? `<span>${escapeHtml(action.column)}</span>` : (isNote ? `<span style="font-size:0.7rem;color:var(--color-accent);">${ts}</span>` : '')}
            <p>${escapeHtml(action.reason || "")}</p>
          </div>
          <button class="log-item__undo" data-undo-index="${index}" type="button" title="Deshacer">&#10005;</button>
        </div>
      </div>`;
      },
    )
    .join("");

  document.querySelectorAll("[data-undo-index]").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.undoIndex);
      store.removeAction(index);
      renderLog();
      renderRules();
      renderDepurationBoard();
      populateAdvancedColumns();
      els.systemStatus.textContent = `${store.state.actions.length} decisión(es) documentada(s)`;
    });
  });
}

function renderAnalystNotes() {
  const list = document.getElementById('analystNotesList');
  if (!list) return;

  const notes = store.state.actions.filter(a => a.kind === 'analyst_note');
  if (!notes.length) {
    list.innerHTML = '';
    return;
  }

  list.innerHTML = notes.map((note, idx) => {
    const realIndex = store.state.actions.indexOf(note);
    const ts = note.timestamp ? new Date(note.timestamp).toLocaleString('es-CO', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';
    return `
      <div class="analyst-note-item" data-note-idx="${realIndex}">
        <div class="analyst-note-item__content">
          <div class="analyst-note-item__text">${escapeHtml(note.reason || '')}</div>
          <div class="analyst-note-item__time">${ts}</div>
        </div>
        <div class="analyst-note-item__actions">
          <button data-edit-note="${realIndex}" type="button" title="Editar nota">&#9998;</button>
          <button data-remove-note="${realIndex}" type="button" title="Eliminar nota">&#10005;</button>
        </div>
      </div>
    `;
  }).join('');

  list.querySelectorAll('[data-edit-note]').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = Number(btn.dataset.editNote);
      const action = store.state.actions[idx];
      if (!action) return;
      const textarea = document.getElementById('analystNoteInput');
      if (textarea) {
        textarea.value = action.reason || '';
        textarea.focus();
      }
      store.removeAction(idx);
      renderAnalystNotes();
      renderLog();
    });
  });

  list.querySelectorAll('[data-remove-note]').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = Number(btn.dataset.removeNote);
      store.removeAction(idx);
      renderAnalystNotes();
      renderLog();
    });
  });
}

function addAnalystNote() {
  const textarea = document.getElementById('analystNoteInput');
  if (!textarea) return;
  const text = textarea.value.trim();
  if (!text) return;

  addAction({
    kind: 'analyst_note',
    column: null,
    reason: text,
    timestamp: new Date().toISOString(),
  });

  textarea.value = '';
  renderAnalystNotes();
}

async function runCleaning() {
  showLoading("Aplicando limpieza documentada y generando reporte...");
  els.systemStatus.textContent = "Aplicando limpieza documentada...";
  try {
    const response = await postJson("/api/clean", {
      filename: store.state.filename,
      content_base64: store.state.fileBase64,
      actions: store.state.actions,
    });
    store.setCleaning(response.cleaning);
    renderValidation();
    renderReportPreview();
    enableStep(4);
    enableStep(5);
    els.systemStatus.textContent = "Limpieza compilada y validada";
    if (currentUser && authAvailable) {
      let pdfBase64 = "";
      try {
        const pdfResp = await postJson("/api/report/pdf", {
          cleaning: response.cleaning,
          analyst: els.analystInput.value,
          version: els.versionInput.value || "v1.0",
          row_meaning: store.state.rowMeaning || "",
          analysis_objective: store.state.analysisObjective || "",
        });
        pdfBase64 = pdfResp.content_base64 || "";
      } catch (_) { /* PDF optional for history */ }
      saveToHistory(
        { filename: store.state.filename, row_count: store.state.analysis?.row_count || 0, column_count: store.state.analysis?.column_count || 0, row_meaning: store.state.rowMeaning || "", analysis_objective: store.state.analysisObjective || "" },
        store.state.analysis,
        store.state.actions,
        response.cleaning.before,
        response.cleaning.after,
        pdfBase64
      ).then((id) => { if (id) loadHistory(); }).catch(() => { showToast("No se pudo guardar en historial.", "error"); });
    }
  } finally {
    hideLoading();
  }
}

function renderValidation() {
  const cleaning = store.state.cleaning;
  if (!cleaning) return;
  const before = cleaning.before;
  const after = cleaning.after;

  const missingBefore = before.columns.reduce((sum, c) => sum + (c.missing || 0), 0);
  const missingAfter = after.columns.reduce((sum, c) => sum + (c.missing || 0), 0);
  const formatBefore = before.columns.reduce((sum, c) => sum + (c.format_issues || 0), 0);
  const formatAfter = after.columns.reduce((sum, c) => sum + (c.format_issues || 0), 0);
  const outliersBefore = before.columns.reduce((sum, c) => sum + (c.outliers || 0), 0);
  const outliersAfter = after.columns.reduce((sum, c) => sum + (c.outliers || 0), 0);

  els.comparisonGrid.innerHTML = [
    compareMetric("Filas", before.row_count, after.row_count),
    compareMetric("Columnas", before.column_count, after.column_count),
    compareMetric("Duplicados", before.duplicate_rows, after.duplicate_rows),
    compareMetric("Calidad general", `${before.scores.overall}%`, `${after.scores.overall}%`),
  ].join("");

  const rows = [
    validationRow("Completitud", after.scores.completeness >= 95, `${before.scores.completeness}% → ${after.scores.completeness}% (${missingBefore} → ${missingAfter} faltantes)`),
    validationRow("Consistencia", after.scores.consistency >= 95, `${before.scores.consistency}% → ${after.scores.consistency}% (${formatBefore} → ${formatAfter} inconsistencias)`),
    validationRow("Exactitud", after.scores.accuracy >= 95, `${before.scores.accuracy}% → ${after.scores.accuracy}% (${outliersBefore} → ${outliersAfter} outliers)`),
    validationRow("Unicidad", after.duplicate_rows === 0, `${before.duplicate_rows} → ${after.duplicate_rows} filas duplicadas`),
    validationRow("Calidad general", after.scores.overall >= 90, `${before.scores.overall}% → ${after.scores.overall}%`),
    validationRow("Documentación", cleaning.actions.length > 0, `${cleaning.actions.length} decisiones documentadas en bitácora`),
  ];
  els.validationTable.innerHTML = rows.join("");
}

function renderReportPreview() {
  const cleaning = store.state.cleaning;
  if (!cleaning) return;
  const before = cleaning.before;
  const after = cleaning.after;
  const actions = cleaning.actions || [];

  const missingBefore = before.columns.reduce((sum, c) => sum + (c.missing || 0), 0);
  const formatBefore = before.columns.reduce((sum, c) => sum + (c.format_issues || 0), 0);
  const outliersBefore = before.columns.reduce((sum, c) => sum + (c.outliers || 0), 0);

  const changedDims = [];
  const dims = [
    ["Completitud", "completeness"],
    ["Consistencia", "consistency"],
    ["Exactitud", "accuracy"],
    ["Unicidad", "uniqueness"],
  ];
  for (const [label, key] of dims) {
    const diff = after.scores[key] - before.scores[key];
    if (Math.abs(diff) >= 0.01) {
      changedDims.push(`${label}: ${before.scores[key]}% → ${after.scores[key]}% (${diff > 0 ? '+' : ''}${diff.toFixed(1)}%)`);
    }
  }

  els.reportPreview.innerHTML = `
    <h3>Vista previa del Data Cleaning Report</h3>
    <p>El informe PDF contiene 10 secciones: Información General, Resumen Ejecutivo, Indicadores Clave (antes/después), Problemas Encontrados (6 dimensiones), Outliers y Fuera de Rango, Plan de Acciones, Evaluación de Calidad, Checklist de Validación, Riesgos Identificados, Metodología y Conclusión.</p>
    <div style="margin: 0.75rem 0; padding: 0.75rem; background: var(--color-black); border-radius: var(--radius-sm); border: 1px solid var(--color-border);">
      <p style="margin:0 0 0.4rem;"><strong>Dataset:</strong> ${escapeHtml(before.filename)}</p>
      <p style="margin:0 0 0.4rem;"><strong>Calidad general:</strong> ${before.scores.overall}% → ${after.scores.overall}%</p>
      <p style="margin:0 0 0.4rem;"><strong>Registros:</strong> ${before.row_count} → ${after.row_count} | <strong>Columnas:</strong> ${before.column_count} → ${after.column_count}</p>
      <p style="margin:0 0 0.4rem;"><strong>Problemas detectados antes:</strong> ${missingBefore} faltantes, ${formatBefore} inconsistencias, ${before.duplicate_rows} duplicados, ${outliersBefore} outliers</p>
      <p style="margin:0 0 0.4rem;"><strong>Acciones documentadas:</strong> ${actions.length}</p>
      ${changedDims.length ? `<p style="margin:0;"><strong>Mejoras:</strong> ${changedDims.join(' | ')}</p>` : '<p style="margin:0;"><strong>Sin cambios significativos</strong></p>'}
    </div>
    <p style="font-size:0.85rem; color: var(--color-muted);">Salida disponible: informe PDF (formato academico), informe Markdown y dataset limpio CSV.</p>
  `;
}

function onNext() {
  if (store.state.step === 3) {
    enableStep(4);
    nube._handleSkipValidation();
    router.navigate(4);
    return;
  }
  if (store.state.step === 4) {
    if (store.state.actions.length === 0) {
      store.setCleaning({
        before: store.state.analysis,
        after: store.state.analysis,
        actions: [],
        clean_csv: "",
      });
      renderValidation();
      renderReportPreview();
      enableStep(5);
      enableStep(6);
      router.navigate(5);
      return;
    }
    runCleaning().then(() => {
      enableStep(5);
      enableStep(6);
      router.navigate(5);
    }).catch((error) => {
      els.systemStatus.textContent = `Error: ${error.message}. Intenta de nuevo.`;
      store.setCleaning({
        before: store.state.analysis,
        after: store.state.analysis,
        actions: store.state.actions,
        clean_csv: "",
      });
      renderValidation();
      renderReportPreview();
      enableStep(5);
      enableStep(6);
      router.navigate(5);
    });
    return;
  }
  router.navigate(store.state.step + 1);
}

function goToStep(step) {
  if (step < 0 || step > 6) return;
  const button = document.querySelector(`[data-step-button="${step}"]`);
  if (button?.disabled) return;
  store.setStep(step);
  document.querySelectorAll("[data-step]").forEach((section) => {
    section.classList.toggle("is-active", Number(section.dataset.step) === step);
  });
  document.querySelectorAll("[data-step-button]").forEach((item) => {
    const index = Number(item.dataset.stepButton);
    item.classList.toggle("is-active", index === step);
    item.classList.toggle("is-done", index < step);
  });
  els.previousButton.disabled = step === 0;
  els.nextButton.disabled = !store.state.analysis || step === 6;
  if (step === 4) {
    els.nextButton.textContent = "Aplicar limpieza y validar";
  } else if (step === 5) {
    els.nextButton.textContent = "Generar informe";
  } else {
    els.nextButton.textContent = "Siguiente etapa";
  }

  // Cargar recomendaciónes de IA al entrar al step 3
  if (step === 3 && store.state.filename && store.state.fileBase64) {
    nube.loadRecommendations(store.state.filename, store.state.fileBase64);
  }

  // Re-renderizar tablero de depuración al entrar al step 4
  if (step === 4) {
    renderDepurationBoard();
  }
}

function enableStep(step) {
  const btn = document.querySelector(`[data-step-button="${step}"]`);
  if (btn) btn.disabled = false;
  if (step <= 5) {
    els.nextButton.disabled = false;
  }
}

async function downloadReport(type) {
  const cleaning = store.state.cleaning;
  if (!cleaning) {
    showToast("No hay datos de limpieza disponibles. Ejecuta la limpieza primero.", "error");
    return;
  }
  showLoading(`Generando informe ${type === "pdf" ? "PDF" : "Markdown"}...`);
  try {
    const route = type === "pdf" ? "/api/report/pdf" : "/api/report/markdown";
    const response = await postJson(route, {
      cleaning: cleaning,
      analyst: els.analystInput.value,
      version: els.versionInput.value || "v1.0",
      row_meaning: store.state.rowMeaning || "",
      analysis_objective: store.state.analysisObjective || "",
    });
    if (type === "pdf") {
      downloadBlob(response.filename, base64ToBlob(response.content_base64, "application/pdf"));
    } else {
      downloadBlob(response.filename, new Blob([response.content], { type: "text/markdown;charset=utf-8" }));
    }
    showToast(`Informe ${type === "pdf" ? "PDF" : "Markdown"} descargado.`, "success");
  } catch (error) {
    showToast(`Error generando informe: ${error.message}`, "error");
  } finally {
    hideLoading();
  }
}

function downloadCleanCsv() {
  const cleaning = store.state.cleaning;
  if (!cleaning) {
    showToast("No hay dataset limpio disponible. Ejecuta la limpieza primero.", "error");
    return;
  }
  downloadBlob("dataset_limpio.csv", new Blob([cleaning.clean_csv], { type: "text/csv;charset=utf-8" }));
  showToast("Dataset limpio descargado.", "success");
}

async function downloadAuditLog() {
  if (!store.state.fileBase64 || !store.state.actions.length) {
    showToast("No hay acciones documentadas para generar bitácora.", "error");
    return;
  }
  showLoading("Generando bitácora de cambios...");
  try {
    const response = await postJson("/api/report/audit-log", {
      filename: store.state.filename,
      content_base64: store.state.fileBase64,
      actions: store.state.actions,
    });
    downloadBlob(response.filename, new Blob([response.content], { type: "text/markdown;charset=utf-8" }));
    showToast("Bitácora de cambios descargada.", "success");
  } catch (error) {
    showToast(`Error generando bitácora: ${error.message}`, "error");
  } finally {
    hideLoading();
  }
}

async function saveToCloud() {
  const cleaning = store.state.cleaning;
  if (!cleaning) {
    showToast("No hay datos de limpieza para guardar.", "error");
    return;
  }
  if (!currentUser || !authAvailable) {
    showToast("Inicia sesión con Google para guardar en la nube.", "error");
    return;
  }
  showLoading("Guardando en la nube...");
  try {
    let pdfBase64 = "";
    try {
      const pdfResp = await postJson("/api/report/pdf", {
        cleaning: cleaning,
        analyst: els.analystInput.value,
        version: els.versionInput.value || "v1.0",
        row_meaning: store.state.rowMeaning || "",
        analysis_objective: store.state.analysisObjective || "",
      });
      pdfBase64 = pdfResp.content_base64 || "";
    } catch (_) { /* PDF optional */ }
    const id = await saveToHistory(
      { filename: store.state.filename, row_count: store.state.analysis?.row_count || 0, column_count: store.state.analysis?.column_count || 0, row_meaning: store.state.rowMeaning || "", analysis_objective: store.state.analysisObjective || "" },
      store.state.analysis,
      store.state.actions,
      cleaning.before,
      cleaning.after,
      pdfBase64
    );
    if (id) {
      showToast("Sesión guardada en la nube correctamente.", "success");
      loadHistory();
    } else {
      showToast("No se pudo guardar. Verifica tu conexión.", "error");
    }
  } catch (error) {
    showToast(`Error guardando en la nube: ${error.message}`, "error");
  } finally {
    hideLoading();
  }
}

function resetProject() {
  if (!confirm("¿Estás seguro? Se borrará todo: dataset, análisis, acciones e informe.")) return;
  store.clear();
  els.systemStatus.textContent = "Esperando dataset";
  els.datasetMeta.textContent = "Motor Python local";
  els.analyzeButton.disabled = true;
  els.profileTitle.textContent = "Perfilado técnico del dataset";
  els.metrics.innerHTML = "";
  els.profileTable.innerHTML = "";
  els.rulesBoard.innerHTML = "";
  els.actionsLog.innerHTML = `<p class="empty-state">Aún no hay acciones registradas.</p>`;
  els.comparisonGrid.innerHTML = "";
  els.validationTable.innerHTML = "";
  els.reportPreview.innerHTML = "";
  els.fileInput.value = "";
  els.analystInput.value = "";
  els.versionInput.value = "v1.0";
  router.navigate(0);
}

function metric(label, value) {
  return `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`;
}

function compareMetric(label, before, after) {
  return `<div class="metric"><span>${label}</span><strong>${before} -> ${after}</strong></div>`;
}

function validationRow(label, pass, description) {
  return `<tr><td>${label}</td><td><span class="status ${pass ? "status--ok" : "status--warn"}">${pass ? "Cumple" : "Revisar"}</span></td><td>${description}</td></tr>`;
}

function labelForAction(kind) {
  const labels = {
    analyst_note: "Nota del Analista",
    delete_column: "Eliminar columna",
    drop_missing_rows: "Eliminar filas con faltantes",
    impute_missing: "Imputar faltantes",
    standardize_text: "Estandarizar texto",
    remove_duplicate_rows: "Eliminar duplicados",
    flag_outliers: "Marcar outliers",
    fill_missing: "Rellenar celdas vacias",
    fill_empty: "Rellenar celdas vacias",
    replace_with_null: "Reemplazar con NULL",
    rename_column: "Renombrar columna",
    drop_duplicates: "Eliminar duplicados",
    convert_type: "Convertir tipo de dato",
    change_type: "Cambiar tipo de dato",
    drop_rows: "Eliminar filas",
    fix_format: "Corregir formato",
    replace_value: "Reemplazar valor",
  };
  return labels[kind] || kind;
}

async function postJson(route, payload) {
  const response = await fetch(route, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    const msg = data.detail || data.error || "Error de servidor";
    throw new Error(msg);
  }
  return data;
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function base64ToBlob(base64, type) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return new Blob([bytes], { type });
}

function downloadBlob(filename, blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function valueOrDash(value) {
  return value === null || value === undefined ? "-" : value;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => {
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
    return map[character];
  });
}

function renderExample(e) {
  if (typeof e === 'string') return escapeHtml(e);
  if (!e || typeof e !== 'object') return String(e);
  if (e.row !== undefined && e.original !== undefined && e.standard !== undefined)
    return `Fila ${e.row}: "${escapeHtml(e.original)}" → "${escapeHtml(e.standard)}"`;
  if (e.row !== undefined && e.meaning !== undefined)
    return `Fila ${e.row}: ${escapeHtml(e.value)} = ${escapeHtml(e.meaning)}`;
  if (e.row !== undefined && e.detail !== undefined)
    return `Fila ${e.row}: ${escapeHtml(e.detail)}`;
  if (e.row !== undefined && e.format !== undefined)
    return `Fila ${e.row}: ${escapeHtml(e.format)} (${e.count || 0})`;
  if (e.row !== undefined && e.error !== undefined)
    return `Fila ${e.row}: ${escapeHtml(e.error)} (${e.count || 0})`;
  if (e.row !== undefined && e.variants !== undefined)
    return `Fila ${e.row}: "${escapeHtml(e.value)}" (${e.variants.length} variantes)`;
  if (e.row !== undefined && e.value !== undefined)
    return `Fila ${e.row}: ${escapeHtml(String(e.value))}`;
  if (e.rows !== undefined && e.match !== undefined)
    return `Filas [${e.rows.join(', ')}] (${e.match})`;
  if (e.value !== undefined) return escapeHtml(String(e.value));
  if (e.format !== undefined) return `${escapeHtml(e.format)} (${e.count || 0})`;
  if (e.error !== undefined) return `${escapeHtml(e.error)} (${e.count || 0})`;
  return escapeHtml(JSON.stringify(e));
}

function abbreviateRows(rows, maxShow) {
  maxShow = maxShow || 8;
  if (!rows || rows.length === 0) return '';
  if (rows.length <= maxShow) return rows.join(', ');
  return rows.slice(0, maxShow).join(', ') + ` (+${rows.length - maxShow} mas)`;
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, "&#096;");
}

function cssEscape(value) {
  return CSS.escape(value);
}

function populateAdvancedColumns() {
  const cols = store.state.analysis?.columns || [];
  els.advColSelect.innerHTML = `<option value="">Selecciona columna...</option>` +
    cols.map(c => `<option value="${escapeAttr(c.name)}">${escapeHtml(c.name)}</option>`).join("");
}

els.advActionSelect.addEventListener("change", () => {
  const action = els.advActionSelect.value;
  els.advParam1Input.disabled = false;
  els.advParam2Row.style.display = "none";
  els.advParam1Input.value = "";
  els.advParam2Input.value = "";
  
  let helpEl = document.querySelector('#advHelpText');
  if (!helpEl) { helpEl = document.createElement('div'); helpEl.id = 'advHelpText'; els.advParam1Label.appendChild(helpEl); }
  helpEl.style.cssText = 'font-size:0.75rem;color:var(--color-muted);margin-top:4px;';

  if (action === "fill_empty") {
    els.advParam1Label.firstChild.textContent = "Nuevo valor para celdas vacias";
    els.advParam1Input.placeholder = "Ej. N/A, NULL, 0, Sin dato";
    helpEl.innerHTML = 'Detecta automaticamente las celdas vacias de la columna y las rellena con el valor indicado. No necesitas buscar el valor original.';
    els.advParam2Row.style.display = "none";
  } else if (action === "fill_missing") {
    els.advParam1Label.firstChild.textContent = "Estrategia de relleno";
    els.advParam1Input.placeholder = "null / mean / median / mode";
    helpEl.innerHTML = '<strong>null</strong> = vacío explicito · <strong>mean</strong> = media · <strong>median</strong> = mediana · <strong>mode</strong> = moda (valor mas frecuente)';
    els.advParam2Row.style.display = "none";
  } else if (action === "replace_value") {
    els.advParam1Label.firstChild.textContent = "Valor original (a buscar)";
    els.advParam1Input.placeholder = "Ej. bogota";
    els.advParam2Label.firstChild.textContent = "Nuevo valor (reemplazo)";
    els.advParam2Input.placeholder = "Ej. Bogota";
    els.advParam2Row.style.display = "block";
    helpEl.innerHTML = 'Busca todas las celdas con el valor exacto y las reemplaza por el nuevo.';
  } else if (action === "rename_column") {
    els.advParam1Label.firstChild.textContent = "Nuevo nombre de columna";
    els.advParam1Input.placeholder = "Ej. edad_anios";
    helpEl.innerHTML = 'Cambia el nombre de la columna. El nombre anterior desaparece del CSV.';
  } else if (action === "change_type") {
    els.advParam1Label.firstChild.textContent = "Nuevo tipo de dato";
    els.advParam1Input.placeholder = "number / text / boolean";
    helpEl.innerHTML = '<strong>number</strong> = convierte a numero · <strong>text</strong> = texto libre · <strong>boolean</strong> = true/false → si/no';
  } else {
    els.advParam1Label.firstChild.textContent = "Parámetro 1";
    els.advParam1Input.placeholder = "Selecciona acción primero";
    els.advParam1Input.disabled = true;
    helpEl.innerHTML = '';
  }
});

els.applyAdvActionButton.addEventListener("click", () => {
  const column = els.advColSelect.value;
  const kind = els.advActionSelect.value;
  const param1 = els.advParam1Input.value.trim();
  const param2 = els.advParam2Input.value.trim();
  const reason = els.advReasonInput.value.trim() || "Acción avanzada libre aplicada por el analista.";
  
  if (!column || !kind) {
    alert("Por favor selecciona columna y acción.");
    return;
  }
  if (kind === "fill_empty" && !param1) {
    alert("Por favor especifica el valor para rellenar las celdas vacías.");
    return;
  }
  if (kind === "fill_missing" && !["null", "mean", "median", "mode"].includes(param1)) {
    alert("Estrategia inválida. Usa: null, mean, median o mode");
    return;
  }
  if (kind === "replace_value" && (!param1 || !param2)) {
    alert("Por favor completa los dos valores para reemplazar.");
    return;
  }
  if (kind === "rename_column" && !param1) {
    alert("Por favor especifica el nuevo nombre de la columna.");
    return;
  }
  if (kind === "change_type" && !param1) {
    alert("Por favor especifica el nuevo tipo de dato.");
    return;
  }
  if (kind === "change_type" && !["number", "text", "boolean"].includes(param1)) {
    alert("Tipo inválido. Usa: number, text o boolean");
    return;
  }
  
  let action;
  if (kind === "fill_empty") {
    action = { kind, column, reason, value: param1 };
  } else if (kind === "fill_missing") {
    action = { kind, column, reason, method: param1, value: param1 };
  } else if (kind === "replace_value") {
    action = { kind, column, reason, method: param1, value: param2 };
  } else {
    action = { kind, column, reason, method: param1, value: param1 };
  }
  
  addAction(action);
  
  els.advActionSelect.value = "";
  els.advParam1Input.value = "";
  els.advParam1Input.disabled = true;
  els.advParam1Input.placeholder = "Selecciona acción primero";
  els.advParam2Input.value = "";
  els.advReasonInput.value = "";
  els.advParam2Row.style.display = "none";
  let helpEl = document.querySelector('#advHelpText');
  if (helpEl) helpEl.innerHTML = '';
});

function toggleHistory() {
  const isOpen = els.historyPanel.classList.contains("is-open");
  els.historyPanel.classList.toggle("is-open", !isOpen);
  els.historyBackdrop.classList.toggle("is-open", !isOpen);
  if (!isOpen) loadHistory();
}

function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("es-CO", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function showToast(message, type) {
  const existing = document.querySelector(".toast");
  if (existing) existing.remove();
  const toast = document.createElement("div");
  toast.className = `toast toast--${type || "info"}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.classList.add("is-visible"), 10);
  setTimeout(() => { toast.classList.remove("is-visible"); setTimeout(() => toast.remove(), 300); }, 4000);
}

async function loadHistory() {
  if (!currentUser) return;
  try {
    const items = await getHistory();
    if (!items.length) {
      els.historyList.innerHTML = '<p class="history-panel__empty">Aún no hay análisis guardados.</p>';
      return;
    }
    els.historyList.innerHTML = items.map(item => {
      const ds = item.datasets || {};
      const actions = item.actions_json || [];
      const hasData = item.before_json && item.after_json;
      const hasPdf = item.report_pdf_base64 && item.report_pdf_base64.length > 10;
      return `<div class="history-item${hasData ? " history-item--clickable" : ""}" data-session-id="${item.id}"${hasData ? ' role="button" tabindex="0"' : ""}>
        <div class="history-item__name">${escapeHtml(ds.filename || "dataset")}</div>
        <div class="history-item__meta">${ds.row_count || 0} filas | ${ds.column_count || 0} columnas | ${actions.length} acciones</div>
        <div class="history-item__date">${formatDate(item.created_at)}</div>
        <div class="history-item__actions">
          ${hasData ? '<span class="history-item__action">Restaurar</span>' : ""}
          ${hasPdf ? `<button class="history-item__download" data-pdf="${escapeAttr(item.report_pdf_base64)}" data-filename="${escapeAttr(ds.filename || "dataset")}" type="button">Descargar PDF</button>` : ""}
        </div>
      </div>`;
    }).join("");
    els.historyList.querySelectorAll(".history-item--clickable").forEach(el => {
      el.addEventListener("click", (e) => {
        if (e.target.closest(".history-item__download")) return;
        restoreSession(el.dataset.sessionId);
      });
    });
    els.historyList.querySelectorAll(".history-item__download").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const pdfB64 = btn.dataset.pdf;
        const fname = btn.dataset.filename;
        if (pdfB64) downloadBlob(`data_cleaning_report_${fname}.pdf`, base64ToBlob(pdfB64, "application/pdf"));
      });
    });
  } catch (e) {
    console.warn("History load failed:", e);
  }
}

async function restoreSession(sessionId) {
  showLoading("Restaurando sesión desde historial...");
  try {
    const session = await getHistorySession(sessionId);
    if (!session || !session.before_json || !session.after_json) {
      showToast("No se pudo restaurar: datos incompletos.", "error");
      return;
    }
    store.setFile(session.datasets.filename, "");
    store.state.analysis = session.before_json;
    store.state.actions = session.actions_json || [];
    store.setCleaning({ before: session.before_json, after: session.after_json, actions: session.actions_json || [], clean_csv: "" });
    store.saveState();
    router.navigate(4);
    renderValidation();
    renderReportPreview();
    enableStep(4);
    enableStep(5);
    els.systemStatus.textContent = `Sesión restaurada: ${session.datasets.filename}`;
    toggleHistory();
    showToast("Sesión restaurada correctamente.", "success");
  } catch (e) {
    showToast("Error al restaurar sesión.", "error");
    console.warn("Restore failed:", e);
  } finally {
    hideLoading();
  }
}

els.historyButton?.addEventListener("click", toggleHistory);
els.historyCloseButton?.addEventListener("click", toggleHistory);
els.historyBackdrop?.addEventListener("click", toggleHistory);

initAuth();
