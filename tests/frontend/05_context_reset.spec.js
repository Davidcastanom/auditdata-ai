const { test, expect } = require("@playwright/test");

const URL = "/?test";

async function clearAndLoad(page) {
  await page.goto(URL);
  await page.evaluate(() => localStorage.clear());
  await page.goto(URL);
}

test.describe("AuditData AI - Contexto y Reset", () => {
  test("llenar contexto se guarda y persiste al recargar", async ({ page }) => {
    await clearAndLoad(page);
    await page.fill("#rowMeaningInput", "cada fila es un participante");
    await page.fill("#objectiveInput", "validar calidad del dataset");
    await page.click("#loadSampleButton");
    await expect(page.locator('[data-step="1"]')).toHaveClass(/is-active/, { timeout: 15000 });
    await page.reload();
    await expect(page.locator("#rowMeaningInput")).toHaveValue("cada fila es un participante");
    await expect(page.locator("#objectiveInput")).toHaveValue("validar calidad del dataset");
  });

  test("contexto vacio no afecta el analisis", async ({ page }) => {
    await clearAndLoad(page);
    await page.click("#loadSampleButton");
    await expect(page.locator('[data-step="1"]')).toHaveClass(/is-active/, { timeout: 15000 });
    await expect(page.locator("#metrics .metric")).toHaveCount(4);
  });
});
