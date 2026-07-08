import { expect, test, type Page } from '@playwright/test'

type Project = {
  id: string
  user_id: string
  name: string
  display_name: string
  description: string | null
  tech_tags: string[]
  status: string
  created_at: string
  updated_at: string
}

type ProjectSession = {
  id: string
  project_id: string
  title: string
  intent_type: string | null
  current_pipeline_run_id: string | null
  created_at: string
  updated_at: string
}

type PipelineStageState = {
  id: string
  pipeline_run_id: string
  stage_id: string
  stage_name: string
  order_index: number
  required: boolean
  status: 'pending' | 'running' | 'waiting_confirmation' | 'completed' | 'skipped' | 'failed'
  skip_reason: string | null
  confirmation_required: boolean
  confirmation_action: string | null
  confirmation_feedback: string | null
  confirmation_resolved_at: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

type PipelineRun = {
  id: string
  project_id: string
  session_id: string
  intent_type: 'new_feature'
  status: string
  current_stage_id: string | null
  created_at: string
  updated_at: string
  stages: PipelineStageState[]
}

type Artifact = {
  id: string
  project_id: string
  session_id: string | null
  pipeline_run_id: string | null
  stage_state_id: string | null
  artifact_type: string
  name: string
  content: string
  file_type: string | null
  source_message_id: string | null
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

const now = '2026-07-08T12:00:00.000Z'

const project: Project = {
  id: 'project-api',
  user_id: 'user-1',
  name: '订单中台 API',
  display_name: '订单中台 API',
  description: '处理订单、退款和库存锁定',
  tech_tags: ['FastAPI', 'Vue 3'],
  status: 'active',
  created_at: now,
  updated_at: now,
}

const session: ProjectSession = {
  id: 'session-confirm',
  project_id: project.id,
  title: '新增支付渠道',
  intent_type: 'new_feature',
  current_pipeline_run_id: 'run-feature',
  created_at: now,
  updated_at: now,
}

function stage(
  stageId: string,
  stageName: string,
  orderIndex: number,
  overrides: Partial<PipelineStageState> = {},
): PipelineStageState {
  return {
    id: `stage-${stageId}`,
    pipeline_run_id: 'run-feature',
    stage_id: stageId,
    stage_name: stageName,
    order_index: orderIndex,
    required: true,
    status: 'pending',
    skip_reason: null,
    confirmation_required: false,
    confirmation_action: null,
    confirmation_feedback: null,
    confirmation_resolved_at: null,
    started_at: null,
    completed_at: null,
    created_at: now,
    updated_at: now,
    ...overrides,
  }
}

function waitingRun(): PipelineRun {
  return {
    id: 'run-feature',
    project_id: project.id,
    session_id: session.id,
    intent_type: 'new_feature',
    status: 'waiting_confirmation',
    current_stage_id: 'analysis',
    created_at: now,
    updated_at: now,
    stages: [
      stage('analysis', '需求分析', 0, {
        status: 'waiting_confirmation',
        confirmation_required: true,
        started_at: now,
        completed_at: now,
      }),
      stage('design', '架构设计', 1, { confirmation_required: true }),
      stage('backend_dev', '后端开发', 2),
    ],
  }
}

const artifact: Artifact = {
  id: 'artifact-analysis',
  project_id: project.id,
  session_id: session.id,
  pipeline_run_id: 'run-feature',
  stage_state_id: 'stage-analysis',
  artifact_type: 'prd',
  name: '需求分析.md',
  content: '# 需求分析\n\n新增支付渠道。',
  file_type: 'markdown',
  source_message_id: 'msg-assistant',
  metadata: { stage_id: 'analysis', stage_name: '需求分析' },
  created_at: now,
  updated_at: now,
}

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
    window.localStorage.setItem('agentforge.current_project_id', 'project-api')
  })
}

async function mockConfirmationApi(page: Page, options: {
  confirmRequests: Array<{ action: string; feedback: string | null }>
}) {
  let pipelineRun = waitingRun()

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname
    const method = request.method()

    if (method === 'GET' && path === '/api/v1/agents/settings/me') {
      await route.fulfill(json({ agent_name: 'CodeSoul', avatar_url: null }))
      return
    }

    if (method === 'GET' && path === '/api/v1/projects') {
      await route.fulfill(json([project]))
      return
    }

    if (method === 'GET' && path === `/api/v1/projects/${project.id}/sessions`) {
      await route.fulfill(json([session]))
      return
    }

    if (method === 'GET' && path === `/api/v1/projects/${project.id}/artifacts`) {
      await route.fulfill(json([artifact]))
      return
    }

    if (method === 'GET' && path === `/api/v1/artifacts/${artifact.id}`) {
      await route.fulfill(json(artifact))
      return
    }

    if (method === 'GET' && path === `/api/v1/sessions/${session.id}/messages`) {
      await route.fulfill(json([
        {
          id: 'msg-assistant',
          role: 'assistant',
          content: '需求分析已生成，请确认。',
          task_id: 'task-analysis',
          extra_data: null,
          artifacts: [artifact],
          created_at: now,
        },
      ]))
      return
    }

    if (method === 'GET' && path === `/api/v1/pipeline-runs/${pipelineRun.id}`) {
      await route.fulfill(json(pipelineRun))
      return
    }

    if (method === 'POST' && path === `/api/v1/pipeline-runs/${pipelineRun.id}/stages/analysis/confirm`) {
      const payload = request.postDataJSON()
      options.confirmRequests.push({
        action: payload.action,
        feedback: payload.feedback ?? null,
      })
      pipelineRun = {
        ...pipelineRun,
        status: payload.action === 'cancel' ? 'cancelled' : (payload.action === 'approve' ? 'running' : 'planned'),
        current_stage_id: payload.action === 'approve' ? 'design' : 'analysis',
        stages: pipelineRun.stages.map((item) => {
          if (item.stage_id !== 'analysis') return item
          if (payload.action === 'approve') {
            return {
              ...item,
              status: 'completed',
              confirmation_action: 'approve',
              confirmation_feedback: null,
              confirmation_resolved_at: now,
            }
          }
          if (payload.action === 'revise') {
            return {
              ...item,
              status: 'pending',
              confirmation_action: 'revise',
              confirmation_feedback: payload.feedback,
              confirmation_resolved_at: now,
              completed_at: null,
            }
          }
          return {
            ...item,
            status: 'failed',
            confirmation_action: 'cancel',
            confirmation_resolved_at: now,
          }
        }),
      }
      await route.fulfill(json(pipelineRun))
      return
    }

    await route.fulfill(json({ detail: `Unhandled ${method} ${path}` }, 404))
  })
}

test.describe('TASK-017 human confirmation gate', () => {
  test('approves a waiting stage from the chat confirmation card', async ({ page }) => {
    const confirmRequests: Array<{ action: string; feedback: string | null }> = []
    await login(page)
    await mockConfirmationApi(page, { confirmRequests })

    await page.goto('/chat/session-confirm')

    await expect(page.getByTestId('confirm-card')).toContainText('需求分析等待确认')
    await expect(page.getByTestId('confirm-card')).toContainText('需求分析.md')
    await expect(page.getByTestId('confirm-card').getByRole('link', { name: /查看产物并交付/ })).toBeVisible()

    await page.getByRole('button', { name: '确认继续' }).click()

    await expect.poll(() => confirmRequests).toEqual([{ action: 'approve', feedback: null }])
    await expect(page.getByTestId('confirm-card')).toHaveCount(0)
  })

  test('submits revision feedback from the chat confirmation card', async ({ page }) => {
    const confirmRequests: Array<{ action: string; feedback: string | null }> = []
    await login(page)
    await mockConfirmationApi(page, { confirmRequests })

    await page.goto('/chat/session-confirm')

    await page.getByRole('button', { name: '我有修改意见' }).click()
    await page.locator('.revision-box__input').fill('补充异常场景和验收标准')
    await page.getByRole('button', { name: '提交修改意见' }).click()

    await expect.poll(() => confirmRequests).toEqual([
      { action: 'revise', feedback: '补充异常场景和验收标准' },
    ])
    await expect(page.getByTestId('confirm-card')).toHaveCount(0)
  })

  test('opens the generated artifact from the confirmation card', async ({ page }) => {
    const confirmRequests: Array<{ action: string; feedback: string | null }> = []
    await login(page)
    await mockConfirmationApi(page, { confirmRequests })

    await page.goto('/chat/session-confirm')

    await page.getByTestId('confirm-card').getByRole('link', { name: /查看产物并交付/ }).click()

    await expect(page).toHaveURL('/artifacts/artifact-analysis')
    await expect(page.locator('.artifact-viewer')).toContainText('需求分析')
    expect(confirmRequests).toHaveLength(0)
  })
})
