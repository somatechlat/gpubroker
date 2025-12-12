import { defineConfig, devices } from '@playwright/test'

const PORT = process.env.PORT || '28030'
const BASE_URL = process.env.BASE_URL || `http://localhost:${PORT}`
const USE_EXTERNAL_SERVER = process.env.USE_EXTERNAL_SERVER === '1'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30 * 1000,
  expect: { timeout: 5000 },
  retries: 0,
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure'
  },
  webServer: USE_EXTERNAL_SERVER
    ? undefined
    : {
        command: `PORT=${PORT} npm run dev -- --hostname 0.0.0.0 --port ${PORT}`,
        url: `http://localhost:${PORT}`,
        reuseExistingServer: true,
        timeout: 120 * 1000
      },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    }
  ]
})
