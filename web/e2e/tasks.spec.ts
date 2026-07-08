import { expect, test, type Page } from '@playwright/test'

function json(data: unknown, status = 200) {
  return {
    status,
    contentType: 'application/json',
    body: JSON.stringify(data),
  }
}

async function login(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('access_token', 'e2e-token')
  })
}

test.describe('Task list filters', () => {
  test('shows all as the default label for status and priority filters', async ({ page }) => {
    await login(page)
    const taskListRequests: string[] = []

    await page.route('**/api/v1/tasks**', async (route) => {
      taskListRequests.push(route.request().url())
      await route.fulfill(json({
        items: [],
        total: 0,
        page: 1,
        per_page: 20,
      }))
    })

    await page.goto('/chat')
    await page.locator('.nav-item[title="任务管理"]').click()
    await expect(page).toHaveURL('/tasks')

    const filters = page.locator('.filter-form .el-select')
    await expect(filters).toHaveCount(2)
    await expect(filters.nth(0)).toContainText('全部')
    await expect(filters.nth(1)).toContainText('全部')

    expect(taskListRequests).toHaveLength(1)
    const initialRequestUrl = new URL(taskListRequests[0])
    expect(initialRequestUrl.searchParams.has('status')).toBe(false)
    expect(initialRequestUrl.searchParams.has('priority')).toBe(false)
  })
})
