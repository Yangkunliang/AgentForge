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
    // Element Plus 表单验证会显示错误提示
    await expect(page.locator('.el-form-item__error')).toBeVisible()
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
})