const { test, expect } = require("@playwright/test");

test.describe("AuditData AI - Login con Google", () => {
  test("muestra la pantalla de login cuando no hay sesion", async ({ page }) => {
    await page.goto("/");
    const loginScreen = page.locator("#loginScreen");
    await expect(loginScreen).toBeVisible({ timeout: 10000 });
    await expect(page.locator("#googleLoginButton")).toBeVisible();
  });

  test("el boton de Google esta habilitado", async ({ page }) => {
    await page.goto("/");
    const btn = page.locator("#googleLoginButton");
    await expect(btn).toBeVisible({ timeout: 10000 });
    await expect(btn).toBeEnabled();
  });

  test("sin ?test, la app no se muestra sin autenticar", async ({ page }) => {
    await page.goto("/");
    await page.waitForTimeout(4000);
    const appContent = page.locator("#appContent");
    const isVisible = await appContent.isVisible();
    expect(isVisible).toBe(false);
  });

  test("con ?test, la app se muestra sin login", async ({ page }) => {
    await page.goto("/?test");
    const appContent = page.locator("#appContent");
    await expect(appContent).toBeVisible({ timeout: 10000 });
  });
});
