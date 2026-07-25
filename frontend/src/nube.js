/**
 * ============================================================================
 * NUBE DE VALIDACION - AuditData AI
 * ============================================================================
 *
 * DOS MODOS DE OPERACION:
 * -----------------------
 * 1. CON IA: Groq/Llama analiza y genera recomendaciones automaticas
 * 2. SIN IA: El analista revisa el diagnostico 28 categorias manualmente
 *
 * Ambos modos permiten continuar al paso 4 (Depuracion).
 *
 * AUTOR: AuditData AI
 * VERSION: 2.0
 * ============================================================================
 */

export class NubeValidacion {
  constructor(options = {}) {
    this.container = options.container;
    this.onActionReady = options.onActionReady || (() => {});
    this.onAllReviewed = options.onAllReviewed || (() => {});

    this.recommendations = [];
    this.reviewedCount = 0;
    this.acceptedActions = [];
    this.mode = null;
    this.filename = null;
    this.contentBase64 = null;
    this.diagnosticData = null;

    this._init();
  }

  _init() {
    if (!this.container) return;
    this._renderModeSelector();
  }

  _escHtml(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  /**
   * Paso 1: Mostrar selector de modo
   */
  _renderModeSelector() {
    this.container.innerHTML = `
      <div class="nube-mode-selector">
        <div class="nube-mode-header">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
          </svg>
          <h2>Como quieres validar?</h2>
          <p>Elige un metodo para revisar la calidad de tu dataset.</p>
        </div>
        <div class="nube-mode-cards">
          <button class="nube-mode-card nube-mode-card--ai" id="nubeModeAI" type="button">
            <div class="nube-mode-card__icon">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
              </svg>
            </div>
            <h3>Analisis con IA</h3>
            <p>Llama 3.1 analiza tu dataset y genera recomendaciones automaticas para cada problema detectado.</p>
            <span class="nube-mode-card__tag">Recomendado</span>
          </button>
          <button class="nube-mode-card nube-mode-card--manual" id="nubeModeManual" type="button">
            <div class="nube-mode-card__icon">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
              </svg>
            </div>
            <h3>Validacion manual</h3>
            <p>Revisa el diagnostico de 28 categorias y selecciona que problemas quieres abordar.</p>
          </button>
        </div>
      </div>
    `;

    this.container.querySelector('#nubeModeAI').addEventListener('click', () => this._startAIMode());
    this.container.querySelector('#nubeModeManual').addEventListener('click', () => this._startManualMode());
  }

  /**
   * Carga datos del dataset y muestra selector
   */
  loadRecommendations(filename, contentBase64) {
    this.filename = filename;
    this.contentBase64 = contentBase64;
    this.recommendations = [];
    this.reviewedCount = 0;
    this.acceptedActions = [];
    this.mode = null;
    this.diagnosticData = null;
    this._renderModeSelector();
  }

  /**
   * Paso 2a: Modo IA - llamar a Groq
   */
  async _startAIMode() {
    this.mode = 'ai';
    this.container.innerHTML = this._renderLoading();

    try {
      const response = await fetch("/api/ai/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: this.filename, content_base64: this.contentBase64 }),
      });

      if (!response.ok) throw new Error("Error al obtener recomendaciones de IA");

      const data = await response.json();
      this.recommendations = data.recommendations?.recommendations || [];
      this.reviewedCount = 0;
      this.acceptedActions = [];

      if (this.recommendations.length === 0) {
        this.container.innerHTML = this._renderSuccess(data.recommendations?.message || "Sin problemas detectados");
        this.onAllReviewed([]);
        return;
      }

      this._renderAICloud();
      this._updateProgress();
    } catch (error) {
      this.container.innerHTML = this._renderErrorWithFallback(error.message);
    }
  }

  /**
   * Paso 2b: Modo Manual - cargar diagnostico y mostrar checkboxes
   */
  async _startManualMode() {
    this.mode = 'manual';
    this.container.innerHTML = this._renderLoading();

    try {
      const response = await fetch("/api/diagnose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: this.filename, content_base64: this.contentBase64 }),
      });

      if (!response.ok) throw new Error("Error al ejecutar diagnostico");

      const data = await response.json();
      this.diagnosticData = data.diagnostic;
      this.reviewedCount = 0;
      this.acceptedActions = [];

      this._renderManualView();
    } catch (error) {
      this.container.innerHTML = this._renderErrorWithFallback(error.message);
    }
  }

  /**
   * Renderiza la nube IA completa
   */
  _renderAICloud() {
    const total = this.recommendations.reduce((s, c) => s + (c.recommendations?.length || 0), 0);

    this.container.innerHTML = `
      <div class="nube-header">
        <div class="nube-header__title">
          <div class="nube-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
            </svg>
          </div>
          <div>
            <h2>Recomendaciones de IA</h2>
            <p class="nube-subtitle">${total} recomendacion${total !== 1 ? 'es' : ''} de Llama 3.1 - Tu decides que hacer</p>
          </div>
        </div>
        <div class="nube-actions-global">
          <button class="nube-btn nube-btn--ghost" id="nubeAcceptAll" type="button">Aceptar todas</button>
          <button class="nube-btn nube-btn--ghost nube-btn--danger" id="nubeRejectAll" type="button">Rechazar todas</button>
        </div>
      </div>
      <div class="nube-progress">
        <div class="nube-progress__bar"><div class="nube-progress__fill" style="width: 0%"></div></div>
        <span class="nube-progress__text">0 de ${total} revisadas</span>
      </div>
      <div class="nube-columns">
        ${this.recommendations.map(col => this._renderColumnCard(col)).join('')}
      </div>
    `;

    this._bindAIEvents();
  }

  /**
   * Renderiza vista manual con diagnostico 28 categorias
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
            <h2>Validacion manual</h2>
            <p class="nube-subtitle">${cols.length} columnas, ${totalIssues} problema${totalIssues !== 1 ? 's' : ''} detectado${totalIssues !== 1 ? 's' : ''}</p>
          </div>
        </div>
        <div class="nube-actions-global">
          <button class="nube-btn nube-btn--ghost" id="nubeSelectAllManual" type="button">Seleccionar todo</button>
          <button class="nube-btn nube-btn--ghost nube-btn--danger" id="nubeDeselectAll" type="button">Limpiar seleccion</button>
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
          Confirmar seleccion y continuar
        </button>
      </div>
    `;

    this._bindManualEvents();
    this._updateManualProgress();
  }

  _renderManualColumnCard(colData) {
    const issues = colData.issues || [];
    if (issues.length === 0) return '';

    return `
      <div class="nube-column nube-column--manual" data-column="${this._escHtml(colData.column_name)}">
        <div class="nube-column__header">
          <div class="nube-column__title">
            <span class="nube-column__name">${this._escHtml(colData.column_name)}</span>
            <span class="nube-column__domain">${this._escHtml(colData.column_type || 'texto')}</span>
          </div>
          <span class="nube-column__count">${issues.length} problema${issues.length !== 1 ? 's' : ''}</span>
        </div>
        <div class="nube-column__body">
          ${issues.map(issue => `
            <div class="nube-manual-issue" data-category="${this._escHtml(issue.category_code)}">
              <label class="nube-manual-issue__label">
                <input type="checkbox" class="nube-manual-check" data-column="${this._escHtml(colData.column_name)}" data-category="${this._escHtml(issue.category_code)}" data-count="${issue.count || 0}" />
                <div class="nube-manual-issue__info">
                  <div class="nube-manual-issue__header">
                    <span class="nube-rec__severity nube-rec__severity--${this._getSeverity(issue.category_code)}">${this._getSeverity(issue.category_code)}</span>
                    <strong>${this._escHtml(issue.category_code)}</strong>
                    <span class="nube-manual-issue__count">${issue.count || 0} filas afectadas (${issue.percentage || 0}%)</span>
                  </div>
                  <p class="nube-manual-issue__desc">${this._escHtml(issue.description || '')}</p>
                  ${issue.examples && issue.examples.length > 0 ? `
                    <div class="nube-manual-issue__examples">
                      Ejemplos: <code>${issue.examples.slice(0, 3).map(e => this._escHtml(String(e))).join('</code>, <code>')}</code>
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

    if (selectAll) selectAll.addEventListener('click', () => {
      checks.forEach(ch => { ch.checked = true; });
      this._updateManualProgress();
    });
    if (deselectAll) deselectAll.addEventListener('click', () => {
      checks.forEach(ch => { ch.checked = false; });
      this._updateManualProgress();
    });
    if (confirmBtn) confirmBtn.addEventListener('click', () => this._confirmManualSelection());
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
        reason: `Problema ${ch.dataset.category} seleccionado en validacion manual`,
      };
      this.acceptedActions.push(actionData);
      this.onActionReady(actionData);
    });

    const total = this.container.querySelectorAll('.nube-manual-check').length;
    this.reviewedCount = total;
    this.onAllReviewed(this.acceptedActions);
  }

  // --- Eventos modo IA ---

  _bindAIEvents() {
    this.container.querySelectorAll('.nube-btn[data-action]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this._handleAIAction(e.currentTarget.dataset.action, e.currentTarget.dataset.id);
      });
    });

    const acceptAll = this.container.querySelector('#nubeAcceptAll');
    const rejectAll = this.container.querySelector('#nubeRejectAll');
    if (acceptAll) acceptAll.addEventListener('click', () => this._handleAcceptAll());
    if (rejectAll) rejectAll.addEventListener('click', () => this._handleRejectAll());
  }

  _handleAIAction(action, id) {
    const el = this.container.querySelector(`[data-rec-id="${id}"]`);
    if (!el || el.dataset.status !== 'pending') return;

    const textEl = el.querySelector('.nube-rec__editable');
    const finalText = textEl ? textEl.textContent.trim() : '';
    const rec = this._findRec(id);
    if (!rec) return;

    el.dataset.status = action;
    el.classList.add(`nube-rec--${action}`);
    el.querySelectorAll('.nube-btn').forEach(b => b.disabled = true);

    this.reviewedCount++;
    this._updateProgress();

    if (action === 'accept' || action === 'modify') {
      const actionData = {
        kind: rec.action?.kind || 'unknown',
        column: this._getColName(id),
        reason: finalText,
        method: rec.action?.method || '',
        value: rec.action?.value || '',
        original_confidence: rec.confidence || 0.5,
        ai_text: rec.text || '',
      };
      this.acceptedActions.push(actionData);
      this.onActionReady(actionData);
    }

    if (this.reviewedCount >= this._getTotalRecs()) {
      this.onAllReviewed(this.acceptedActions);
    }
  }

  _handleAcceptAll() {
    this.container.querySelectorAll('.nube-rec[data-status="pending"]').forEach(el => {
      this._handleAIAction('accept', el.dataset.recId);
    });
  }

  _handleRejectAll() {
    this.container.querySelectorAll('.nube-rec[data-status="pending"]').forEach(el => {
      this._handleAIAction('reject', el.dataset.recId);
    });
  }

  // --- Renderers IA ---

  _renderColumnCard(colData) {
    const recs = colData.recommendations || [];
    const domain = colData.inferred_domain || 'desconocido';
    return `
      <div class="nube-column" data-column="${this._escHtml(colData.column)}">
        <div class="nube-column__header">
          <div class="nube-column__title">
            <span class="nube-column__name">${this._escHtml(colData.column)}</span>
            <span class="nube-column__domain">${this._escHtml(domain)}</span>
          </div>
          <span class="nube-column__count">${recs.length} recomendacion${recs.length !== 1 ? 'es' : ''}</span>
        </div>
        <div class="nube-column__body">
          ${recs.length > 0 ? recs.map((rec, idx) => this._renderRec(colData.column, rec, idx)).join('') : `
            <div class="nube-empty">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
              <p>Sin problemas detectados</p>
            </div>
          `}
        </div>
      </div>
    `;
  }

  _renderRec(column, rec, index) {
    const id = `rec-${column}-${index}`;
    const confidence = Math.round((rec.confidence || 0.5) * 100);
    const cClass = confidence >= 80 ? 'high' : confidence >= 50 ? 'medium' : 'low';
    const sev = this._getSeverity(rec.category);

    return `
      <div class="nube-rec" data-rec-id="${id}" data-status="pending">
        <div class="nube-rec__header">
          <div class="nube-rec__category">
            <span class="nube-rec__severity nube-rec__severity--${sev}">${sev}</span>
            <span class="nube-rec__cat-name">${this._escHtml(rec.category)}</span>
          </div>
          <div class="nube-rec__confidence">
            <div class="nube-confidence-bar"><div class="nube-confidence-fill nube-confidence-fill--${cClass}" style="width:${confidence}%"></div></div>
            <span>${confidence}%</span>
          </div>
        </div>
        <div class="nube-rec__body">
          <div class="nube-rec__text">
            <label class="nube-rec__label">Recomendacion de IA:</label>
            <div class="nube-rec__editable" contenteditable="true" data-field="text">${this._escHtml(rec.text || '')}</div>
          </div>
          ${rec.action && Object.keys(rec.action).length > 0 ? `
            <div class="nube-rec__action">
              <label class="nube-rec__label">Accion sugerida:</label>
              <div class="nube-rec__action-preview">
                <span class="nube-rec__action-kind">${this._escHtml(rec.action.kind || 'N/A')}</span>
                ${rec.action.method ? `<span class="nube-rec__action-method">${this._escHtml(rec.action.method)}</span>` : ''}
              </div>
            </div>
          ` : ''}
        </div>
        <div class="nube-rec__footer">
          <div class="nube-rec__buttons">
            <button class="nube-btn nube-btn--accept" data-action="accept" data-id="${id}" type="button">Aceptar</button>
            <button class="nube-btn nube-btn--modify" data-action="modify" data-id="${id}" type="button">Modificar</button>
            <button class="nube-btn nube-btn--reject" data-action="reject" data-id="${id}" type="button">Rechazar</button>
          </div>
        </div>
      </div>
    `;
  }

  // --- Helpers ---

  _updateProgress() {
    const total = this._getTotalRecs();
    const pct = total > 0 ? (this.reviewedCount / total) * 100 : 0;
    const fill = this.container.querySelector('.nube-progress__fill');
    const text = this.container.querySelector('.nube-progress__text');
    if (fill) fill.style.width = `${pct}%`;
    if (text) text.textContent = `${this.reviewedCount} de ${total} revisadas`;
  }

  _findRec(id) {
    const parts = id.split('-');
    const column = parts.slice(1, -1).join('-');
    const index = parseInt(parts[parts.length - 1]);
    const col = this.recommendations.find(c => c.column === column);
    return col?.recommendations?.[index] || null;
  }

  _getColName(id) {
    const parts = id.split('-');
    return parts.slice(1, -1).join('-');
  }

  _getTotalRecs() {
    return this.recommendations.reduce((s, c) => s + (c.recommendations?.length || 0), 0);
  }

  _getSeverity(category) {
    const high = ['MISSING', 'DUPLICATE', 'NUMERIC_DOMAIN', 'OUT_OF_RANGE', 'FORMULA_ERROR', 'TYPE_PER_CELL'];
    const medium = ['DATE_FORMAT', 'CATEGORICAL', 'TYPE_ERROR', 'UNIT_ERROR', 'MULTI_VALUE', 'TEXT_ERROR', 'ENCODING', 'SCIENTIFIC'];
    if (high.includes(category)) return 'alta';
    if (medium.includes(category)) return 'media';
    return 'baja';
  }

  // --- Shared renderers ---

  _renderLoading() {
    return `
      <div class="nube-loading">
        <div class="nube-spinner"></div>
        <h3>Analizando dataset...</h3>
        <p>Ejecutando diagnostico de 28 categorias de calidad</p>
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
          <p>Puedes intentar con <strong>Validacion manual</strong> en su lugar.</p>
          <button class="button button--primary" id="nubeFallbackManual" type="button">Usar validacion manual</button>
          <button class="button button--ghost" id="nubeFallbackRetry" type="button">Reintentar</button>
        </div>
      </div>
    `;

    setTimeout(() => {
      const fb = this.container.querySelector('#nubeFallbackManual');
      const retry = this.container.querySelector('#nubeFallbackRetry');
      if (fb) fb.addEventListener('click', () => this._startManualMode());
      if (retry) retry.addEventListener('click', () => {
        if (this.mode === 'ai') this._startAIMode();
        else this._renderModeSelector();
      });
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
  isComplete() { return this.mode === 'manual' || this.reviewedCount >= this._getTotalRecs(); }
}
