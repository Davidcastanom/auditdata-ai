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
    await expect(page.locator("#consentModal .consent-modal__body")).toBeVisible();
    await expect(page.locator("#consentModal .consent-modal__version")).toContainText("2.1");
    await expect(page.locator('#consentModal .consent-modal__body a[href="/privacidad"]')).toBeVisible();
    await expect(page.locator('#consentModal .consent-modal__body a[href="/terminos"]')).toBeVisible();

    const acceptBtn = page.locator("#consentAcceptButton");
    await expect(acceptBtn).toBeDisabled();

    await page.locator("#consentCheckbox").check();
    await expect(acceptBtn).toBeEnabled();

    await page.locator("#consentCancelButton").click();
    await expect(modal).toBeHidden();
  });

  test("el aviso de privacidad y los terminos estan enlazados y son accesibles", async ({ page }) => {
    await page.goto("/");
    const privacyLink = page.locator('footer a[href="/privacidad"]');
    await expect(privacyLink).toBeVisible({ timeout: 10000 });
    await expect(privacyLink).toHaveAttribute("href", "/privacidad");
    const termsLink = page.locator('footer a[href="/terminos"]');
    await expect(termsLink).toBeVisible({ timeout: 10000 });
    await expect(termsLink).toHaveAttribute("href", "/terminos");

    await page.goto("/privacidad");
    await expect(page.locator("h1")).toContainText("privacidad");
    await expect(page.locator("body")).toContainText("Versi\u00f3n 2.1");
    await expect(page.locator("body")).toContainText("RGPD");
    await expect(page.locator("body")).toContainText("1581");
    await expect(page.locator("body")).toContainText("CCPA");

    await page.goto("/terminos");
    await expect(page.locator("h1")).toContainText("T\u00e9rminos y Condiciones");
    await expect(page.locator("body")).toContainText("Responsabilidad del usuario sobre sus datos");
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

  test("existe un modal de autorizacion de datos sensibles oculto", async ({ page }) => {
    await page.goto("/?test");
    const modal = page.locator("#sensitiveConsentModal");
    await expect(modal).toHaveCount(1);
    await expect(modal).toHaveAttribute("aria-hidden", "true");
  });

  test("chat con datos sensibles pide autorizacion antes de enviar a la IA", async ({ page }) => {
    await page.goto("/?test");
    await page.evaluate(() => localStorage.clear());
    await page.goto("/?test");

    // Simula la respuesta del backend: el archivo parece contener datos sensibles.
    await page.route("**/api/ai/chat-column", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "sensitive_required",
          sensitive_columns: ["email"],
          response: "Se requiere autorizacion para datos sensibles",
        }),
      });
    });

    await page.click("#loadSampleButton");
    await expect(page.locator('[data-step="1"]')).toHaveClass(/is-active/, { timeout: 15000 });

    await page.evaluate(() => {
      document.querySelectorAll("[data-step-button]").forEach((b) => { b.disabled = false; });
      window.location.hash = "#/validar-ia";
    });
    await expect(page.locator("#nubeSkipManual")).toBeVisible({ timeout: 30000 });
    await page.locator("#nubeSkipManual").click();

    await page.evaluate(() => { window.location.hash = "#/depurar"; });
    await expect(page.locator('[data-step="4"]')).toHaveClass(/is-active/, { timeout: 10000 });

    await page.locator("[data-depur-open-col]").first().click();
    await expect(page.locator("#aiColumnDrawer.is-active")).toBeVisible({ timeout: 10000 });

    await page.fill("#drawerChatInput", "¿Qué problemas tiene esta columna?");
    await page.click("#drawerChatSendButton");

    const modal = page.locator("#sensitiveConsentModal");
    await expect(modal).toHaveClass(/is-active/, { timeout: 5000 });
    await expect(page.locator("#sensitiveColumnsLabel")).toContainText("email");

    await page.click("#sensitiveDeclineButton");
    await expect(modal).not.toHaveClass(/is-active/);
    await expect(page.locator("#drawerChatFeed .chat-bubble--error")).toContainText("No autorizaste");
  });
});
