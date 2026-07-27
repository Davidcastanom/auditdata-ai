const { test, expect } = require("@playwright/test");

const URL = "/?test";

async function clearAndLoad(page) {
  await page.goto(URL);
  await page.evaluate(() => localStorage.clear());
  await page.goto(URL);
}

test.describe("AuditData AI - Muestra y Análisis", () => {
  test("cargar muestra analiza y avanza al paso 1", async ({ page }) => {
    await clearAndLoad(page);
    await page.click("#loadSampleButton");
    await expect(page.locator('[data-step="1"]')).toHaveClass(/is-active/, { timeout: 15000 });
  });

  test("después de analizar se muestra la tabla de perfilado con filas", async ({ page }) => {
    await clearAndLoad(page);
    await page.click("#loadSampleButton");
    await expect(page.locator('[data-step="1"]')).toHaveClass(/is-active/, { timeout: 15000 });
    const rows = page.locator("#profileTable tr");
    await expect(rows.first()).toBeVisible({ timeout: 5000 });
  });

  test("después de analizar se muestran las métricas", async ({ page }) => {
    await clearAndLoad(page);
    await page.click("#loadSampleButton");
    await expect(page.locator('[data-step="1"]')).toHaveClass(/is-active/, { timeout: 15000 });
    await expect(page.locator("#metrics .metric")).toHaveCount(4);
  });

  test("el boton Siguiente se habilita después de analizar", async ({ page }) => {
    await clearAndLoad(page);
    await page.click("#loadSampleButton");
    await expect(page.locator('[data-step="1"]')).toHaveClass(/is-active/, { timeout: 15000 });
    await expect(page.locator("#nextButton")).toBeEnabled();
  });
});
