import { Store } from "./state.js";
import { Router } from "./router.js";

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
  cleaningBoard: document.querySelector("#cleaningBoard"),
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
  advColSelect: document.querySelector("#advColSelect"),
  advActionSelect: document.querySelector("#advActionSelect"),
  advParam1Label: document.querySelector("#advParam1Label"),
  advParam1Input: document.querySelector("#advParam1Input"),
  advParam2Row: document.querySelector("#advParam2Row"),
  advParam2Label: document.querySelector("#advParam2Label"),
  advParam2Input: document.querySelector("#advParam2Input"),
  advReasonInput: document.querySelector("#advReasonInput"),
  applyAdvActionButton: document.querySelector("#applyAdvActionButton"),
};

const router = new Router(goToStep);

els.fileInput.addEventListener("change", () => {
  const file = els.fileInput.files[0];
  if (file) {
    fileToBase64(file).then(base64 => {
      store.setFile(file.name, base64);
      els.analyzeButton.disabled = false;
      els.systemStatus.textContent = `Archivo listo: ${file.name}`;
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
      store.setFile(file.name, base64);
      els.analyzeButton.disabled = false;
      els.systemStatus.textContent = `Archivo listo: ${file.name}`;
    });
  }
});

els.analyzeButton.addEventListener("click", analyzeSelectedFile);
els.loadSampleButton.addEventListener("click", loadSample);
els.previousButton.addEventListener("click", () => router.navigate(store.state.step - 1));
els.nextButton.addEventListener("click", onNext);
els.downloadMarkdownButton.addEventListener("click", () => downloadReport("markdown"));
els.downloadPdfButton.addEventListener("click", () => downloadReport("pdf"));
els.downloadCsvButton.addEventListener("click", downloadCleanCsv);
els.undoButton.addEventListener("click", undoLastAction);

document.querySelectorAll("[data-step-button]").forEach((button) => {
  button.addEventListener("click", () => router.navigate(Number(button.dataset.stepButton)));
});

function init() {
  if (store.state.filename) {
    els.systemStatus.textContent = `Sesión recuperada: ${store.state.filename}`;
    if (store.state.analysis) {
      renderProfile();
      renderRules();
      renderCleaningBoard();
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
      enableStep(4);
      enableStep(5);
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
    const response = await postJson("/api/analyze", {
      filename: store.state.filename,
      content_base64: store.state.fileBase64,
    });
    store.setAnalysis(response.analysis);
    renderProfile();
    renderRules();
    renderCleaningBoard();
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

function renderProfile() {
  const analysis = store.state.analysis;
  if (!analysis) return;
  els.profileTitle.textContent = `Perfilado técnico - ${analysis.filename}`;
  els.metrics.innerHTML = [
    metric("Filas", analysis.row_count),
    metric("Columnas", analysis.column_count),
    metric("Duplicados", analysis.duplicate_rows),
    metric("Calidad general", `${analysis.scores.overall}%`),
  ].join("");

  els.profileTable.innerHTML = analysis.columns
    .map(
      (column) => `
      <tr>
        <td>${escapeHtml(column.name)}</td>
        <td><span class="tag">${escapeHtml(column.detected_type)}</span></td>
        <td>${column.unique_values}</td>
        <td>${column.missing}</td>
        <td>${valueOrDash(column.min_value)}</td>
        <td>${valueOrDash(column.max_value)}</td>
        <td>${escapeHtml((column.examples || []).slice(0, 4).join(", "))}</td>
      </tr>`,
    )
    .join("");
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
      <article class="decision-card ${isDeleted ? "decision-card--disabled" : ""}">
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

const ACTION_DESCRIPTIONS = {
  remove_duplicate_rows: "Elimina filas que son idénticas en todas las columnas. Solo úsalo si cada fila representa una entidad única (ej. un participante, un cliente).",
  impute_missing: "Reemplaza valores vacíos con un valor calculado (media, mediana, moda o uno que tú definas). Útil cuando hay pocos datos faltantes.",
  drop_missing_rows: "Elimina filas completas que tienen al menos un valor vacío en esta columna. Úsalo cuando la fila no tiene sentido sin ese dato.",
  standardize_text: "Unifica la escritura del texto (mayúsculas, minúsculas o capitalizado). Evita que la misma cosa aparezca como categorías diferentes.",
  flag_outliers: "Marca valores extremos para que los revises manualmente. No elimina nada: solo te alerta sobre datos inusuales.",
  delete_column: "Elimina toda la columna del dataset. Úsalo solo si la columna no aporta nada al objetivo del análisis.",
};

function renderCleaningBoard() {
  const analysis = store.state.analysis;
  if (!analysis) return;
  const cards = [];
  const appliedActions = store.state.actions;

  function isActionApplied(kind, column) {
    return appliedActions.some(a => a.kind === kind && a.column === column);
  }

  if (analysis.duplicate_rows > 0) {
    const applied = isActionApplied("remove_duplicate_rows", "Dataset");
    cards.push(`
      <article class="decision-card decision-card--critical ${applied ? "decision-card--done" : ""}">
        <span class="tag">Unicidad</span>
        <h3>Filas duplicadas completas</h3>
        <p class="action-desc">${ACTION_DESCRIPTIONS.remove_duplicate_rows}</p>
        <p class="action-detail">Se detectaron <strong>${analysis.duplicate_rows}</strong> filas duplicadas.</p>
        ${applied ? `
          <div class="action-done">
            <span class="status status--ok">Acción aplicada</span>
          </div>
        ` : `
          <label>¿Por qué eliminas los duplicados?<input type="text" id="dedupeReason" placeholder="Ej. cada fila es un participante único" /></label>
          <button class="button button--primary" type="button" id="dedupeButton">Eliminar duplicados</button>
        `}
      </article>`);
  }

  for (const column of analysis.columns) {
    const hasMissing = column.missing > 0;
    const hasFormatIssues = column.detected_type !== "number" && column.format_issues > 0;
    const hasOutliers = column.outliers > 0;

    if (!hasMissing && !hasFormatIssues && !hasOutliers) continue;

    let issuesList = [];
    if (hasMissing) issuesList.push(`${column.missing} valores vacíos`);
    if (hasFormatIssues) issuesList.push(`${column.format_issues} variantes de formato`);
    if (hasOutliers) issuesList.push(`${column.outliers} valores atípicos`);

    let actionsHtml = "";

    if (hasMissing) {
      const imputeApplied = isActionApplied("impute_missing", column.name);
      const dropApplied = isActionApplied("drop_missing_rows", column.name);
      actionsHtml += `
        <div class="action-group">
          <p class="action-group__title">Valores vacíos → ¿Qué hacemos?</p>
          <p class="action-desc">${ACTION_DESCRIPTIONS.impute_missing}</p>
          ${imputeApplied ? `
            <div class="action-done">
              <span class="status status--ok">Imputación aplicada</span>
            </div>
          ` : `
            <div class="inline-controls">
              <select data-impute-method="${escapeAttr(column.name)}">
                <option value="mode">Rellenar con la moda (más frecuente)</option>
                <option value="mean">Rellenar con el promedio</option>
                <option value="median">Rellenar con la mediana</option>
                <option value="custom">Rellenar con un valor que yo defina</option>
              </select>
              <input type="text" data-custom-value="${escapeAttr(column.name)}" placeholder="Valor personalizado (si aplica)" />
            </div>
            <label>¿Por qué imputas este valor?<input type="text" data-impute-reason="${escapeAttr(column.name)}" placeholder="Ej. solo el 5% están vacíos, es seguro rellenar" /></label>
            <button class="button button--primary" type="button" data-impute="${escapeAttr(column.name)}">Imputar valores vacíos</button>
          `}
          ${!imputeApplied && !dropApplied ? `<p class="action-desc" style="margin-top:0.5rem">${ACTION_DESCRIPTIONS.drop_missing_rows}</p>` : ""}
          ${dropApplied ? `
            <div class="action-done">
              <span class="status status--ok">Filas eliminadas</span>
            </div>
          ` : !imputeApplied ? `
            <button class="button button--ghost" type="button" data-drop-missing="${escapeAttr(column.name)}">Eliminar filas con vacío</button>
          ` : ""}
        </div>`;
    }

    if (hasFormatIssues) {
      const stdApplied = isActionApplied("standardize_text", column.name);
      actionsHtml += `
        <div class="action-group">
          <p class="action-group__title">Variantes de texto → ¿Unificamos?</p>
          <p class="action-desc">${ACTION_DESCRIPTIONS.standardize_text}</p>
          ${stdApplied ? `
            <div class="action-done">
              <span class="status status--ok">Texto estandarizado</span>
            </div>
          ` : `
            <div class="inline-controls">
              <select data-standardize-method="${escapeAttr(column.name)}">
                <option value="title">Capitalizar (primera letra mayúscula)</option>
                <option value="upper">TODO EN MAYÚSCULAS</option>
                <option value="lower">todo en minúsculas</option>
              </select>
            </div>
            <label>¿Por qué unificas la escritura?<input type="text" data-standardize-reason="${escapeAttr(column.name)}" placeholder="Ej. 'Bogota' y 'bogota' son lo mismo" /></label>
            <button class="button button--primary" type="button" data-standardize="${escapeAttr(column.name)}">Unificar escritura</button>
          `}
        </div>`;
    }

    if (hasOutliers) {
      const flagApplied = isActionApplied("flag_outliers", column.name);
      actionsHtml += `
        <div class="action-group">
          <p class="action-group__title">Valores atípicos → ¿Qué hacemos?</p>
          <p class="action-desc">${ACTION_DESCRIPTIONS.flag_outliers}</p>
          ${flagApplied ? `
            <div class="action-done">
              <span class="status status--ok">Marcado para revisión</span>
            </div>
          ` : `
            <label>¿Por qué marcas estos valores?<input type="text" data-outlier-reason="${escapeAttr(column.name)}" placeholder="Ej. edad 450 no es posible, revisar fuente" /></label>
            <button class="button button--ghost" type="button" data-flag-outliers="${escapeAttr(column.name)}">Marcar para revisión</button>
          `}
        </div>`;
    }

    cards.push(`
      <article class="decision-card">
        <div>
          <span class="tag">${escapeHtml(column.name)}</span>
          <h3>${escapeHtml(column.name)}</h3>
          <p class="action-detail">${issuesList.join(" · ")}</p>
        </div>
        ${actionsHtml}
      </article>`);
  }

  els.cleaningBoard.innerHTML = cards.length ? cards.join("") : `<p class="empty-state">No se detectaron problemas. Puedes avanzar a la siguiente etapa.</p>`;
  bindCleaningActions();
}

function bindCleaningActions() {
  document.querySelector("#dedupeButton")?.addEventListener("click", () => {
    addAction({
      kind: "remove_duplicate_rows",
      column: "Dataset",
      reason: document.querySelector("#dedupeReason")?.value || "Duplicados completos eliminados por criterio de unicidad.",
    });
  });

  document.querySelectorAll("[data-impute]").forEach((button) => {
    button.addEventListener("click", () => {
      const column = button.dataset.impute;
      addAction({
        kind: "impute_missing",
        column,
        method: document.querySelector(`[data-impute-method="${cssEscape(column)}"]`)?.value || "mode",
        value: document.querySelector(`[data-custom-value="${cssEscape(column)}"]`)?.value || "",
        reason: document.querySelector(`[data-impute-reason="${cssEscape(column)}"]`)?.value || "Imputación documentada por el analista.",
      });
    });
  });

  document.querySelectorAll("[data-drop-missing]").forEach((button) => {
    button.addEventListener("click", () => {
      const column = button.dataset.dropMissing;
      addAction({
        kind: "drop_missing_rows",
        column,
        reason: document.querySelector(`[data-impute-reason="${cssEscape(column)}"]`)?.value || "Filas eliminadas por faltante crítico.",
      });
    });
  });

  document.querySelectorAll("[data-standardize]").forEach((button) => {
    button.addEventListener("click", () => {
      const column = button.dataset.standardize;
      addAction({
        kind: "standardize_text",
        column,
        method: document.querySelector(`[data-standardize-method="${cssEscape(column)}"]`)?.value || "title",
        reason: document.querySelector(`[data-standardize-reason="${cssEscape(column)}"]`)?.value || "Estandarización para consistencia categórica.",
      });
    });
  });

  document.querySelectorAll("[data-flag-outliers]").forEach((button) => {
    button.addEventListener("click", () => {
      const column = button.dataset.flagOutliers;
      addAction({
        kind: "flag_outliers",
        column,
        reason: document.querySelector(`[data-outlier-reason="${cssEscape(column)}"]`)?.value || "Outlier marcado para validación con negocio.",
      });
    });
  });
}

function addAction(action) {
  store.addAction(action);
  renderLog();
  els.systemStatus.textContent = `${store.state.actions.length} decisión(es) documentada(s)`;
}

function undoLastAction() {
  const undone = store.undoAction();
  if (undone) {
    renderLog();
    renderRules();
    renderCleaningBoard();
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
      (action, index) => `
      <div class="log-item">
        <div class="log-item__row">
          <div class="log-item__text">
            <strong>${index + 1}. ${labelForAction(action.kind)}</strong>
            <span>${escapeHtml(action.column || "Dataset")}</span>
            <p>${escapeHtml(action.reason || "")}</p>
          </div>
          <button class="log-item__undo" data-undo-index="${index}" type="button" title="Deshacer esta acción">✕</button>
        </div>
      </div>`,
    )
    .join("");

  document.querySelectorAll("[data-undo-index]").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.undoIndex);
      store.removeAction(index);
      renderLog();
      renderRules();
      renderCleaningBoard();
      populateAdvancedColumns();
      els.systemStatus.textContent = `${store.state.actions.length} decisión(es) documentada(s)`;
    });
  });
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
    validationRow("Documentacion", cleaning.actions.length > 0, `${cleaning.actions.length} decisiones documentadas en bitacora`),
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
    <p>El informe PDF contiene 10 secciones: Informacion General, Resumen Ejecutivo, Indicadores Clave (antes/despues), Problemas Encontrados (6 dimensiones), Outliers y Fuera de Rango, Plan de Acciones, Evaluacion de Calidad, Checklist de Validacion, Riesgos Identificados, Metodologia y Conclusion.</p>
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
    if (store.state.actions.length === 0) {
      store.setCleaning({
        before: store.state.analysis,
        after: store.state.analysis,
        actions: [],
        clean_csv: "",
      });
      renderValidation();
      renderReportPreview();
      enableStep(4);
      enableStep(5);
      router.navigate(4);
      return;
    }
    runCleaning().then(() => router.navigate(4)).catch((error) => {
      els.systemStatus.textContent = `Error: ${error.message}`;
    });
    return;
  }
  router.navigate(store.state.step + 1);
}

function goToStep(step) {
  if (step < 0 || step > 5) return;
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
  els.nextButton.disabled = !store.state.analysis || step === 5;
  els.nextButton.textContent = step === 3 ? "Aplicar limpieza y validar" : "Siguiente etapa";
}

function enableStep(step) {
  const btn = document.querySelector(`[data-step-button="${step}"]`);
  if (btn) btn.disabled = false;
  if (step <= 3) {
    els.nextButton.disabled = false;
  }
}

async function downloadReport(type) {
  const cleaning = store.state.cleaning;
  if (!cleaning) return;
  showLoading(`Generando informe ${type === "pdf" ? "PDF" : "Markdown"}...`);
  try {
    const route = type === "pdf" ? "/api/report/pdf" : "/api/report/markdown";
    const response = await postJson(route, {
      cleaning: cleaning,
      analyst: els.analystInput.value,
      version: els.versionInput.value || "v1.0",
    });
    if (type === "pdf") {
      downloadBlob(response.filename, base64ToBlob(response.content_base64, "application/pdf"));
    } else {
      downloadBlob(response.filename, new Blob([response.content], { type: "text/markdown;charset=utf-8" }));
    }
  } finally {
    hideLoading();
  }
}

function downloadCleanCsv() {
  const cleaning = store.state.cleaning;
  if (!cleaning) return;
  downloadBlob("dataset_limpio.csv", new Blob([cleaning.clean_csv], { type: "text/csv;charset=utf-8" }));
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
    delete_column: "Eliminar columna",
    drop_missing_rows: "Eliminar filas con faltantes",
    impute_missing: "Imputar faltantes",
    standardize_text: "Estandarizar texto",
    remove_duplicate_rows: "Eliminar duplicados",
    flag_outliers: "Marcar outliers",
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
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
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
  els.advParam2Row.style.display = "none";
  els.advParam1Input.value = "";
  els.advParam2Input.value = "";
  
  if (action === "change_type") {
    els.advParam1Label.firstChild.textContent = "Nuevo tipo de dato";
    els.advParam1Input.placeholder = "number, text, o boolean";
  } else if (action === "replace_value") {
    els.advParam1Label.firstChild.textContent = "Valor original (a buscar)";
    els.advParam1Input.placeholder = "Ej. bogota";
    els.advParam2Label.firstChild.textContent = "Nuevo valor (reemplazo)";
    els.advParam2Input.placeholder = "Ej. Bogotá";
    els.advParam2Row.style.display = "block";
  } else if (action === "rename_column") {
    els.advParam1Label.firstChild.textContent = "Nuevo nombre de columna";
    els.advParam1Input.placeholder = "Ej. edad_años";
  } else {
    els.advParam1Label.firstChild.textContent = "Parámetro 1";
    els.advParam1Input.placeholder = "";
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
  if (kind === "change_type" && !param1) {
    alert("Por favor especifica el nuevo tipo de dato.");
    return;
  }
  if (kind === "change_type" && !["number", "text", "boolean"].includes(param1)) {
    alert("Tipo inválido. Usa: number, text o boolean");
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
  
  const action = {
    kind,
    column,
    reason,
    method: param1,
    value: kind === "replace_value" ? param2 : param1
  };
  
  addAction(action);
  
  els.advActionSelect.value = "";
  els.advParam1Input.value = "";
  els.advParam2Input.value = "";
  els.advReasonInput.value = "";
  els.advParam2Row.style.display = "none";
});

init();
