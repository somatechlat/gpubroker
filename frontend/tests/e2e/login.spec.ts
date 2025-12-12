import { test, expect } from '@playwright/test'

test.describe('Login page', () => {
  test('renders login form and allows typing credentials', async ({ page }) => {
    await page.goto('/login', { waitUntil: 'networkidle' })

    await expect(page.getByRole('heading', { name: /sign in to gpubroker/i })).toBeVisible()

    const email = page.locator('input[type="email"]')
    const password = page.locator('input[type="password"]')
    await expect(email).toBeVisible()
    await expect(password).toBeVisible()

    await email.fill('user@example.com')
    await password.fill('correcthorsebatterystaple')

    await expect(page.getByRole('button', { name: /sign in/i })).toBeEnabled()
  })
})
