const { test, expect } = require("@playwright/test");

const URL = "/?test";

async function clearLoadAnalyze(page) {
  await page.goto(URL);
  await page.evaluate(() => localStorage.clear());
  await page.goto(URL);
  await page.click("#loadSampleButton");
  await expect(page.locator('[data-step="1"]')).toHaveClass(/is-active/, { timeout: 15000 });
}

test.describe("AuditData AI - Acciónes de Limpieza y Undo", () => {
  test("paso 2 muestra tarjetas de decisión en rulesBoard", async ({ page }) => {
    await clearLoadAnalyze(page);
    await page.click("#nextButton");
    await expect(page.locator('[data-step="2"]')).toHaveClass(/is-active/);
    const rulesCards = page.locator("#rulesBoard .decisión-card");
    await expect(rulesCards.first()).toBeVisible();
  });

  test("eliminar una columna registra la acción en el log", async ({ page }) => {
    await clearLoadAnalyze(page);
    await page.click("#nextButton");
    await expect(page.locator('[data-step="2"]')).toHaveClass(/is-active/);
    const firstDeleteBtn = page.locator("#rulesBoard button[data-delete-column]").first();
    await firstDeleteBtn.click();
    await expect(page.locator("#actionsLog .log-item")).toHaveCount(1);
  });

  test("deshacer individual elimina solo esa acción", async ({ page }) => {
    await clearLoadAnalyze(page);
    await page.click("#nextButton");
    await expect(page.locator('[data-step="2"]')).toHaveClass(/is-active/);
    const firstDeleteBtn = page.locator("#rulesBoard button[data-delete-column]").first();
    await firstDeleteBtn.click();
    await expect(page.locator("#actionsLog .log-item")).toHaveCount(1);
    await page.evaluate(() => {
      document.querySelectorAll("[data-step-button]").forEach(b => b.disabled = false);
      window.location.hash = "#/depurar";
    });
    await expect(page.locator('[data-step="4"]')).toHaveClass(/is-active/, { timeout: 15000 });
    const undoBtn = page.locator("#actionsLog .log-item__undo").first();
    await undoBtn.click({ force: true });
    await expect(page.locator("#actionsLog .log-item")).toHaveCount(0);
  });

  test("deshacer global elimina la ultima acción", async ({ page }) => {
    await clearLoadAnalyze(page);
    await page.click("#nextButton");
    await expect(page.locator('[data-step="2"]')).toHaveClass(/is-active/);
    const firstDeleteBtn = page.locator("#rulesBoard button[data-delete-column]").first();
    await firstDeleteBtn.click();
    await expect(page.locator("#actionsLog .log-item")).toHaveCount(1);
    await page.evaluate(() => {
      document.querySelectorAll("[data-step-button]").forEach(b => b.disabled = false);
      window.location.hash = "#/depurar";
    });
    await expect(page.locator('[data-step="4"]')).toHaveClass(/is-active/, { timeout: 15000 });
    await page.click("#undoButton");
    await expect(page.locator("#actionsLog .log-item")).toHaveCount(0);
  });
});
