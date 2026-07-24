const { test, expect } = require("@playwright/test");

const URL = "/?test";

test.describe("AuditData AI - Carga de pagina", () => {
  test("la pagina carga y muestra el titulo correcto", async ({ page }) => {
    await page.goto(URL);
    await expect(page).toHaveTitle(/AuditData AI/);
  });

  test("muestra la etapa 01 (Comprension) activa por defecto", async ({ page }) => {
    await page.goto(URL);
    const step0 = page.locator('[data-step="0"]');
    await expect(step0).toHaveClass(/is-active/);
  });

  test("muestra los campos opcionales de contexto", async ({ page }) => {
    await page.goto(URL);
    await expect(page.locator("#rowMeaningInput")).toBeVisible();
    await expect(page.locator("#objectiveInput")).toBeVisible();
  });

  test("el boton Analizar esta deshabilitado sin archivo", async ({ page }) => {
    await page.goto(URL);
    const button = page.locator("#analyzeButton");
    await expect(button).toBeDisabled();
  });

  test("muestra el dropzone para subir archivos", async ({ page }) => {
    await page.goto(URL);
    await expect(page.locator("#dropzone")).toBeVisible();
  });

  test("muestra los 6 pasos de navegacion", async ({ page }) => {
    await page.goto(URL);
    const navButtons = page.locator("[data-step-button]");
    await expect(navButtons).toHaveCount(6);
  });
});
