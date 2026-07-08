import { expect, test } from '@playwright/test'

test.describe('TASK-009 execution steps visualization', () => {
  test('does not render an empty execution list for pure dialogue', async ({ page }) => {
    await page.goto('/__e2e__/execution-steps?scenario=pure')

    await expect(page.getByText('这是一个普通回复，没有工具调用。')).toBeVisible()
    await expect(page.locator('.execution-step-list')).toHaveCount(0)
  })

  test('renders thinking, weather tool, and code execution in event order', async ({ page }) => {
    await page.goto('/__e2e__/execution-steps?scenario=mixed')

    const steps = page.locator('.execution-step-list__item')
    await expect(page.getByText('执行过程 · 3步')).toBeVisible()
    await expect(steps).toHaveCount(3)
    await expect(steps.nth(0)).toContainText('分析用户意图')
    await expect(steps.nth(1)).toContainText('get_weather')
    await expect(steps.nth(1)).toContainText('地点: 厦门')
    await expect(steps.nth(2)).toContainText('执行代码')
    await expect(steps.nth(2)).toContainText('hello from code')
    await expect(page.getByText('code_executor')).toHaveCount(0)
  })

  test('keeps legacy tool_calls readable for historical messages', async ({ page }) => {
    await page.goto('/__e2e__/execution-steps?scenario=legacy')

    await expect(page.getByText('工具调用 (1)')).toBeVisible()
    await expect(page.getByText('web_search')).toBeVisible()
    await expect(page.getByText('"query": "AgentForge"')).toBeVisible()
  })

  test('shows interrupted stream as finalized message without spinner', async ({ page }) => {
    await page.goto('/__e2e__/execution-steps?scenario=interrupted')

    await expect(page.getByText('连接中断，请重试。')).toBeVisible()
    await expect(page.locator('.stream-cursor')).toHaveCount(0)
    await expect(page.locator('.execution-progress')).toHaveCount(0)
  })

  test('keeps running execution steps expanded with progress feedback', async ({ page }) => {
    await page.goto('/__e2e__/execution-steps?scenario=streaming')

    await expect(page.getByText('执行过程 · 2步')).toBeVisible()
    await expect(page.locator('.execution-progress')).toBeVisible()
    await expect(page.locator('.execution-step-list__spinner')).toBeVisible()
    const runningStep = page.locator('.execution-step-list__item').nth(1)
    await expect(runningStep).toContainText('get_weather')
    await expect(runningStep).toContainText('执行中')
    await expect(runningStep.locator('.tool-call-card__spinner')).toBeVisible()
  })

  test('collapses and expands execution steps within the expected animation budget', async ({ page }) => {
    await page.goto('/__e2e__/execution-steps?scenario=mixed')

    const content = page.locator('.execution-step-list__content')
    await page.getByRole('button', { name: /执行过程 · 3步/ }).click()
    await expect(content).toBeVisible()

    const maxTransitionMs = await content.evaluate((element) => {
      const style = getComputedStyle(element)
      return Math.max(
        ...style.transitionDuration.split(',').map((duration) => {
          const value = Number.parseFloat(duration)
          return duration.trim().endsWith('ms') ? value : value * 1000
        }),
      )
    })
    expect(maxTransitionMs).toBeLessThanOrEqual(300)

    await page.getByRole('button', { name: /执行过程 · 3步/ }).click()
    await expect(content).toBeHidden({ timeout: maxTransitionMs + 1000 })

    await page.getByRole('button', { name: /执行过程 · 3步/ }).click()
    await expect(content).toBeVisible({ timeout: maxTransitionMs + 1000 })
  })

  test('keeps multi-step timeline connectors aligned', async ({ page }) => {
    await page.goto('/__e2e__/execution-steps?scenario=mixed')

    await page.getByRole('button', { name: /执行过程 · 3步/ }).click()
    const connectors = page.locator('.execution-step-list__connector')
    await expect(connectors).toHaveCount(3)

    const metrics = await connectors.evaluateAll((nodes) => nodes.map((node) => {
      const rect = node.getBoundingClientRect()
      return {
        centerX: rect.left + rect.width / 2,
        height: rect.height,
      }
    }))
    const firstCenterX = metrics[0].centerX
    for (const metric of metrics) {
      expect(Math.abs(metric.centerX - firstCenterX)).toBeLessThanOrEqual(0.5)
      expect(metric.height).toBeGreaterThan(16)
    }
  })

  test('does not overflow horizontally on a 375px mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/__e2e__/execution-steps?scenario=mixed')

    await expect(page.getByText('执行过程 · 3步')).toBeVisible()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(1)
  })
})
