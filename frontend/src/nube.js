/**
 * ============================================================================
 * NUBE DE VALIDACION - AuditData AI
 * ============================================================================
 *
 * MODO DE OPERACION:
 * ------------------
 * Validación manual: El analista revisa el diagnóstico 28 categorías
 * y selecciona que problemas quiere abordar en la depuración.
 *
 * La IA se utiliza exclusivamente en el Step 4 (Depuración) como
 * Copiloto Conversacional en el Side Drawer.
 *
 * AUTOR: AuditData AI
 * VERSION: 3.0
 * ============================================================================
 */

export class NubeValidación {
  constructor(options = {}) {
    this.container = options.container;
    this.onActionReady = options.onActionReady || (() => {});
    this.onAllReviewed = options.onAllReviewed || (() => {});
    this.onDiagnosticReady = options.onDiagnosticReady || (() => {});

    this.reviewedCount = 0;
    this.acceptedActions = [];
    this.filename = null;
    this.contentBase64 = null;
    this.diagnosticData = null;
    this.currentDrawerColumn = null;
    this.drawerChatHistory = {};
    this.columnAnalysisCache = {};
  }

  _escHtml(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  _escapeAttr(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  _renderExample(e) {
    if (typeof e === 'string') return this._escHtml(e);
    if (!e || typeof e !== 'object') return String(e);
    if (e.row !== undefined && e.value !== undefined) {
      return `Fila ${e.row}: ${this._escHtml(String(e.value))}`;
    }
    if (e.row !== undefined && e.detail !== undefined) {
      return `Fila ${e.row}: ${this._escHtml(e.detail)}`;
    }
    if (e.row !== undefined && e.format !== undefined) {
      return `Fila ${e.row}: ${this._escHtml(e.format)} (${e.count || 0})`;
    }
    if (e.row !== undefined && e.original !== undefined && e.standard !== undefined) {
      return `Fila ${e.row}: "${this._escHtml(e.original)}" → "${this._escHtml(e.standard)}"`;
    }
    if (e.row !== undefined && e.meaning !== undefined) {
      return `Fila ${e.row}: ${this._escHtml(e.value)} = ${this._escHtml(e.meaning)}`;
    }
    if (e.row !== undefined && e.error !== undefined) {
      return `Fila ${e.row}: ${this._escHtml(e.error)} (${e.count || 0})`;
    }
    if (e.rows !== undefined && e.match !== undefined) {
      return `Filas [${e.rows.join(", ")}] (${e.match})`;
    }
    if (e.value !== undefined) return this._escHtml(String(e.value));
    if (e.format !== undefined) return `${this._escHtml(e.format)} (${e.count || 0})`;
    if (e.error !== undefined) return `${this._escHtml(e.error)} (${e.count || 0})`;
    return this._escHtml(JSON.stringify(e));
  }

  /**
   * Carga datos del dataset y muestra diagnóstico directamente
   */
  loadRecommendations(filename, contentBase64) {
    this.filename = filename;
    this.contentBase64 = contentBase64;
    this.reviewedCount = 0;
    this.acceptedActions = [];
    this.diagnosticData = null;
    this._startManualMode();
  }

  /**
   * Cargar diagnóstico y mostrar checkboxes
   */
  async _startManualMode() {
    this.container.innerHTML = this._renderLoading();

    try {
      const response = await fetch("/api/diagnose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: this.filename, content_base64: this.contentBase64 }),
      });

      if (!response.ok) throw new Error("Error al ejecutar diagnóstico");

      const data = await response.json();
      this.diagnosticData = data.diagnostic;
      this.reviewedCount = 0;
      this.acceptedActions = [];
      this.onDiagnosticReady(this.diagnosticData);

      this._renderManualView();
    } catch (error) {
      this.container.innerHTML = this._renderErrorWithFallback(error.message);
    }
  }

  /**
   * Renderiza vista manual con diagnóstico 28 categorías
   */
  _renderManualView() {
    const cols = this.diagnosticData?.columns || [];
    const totalIssues = cols.reduce((s, c) => s + (c.issues?.length || 0), 0);

    if (totalIssues === 0) {
      this.container.innerHTML = this._renderSuccess("No se encontraron problemas de calidad.");
      this.onAllReviewed([]);
      return;
    }

    this.container.innerHTML = `
      <div class="nube-header">
        <div class="nube-header__title">
          <div class="nube-icon nube-icon--manual">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
            </svg>
          </div>
          <div>
            <h2>Validación de Calidad</h2>
            <p class="nube-subtitle">${cols.length} columnas, ${totalIssues} problema${totalIssues !== 1 ? 's' : ''} detectado${totalIssues !== 1 ? 's' : ''}</p>
          </div>
        </div>
        <div class="nube-actions-global">
          <button class="nube-btn nube-btn--ghost nube-btn--skip" id="nubeSkipManual" type="button">Omitir validación</button>
          <button class="nube-btn nube-btn--ghost" id="nubeSelectAllManual" type="button">Seleccionar todo</button>
          <button class="nube-btn nube-btn--ghost nube-btn--danger" id="nubeDeselectAll" type="button">Limpiar selección</button>
        </div>
      </div>
      <div class="nube-progress">
        <div class="nube-progress__bar"><div class="nube-progress__fill nube-progress__fill--manual" style="width: 0%"></div></div>
        <span class="nube-progress__text">0 de ${totalIssues} problemas seleccionados</span>
      </div>
      <div class="nube-columns">
        ${cols.map(col => this._renderManualColumnCard(col)).join('')}
      </div>
      <div class="nube-manual-actions">
        <button class="button button--primary" id="nubeManualConfirm" type="button">
          Confirmar selección y continuar
        </button>
      </div>
    `;

    this._bindManualEvents();
    this._updateManualProgress();
  }

  _renderManualColumnCard(colData) {
    const issues = colData.issues || [];
    if (issues.length === 0) return '';

    const rawCol = colData.column || colData.column_name || 'Dataset';
    const isDataset = rawCol === '__dataset__';
    const displayName = isDataset ? 'Dataset Global (Filas Duplicadas)' : rawCol;
    const displayDomain = isDataset ? 'Multicolumna' : (colData.inferred_domain || 'general');

    const hasAnalysis = !isDataset;
    const analysisId = `colAnalysis_${rawCol}`;

    return `
      <div class="nube-column nube-column--manual" data-column="${this._escapeAttr(rawCol)}">
        <div class="nube-column__header">
          <div class="nube-column__title">
            <span class="nube-column__name" style="font-weight: 700; font-size: 1.05rem; color: var(--color-primary);">${this._escHtml(displayName)}</span>
            <span class="nube-column__domain">${this._escHtml(displayDomain)}</span>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <span class="nube-column__count">${issues.length} problema${issues.length !== 1 ? 's' : ''}</span>
            <button class="button button--ghost button--sm" data-inspect-col="${this._escapeAttr(rawCol)}" type="button">Inspeccionar</button>
          </div>
        </div>
        ${hasAnalysis ? `
        <div class="nube-column-ia drawer-section--collapsible" data-col-analysis="${this._escapeAttr(rawCol)}">
          <button class="drawer-section__toggle nube-ia-toggle" type="button" onclick="this.parentElement.classList.toggle('is-open')">
            Recomendaci\u00f3n de Copiloto <span class="toggle-arrow">\u25be</span>
          </button>
          <div class="drawer-section__body nube-ia-body">
            <button class="button button--primary button--sm btn-analyze-col" data-analyze-col="${this._escapeAttr(rawCol)}" type="button">Ejecutar an\u00e1lisis</button>
            <div id="${analysisId}" class="nube-ia-output"></div>
          </div>
        </div>
        ` : ''}
        <div class="nube-column__body">
          ${issues.map(issue => `
            <div class="nube-manual-issue" data-category="${this._escapeAttr(issue.category_code)}">
              <label class="nube-manual-issue__label">
                <input type="checkbox" class="nube-manual-check" data-column="${this._escapeAttr(rawCol)}" data-category="${this._escapeAttr(issue.category_code)}" data-count="${issue.count || 0}" checked />
                <div class="nube-manual-issue__info">
                  <div class="nube-manual-issue__header">
                    <span class="nube-rec__severity nube-rec__severity--${this._getSeverityClass(issue.severity)}">${this._escHtml(issue.severity || '')}</span>
                    ${issue.signal ? `<span class="nube-rec__signal nube-rec__signal--${issue.signal === 'CONFIRMADO' ? 'confirmado' : 'a_revisar'}">${this._escHtml(issue.signal)}</span>` : ''}
                    <strong>${this._escHtml(issue.category_code)}</strong>
                    <span class="nube-manual-issue__count">${issue.count || 0} filas afectadas (${(issue.percentage || 0).toFixed(1)}%)</span>
                  </div>
                  <p class="nube-manual-issue__desc">${this._escHtml(issue.description || '')}</p>
                  ${issue.examples && issue.examples.length > 0 ? `
                    <div class="nube-manual-issue__examples">
                      Ejemplos: <code>${issue.examples.slice(0, 3).map(e => this._renderExample(e)).join('</code>, <code>')}</code>
                    </div>
                  ` : ''}
                  ${issue.affected_rows && issue.affected_rows.length > 0 ? `
                    <div class="nube-manual-issue__affected">
                      Filas afectadas: <code>${issue.affected_rows.slice(0, 10).join(', ')}</code>${issue.affected_rows.length > 10 ? ` (+${issue.affected_rows.length - 10} mas)` : ''}
                    </div>
                  ` : ''}
                </div>
              </label>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  _bindManualEvents() {
    const checks = this.container.querySelectorAll('.nube-manual-check');
    checks.forEach(ch => ch.addEventListener('change', () => this._updateManualProgress()));

    const selectAll = this.container.querySelector('#nubeSelectAllManual');
    const deselectAll = this.container.querySelector('#nubeDeselectAll');
    const confirmBtn = this.container.querySelector('#nubeManualConfirm');
    const skipManual = this.container.querySelector('#nubeSkipManual');

    this.container.querySelectorAll('[data-inspect-col]').forEach(btn => {
      btn.onclick = () => {
        const col = btn.getAttribute('data-inspect-col');
        this.openDrawerForColumn(col);
      };
    });

    this._bindColumnAnalysisButtons();

    if (selectAll) selectAll.addEventListener('click', () => {
      checks.forEach(ch => { ch.checked = true; });
      this._updateManualProgress();
    });
    if (deselectAll) deselectAll.addEventListener('click', () => {
      checks.forEach(ch => { ch.checked = false; });
      this._updateManualProgress();
    });
    if (confirmBtn) confirmBtn.addEventListener('click', () => this._confirmManualSelection());
    if (skipManual) skipManual.addEventListener('click', () => this._handleSkipValidation());
  }

  _bindColumnAnalysisButtons() {
    this.container.querySelectorAll('.btn-analyze-col').forEach(btn => {
      btn.onclick = async () => {
        const col = btn.getAttribute('data-analyze-col');
        if (!col) return;

        if (this.columnAnalysisCache[col]) {
          document.getElementById(`colAnalysis_${col}`).innerHTML = this.columnAnalysisCache[col];
          return;
        }

        const outputEl = document.getElementById(`colAnalysis_${col}`);
        if (!outputEl) return;

        btn.disabled = true;
        btn.textContent = 'Analizando...';
        outputEl.innerHTML = '<div class="nube-loading" style="padding:var(--space-2);"><div class="nube-spinner"></div></div>';

        // Look up column data for type and domain
        const colData = this.diagnostic?.columns?.find(c => c.column === col);
        const detectedType = colData?.profiler?.type || 'unknown';
        const inferredDomain = colData?.inferred_domain || '';

        try {
          const response = await fetch('/api/ai/column-deep-analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              filename: this.filename,
              content_base64: this.contentBase64,
              column: col,
              detected_type: detectedType,
              inferred_domain: inferredDomain,
            }),
          });

          if (!response.ok) throw new Error('Error en el an\u00e1lisis');

          const data = await response.json();
          const analysis = data.analysis || 'Sin resultados';
          const html = `<div class="nube-ia-result">${this._renderMarkdown(analysis)}</div>`;
          this.columnAnalysisCache[col] = html;
          outputEl.innerHTML = html;
        } catch (e) {
          outputEl.innerHTML = `<p class="empty-state" style="font-size:0.8rem;">Error: ${this._escHtml(e.message)}</p>`;
        } finally {
          btn.disabled = false;
          btn.textContent = 'Ejecutar an\u00e1lisis';
        }
      };
    });
  }

  _updateManualProgress() {
    const checks = this.container.querySelectorAll('.nube-manual-check');
    const total = checks.length;
    const selected = this.container.querySelectorAll('.nube-manual-check:checked').length;
    const pct = total > 0 ? (selected / total) * 100 : 0;

    const fill = this.container.querySelector('.nube-progress__fill');
    const text = this.container.querySelector('.nube-progress__text');
    if (fill) fill.style.width = `${pct}%`;
    if (text) text.textContent = `${selected} de ${total} problemas seleccionados`;
  }

  _confirmManualSelection() {
    const checks = this.container.querySelectorAll('.nube-manual-check:checked');
    this.acceptedActions = [];

    checks.forEach(ch => {
      const actionData = {
        kind: 'review_issue',
        column: ch.dataset.column,
        category: ch.dataset.category,
        count: parseInt(ch.dataset.count) || 0,
        reason: `Problema ${ch.dataset.category} seleccionado en validación manual`,
      };
      this.acceptedActions.push(actionData);
      this.onActionReady(actionData);
    });

    const total = this.container.querySelectorAll('.nube-manual-check').length;
    this.reviewedCount = total;
    this.onAllReviewed(this.acceptedActions);
  }

  _handleSkipValidation() {
    this.acceptedActions = [];
    this.reviewedCount = 1;
    this.onAllReviewed([]);
  }

  // DG-09 (C2): la severidad es única y viene del backend (CRITICA/ALTA/MEDIA/BAJA).
  // Solo se mapea el valor a la clase CSS: CRITICA y ALTA comparten semaforo rojo.
  _getSeverityClass(severity) {
    const map = { CRITICA: 'alta', ALTA: 'alta', MEDIA: 'media', BAJA: 'baja' };
    return map[severity] || 'baja';
  }

  // --- Shared renderers ---

  _renderLoading() {
    return `
      <div class="nube-loading">
        <div class="nube-spinner"></div>
        <h3>Analizando dataset...</h3>
        <p>Ejecutando diagnóstico de 28 categorías de calidad</p>
        <div class="nube-loading__dots"><span></span><span></span><span></span></div>
      </div>
    `;
  }

  _renderErrorWithFallback(message) {
    return `
      <div class="nube-error">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
        </svg>
        <h3>Error</h3>
        <p>${this._escHtml(message)}</p>
        <div class="nube-error__fallback">
          <button class="button button--primary" id="nubeFallbackRetry" type="button">Reintentar</button>
        </div>
      </div>
    `;

    setTimeout(() => {
      const retry = this.container.querySelector('#nubeFallbackRetry');
      if (retry) retry.addEventListener('click', () => this._startManualMode());
    }, 0);
  }

  _renderSuccess(message) {
    return `
      <div class="nube-success">
        <div class="nube-success__icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
        <h2>Sin problemas detectados</h2>
        <p>${this._escHtml(message)}</p>
        <p class="nube-success__hint">Puedes continuar al siguiente paso.</p>
      </div>
    `;
  }

  getAcceptedActions() { return this.acceptedActions; }
  isComplete() { return this.reviewedCount > 0; }

  // --- Side Drawer (used in Step 3 for inspection) ---

  _renderMarkdown(text) {
    const esc = text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    const bold = esc.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    const code = bold.replace(/`(.+?)`/g, '<code>$1</code>');
    const lines = code.split('\n');
    const out = [];
    let inList = false, listType = null;
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      const t = line.trim();
      const bm = t.match(/^[-*]\s+(.+)/);
      const nm = t.match(/^\d+[.)]\s+(.+)/);
      if (bm || nm) {
        const isOl = !!nm;
        const prefix = isOl ? 'ol' : 'ul';
        const content = (isOl ? nm[1] : bm[1]);
        if (!inList || listType !== prefix) {
          if (inList) out.push(`</${listType}>`);
          out.push(`<${prefix}>`);
          inList = true;
          listType = prefix;
        }
        let itemHtml = content;
        i++;
        while (i < lines.length) {
          const next = lines[i];
          const nextTrim = next.trim();
          if (nextTrim === '') { i++; break; }
          const nextBm = nextTrim.match(/^[-*]\s+(.+)/);
          const nextNm = nextTrim.match(/^\d+[.)]\s+(.+)/);
          if (nextBm || nextNm) break;
          if (next.startsWith('   ') || next.startsWith('\t')) {
            itemHtml += '<br>' + nextTrim;
            i++;
          } else {
            break;
          }
        }
        out.push(`<li>${itemHtml}</li>`);
      } else {
        if (inList) { out.push(`</${listType}>`); inList = false; listType = null; }
        out.push(t === '' ? '<br>' : line);
        i++;
      }
    }
    if (inList) out.push(`</${listType}>`);
    return out.join('\n');
  }

  initDrawerEvents() {
    const drawer = document.querySelector('#aiColumnDrawer');
    const backdrop = document.querySelector('#aiColumnDrawerBackdrop');
    const closeBtn = document.querySelector('#drawerCloseButton');
    const sendBtn = document.querySelector('#drawerChatSendButton');
    const input = document.querySelector('#drawerChatInput');

    if (closeBtn) closeBtn.onclick = () => this.closeDrawer();
    if (backdrop) backdrop.onclick = () => this.closeDrawer();

    if (sendBtn && input) {
      const handleSend = () => {
        const query = input.value.trim();
        if (!query || !this.currentDrawerColumn) return;
        input.value = '';
        this.sendDrawerChatMessage(this.currentDrawerColumn, query);
      };
      sendBtn.onclick = handleSend;
      input.onkeydown = (e) => {
        if (e.key === 'Enter') handleSend();
      };
    }
  }

  openDrawerForColumn(columnName) {
    this.currentDrawerColumn = columnName;
    const drawer = document.querySelector('#aiColumnDrawer');
    const backdrop = document.querySelector('#aiColumnDrawerBackdrop');
    const badge = document.querySelector('#drawerColBadge');
    const title = document.querySelector('#drawerColTitle');
    const meta = document.querySelector('#drawerColMeta');
    const diagBox = document.querySelector('#drawerDiagnostics');
    const chatFeed = document.querySelector('#drawerChatFeed');

    if (!drawer || !backdrop) return;

    this.initDrawerEvents();

    this.drawerColumnType = 'unknown';
    this.drawerColumnDomain = '';

    if (columnName === '__dataset__') {
      badge.textContent = 'Dataset Global';
      title.textContent = 'Filas Duplicadas en Dataset';
      meta.textContent = 'Anomalia de Unicidad de Registro Completo';
    } else {
      badge.textContent = 'Columna';
      title.textContent = columnName;
      meta.textContent = 'Inspector de Celdas y Calidad';
    }

    let colDiag = null;
    if (this.diagnosticData?.columns) {
      colDiag = this.diagnosticData.columns.find(c => c.column === columnName);
    }
    const issues = colDiag?.issues || [];
    const profiler = colDiag?.profiler || {};
    this.drawerColumnType = profiler.type || 'unknown';
    this.drawerColumnDomain = colDiag?.inferred_domain || '';

    let extraSections = '';
    if (['CATEGORICA', 'BOOLEANA', 'CONSTANTE', 'TEXTO_LIBRE'].includes(profiler.type)) {
      const allVals = [
        ...(profiler.dominant_values || []),
        ...(profiler.suspicious_values || []),
      ].sort((a, b) => b.pct - a.pct);
      if (allVals.length > 0) {
        const maxPct = Math.max(...allVals.map(v => v.pct), 1);
        const rows = allVals.map(v => {
          const barW = Math.max((v.pct / maxPct) * 100, 2);
          const isSusp = (profiler.suspicious_values || []).some(s => s.value === v.value);
          return `<div class="freq-row${isSusp ? ' freq-row--suspicious' : ''}">
            <span class="freq-val">${this._escHtml(v.value)}</span>
            <span class="freq-bar-wrap"><span class="freq-bar" style="width:${barW}%"></span></span>
            <span class="freq-pct">${v.pct}%</span>
            <span class="freq-count">${v.freq}</span>
          </div>`;
        }).join('');
        extraSections = `
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

    if (issues.length === 0 && !extraSections) {
      diagBox.innerHTML = `<p class="empty-state">No se registraron problemas técnicos en esta columna.</p>`;
    } else {
      const issuesHtml = issues.map(iss => `
        <div class="drawer-issue-item">
          <span class="nube-rec__severity nube-rec__severity--${this._getSeverityClass(iss.severity)}">${this._escapeAttr(iss.severity || '')}</span>
          ${iss.signal ? `<span class="nube-rec__signal nube-rec__signal--${iss.signal === 'CONFIRMADO' ? 'confirmado' : 'a_revisar'}">${this._escapeAttr(iss.signal)}</span>` : ''}
          <strong>${this._escHtml(iss.category || iss.category_code)}</strong>: ${iss.count || 0} ocurrencias (${(iss.percentage || 0).toFixed(1)}%).
          <div class="depur-examples" style="margin-top: 4px;">
            ${(iss.examples || []).slice(0, 3).map(e => `<div>${this._renderExample(e)}</div>`).join('')}
          </div>
        </div>
      `).join('');
      diagBox.innerHTML = extraSections + issuesHtml;
    }

    const history = this.drawerChatHistory[columnName] || [];
    chatFeed.innerHTML = '';
    history.forEach(msg => {
      const div = document.createElement('div');
      div.className = `chat-bubble chat-bubble--${msg.role === 'assistant' ? 'ai' : 'user'}`;
      div.innerHTML = `<strong>${msg.role === 'assistant' ? 'Copiloto IA' : 'Tu'}:</strong> ${this._escHtml(msg.content)}`;
      chatFeed.appendChild(div);
    });
    if (history.length === 0) {
      const issueList = issues.length > 0
        ? `<ul>${issues.map(i => `<li><strong>${this._escHtml(i.category_code)}</strong> (${i.count} filas, ${(i.percentage || 0).toFixed(1)}%)</li>`).join('')}</ul>`
        : '';
      chatFeed.innerHTML = `
        <div class="chat-bubble chat-bubble--ai">
          <strong>Copiloto IA:</strong> Analicé <code>${this._escHtml(columnName)}</code>.
          ${issues.length > 0
            ? `Encontré <strong>${issues.length}</strong> problema(s):${issueList}Pregúntame cómo corregirlos. Tú tienes el control final.`
            : 'No encontré problemas de calidad. ¿Quieres que revise alguna condición específica?'}
        </div>
      `;
    }

    drawer.classList.add('is-active');
    backdrop.classList.add('is-active');
  }

  closeDrawer() {
    const drawer = document.querySelector('#aiColumnDrawer');
    const backdrop = document.querySelector('#aiColumnDrawerBackdrop');
    if (drawer) drawer.classList.remove('is-active');
    if (backdrop) backdrop.classList.remove('is-active');
  }

  async sendDrawerChatMessage(columnName, query) {
    const chatFeed = document.querySelector('#drawerChatFeed');
    if (!chatFeed) return;

    const userMsgDiv = document.createElement('div');
    userMsgDiv.className = 'chat-bubble chat-bubble--user';
    userMsgDiv.innerHTML = `<strong>Tu:</strong> ${this._escHtml(query)}`;
    chatFeed.appendChild(userMsgDiv);

    if (!this.drawerChatHistory[columnName]) this.drawerChatHistory[columnName] = [];
    this.drawerChatHistory[columnName].push({ role: 'user', content: query });

    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'chat-bubble chat-bubble--ai';
    thinkingDiv.innerHTML = `<strong>Copiloto IA:</strong> <em>Analizando...</em>`;
    chatFeed.appendChild(thinkingDiv);
    chatFeed.scrollTop = chatFeed.scrollHeight;

    try {
      const response = await fetch('/api/ai/chat-column', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: this.filename,
          content_base64: this.contentBase64,
          column: columnName,
          user_query: query,
          detected_type: this.drawerColumnType || 'unknown',
          inferred_domain: this.drawerColumnDomain || '',
          chat_history: this.drawerChatHistory[columnName].slice(-10)
        })
      });

      if (!response.ok) throw new Error('Error de conexión con la IA');

      const data = await response.json();
      const answer = data.response || 'Sin respuesta';
      thinkingDiv.innerHTML = `<strong>Copiloto IA:</strong> ${this._renderMarkdown(answer)}`;
      this.drawerChatHistory[columnName].push({ role: 'assistant', content: answer });
    } catch (e) {
      thinkingDiv.innerHTML = `<strong>Copiloto IA:</strong> Error al consultar: ${this._escHtml(e.message)}`;
    }
    chatFeed.scrollTop = chatFeed.scrollHeight;
  }
}
