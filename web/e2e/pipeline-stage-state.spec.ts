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
  status: 'pending' | 'running' | 'completed' | 'skipped' | 'failed'
  skip_reason: string | null
  confirmation_required: boolean
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

type PipelineRun = {
  id: string
  project_id: string
  session_id: string
  intent_type: 'iteration'
  status: string
  current_stage_id: string | null
  created_at: string
  updated_at: string
  stages: PipelineStageState[]
}

const now = '2026-07-08T10:00:00.000Z'

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
  id: 'session-pipeline',
  project_id: project.id,
  title: '优化退款状态流转',
  intent_type: 'iteration',
  current_pipeline_run_id: 'run-iteration',
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
    pipeline_run_id: 'run-iteration',
    stage_id: stageId,
    stage_name: stageName,
    order_index: orderIndex,
    required: true,
    status: 'pending',
    skip_reason: null,
    confirmation_required: false,
    started_at: null,
    completed_at: null,
    created_at: now,
    updated_at: now,
    ...overrides,
  }
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

async function mockPipelineApi(page: Page, options: {
  skipRequests: string[]
  pipelineGets: string[]
}) {
  let pipelineRun: PipelineRun = {
    id: 'run-iteration',
    project_id: project.id,
    session_id: session.id,
    intent_type: 'iteration',
    status: 'running',
    current_stage_id: 'backend_dev',
    created_at: now,
    updated_at: now,
    stages: [
      stage('diff', '需求 Diff', 0, { status: 'completed', completed_at: now }),
      stage('impact', '影响评估', 1, { required: false }),
      stage('backend_dev', '后端开发', 2, { status: 'running', started_at: now }),
      stage('frontend_dev', '前端开发', 3, {
        required: false,
        status: 'skipped',
        skip_reason: 'user_override',
        completed_at: now,
      }),
      stage('regression', '回归测试', 4),
    ],
  }

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

    if (method === 'GET' && path === `/api/v1/sessions/${session.id}/messages`) {
      await route.fulfill(json([]))
      return
    }

    if (method === 'GET' && path === `/api/v1/pipeline-runs/${pipelineRun.id}`) {
      options.pipelineGets.push(pipelineRun.id)
      await route.fulfill(json(pipelineRun))
      return
    }

    if (method === 'POST' && path === `/api/v1/pipeline-runs/${pipelineRun.id}/stages/impact/skip`) {
      options.skipRequests.push('impact')
      pipelineRun = {
        ...pipelineRun,
        stages: pipelineRun.stages.map((item) =>
          item.stage_id === 'impact'
            ? { ...item, status: 'skipped', skip_reason: 'user_skipped', completed_at: now }
            : item,
        ),
      }
      await route.fulfill(json(pipelineRun))
      return
    }

    await route.fulfill(json({ detail: `Unhandled ${method} ${path}` }, 404))
  })
}

test.describe('TASK-015 pipeline stage state', () => {
  test('renders persisted PipelineRun state and skips optional stages through the API', async ({ page }) => {
    const pipelineGets: string[] = []
    const skipRequests: string[] = []

    await login(page)
    await mockPipelineApi(page, { pipelineGets, skipRequests })

    await page.goto('/chat/session-pipeline')

    await page.locator('.intent-pill').click()

    await expect(page.getByTestId('stage-preview-summary')).toContainText('当前：后端开发')
    await expect(page.getByTestId('stage-preview-summary')).toContainText('运行中')
    await expect(page.locator('.stage-pill').filter({ hasText: '前端开发' })).toHaveClass(/skipped/)
    expect(pipelineGets).toContain('run-iteration')

    await page.locator('.stage-pill').filter({ hasText: '影响评估' }).click()

    await expect.poll(() => skipRequests).toEqual(['impact'])
    await expect(page.locator('.stage-pill').filter({ hasText: '影响评估' })).toHaveClass(/skipped/)
  })
})
