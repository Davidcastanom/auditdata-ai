const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests/frontend",
  timeout: 30000,
  retries: 0,
  use: {
    baseURL: "http://127.0.0.1:8000",
    headless: true,
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "python -m backend.app.server",
    port: 8000,
    timeout: 15000,
    reuseExistingServer: true,
  },
});
