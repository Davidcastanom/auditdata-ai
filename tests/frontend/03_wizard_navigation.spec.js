const { test, expect } = require("@playwright/test");

async function clearLoadAnalyze(page) {
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await page.goto("/");
  await page.click("#loadSampleButton");
  await expect(page.locator('[data-step="1"]')).toHaveClass(/is-active/, { timeout: 15000 });
}

test.describe("AuditData AI - Navegacion del Wizard", () => {
  test("boton Siguiente esta habilitado en paso 1", async ({ page }) => {
    await clearLoadAnalyze(page);
    await expect(page.locator("#nextButton")).toBeEnabled();
  });

  test("hacer clic en Siguiente avanza al paso 2", async ({ page }) => {
    await clearLoadAnalyze(page);
    await page.click("#nextButton");
    await expect(page.locator('[data-step="2"]')).toHaveClass(/is-active/);
  });

  test("navegar al paso 2 y volver con Anterior", async ({ page }) => {
    await clearLoadAnalyze(page);
    await page.click("#nextButton");
    await expect(page.locator('[data-step="2"]')).toHaveClass(/is-active/);
    await page.click("#previousButton");
    await expect(page.locator('[data-step="1"]')).toHaveClass(/is-active/);
  });

  test("hacer clic en un boton de paso navega directamente", async ({ page }) => {
    await clearLoadAnalyze(page);
    await page.click('[data-step-button="2"]');
    await expect(page.locator('[data-step="2"]')).toHaveClass(/is-active/);
  });
});
