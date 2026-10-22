import { defineConfig, devices } from '@playwright/test';

/**
 * ATS v8 — Playwright Configuration
 * Base URL is injected at runtime via ATS_BASE_URL env var.
 */
export default defineConfig({
  testDir: './tests',

  /* Sequential: external sites rate-limit parallel requests */
  fullyParallel: false,
  workers: 1,

  /* Fail the build on CI if test.only is accidentally left in */
  forbidOnly: !!process.env.CI,

  /* No retries — ATS repair loop handles failed tests */
  retries: 0,

  /* Reporter: JSON output path driven by PLAYWRIGHT_JSON_OUTPUT_NAME env var */
  reporter: [
    ['json'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['list'],
  ],

  use: {
    /* Base URL injected by ATS evaluator via ATS_BASE_URL */
    baseURL: process.env.ATS_BASE_URL || 'https://localhost:3000',

    /* No traces/video — keeps runs fast */
    trace: 'off',
    screenshot: 'only-on-failure',
    video: 'off',

    /* Per-action and navigation timeouts */
    actionTimeout:     20_000,
    navigationTimeout: 45_000,
  },

  /* Per-test timeout: 90s is enough for network-heavy external sites */
  timeout: 90_000,

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1400, height: 900 },
      },
    },
  ],

  outputDir: 'test-results/',
});
