const { test, expect } = require("@playwright/test");

test.describe("AuditData AI - Login con Google", () => {
  test("muestra la pantalla de login cuando no hay sesión", async ({ page }) => {
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

  test("al pulsar Iniciar sesion se exige aceptar el consentimiento", async ({ page }) => {
    await page.goto("/");
    const googleBtn = page.locator("#googleLoginButton");
    await expect(googleBtn).toBeVisible({ timeout: 10000 });
    await googleBtn.click();

    const modal = page.locator("#consentModal");
    await expect(modal).toBeVisible({ timeout: 10000 });
    await expect(page.locator("#consentModal__body, .consent-modal__body")).toBeVisible();
    await expect(page.locator(".consent-modal__version")).toContainText("2.0");
    await expect(page.locator('.consent-modal__body a[href="/privacidad"]')).toBeVisible();

    const acceptBtn = page.locator("#consentAcceptButton");
    await expect(acceptBtn).toBeDisabled();

    await page.locator("#consentCheckbox").check();
    await expect(acceptBtn).toBeEnabled();

    await page.locator("#consentCancelButton").click();
    await expect(modal).toBeHidden();
  });

  test("el aviso de privacidad esta enlazado en el footer y es accesible", async ({ page }) => {
    await page.goto("/");
    const link = page.locator('footer a[href="/privacidad"]');
    await expect(link).toBeVisible({ timeout: 10000 });
    await expect(link).toHaveAttribute("href", "/privacidad");

    await page.goto("/privacidad");
    await expect(page.locator("h1")).toContainText("privacidad");
    await expect(page.locator("body")).toContainText("Versi\u00f3n 2.0");
  });

  test("sin consentimiento aceptado, la sesion no guarda historial", async ({ page }) => {
    await page.goto("/?test");
    const appContent = page.locator("#appContent");
    await expect(appContent).toBeVisible({ timeout: 10000 });
    const consent = await page.evaluate(() => localStorage.getItem("auditdata_consent"));
    expect(consent).toBeNull();
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
