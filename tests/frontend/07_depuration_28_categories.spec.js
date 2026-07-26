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

async function runDiagnostic(page) {
  await navigateToStep(page, 3);
  await expect(page.locator("#nubeSkipManual")).toBeVisible({ timeout: 30000 });
}

async function skipValidationAndGoToStep4(page) {
  await runDiagnostic(page);
  await page.locator("#nubeSkipManual").click();
  await navigateToStep(page, 4);
}

test.describe("AuditData AI - Depuracion 28 Categorias", () => {
  test("step 3 muestra diagnostico directo sin selector de modo", async ({ page }) => {
    await clearLoadAnalyze(page);
    await navigateToStep(page, 3);
    await expect(page.locator("#nubeSkipManual")).toBeVisible({ timeout: 30000 });
    await expect(page.locator("#nubeModeAI")).toHaveCount(0);
  });

  test("step 3 muestra skip manual", async ({ page }) => {
    await clearLoadAnalyze(page);
    await runDiagnostic(page);
    await expect(page.locator("#nubeSkipManual")).toBeVisible();
  });

  test("omitir validacion habilita avanzar", async ({ page }) => {
    await clearLoadAnalyze(page);
    await runDiagnostic(page);
    await page.locator("#nubeSkipManual").click();
    await expect(page.locator("#nextButton")).toBeEnabled({ timeout: 5000 });
  });

  test("step 4 muestra columna grid con tarjetas", async ({ page }) => {
    await clearLoadAnalyze(page);
    await skipValidationAndGoToStep4(page);
    await expect(page.locator("#depurColumnGrid .column-card").first()).toBeVisible({ timeout: 10000 });
  });

  test("step 4 muestra tarjeta de dataset para duplicados", async ({ page }) => {
    await clearLoadAnalyze(page);
    await skipValidationAndGoToStep4(page);
    await expect(page.locator("#datasetSummaryCard")).toBeVisible({ timeout: 10000 });
  });

  test("click en columna abre drawer con chat", async ({ page }) => {
    await clearLoadAnalyze(page);
    await skipValidationAndGoToStep4(page);
    await page.locator("[data-depur-open-col]").first().click();
    await expect(page.locator("#aiColumnDrawer.is-active")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("#drawerChatFeed")).toBeVisible();
  });

  test("drawer muestra diagnosticos de la columna", async ({ page }) => {
    await clearLoadAnalyze(page);
    await skipValidationAndGoToStep4(page);
    await page.locator("[data-depur-open-col]").first().click();
    await expect(page.locator("#aiColumnDrawer.is-active")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("#drawerDiagnostics")).toBeVisible();
  });

  test("drawer carga recomendaciones de IA", async ({ page }) => {
    await clearLoadAnalyze(page);
    await skipValidationAndGoToStep4(page);
    await page.locator("[data-depur-open-col]").first().click();
    await expect(page.locator("#aiColumnDrawer.is-active")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("#drawerAIRecs")).toBeVisible();
  });

  test("chat en drawer funciona con preguntas", async ({ page }) => {
    await clearLoadAnalyze(page);
    await skipValidationAndGoToStep4(page);
    await page.locator("[data-depur-open-col]").first().click();
    await expect(page.locator("#aiColumnDrawer.is-active")).toBeVisible({ timeout: 10000 });
    await page.fill("#drawerChatInput", "Que problemas tiene esta columna?");
    await page.click("#drawerChatSendButton");
    await expect(page.locator(".chat-bubble--user")).toHaveCount(1, { timeout: 5000 });
  });

  test("cerrar drawer oculta el panel", async ({ page }) => {
    await clearLoadAnalyze(page);
    await skipValidationAndGoToStep4(page);
    await page.locator("[data-depur-open-col]").first().click();
    await expect(page.locator("#aiColumnDrawer.is-active")).toBeVisible({ timeout: 10000 });
    await page.click("#drawerCloseButton");
    await expect(page.locator("#aiColumnDrawer.is-active")).toHaveCount(0);
  });
});
