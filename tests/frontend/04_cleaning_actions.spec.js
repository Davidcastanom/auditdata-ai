const { test, expect } = require("@playwright/test");

async function clearLoadAnalyze(page) {
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await page.goto("/");
  await page.click("#loadSampleButton");
  await expect(page.locator('[data-step="1"]')).toHaveClass(/is-active/, { timeout: 15000 });
}

test.describe("AuditData AI - Acciones de Limpieza y Undo", () => {
  test("paso 2 muestra tarjetas de decision en rulesBoard", async ({ page }) => {
    await clearLoadAnalyze(page);
    await page.click("#nextButton");
    await expect(page.locator('[data-step="2"]')).toHaveClass(/is-active/);
    const rulesCards = page.locator("#rulesBoard .decision-card");
    await expect(rulesCards.first()).toBeVisible();
  });

  test("eliminar una columna registra la accion en el log", async ({ page }) => {
    await clearLoadAnalyze(page);
    await page.click("#nextButton");
    await expect(page.locator('[data-step="2"]')).toHaveClass(/is-active/);
    const firstDeleteBtn = page.locator("#rulesBoard button[data-delete-column]").first();
    await firstDeleteBtn.click();
    await expect(page.locator("#actionsLog .log-item")).toHaveCount(1);
  });

  test("deshacer individual elimina solo esa accion", async ({ page }) => {
    await clearLoadAnalyze(page);
    await page.click("#nextButton");
    await expect(page.locator('[data-step="2"]')).toHaveClass(/is-active/);
    const firstDeleteBtn = page.locator("#rulesBoard button[data-delete-column]").first();
    await firstDeleteBtn.click();
    await expect(page.locator("#actionsLog .log-item")).toHaveCount(1);
    await page.click("#nextButton");
    await expect(page.locator('[data-step="3"]')).toHaveClass(/is-active/);
    const undoBtn = page.locator("#actionsLog .log-item__undo").first();
    await undoBtn.click({ force: true });
    await expect(page.locator("#actionsLog .log-item")).toHaveCount(0);
  });

  test("deshacer global elimina la ultima accion", async ({ page }) => {
    await clearLoadAnalyze(page);
    await page.click("#nextButton");
    await expect(page.locator('[data-step="2"]')).toHaveClass(/is-active/);
    const firstDeleteBtn = page.locator("#rulesBoard button[data-delete-column]").first();
    await firstDeleteBtn.click();
    await expect(page.locator("#actionsLog .log-item")).toHaveCount(1);
    await page.click("#nextButton");
    await expect(page.locator('[data-step="3"]')).toHaveClass(/is-active/);
    await page.click("#undoButton");
    await expect(page.locator("#actionsLog .log-item")).toHaveCount(0);
  });
});
