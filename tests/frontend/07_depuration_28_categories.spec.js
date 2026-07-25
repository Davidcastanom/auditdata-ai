const { test, expect } = require("@playwright/test");

const URL = "/?test";

async function clearLoadAnalyze(page) {
  await page.goto(URL);
  await page.evaluate(() => localStorage.clear());
  await page.goto(URL);
  await page.click("#loadSampleButton");
  await expect(page.locator('[data-step="1"]')).toHaveClass(/is-active/, { timeout: 15000 });
}

async function navigateToStep(page, step) {
  await page.evaluate(() => {
    document.querySelectorAll("[data-step-button]").forEach(b => b.disabled = false);
  });
  const hashes = { 2: "#/reglas", 3: "#/validar-ia", 4: "#/depurar" };
  await page.evaluate((h) => { window.location.hash = h; }, hashes[step]);
  await expect(page.locator(`[data-step="${step}"]`)).toHaveClass(/is-active/, { timeout: 10000 });
}

async function runDiagnosticManual(page) {
  await navigateToStep(page, 3);
  await page.locator("#nubeModeManual").click();
  await expect(page.locator("#nubeSkipManual")).toBeVisible({ timeout: 30000 });
}

async function skipValidationAndGoToStep4(page) {
  await runDiagnosticManual(page);
  await page.locator("#nubeSkipManual").click();
  await navigateToStep(page, 4);
}

test.describe("AuditData AI - Depuracion 28 Categorias", () => {
  test("step 3 muestra selector de modo IA vs Manual", async ({ page }) => {
    await clearLoadAnalyze(page);
    await navigateToStep(page, 3);
    await expect(page.locator("#nubeModeAI")).toBeVisible();
    await expect(page.locator("#nubeModeManual")).toBeVisible();
  });

  test("modo manual muestra skip manual", async ({ page }) => {
    await clearLoadAnalyze(page);
    await runDiagnosticManual(page);
    await expect(page.locator("#nubeSkipManual")).toBeVisible();
  });

  test("omitir validacion en modo manual habilita avanzar", async ({ page }) => {
    await clearLoadAnalyze(page);
    await runDiagnosticManual(page);
    await page.locator("#nubeSkipManual").click();
    await expect(page.locator("#nextButton")).toBeEnabled({ timeout: 5000 });
  });

  test("step 4 muestra decision-cards con diagnostico", async ({ page }) => {
    await clearLoadAnalyze(page);
    await skipValidationAndGoToStep4(page);
    await expect(page.locator("#cleaningBoard .decision-card").first()).toBeVisible({ timeout: 10000 });
  });

  test("depuracion muestra grupos con codigo de categoria", async ({ page }) => {
    await clearLoadAnalyze(page);
    await skipValidationAndGoToStep4(page);
    await expect(page.locator(".depur-group__code").first()).toBeVisible({ timeout: 10000 });
  });

  test("depuracion muestra filas afectadas por grupo", async ({ page }) => {
    await clearLoadAnalyze(page);
    await skipValidationAndGoToStep4(page);
    await expect(page.locator(".depur-rows").first()).toBeVisible({ timeout: 10000 });
  });

  test("depuracion muestra botones de accion por grupo", async ({ page }) => {
    await clearLoadAnalyze(page);
    await skipValidationAndGoToStep4(page);
    await expect(page.locator(".depur-group__actions button").first()).toBeVisible({ timeout: 10000 });
  });

  test("aplicar accion por grupo registra en bitacora", async ({ page }) => {
    await clearLoadAnalyze(page);
    await skipValidationAndGoToStep4(page);
    const btn = page.locator(".depur-group__actions button").first();
    await expect(btn).toBeVisible({ timeout: 10000 });
    await btn.click();
    await expect(page.locator("#actionsLog .log-item")).toHaveCount(1, { timeout: 5000 });
  });

  test("deshacer accion de grupo restaura grupo", async ({ page }) => {
    await clearLoadAnalyze(page);
    await skipValidationAndGoToStep4(page);
    const btn = page.locator(".depur-group__actions button").first();
    await expect(btn).toBeVisible({ timeout: 10000 });
    await btn.click();
    await expect(page.locator("#actionsLog .log-item")).toHaveCount(1, { timeout: 5000 });
    await page.click("#undoButton");
    await expect(page.locator("#actionsLog .log-item")).toHaveCount(0);
    await expect(page.locator(".depur-group__actions button").first()).toBeVisible();
  });
});
