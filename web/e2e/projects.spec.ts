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

const now = '2026-07-08T09:00:00.000Z'

const baseProjects: Project[] = [
  {
    id: 'project-api',
    user_id: 'user-1',
    name: '订单中台 API',
    display_name: '订单中台 API',
    description: '处理订单、退款和库存锁定',
    tech_tags: ['FastAPI', 'PostgreSQL'],
    status: 'active',
    created_at: now,
    updated_at: now,
  },
  {
    id: 'project-web',
    user_id: 'user-1',
    name: '设计系统前端',
    display_name: '设计系统前端',
    description: '组件库与多端主题',
    tech_tags: ['Vue 3', 'TypeScript'],
    status: 'active',
    created_at: now,
    updated_at: now,
  },
]

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

async function mockProjectApi(page: Page, options?: {
  projects?: Project[]
  onCreateProject?: (payload: unknown) => Project
  onCreateMount?: (projectId: string, payload: unknown) => void
  sessionRequests?: string[]
}) {
  const projects = options?.projects ?? [...baseProjects]
  const sessionsByProject: Record<string, ProjectSession[]> = {
    'project-api': [
      {
        id: 'session-api',
        project_id: 'project-api',
        title: '订单退款流程',
        intent_type: 'bug_fix',
        current_pipeline_run_id: null,
        created_at: now,
        updated_at: now,
      },
    ],
    'project-web': [
      {
        id: 'session-web',
        project_id: 'project-web',
        title: '前端颜色系统',
        intent_type: 'ui_adjust',
        current_pipeline_run_id: null,
        created_at: now,
        updated_at: now,
      },
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
      await route.fulfill(json(projects))
      return
    }

    const projectSessionsMatch = path.match(/^\/api\/v1\/projects\/([^/]+)\/sessions$/)
    if (projectSessionsMatch && method === 'GET') {
      const projectId = projectSessionsMatch[1]
      options?.sessionRequests?.push(projectId)
      await route.fulfill(json(sessionsByProject[projectId] ?? []))
      return
    }

    const projectMountsMatch = path.match(/^\/api\/v1\/projects\/([^/]+)\/mounts$/)
    if (projectMountsMatch && method === 'GET') {
      const projectId = projectMountsMatch[1]
      await route.fulfill(json([
        {
          id: `${projectId}-mount`,
          project_id: projectId,
          mount_type: 'local',
          display_name: '主代码库',
          locator: `/workspace/${projectId}`,
          role: 'primary',
          status: 'connected',
          metadata: {},
          created_at: now,
          updated_at: now,
        },
      ]))
      return
    }

    if (method === 'POST' && path === '/api/v1/projects') {
      const payload = request.postDataJSON()
      const created = options?.onCreateProject?.(payload) ?? {
        id: 'project-created',
        user_id: 'user-1',
        name: payload.name,
        display_name: payload.name,
        description: payload.description,
        tech_tags: payload.tech_tags,
        status: 'active',
        created_at: now,
        updated_at: now,
      }
      projects.unshift(created)
      await route.fulfill(json(created, 201))
      return
    }

    if (projectMountsMatch && method === 'POST') {
      const projectId = projectMountsMatch[1]
      const payload = request.postDataJSON()
      options?.onCreateMount?.(projectId, payload)
      await route.fulfill(json({
        id: `${projectId}-mount-created`,
        project_id: projectId,
        ...payload,
        metadata: payload.metadata ?? {},
        created_at: now,
        updated_at: now,
      }, 201))
      return
    }

    await route.fulfill(json({ detail: `Unhandled ${method} ${path}` }, 404))
  })
}

test.describe('TASK-014 project real data flow', () => {
  test('renders projects from API and scopes chat sessions to the selected project', async ({ page }) => {
    const sessionRequests: string[] = []
    await login(page)
    await mockProjectApi(page, { sessionRequests })

    await page.goto('/projects')

    await expect(page.getByText('订单中台 API')).toBeVisible()
    await expect(page.getByText('设计系统前端')).toBeVisible()
    await expect(page.getByText('我的电商后端')).toHaveCount(0)

    await page
      .locator('.project-card')
      .filter({ hasText: '设计系统前端' })
      .getByRole('button', { name: /开始对话/ })
      .click()

    await expect(page).toHaveURL('/chat')
    await expect(page.locator('.project-bar')).toContainText('设计系统前端')
    await expect(page.locator('.session-list')).toContainText('前端颜色系统')
    expect(sessionRequests).toContain('project-web')

    await page.locator('.project-info').click()
    await page.locator('.dropdown-item').filter({ hasText: '订单中台 API' }).click()

    await expect(page.locator('.project-bar')).toContainText('订单中台 API')
    await expect(page.locator('.session-list')).toContainText('订单退款流程')
    expect(sessionRequests).toContain('project-api')

    await page.reload()
    await expect(page.locator('.project-bar')).toContainText('订单中台 API')
  })

  test('creates a project and a primary mount before showing success', async ({ page }) => {
    let createProjectPayload: unknown
    let createMountPayload: unknown
    let mountedProjectId: string | undefined

    await login(page)
    await mockProjectApi(page, {
      onCreateProject: (payload) => {
        createProjectPayload = payload
        return {
          id: 'project-created',
          user_id: 'user-1',
          name: '支付网关服务',
          display_name: '支付网关服务',
          description: '接入支付渠道和对账',
          tech_tags: ['FastAPI'],
          status: 'active',
          created_at: now,
          updated_at: now,
        }
      },
      onCreateMount: (projectId, payload) => {
        mountedProjectId = projectId
        createMountPayload = payload
      },
    })

    await page.goto('/projects/create')

    await page.getByPlaceholder('例如：我的电商后端').fill('支付网关服务')
    await page.getByPlaceholder('简要描述这个项目的用途...').fill('接入支付渠道和对账')
    await page.getByRole('button', { name: '下一步' }).click()

    await page.getByPlaceholder('例如：/Users/me/work/payment-service').fill('/Users/me/work/payment-service')
    await page.getByRole('button', { name: '下一步' }).click()

    await page.getByText('FastAPI', { exact: true }).click()
    await page.getByRole('button', { name: '完成' }).click()

    await expect(page.getByText('项目创建成功')).toBeVisible()
    expect(createProjectPayload).toEqual({
      name: '支付网关服务',
      description: '接入支付渠道和对账',
      tech_tags: ['FastAPI'],
    })
    expect(mountedProjectId).toBe('project-created')
    expect(createMountPayload).toMatchObject({
      mount_type: 'local',
      display_name: '主代码库',
      locator: '/Users/me/work/payment-service',
      role: 'primary',
      status: 'connected',
    })
  })
})
