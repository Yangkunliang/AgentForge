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
  delivery_status: string
  delivery_target_path: string | null
  delivered_at: string | null
  delivery_report: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

const now = '2026-07-08T11:00:00.000Z'

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

const artifact: Artifact = {
  id: 'artifact-design',
  project_id: project.id,
  session_id: 'session-artifact',
  pipeline_run_id: 'run-feature',
  stage_state_id: 'stage-design',
  artifact_type: 'architecture',
  name: '架构设计.md',
  content: '# 架构设计\n\n- API 使用 FastAPI\n- 前端使用 Vue 3',
  file_type: 'markdown',
  source_message_id: 'msg-assistant',
  metadata: { stage_id: 'design', stage_name: '架构设计' },
  delivery_status: 'pending',
  delivery_target_path: null,
  delivered_at: null,
  delivery_report: null,
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

async function mockArtifactApi(page: Page) {
  const applyRequests: Array<Record<string, unknown>> = []
  const githubApplyRequests: Array<Record<string, unknown>> = []
  let deliveredArtifact: Artifact | null = null

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

    if (method === 'GET' && path === `/api/v1/projects/${project.id}/mounts`) {
      await route.fulfill(json([
        {
          id: 'mount-api',
          project_id: project.id,
          mount_type: 'local',
          display_name: '主代码库',
          locator: '/workspace/project-api',
          role: 'primary',
          status: 'connected',
          metadata: {},
          created_at: now,
          updated_at: now,
        },
        {
          id: 'mount-github',
          project_id: project.id,
          mount_type: 'github',
          display_name: 'GitHub acme/shop-api',
          locator: 'github://acme/shop-api',
          role: 'primary',
          status: 'connected',
          metadata: {
            repo_full_name: 'acme/shop-api',
            default_branch: 'main',
          },
          created_at: now,
          updated_at: now,
        },
      ]))
      return
    }

    if (method === 'GET' && path === `/api/v1/projects/${project.id}/artifacts`) {
      await route.fulfill(json([artifact]))
      return
    }

    if (method === 'GET' && path === `/api/v1/artifacts/${artifact.id}`) {
      await route.fulfill(json(deliveredArtifact ?? artifact))
      return
    }

    if (method === 'POST' && path === `/api/v1/artifacts/${artifact.id}/delivery/preview`) {
      await route.fulfill(json({
        artifact_id: artifact.id,
        project_id: project.id,
        mount_id: 'mount-api',
        target_path: 'docs/architecture.md',
        status: 'previewed',
        has_changes: true,
        unified_diff: '--- a/docs/architecture.md\n+++ b/docs/architecture.md\n@@ -1 +1 @@\n-旧架构\n+新架构\n',
        report: {
          mount_id: 'mount-api',
          target_path: 'docs/architecture.md',
          bytes_to_write: 48,
        },
      }))
      return
    }

    if (method === 'POST' && path === `/api/v1/artifacts/${artifact.id}/delivery/apply`) {
      const payload = request.postDataJSON() as Record<string, unknown>
      applyRequests.push(payload)
      deliveredArtifact = {
        ...artifact,
        delivery_status: 'delivered',
        delivery_target_path: 'docs/architecture.md',
        delivered_at: now,
        delivery_report: {
          mount_id: 'mount-api',
          target_path: 'docs/architecture.md',
          backup_path: 'docs/architecture.md.agentforge.bak',
          bytes_written: 48,
        },
      }
      await route.fulfill(json({
        artifact_id: artifact.id,
        project_id: project.id,
        mount_id: 'mount-api',
        target_path: 'docs/architecture.md',
        status: 'delivered',
        has_changes: true,
        unified_diff: '--- a/docs/architecture.md\n+++ b/docs/architecture.md\n@@ -1 +1 @@\n-旧架构\n+新架构\n',
        report: {
          mount_id: 'mount-api',
          target_path: 'docs/architecture.md',
          backup_path: 'docs/architecture.md.agentforge.bak',
          bytes_written: 48,
        },
      }))
      return
    }

    if (method === 'POST' && path === `/api/v1/artifacts/${artifact.id}/delivery/github/preview`) {
      await route.fulfill(json({
        artifact_id: artifact.id,
        project_id: project.id,
        mount_id: 'mount-github',
        target_path: 'docs/architecture.md',
        status: 'previewed',
        has_changes: true,
        unified_diff: '--- a/docs/architecture.md\n+++ b/docs/architecture.md\n@@ -1 +1 @@\n-旧架构\n+GitHub 新架构\n',
        report: {
          delivery_channel: 'github_pr',
          mount_id: 'mount-github',
          repo_full_name: 'acme/shop-api',
          target_path: 'docs/architecture.md',
          base_branch: 'main',
          target_branch: 'agentforge/artifact',
          base_sha: 'base-sha-1',
          target_file_sha: 'file-sha-1',
        },
      }))
      return
    }

    if (method === 'POST' && path === `/api/v1/artifacts/${artifact.id}/delivery/github/apply`) {
      const payload = request.postDataJSON() as Record<string, unknown>
      githubApplyRequests.push(payload)
      deliveredArtifact = {
        ...artifact,
        delivery_status: 'delivered',
        delivery_target_path: 'github://acme/shop-api/docs/architecture.md',
        delivered_at: now,
        delivery_report: {
          delivery_channel: 'github_pr',
          mount_id: 'mount-github',
          repo_full_name: 'acme/shop-api',
          target_path: 'docs/architecture.md',
          base_branch: 'main',
          target_branch: 'agentforge/artifact',
          pr_url: 'https://github.com/acme/shop-api/pull/42',
          commit_sha: 'commit-sha-1',
        },
      }
      await route.fulfill(json({
        artifact_id: artifact.id,
        project_id: project.id,
        mount_id: 'mount-github',
        target_path: 'docs/architecture.md',
        status: 'delivered',
        has_changes: true,
        unified_diff: '--- a/docs/architecture.md\n+++ b/docs/architecture.md\n@@ -1 +1 @@\n-旧架构\n+GitHub 新架构\n',
        report: deliveredArtifact.delivery_report,
      }))
      return
    }

    if (method === 'GET' && path === `/api/v1/artifacts/${artifact.id}/delivery/report`) {
      await route.fulfill({
        status: 200,
        contentType: 'text/markdown',
        body: '# Delivery Report\n\n- Target Path: docs/architecture.md\n- Backup Path: docs/architecture.md.agentforge.bak\n',
      })
      return
    }

    if (method === 'GET' && path === `/api/v1/projects/${project.id}/sessions`) {
      await route.fulfill(json([
        {
          id: 'session-artifact',
          project_id: project.id,
          title: '生成架构方案',
          intent_type: 'new_feature',
          current_pipeline_run_id: null,
          created_at: now,
          updated_at: now,
        },
      ]))
      return
    }

    if (method === 'GET' && path === '/api/v1/sessions/session-artifact/messages') {
      await route.fulfill(json([
        {
          id: 'msg-assistant',
          role: 'assistant',
          content: '架构方案已经生成。',
          task_id: 'task-design',
          extra_data: null,
          artifacts: [artifact],
          created_at: now,
        },
      ]))
      return
    }

    await route.fulfill(json({ detail: `Unhandled ${method} ${path}` }, 404))
  })

  return { applyRequests, githubApplyRequests }
}

test.describe('TASK-016 artifact viewer', () => {
  test('renders project artifacts and opens markdown viewer', async ({ page }) => {
    await login(page)
    await mockArtifactApi(page)

    await page.goto('/projects')

    await expect(page.getByText('最近产物', { exact: true })).toBeVisible()
    await expect(page.getByText('架构设计.md')).toBeVisible()

    await page.getByRole('link', { name: /架构设计\.md/ }).click()

    await expect(page).toHaveURL('/artifacts/artifact-design')
    await expect(page.locator('.artifact-viewer')).toContainText('架构设计')
    await expect(page.locator('.markdown-body')).toContainText('API 使用 FastAPI')
  })

  test('renders chat artifact card and adds it as context', async ({ page }) => {
    await login(page)
    await mockArtifactApi(page)

    await page.goto('/chat/session-artifact')

    await expect(page.locator('.artifact-card')).toContainText('架构设计.md')
    await page.getByRole('button', { name: '加入上下文' }).click()
    await page.getByTitle('高级设置').click()

    await expect(page.locator('.context-chip')).toContainText('产物')
    await expect(page.locator('.context-chip')).toContainText('架构设计.md')
  })

  test('previews delivery diff before confirmed writeback', async ({ page }) => {
    await login(page)
    const api = await mockArtifactApi(page)

    await page.goto('/artifacts/artifact-design')

    await page.getByLabel('目标代码库').selectOption('mount-api')
    await page.getByLabel('写入路径').fill('docs/architecture.md')
    await page.getByRole('button', { name: '预览 Diff' }).click()

    await expect(page.locator('.artifact-viewer__diff')).toContainText('-旧架构')
    await expect(page.locator('.artifact-viewer__diff')).toContainText('+新架构')
    expect(api.applyRequests).toHaveLength(0)

    await page.getByRole('button', { name: '确认写入' }).click()

    expect(api.applyRequests).toHaveLength(1)
    expect(api.applyRequests[0]).toMatchObject({
      mount_id: 'mount-api',
      target_path: 'docs/architecture.md',
      confirm_write: true,
    })
    await expect(page.locator('.artifact-viewer__delivery')).toContainText('已交付')
    await expect(page.locator('.artifact-viewer__delivery')).toContainText('docs/architecture.md.agentforge.bak')

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: '导出报告' }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe('架构设计.md.delivery.md')
  })

  test('previews GitHub PR delivery before creating pull request', async ({ page }) => {
    await login(page)
    const api = await mockArtifactApi(page)

    await page.goto('/artifacts/artifact-design')

    await page.getByRole('button', { name: 'GitHub PR' }).click()
    await page.getByLabel('目标代码库').selectOption('mount-github')
    await page.getByLabel('写入路径').fill('docs/architecture.md')
    await page.getByLabel('交付分支').fill('agentforge/artifact')
    await page.getByLabel('PR 标题').fill('Update architecture artifact')
    await page.getByRole('button', { name: '预览 PR Diff' }).click()

    await expect(page.locator('.artifact-viewer__diff')).toContainText('+GitHub 新架构')
    await expect(page.locator('.artifact-viewer__delivery')).toContainText('acme/shop-api')
    expect(api.githubApplyRequests).toHaveLength(0)

    await page.getByRole('button', { name: '创建 PR' }).click()

    expect(api.githubApplyRequests).toHaveLength(1)
    expect(api.githubApplyRequests[0]).toMatchObject({
      mount_id: 'mount-github',
      target_path: 'docs/architecture.md',
      base_branch: 'main',
      target_branch: 'agentforge/artifact',
      pr_title: 'Update architecture artifact',
      confirm_write: true,
      expected_base_sha: 'base-sha-1',
    })
    await expect(page.locator('.artifact-viewer__delivery')).toContainText('已交付')
    await expect(page.locator('.artifact-viewer__delivery')).toContainText('https://github.com/acme/shop-api/pull/42')
  })
})
