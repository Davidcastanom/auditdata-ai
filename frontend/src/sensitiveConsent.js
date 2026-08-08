import {
  getSensitiveConsent,
  hasSensitiveConsent,
  acceptSensitiveConsent,
  clearSensitiveConsent,
} from "./auth.js";

// Modal de autorización de datos sensibles. requestSensitiveAuthorization()
// devuelve una Promise<boolean>: true si el usuario autoriza, false si no.
// Lo reutilizan el chat de columna (app.js y nube.js) y el deep-analysis.

let currentResolver = null;
let currentColumns = [];

function openModal(columns) {
  const modal = document.querySelector("#sensitiveConsentModal");
  const backdrop = document.querySelector("#sensitiveBackdrop");
  const label = document.querySelector("#sensitiveColumnsLabel");
  if (!modal || !backdrop) return false;
  currentColumns = columns || [];
  if (label) label.textContent = currentColumns.length ? currentColumns.join(", ") : "Varias columnas";
  modal.classList.add("is-active");
  modal.setAttribute("aria-hidden", "false");
  backdrop.classList.add("is-active");
  return true;
}

function closeModal() {
  const modal = document.querySelector("#sensitiveConsentModal");
  const backdrop = document.querySelector("#sensitiveBackdrop");
  if (modal) {
    modal.classList.remove("is-active");
    modal.setAttribute("aria-hidden", "true");
  }
  if (backdrop) backdrop.classList.remove("is-active");
}

function settle(result) {
  const resolver = currentResolver;
  currentResolver = null;
  closeModal();
  if (resolver) resolver(result);
}

export async function requestSensitiveAuthorization(columns) {
  if (hasSensitiveConsent()) return true;
  if (!openModal(columns || [])) return false;
  return new Promise((resolve) => {
    currentResolver = resolve;
  });
}

export function initSensitiveConsentModal() {
  const acceptButton = document.querySelector("#sensitiveAcceptButton");
  const declineButton = document.querySelector("#sensitiveDeclineButton");
  const backdrop = document.querySelector("#sensitiveBackdrop");
  if (acceptButton) {
    acceptButton.addEventListener("click", () => {
      acceptSensitiveConsent(currentColumns);
      settle(true);
    });
  }
  if (declineButton) declineButton.addEventListener("click", () => settle(false));
  if (backdrop) backdrop.addEventListener("click", () => settle(false));
}

export {
  getSensitiveConsent,
  hasSensitiveConsent,
  acceptSensitiveConsent,
  clearSensitiveConsent,
};
