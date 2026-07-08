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

const now = '2026-07-08T13:30:00.000Z'

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
  id: 'session-bridge',
  project_id: project.id,
  title: '读取真实代码',
  intent_type: 'iteration',
  current_pipeline_run_id: null,
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

async function mockBridgeApi(page: Page, options: { chatRequests: unknown[] }) {
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
      await route.fulfill(json([]))
      return
    }

    if (method === 'GET' && path === `/api/v1/sessions/${session.id}/messages`) {
      await route.fulfill(json([]))
      return
    }

    if (method === 'GET' && path === `/api/v1/projects/${project.id}/mounts`) {
      await route.fulfill(json([
        {
          id: 'mount-primary',
          project_id: project.id,
          mount_type: 'local',
          display_name: '主代码库',
          locator: '/workspace/shop-api',
          role: 'primary',
          status: 'connected',
          metadata: { root_path: '/workspace/shop-api' },
          created_at: now,
          updated_at: now,
        },
        {
          id: 'mount-upload',
          project_id: project.id,
          mount_type: 'upload',
          display_name: '上传资料',
          locator: 'upload://context-files',
          role: 'docs',
          status: 'connected',
          metadata: {
            upload_id: 'context-files',
            file_count: 1,
          },
          created_at: now,
          updated_at: now,
        },
      ]))
      return
    }

    if (method === 'GET' && path === `/api/v1/projects/${project.id}/mounts/mount-primary/files`) {
      const requestedPath = url.searchParams.get('path') ?? ''
      await route.fulfill(json({
        mount_id: 'mount-primary',
        project_id: project.id,
        path: requestedPath,
        entries: requestedPath
          ? [
              {
                name: 'sessions.py',
                relative_path: 'src/api/routes/sessions.py',
                kind: 'file',
                size: 1280,
                modified_at: now,
              },
            ]
          : [
              {
                name: 'src',
                relative_path: 'src',
                kind: 'directory',
                size: null,
                modified_at: now,
              },
            ],
      }))
      return
    }

    if (method === 'GET' && path === `/api/v1/projects/${project.id}/mounts/mount-upload/files`) {
      const requestedPath = url.searchParams.get('path') ?? ''
      await route.fulfill(json({
        mount_id: 'mount-upload',
        project_id: project.id,
        path: requestedPath,
        entries: requestedPath
          ? [
              {
                name: 'requirements.md',
                relative_path: 'docs/requirements.md',
                kind: 'file',
                size: 640,
                modified_at: now,
              },
            ]
          : [
              {
                name: 'docs',
                relative_path: 'docs',
                kind: 'directory',
                size: null,
                modified_at: now,
              },
            ],
      }))
      return
    }

    if (method === 'POST' && path === `/api/v1/sessions/${session.id}/chat`) {
      options.chatRequests.push(request.postDataJSON())
      await route.fulfill(json({
        message_id: 'msg-user',
        task_id: 'task-bridge',
        pipeline_run_id: null,
      }, 202))
      return
    }

    if (method === 'GET' && path === '/api/v1/sse/tasks/task-bridge/stream') {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: 'event: task_completed\ndata: {"content":"ok"}\n\n',
      })
      return
    }

    await route.fulfill(json({ detail: `Unhandled ${method} ${path}` }, 404))
  })
}

test.describe('TASK-018 bridge context picker', () => {
  test('selects an authorized mount file and sends mount_id with chat payload', async ({ page }) => {
    const chatRequests: unknown[] = []
    await login(page)
    await mockBridgeApi(page, { chatRequests })

    await page.goto('/chat/session-bridge')

    await page.locator('.advanced-btn').click()
    await page.getByRole('button', { name: '添加上下文' }).click()

    await expect(page.locator('.file-browser__path')).toHaveText('主代码库')
    await page.locator('.file-browser__row').filter({ hasText: 'src' }).click()
    await page.locator('.file-browser__row').filter({ hasText: 'sessions.py' }).click()
    await page.getByRole('button', { name: '添加', exact: true }).click()

    await expect(page.locator('.context-chip')).toContainText('主代码库/src/api/routes/sessions.py')

    await page.locator('.advanced-panel__close').click()
    await page.locator('textarea').fill('请基于这个文件分析会话上下文读取逻辑')
    await page.locator('.send-btn').click()

    await expect.poll(() => chatRequests.length).toBe(1)
    expect(chatRequests[0]).toMatchObject({
      content: '请基于这个文件分析会话上下文读取逻辑',
      context_files: [
        {
          type: 'file',
          value: 'src/api/routes/sessions.py',
          label: '主代码库/src/api/routes/sessions.py',
          mount_id: 'mount-primary',
        },
      ],
    })
  })

  test('selects an uploaded mount file and sends mount_id with chat payload', async ({ page }) => {
    const chatRequests: unknown[] = []
    await login(page)
    await mockBridgeApi(page, { chatRequests })

    await page.goto('/chat/session-bridge')

    await page.locator('.advanced-btn').click()
    await page.getByRole('button', { name: '添加上下文' }).click()

    await page.locator('.context-picker__field select').selectOption('mount-upload')
    await expect(page.locator('.file-browser__path')).toHaveText('上传资料')
    await page.locator('.file-browser__row').filter({ hasText: 'docs' }).click()
    await page.locator('.file-browser__row').filter({ hasText: 'requirements.md' }).click()
    await page.getByRole('button', { name: '添加', exact: true }).click()

    await expect(page.locator('.context-chip')).toContainText('上传资料/docs/requirements.md')

    await page.locator('.advanced-panel__close').click()
    await page.locator('textarea').fill('请基于上传的需求文件拆解任务')
    await page.locator('.send-btn').click()

    await expect.poll(() => chatRequests.length).toBe(1)
    expect(chatRequests[0]).toMatchObject({
      content: '请基于上传的需求文件拆解任务',
      context_files: [
        {
          type: 'file',
          value: 'docs/requirements.md',
          label: '上传资料/docs/requirements.md',
          mount_id: 'mount-upload',
        },
      ],
    })
  })
})
