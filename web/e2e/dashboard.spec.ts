import { expect, test, type Page } from '@playwright/test'

function json(data: unknown) {
  return {
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(data),
  }
}

async function login(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('access_token', 'e2e-token')
  })
}

function dashboardPayload(withUsage = true) {
  return {
    tasks: { total: 4, pending: 1, processing: 1, completed: 2, failed: 0 },
    agents: { active: 2, inactive: 1 },
    skills: { total: 5 },
    cost: { today_usd: 1.25, trend_pct: 5, daily_7d: [] },
    evaluation: {
      total_events: 12,
      stage_success_rate: 1,
      skill_success_rate: 1,
      delivery_success_rate: 1,
      average_stage_latency_ms: 900,
      skill_authorizations: {
        required: 0,
        granted: 0,
        grant_rate: 0,
        by_skill: [],
        by_permission: [],
      },
      llm: {
        total_calls: withUsage ? 6 : 0,
        tokens_used: withUsage ? 12345 : 0,
        cost_usd: withUsage ? 0.1234 : 0,
        average_latency_ms: withUsage ? 650 : 0,
        by_model_route: withUsage
          ? [
              {
                model_route_key: 'quality',
                name: 'Quality Route',
                total_calls: 4,
                tokens_used: 10000,
                cost_usd: 0.1,
                average_latency_ms: 700,
              },
            ]
          : [],
        by_stage: withUsage
          ? [
              {
                stage_id: 'backend_dev',
                name: '后端开发',
                total_calls: 3,
                tokens_used: 8000,
                cost_usd: 0.08,
                average_latency_ms: 620,
              },
            ]
          : [],
      },
    },
    recent_tasks: [],
  }
}

test.describe('Dashboard LLM usage', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test('shows LLM usage totals and cost rankings', async ({ page }) => {
    await page.route('**/api/v1/dashboard', async (route) => {
      await route.fulfill(json(dashboardPayload()))
    })

    await page.goto('/dashboard')

    await expect(page.getByText('任务费用（今日）')).toBeVisible()
    const panel = page.getByTestId('llm-usage-panel')
    await expect(panel.getByText('LLM 实际用量')).toBeVisible()
    await expect(panel.getByTestId('llm-total-calls')).toContainText('6')
    await expect(panel.getByTestId('llm-total-cost')).toContainText('$0.1234')
    await expect(panel.getByTestId('llm-total-tokens')).toContainText('12,345')
    await expect(panel.getByTestId('llm-average-latency')).toContainText('650 ms')
    await expect(panel.getByText('Quality Route')).toBeVisible()
    await expect(panel.getByText('后端开发')).toBeVisible()
  })

  test('shows independent empty states for route and stage rankings', async ({ page }) => {
    await page.route('**/api/v1/dashboard', async (route) => {
      await route.fulfill(json(dashboardPayload(false)))
    })

    await page.goto('/dashboard')

    const panel = page.getByTestId('llm-usage-panel')
    await expect(panel.getByText('暂无 LLM 调用记录')).toHaveCount(2)
  })
})
