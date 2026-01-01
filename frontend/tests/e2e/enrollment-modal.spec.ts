/**
 * GPUBROKER Enrollment Modal E2E Tests
 * 
 * Tests the complete enrollment flow from landing page to POD deployment.
 * Based on user journey: Landing Page → Plans → Payment → Pod Confirmation
 * 
 * @see docs/user-journeys/journey-1-landing-to-deployment.md
 */
import { test, expect, Page } from '@playwright/test'

// Landing page URL (served separately from Next.js frontend)
const LANDING_PAGE_URL = process.env.LANDING_PAGE_URL || 'http://localhost:28090'
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:28080'

test.describe('Enrollment Modal Flow', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to landing page
    await page.goto(LANDING_PAGE_URL, { waitUntil: 'networkidle' })
  })

  test('landing page loads with plan buttons', async ({ page }) => {
    // Verify landing page loaded
    await expect(page.locator('h1')).toContainText('GPU')
    
    // Verify plan buttons exist
    const trialButton = page.locator('[data-plan="trial"]').first()
    await expect(trialButton).toBeVisible()
    
    const proButton = page.locator('[data-plan="pro"]').first()
    await expect(proButton).toBeVisible()
  })

  test('clicking plan button opens enrollment modal', async ({ page }) => {
    // Click on Pro plan button
    const proButton = page.locator('[data-plan="pro"]').first()
    await proButton.click()
    
    // Verify modal opens
    const modal = page.locator('#enrollmentModal')
    await expect(modal).toHaveClass(/enrollment-modal--open/)
    
    // Verify modal header with logo
    const modalLogo = page.locator('.enrollment-modal__logo')
    await expect(modalLogo).toBeVisible()
    await expect(modalLogo).toContainText('GPUBROKER')
  })

  test('modal shows geo-detection loading state', async ({ page }) => {
    // Click on Trial plan button
    const trialButton = page.locator('[data-plan="trial"]').first()
    await trialButton.click()
    
    // Verify geo-detection step is visible
    const geoStep = page.locator('#stepGeo')
    await expect(geoStep).toBeVisible()
    
    // Verify loading spinner
    const spinner = page.locator('#stepGeo .spinner')
    await expect(spinner).toBeVisible()
    
    // Verify loading text
    await expect(page.locator('#stepGeo')).toContainText('Detectando ubicación')
  })

  test('modal close button works', async ({ page }) => {
    // Open modal
    const proButton = page.locator('[data-plan="pro"]').first()
    await proButton.click()
    
    // Verify modal is open
    const modal = page.locator('#enrollmentModal')
    await expect(modal).toHaveClass(/enrollment-modal--open/)
    
    // Click close button
    const closeButton = page.locator('#modalClose')
    await closeButton.click()
    
    // Verify modal is closed
    await expect(modal).not.toHaveClass(/enrollment-modal--open/)
  })

  test('modal closes on backdrop click', async ({ page }) => {
    // Open modal
    const proButton = page.locator('[data-plan="pro"]').first()
    await proButton.click()
    
    // Verify modal is open
    const modal = page.locator('#enrollmentModal')
    await expect(modal).toHaveClass(/enrollment-modal--open/)
    
    // Click backdrop
    const backdrop = page.locator('#modalBackdrop')
    await backdrop.click({ force: true })
    
    // Verify modal is closed
    await expect(modal).not.toHaveClass(/enrollment-modal--open/)
  })

  test('modal closes on Escape key', async ({ page }) => {
    // Open modal
    const proButton = page.locator('[data-plan="pro"]').first()
    await proButton.click()
    
    // Verify modal is open
    const modal = page.locator('#enrollmentModal')
    await expect(modal).toHaveClass(/enrollment-modal--open/)
    
    // Press Escape
    await page.keyboard.press('Escape')
    
    // Verify modal is closed
    await expect(modal).not.toHaveClass(/enrollment-modal--open/)
  })

  test('geo-detection transitions to payment step for non-Ecuador users', async ({ page }) => {
    // Mock geo API to return US
    await page.route(`${API_BASE_URL}/api/v2/admin/public/geo/detect`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          geo: {
            country_code: 'US',
            country_name: 'United States',
            detected: true,
            source: 'mock'
          },
          validation: {
            requires_tax_id: false,
            tax_id_name: null,
            tax_id_formats: [],
            language: 'en',
            country_code: 'US'
          },
          show_tax_id: false,
          tax_id_label: null,
          language: 'en'
        })
      })
    })
    
    // Open modal
    const proButton = page.locator('[data-plan="pro"]').first()
    await proButton.click()
    
    // Wait for geo-detection to complete and transition to payment
    await expect(page.locator('#stepPayment')).toBeVisible({ timeout: 5000 })
    
    // Verify payment form is visible
    await expect(page.locator('#modalEmail')).toBeVisible()
    await expect(page.locator('#modalName')).toBeVisible()
    await expect(page.locator('#modalCardNumber')).toBeVisible()
  })

  test('geo-detection shows tax ID step for Ecuador users', async ({ page }) => {
    // Mock geo API to return Ecuador
    await page.route(`${API_BASE_URL}/api/v2/admin/public/geo/detect`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          geo: {
            country_code: 'EC',
            country_name: 'Ecuador',
            detected: true,
            source: 'mock'
          },
          validation: {
            requires_tax_id: true,
            tax_id_name: 'RUC/Cédula',
            tax_id_formats: ['ruc', 'cedula'],
            language: 'es',
            country_code: 'EC'
          },
          show_tax_id: true,
          tax_id_label: 'RUC/Cédula',
          language: 'es'
        })
      })
    })
    
    // Open modal
    const proButton = page.locator('[data-plan="pro"]').first()
    await proButton.click()
    
    // Wait for tax ID step
    await expect(page.locator('#stepTaxId')).toBeVisible({ timeout: 5000 })
    
    // Verify tax ID form elements
    await expect(page.locator('#modalIdentifier')).toBeVisible()
    await expect(page.locator('#modalValidateBtn')).toBeVisible()
    await expect(page.locator('#stepTaxId')).toContainText('Verifica tu Identidad')
  })

  test('payment form validates required fields', async ({ page }) => {
    // Mock geo API to skip tax ID
    await page.route(`${API_BASE_URL}/api/v2/admin/public/geo/detect`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          geo: { country_code: 'US', detected: true },
          show_tax_id: false
        })
      })
    })
    
    // Open modal and wait for payment step
    const proButton = page.locator('[data-plan="pro"]').first()
    await proButton.click()
    await expect(page.locator('#stepPayment')).toBeVisible({ timeout: 5000 })
    
    // Try to submit empty form
    const submitButton = page.locator('#modalPayBtn')
    await submitButton.click()
    
    // Form should not submit (HTML5 validation)
    // Email field should be focused or show validation
    const emailInput = page.locator('#modalEmail')
    await expect(emailInput).toBeFocused()
  })

  test('plan summary shows correct plan details', async ({ page }) => {
    // Mock geo API
    await page.route(`${API_BASE_URL}/api/v2/admin/public/geo/detect`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          geo: { country_code: 'US', detected: true },
          show_tax_id: false
        })
      })
    })
    
    // Open modal with Pro plan
    const proButton = page.locator('[data-plan="pro"]').first()
    await proButton.click()
    await expect(page.locator('#stepPayment')).toBeVisible({ timeout: 5000 })
    
    // Verify plan details
    await expect(page.locator('#modalPlanName')).toContainText('Profesional')
    await expect(page.locator('#modalPlanPrice')).toContainText('$40')
    await expect(page.locator('#modalPlanTokens')).toContainText('10,000')
  })

  test('different plans show correct pricing', async ({ page }) => {
    // Mock geo API
    await page.route(`${API_BASE_URL}/api/v2/admin/public/geo/detect`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          geo: { country_code: 'US', detected: true },
          show_tax_id: false
        })
      })
    })
    
    // Test Trial plan
    const trialButton = page.locator('[data-plan="trial"]').first()
    await trialButton.click()
    await expect(page.locator('#stepPayment')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('#modalPlanPrice')).toContainText('$0')
    
    // Close and reopen with Basic plan
    await page.keyboard.press('Escape')
    const basicButton = page.locator('[data-plan="basic"]').first()
    await basicButton.click()
    await expect(page.locator('#stepPayment')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('#modalPlanPrice')).toContainText('$20')
  })

})

test.describe('Enrollment Modal - Mobile Responsive', () => {
  
  test.use({ viewport: { width: 375, height: 667 } }) // iPhone SE
  
  test('modal is full-screen on mobile', async ({ page }) => {
    await page.goto(LANDING_PAGE_URL, { waitUntil: 'networkidle' })
    
    // Open modal
    const trialButton = page.locator('[data-plan="trial"]').first()
    await trialButton.click()
    
    // Verify modal container takes full viewport
    const modalContainer = page.locator('.enrollment-modal__container')
    const box = await modalContainer.boundingBox()
    
    expect(box?.width).toBe(375)
    expect(box?.height).toBe(667)
  })

  test('form inputs are usable on mobile', async ({ page }) => {
    // Mock geo API
    await page.route(`${API_BASE_URL}/api/v2/admin/public/geo/detect`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          geo: { country_code: 'US', detected: true },
          show_tax_id: false
        })
      })
    })
    
    await page.goto(LANDING_PAGE_URL, { waitUntil: 'networkidle' })
    
    // Open modal
    const trialButton = page.locator('[data-plan="trial"]').first()
    await trialButton.click()
    await expect(page.locator('#stepPayment')).toBeVisible({ timeout: 5000 })
    
    // Fill form on mobile
    await page.locator('#modalEmail').fill('test@example.com')
    await page.locator('#modalName').fill('Test User')
    await page.locator('#modalCardNumber').fill('4242424242424242')
    
    // Verify values
    await expect(page.locator('#modalEmail')).toHaveValue('test@example.com')
    await expect(page.locator('#modalName')).toHaveValue('Test User')
  })

})

test.describe('Enrollment Modal - Desktop Layout', () => {
  
  test.use({ viewport: { width: 1920, height: 1080 } }) // Full HD
  
  test('modal uses full screen on desktop', async ({ page }) => {
    await page.goto(LANDING_PAGE_URL, { waitUntil: 'networkidle' })
    
    // Open modal
    const proButton = page.locator('[data-plan="pro"]').first()
    await proButton.click()
    
    // Verify modal is full-screen
    const modalContainer = page.locator('.enrollment-modal__container')
    const box = await modalContainer.boundingBox()
    
    expect(box?.width).toBe(1920)
    expect(box?.height).toBe(1080)
  })

  test('content is centered in modal', async ({ page }) => {
    // Mock geo API
    await page.route(`${API_BASE_URL}/api/v2/admin/public/geo/detect`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          geo: { country_code: 'US', detected: true },
          show_tax_id: false
        })
      })
    })
    
    await page.goto(LANDING_PAGE_URL, { waitUntil: 'networkidle' })
    
    // Open modal
    const proButton = page.locator('[data-plan="pro"]').first()
    await proButton.click()
    await expect(page.locator('#stepPayment')).toBeVisible({ timeout: 5000 })
    
    // Verify content is centered (max-width: 480px)
    const content = page.locator('.enrollment-modal__content')
    const box = await content.boundingBox()
    
    expect(box?.width).toBeLessThanOrEqual(480)
  })

})

test.describe('API Integration', () => {
  
  test('geo-detection API is called on modal open', async ({ page }) => {
    let geoApiCalled = false
    
    await page.route(`${API_BASE_URL}/api/v2/admin/public/geo/detect`, async route => {
      geoApiCalled = true
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          geo: { country_code: 'US', detected: true },
          show_tax_id: false
        })
      })
    })
    
    await page.goto(LANDING_PAGE_URL, { waitUntil: 'networkidle' })
    
    // Open modal
    const proButton = page.locator('[data-plan="pro"]').first()
    await proButton.click()
    
    // Wait for API call
    await page.waitForTimeout(1000)
    
    expect(geoApiCalled).toBe(true)
  })

  test('handles geo-detection API failure gracefully', async ({ page }) => {
    // Mock geo API to fail
    await page.route(`${API_BASE_URL}/api/v2/admin/public/geo/detect`, async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' })
      })
    })
    
    await page.goto(LANDING_PAGE_URL, { waitUntil: 'networkidle' })
    
    // Open modal
    const proButton = page.locator('[data-plan="pro"]').first()
    await proButton.click()
    
    // Should fallback to payment step (skip tax ID)
    await expect(page.locator('#stepPayment')).toBeVisible({ timeout: 5000 })
  })

})
