import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test('should display login page', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('h1.title')).toHaveText('AgentForge')
    await expect(page.locator('input[placeholder="用户名"]')).toBeVisible()
    await expect(page.locator('input[placeholder="密码"]')).toBeVisible()
  })

  test('should show validation error on empty fields', async ({ page }) => {
    await page.goto('/login')
    await page.click('button[type="submit"]')
    await expect(page.locator('.el-form-item__error').first()).toBeVisible()
  })

  test('should navigate to register page', async ({ page }) => {
    await page.goto('/login')
    await page.click('a[href="/register"]')
    await expect(page).toHaveURL('/register')
    await expect(page.locator('h1.title')).toHaveText('注册')
  })
})

test.describe('Register', () => {
  test('should display register page', async ({ page }) => {
    await page.goto('/register')
    await expect(page.locator('h1.title')).toHaveText('注册')
    await expect(page.locator('input[placeholder="用户名"]')).toBeVisible()
    await expect(page.locator('input[placeholder="邮箱"]')).toBeVisible()
    await expect(page.locator('input[placeholder="密码"]')).toBeVisible()
  })

  test('should navigate to login page', async ({ page }) => {
    await page.goto('/register')
    await page.click('a[href="/login"]')
    await expect(page).toHaveURL('/login')
  })

  test('should reject a password without an uppercase letter before sending the request', async ({ page }) => {
    let registrationRequested = false
    await page.route('**/api/v1/auth/register', async (route) => {
      registrationRequested = true
      await route.abort()
    })
    await page.goto('/register')
    await page.locator('input[placeholder="用户名"]').fill('testuser')
    await page.locator('input[placeholder="邮箱"]').fill('test@example.com')
    await page.locator('input[placeholder="密码"]').fill('yangkl2197')
    await page.click('button[type="submit"]')

    await expect(page.locator('.el-form-item__error')).toContainText('密码必须包含大写字母')
    expect(registrationRequested).toBe(false)
  })

  test('should display backend validation details', async ({ page }) => {
    await page.route('**/api/v1/auth/register', async (route) => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          error: {
            code: 'VALIDATION_ERROR',
            message: '请求参数校验失败',
            details: [{ field: 'password', issue: 'Value error, 需含大写字母' }],
          },
        }),
      })
    })
    await page.goto('/register')
    await page.locator('input[placeholder="用户名"]').fill('testuser')
    await page.locator('input[placeholder="邮箱"]').fill('test@example.com')
    await page.locator('input[placeholder="密码"]').fill('ValidPass123')
    await page.click('button[type="submit"]')

    await expect(page.locator('.el-message--error')).toContainText('需含大写字母')
  })
})
