/**
 * ============================================================================
 * NUBE DE VALIDACION - AuditData AI
 * ============================================================================
 *
 * QUE HACE ESTE ARCHIVO:
 * -----------------------
 * Muestra las recomendaciones de IA en tarjetas interactivas donde el
 * analista puede aceptar, modificar o rechazar cada recomendacion.
 *
 * FLUJO:
 * ------
 * 1. Se ejecuta el diagnostico (28 categorias)
 * 2. Se envian problemas a Groq API
 * 3. Groq responde con recomendaciones
 * 4. Este componente las muestra como tarjetas
 * 5. El analista decide que hacer con cada una
 *
 * DISENO:
 * -------
 * - Tarjetas por columna con problemas
 * - Cada tarjeta tiene: texto de IA + boton de accion
 * - El analista puede: Aceptar (azul), Modificar (amarillo), Rechazar (rojo)
 * - Todo queda registrado en la bitacora
 *
 * AUTOR: AuditData AI
 * VERSION: 1.0
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

    this._init();
  }

  _init() {
    if (!this.container) return;
    this.container.innerHTML = this._renderLoading();
  }

  /**
   * Carga recomendaciones desde el backend
   * @param {string} filename - Nombre del archivo
   * @param {string} contentBase64 - Contenido del archivo en base64
   */
  async loadRecommendations(filename, contentBase64) {
    this.container.innerHTML = this._renderLoading();

    try {
      const response = await fetch("/api/ai/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: filename,
          content_base64: contentBase64,
        }),
      });

      if (!response.ok) {
        throw new Error("Error al obtener recomendaciones de IA");
      }

      const data = await response.json();
      this.recommendations = data.recommendations?.recommendations || [];
      this.reviewedCount = 0;
      this.acceptedActions = [];

      this._render();
      this._updateProgress();
    } catch (error) {
      this.container.innerHTML = this._renderError(error.message);
    }
  }

  /**
   * Renderiza la nube completa
   */
  _render() {
    if (this.recommendations.length === 0) {
      this.container.innerHTML = this._renderNoIssues();
      return;
    }

    const totalRecommendations = this.recommendations.reduce(
      (sum, col) => sum + (col.recommendations?.length || 0), 0
    );

    this.container.innerHTML = `
      <div class="nube-header">
        <div class="nube-header__title">
          <div class="nube-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
            </svg>
          </div>
          <div>
            <h2>Nube de Validacion con IA</h2>
            <p class="nube-subtitle">
              ${totalRecommendations} recomendacion${totalRecommendations !== 1 ? 'es' : ''} de Llama 3.1 
              - Tu decides que hacer con cada una
            </p>
          </div>
        </div>
        <div class="nube-actions-global">
          <button class="nube-btn nube-btn--ghost" id="nubeAcceptAll" type="button">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            Aceptar todas
          </button>
          <button class="nube-btn nube-btn--ghost nube-btn--danger" id="nubeRejectAll" type="button">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            Rechazar todas
          </button>
        </div>
      </div>

      <div class="nube-progress">
        <div class="nube-progress__bar">
          <div class="nube-progress__fill" style="width: 0%"></div>
        </div>
        <span class="nube-progress__text">0 de ${totalRecommendations} revisadas</span>
      </div>

      <div class="nube-columns">
        ${this.recommendations.map(col => this._renderColumnCard(col)).join('')}
      </div>
    `;

    this._bindEvents();
  }

  /**
   * Renderiza una tarjeta de columna
   */
  _renderColumnCard(colData) {
    const recs = colData.recommendations || [];
    const hasIssues = recs.length > 0;
    const domain = colData.inferred_domain || 'desconocido';

    return `
      <div class="nube-column" data-column="${this._escapeHtml(colData.column)}">
        <div class="nube-column__header">
          <div class="nube-column__title">
            <span class="nube-column__name">${this._escapeHtml(colData.column)}</span>
            <span class="nube-column__domain">${this._escapeHtml(domain)}</span>
          </div>
          <span class="nube-column__count">${recs.length} recomendacion${recs.length !== 1 ? 'es' : ''}</span>
        </div>
        
        <div class="nube-column__body">
          ${hasIssues ? recs.map((rec, idx) => this._renderRecommendation(colData.column, rec, idx)).join('') : `
            <div class="nube-empty">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <p>Sin problemas detectados</p>
            </div>
          `}
        </div>
      </div>
    `;
  }

  /**
   * Renderiza una recomendacion individual
   */
  _renderRecommendation(column, rec, index) {
    const id = `rec-${column}-${index}`;
    const confidence = Math.round((rec.confidence || 0.5) * 100);
    const confidenceClass = confidence >= 80 ? 'high' : confidence >= 50 ? 'medium' : 'low';
    const severity = this._getSeverity(rec.category);

    return `
      <div class="nube-rec" data-rec-id="${id}" data-status="pending">
        <div class="nube-rec__header">
          <div class="nube-rec__category">
            <span class="nube-rec__severity nube-rec__severity--${severity}">${severity}</span>
            <span class="nube-rec__cat-name">${this._escapeHtml(rec.category)}</span>
          </div>
          <div class="nube-rec__confidence">
            <div class="nube-confidence-bar">
              <div class="nube-confidence-fill nube-confidence-fill--${confidenceClass}" style="width: ${confidence}%"></div>
            </div>
            <span>${confidence}%</span>
          </div>
        </div>

        <div class="nube-rec__body">
          <div class="nube-rec__text">
            <label class="nube-rec__label">Recomendacion de IA:</label>
            <div class="nube-rec__editable" contenteditable="true" data-field="text">${this._escapeHtml(rec.text || '')}</div>
          </div>

          ${rec.action && Object.keys(rec.action).length > 0 ? `
            <div class="nube-rec__action">
              <label class="nube-rec__label">Accion sugerida:</label>
              <div class="nube-rec__action-preview">
                <span class="nube-rec__action-kind">${this._escapeHtml(rec.action.kind || 'N/A')}</span>
                ${rec.action.method ? `<span class="nube-rec__action-method">${this._escapeHtml(rec.action.method)}</span>` : ''}
              </div>
            </div>
          ` : ''}
        </div>

        <div class="nube-rec__footer">
          <div class="nube-rec__buttons">
            <button class="nube-btn nube-btn--accept" data-action="accept" data-id="${id}" type="button">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 13l4 4L19 7"/>
              </svg>
              Aceptar
            </button>
            <button class="nube-btn nube-btn--modify" data-action="modify" data-id="${id}" type="button">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
              </svg>
              Modificar
            </button>
            <button class="nube-btn nube-btn--reject" data-action="reject" data-id="${id}" type="button">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M6 18L18 6M6 6l12 12"/>
              </svg>
              Rechazar
            </button>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Vincula eventos de la nube
   */
  _bindEvents() {
    // Botones de cada recomendacion
    this.container.querySelectorAll('.nube-btn[data-action]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const action = e.currentTarget.dataset.action;
        const id = e.currentTarget.dataset.id;
        this._handleAction(action, id);
      });
    });

    // Botones globales
    const acceptAllBtn = this.container.querySelector('#nubeAcceptAll');
    const rejectAllBtn = this.container.querySelector('#nubeRejectAll');

    if (acceptAllBtn) {
      acceptAllBtn.addEventListener('click', () => this._handleAcceptAll());
    }
    if (rejectAllBtn) {
      rejectAllBtn.addEventListener('click', () => this._handleRejectAll());
    }
  }

  /**
   * Maneja la accion de una recomendacion
   */
  _handleAction(action, id) {
    const recElement = this.container.querySelector(`[data-rec-id="${id}"]`);
    if (!recElement || recElement.dataset.status !== 'pending') return;

    const textElement = recElement.querySelector('.nube-rec__editable');
    const finalText = textElement ? textElement.textContent.trim() : '';

    // Encontrar la recomendacion original
    const rec = this._findRecommendation(id);
    if (!rec) return;

    // Marcar como revisada
    recElement.dataset.status = action;
    recElement.classList.add(`nube-rec--${action}`);

    // Deshabilitar botones
    recElement.querySelectorAll('.nube-btn').forEach(b => b.disabled = true);

    this.reviewedCount++;
    this._updateProgress();

    // Si fue aceptada o modificada, agregar a acciones
    if (action === 'accept' || action === 'modify') {
      const actionData = {
        kind: rec.action?.kind || 'unknown',
        column: this._getColumnNameFromId(id),
        reason: finalText,
        method: rec.action?.method || '',
        value: rec.action?.value || '',
        original_confidence: rec.confidence || 0.5,
        ai_text: rec.text || '',
      };
      this.acceptedActions.push(actionData);
      this.onActionReady(actionData);
    }

    // Verificar si todas fueron revisadas
    if (this.reviewedCount >= this._getTotalRecommendations()) {
      this.onAllReviewed(this.acceptedActions);
    }
  }

  /**
   * Acepta todas las recomendaciones pendientes
   */
  _handleAcceptAll() {
    this.container.querySelectorAll('.nube-rec[data-status="pending"]').forEach(recEl => {
      const id = recEl.dataset.recId;
      this._handleAction('accept', id);
    });
  }

  /**
   * Rechaza todas las recomendaciones pendientes
   */
  _handleRejectAll() {
    this.container.querySelectorAll('.nube-rec[data-status="pending"]').forEach(recEl => {
      const id = recEl.dataset.recId;
      this._handleAction('reject', id);
    });
  }

  /**
   * Actualiza la barra de progreso
   */
  _updateProgress() {
    const total = this._getTotalRecommendations();
    const percentage = total > 0 ? (this.reviewedCount / total) * 100 : 0;

    const fill = this.container.querySelector('.nube-progress__fill');
    const text = this.container.querySelector('.nube-progress__text');

    if (fill) fill.style.width = `${percentage}%`;
    if (text) text.textContent = `${this.reviewedCount} de ${total} revisadas`;
  }

  /**
   * Encuentra una recomendacion por su ID
   */
  _findRecommendation(id) {
    const parts = id.split('-');
    const column = parts.slice(1, -1).join('-');
    const index = parseInt(parts[parts.length - 1]);

    const colData = this.recommendations.find(c => c.column === column);
    if (colData && colData.recommendations) {
      return colData.recommendations[index];
    }
    return null;
  }

  /**
   * Obtiene el nombre de la columna desde el ID
   */
  _getColumnNameFromId(id) {
    const parts = id.split('-');
    return parts.slice(1, -1).join('-');
  }

  /**
   * Obtiene el total de recomendaciones
   */
  _getTotalRecommendations() {
    return this.recommendations.reduce(
      (sum, col) => sum + (col.recommendations?.length || 0), 0
    );
  }

  /**
   * Determina la severidad basada en la categoria
   */
  _getSeverity(category) {
    const high = ['MISSING', 'DUPLICATE', 'NUMERIC_DOMAIN', 'OUT_OF_RANGE', 'FORMULA_ERROR'];
    const medium = ['DATE_FORMAT', 'CATEGORICAL', 'TYPE_ERROR', 'UNIT_ERROR', 'MULTI_VALUE'];
    
    if (high.includes(category)) return 'alta';
    if (medium.includes(category)) return 'media';
    return 'baja';
  }

  /**
   * Escapa HTML para prevenir XSS
   */
  _escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /**
   * Renderiza estado de carga
   */
  _renderLoading() {
    return `
      <div class="nube-loading">
        <div class="nube-spinner"></div>
        <h3>Conectando con Llama 3.1...</h3>
        <p>Analizando problemas y generando recomendaciones</p>
        <div class="nube-loading__dots">
          <span></span><span></span><span></span>
        </div>
      </div>
    `;
  }

  /**
   * Renderiza error
   */
  _renderError(message) {
    return `
      <div class="nube-error">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
        </svg>
        <h3>Error al conectar con IA</h3>
        <p>${message}</p>
        <p class="nube-error__hint">Verifica que GROQ_API_KEY este configurada</p>
      </div>
    `;
  }

  /**
   * Renderiza cuando no hay problemas
   */
  _renderNoIssues() {
    return `
      <div class="nube-success">
        <div class="nube-success__icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
        <h2>Dataset limpio</h2>
        <p>No se encontraron problemas de calidad de datos.</p>
        <p class="nube-success__hint">Puedes continuar al siguiente paso.</p>
      </div>
    `;
  }

  /**
   * Obtiene las acciones aceptadas
   */
  getAcceptedActions() {
    return this.acceptedActions;
  }

  /**
   * Verifica si todas las recomendaciones fueron revisadas
   */
  isComplete() {
    return this.reviewedCount >= this._getTotalRecommendations();
  }
}
