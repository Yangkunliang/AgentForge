<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/project'
import { useSessionStore } from '@/stores/session'
import { useArtifactStore } from '@/stores/artifact'
import { sessionsApi } from '@/api/modules/sessions'
import type { Artifact, Project, ProjectMount, Session } from '@/types'
import { artifactTypeLabel } from '@/utils/artifacts'

const router = useRouter()
const projectStore = useProjectStore()
const sessionStore = useSessionStore()
const artifactStore = useArtifactStore()

const projects = computed(() => projectStore.projects)
const sessionsByProject = ref<Record<string, Session[]>>({})

onMounted(async () => {
  const data = await projectStore.fetchProjects()
  await Promise.all(
    data.map((project) =>
      projectStore.fetchProjectMounts(project.id).catch(() => [])
    )
  )
  await Promise.all(
    data.map((project) =>
      artifactStore.fetchProjectArtifacts(project.id).catch(() => [])
    )
  )
  await Promise.all(
    data.map(async (project) => {
      try {
        const { data: sessions } = await sessionsApi.list(project.id)
        sessionsByProject.value = {
          ...sessionsByProject.value,
          [project.id]: sessions,
        }
      } catch {
        sessionsByProject.value = {
          ...sessionsByProject.value,
          [project.id]: [],
        }
      }
    })
  )
})

// 每种技术栈对应一个语义色（增强对比度）
const tagColorMap: Record<string, { bg: string; color: string; border: string }> = {
  'FastAPI':      { bg: '#dcfce7', color: '#15803d', border: '#86efac' },
  'Django':       { bg: '#dcfce7', color: '#166534', border: '#86efac' },
  'PostgreSQL':   { bg: '#dbeafe', color: '#1e40af', border: '#93c5fd' },
  'MySQL':        { bg: '#dbeafe', color: '#1d4ed8', border: '#93c5fd' },
  'Redis':        { bg: '#fee2e2', color: '#dc2626', border: '#fca5a5' },
  'Vue 3':        { bg: '#dcfce7', color: '#16a34a', border: '#86efac' },
  'React':        { bg: '#dbeafe', color: '#0369a1', border: '#93c5fd' },
  'ECharts':      { bg: '#ffedd5', color: '#c2410c', border: '#fdba74' },
  'WebSocket':    { bg: '#f3e8ff', color: '#7c3aed', border: '#d8b4fe' },
  'TypeScript':   { bg: '#dbeafe', color: '#1e40af', border: '#93c5fd' },
}
function tagColor(tag: string) {
  return tagColorMap[tag] ?? { bg: '#f3f4f6', color: '#374151', border: '#d1d5db' }
}

// 计算活动热度（基于会话次数和最后活跃时间）
function primaryMount(project: Project): ProjectMount | null {
  return projectStore.primaryMountFor(project.id)
}

function isConnected(project: Project): boolean {
  return primaryMount(project)?.status === 'connected'
}

function mountType(project: Project): string {
  return primaryMount(project)?.mount_type ?? 'local'
}

function mountPath(project: Project): string {
  return primaryMount(project)?.locator ?? '尚未挂载代码库'
}

function formatRelative(isoStr: string): string {
  const date = new Date(isoStr)
  if (Number.isNaN(date.getTime())) return '最近更新'
  const diffMs = Date.now() - date.getTime()
  if (diffMs < 60000) return '刚刚'
  if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)} 分钟前`
  if (diffMs < 86400000) return `${Math.floor(diffMs / 3600000)} 小时前`
  if (diffMs < 172800000) return '昨天'
  return `${Math.floor(diffMs / 86400000)} 天前`
}

function getActivityHeat(updatedAt: string): number {
  const diffDays = Math.max(0, (Date.now() - new Date(updatedAt).getTime()) / 86400000)
  return Math.max(0.2, Math.min(1, 1 - diffDays * 0.18))
}

function latestArtifacts(project: Project): Artifact[] {
  return artifactStore.artifactsForProject(project.id).slice(0, 2)
}

function artifactCount(project: Project): number {
  return artifactStore.artifactsForProject(project.id).length
}

function activePipelineSession(project: Project): Session | null {
  return sessionsByProject.value[project.id]?.find((session) => session.current_pipeline_run_id) ?? null
}

function projectNextAction(project: Project) {
  const activeSession = activePipelineSession(project)
  const count = artifactCount(project)

  if (!isConnected(project)) {
    return {
      tone: 'blocked',
      title: '补充代码库连接',
      detail: '主代码库还不可用，先确认本地目录或远程仓库授权。',
      cta: '进入对话',
    }
  }

  if (activeSession) {
    return {
      tone: 'running',
      title: '继续进行中的流水线',
      detail: `当前会话：${activeSession.title}`,
      cta: '继续推进',
    }
  }

  if (count > 0) {
    return {
      tone: 'ready',
      title: '复用最近产物继续推进',
      detail: `已有 ${count} 个阶段产物，可查看、加入上下文或交付。`,
      cta: '继续对话',
    }
  }

  return {
    tone: 'ready',
    title: '生成第一份阶段产物',
    detail: '描述需求后先做意图分类，再进入需求确认和任务拆解。',
    cta: '开始需求',
  }
}

function handleNewProject() {
  router.push('/projects/create')
}

async function handleContinueChat(project: Project) {
  await projectStore.selectProject(project.id)
  await sessionStore.fetchSessions(project.id)
  router.push('/chat')
}
</script>

<template>
  <div class="projects-page">

    <!-- 页头 -->
    <div class="page-header">
      <div>
        <h1 class="page-title">我的项目</h1>
        <p class="page-subtitle">选择一个项目开始对话，Agent 将自动加载代码库上下文</p>
      </div>
      <button class="btn-create" @click="handleNewProject">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
          <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        新建项目
      </button>
    </div>

    <!-- 空状态 -->
    <div v-if="projectStore.loading" class="empty-state">
      <div class="empty-icon">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 12a9 9 0 1 1-6.2-8.56"/>
        </svg>
      </div>
      <h3 class="empty-title">正在加载项目</h3>
      <p class="empty-desc">正在同步你的项目列表和代码库挂载状态</p>
    </div>

    <div v-else-if="projects.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          <line x1="12" y1="11" x2="12" y2="17"/><line x1="9" y1="14" x2="15" y2="14"/>
        </svg>
      </div>
      <h3 class="empty-title">还没有项目</h3>
      <p class="empty-desc">添加你的第一个项目，让 Agent 了解你的代码库，告别每次重复解释背景</p>
      <button class="btn-create" @click="handleNewProject">创建第一个项目</button>
    </div>

    <!-- 项目网格 -->
    <div v-else class="projects-grid">
      <div
        v-for="project in projects"
        :key="project.id"
        class="project-card"
        :class="{ 'project-card--disconnected': !isConnected(project) }"
      >
        <!-- 左侧彩色竖条 — 已连接绿色，未连接灰色 -->
        <div class="card-accent" :class="isConnected(project) ? 'card-accent--on' : 'card-accent--off'"></div>

        <div class="card-inner">
          <!-- 顶部：icon + 名称 + 连接状态 -->
          <div class="card-top">
            <div class="project-avatar">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <div class="project-title-group">
              <h3 class="project-name">{{ project.name }}</h3>
              <p class="project-desc">{{ project.description }}</p>
            </div>
            <div class="connect-badge" :class="isConnected(project) ? 'connect-badge--on' : 'connect-badge--off'">
              <span class="connect-badge__dot"></span>
              {{ isConnected(project) ? '已连接' : '待挂载' }}
            </div>
          </div>

          <!-- 挂载路径 -->
          <div class="mount-row">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path v-if="mountType(project) === 'local'" d="M3 7a2 2 0 0 1 2-2h3l2 2h9a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/>
              <path v-else-if="mountType(project) === 'github'" d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>
              <path v-else d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline v-if="mountType(project) !== 'local' && mountType(project) !== 'github'" points="17 8 12 3 7 8"/><line v-if="mountType(project) !== 'local' && mountType(project) !== 'github'" x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <span class="mount-path">{{ mountPath(project) }}</span>
          </div>

          <div
            class="next-action"
            :class="`next-action--${projectNextAction(project).tone}`"
            data-testid="project-next-action"
          >
            <span class="next-action__label">下一步</span>
            <div class="next-action__body">
              <strong>{{ projectNextAction(project).title }}</strong>
              <span>{{ projectNextAction(project).detail }}</span>
            </div>
          </div>

          <!-- 技术栈标签 -->
          <div class="tech-tags">
            <span
              v-for="tag in project.tech_tags"
              :key="tag"
              class="tech-tag"
              :style="{
                background: tagColor(tag).bg,
                color: tagColor(tag).color,
                borderColor: tagColor(tag).border
              }"
            >{{ tag }}</span>
          </div>

          <div class="artifact-shelf">
            <div class="artifact-shelf__header">
              <span>最近产物</span>
              <span>{{ artifactCount(project) }}</span>
            </div>
            <div v-if="latestArtifacts(project).length > 0" class="artifact-shelf__list">
              <RouterLink
                v-for="artifact in latestArtifacts(project)"
                :key="artifact.id"
                class="artifact-row"
                :to="`/artifacts/${artifact.id}`"
              >
                <span class="artifact-row__type">{{ artifactTypeLabel(artifact.artifact_type) }}</span>
                <span class="artifact-row__name">{{ artifact.name }}</span>
              </RouterLink>
            </div>
            <p v-else class="artifact-shelf__empty">暂无阶段产物</p>
          </div>

          <!-- 底部：meta + 操作 -->
          <div class="card-footer">
            <div class="card-meta">
              <span class="meta-item">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                {{ formatRelative(project.updated_at) }}
              </span>
              <span class="meta-item">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                {{ projectStore.currentProjectId === project.id ? '当前项目' : '可切换' }}
              </span>
              <!-- 活动热度指示器 -->
              <div class="activity-heat" :title="`最近活跃度: ${Math.round(getActivityHeat(project.updated_at) * 100)}%`">
                <div class="heat-bar" :style="{ width: `${getActivityHeat(project.updated_at) * 100}%` }"></div>
              </div>
            </div>
            <div class="card-actions">
              <RouterLink
                v-if="latestArtifacts(project).length > 0"
                class="action-ghost"
                :to="`/artifacts/${latestArtifacts(project)[0].id}`"
                title="查看最近产物"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="8" y1="13" x2="16" y2="13"/>
                </svg>
              </RouterLink>
              <button class="action-primary" @click="handleContinueChat(project)">
                {{ projectNextAction(project).cta }}
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 新建卡片 -->
      <div class="card-new" @click="handleNewProject">
        <div class="card-new__inner">
          <div class="card-new__icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
          </div>
          <span class="card-new__label">新建项目</span>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped lang="scss">
.projects-page {
  padding: 32px 28px;
  max-width: 1080px;
  margin: 0 auto;
}

// ── 页头 ──────────────────────────────────────────────────────
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 28px;
  gap: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
  margin: 0 0 4px;
  letter-spacing: -0.2px;
}

.page-subtitle {
  font-size: 13px;
  color: #9ca3af;
  margin: 0;
}

.btn-create {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #409eff;
  color: #fff;
  border: none;
  border-radius: $border-radius-md;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: background 0.15s, transform 0.1s;

  &:hover { background: #337ecc; }
  &:active { transform: scale(0.98); }
}

// ── 空状态 ────────────────────────────────────────────────────
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 72px 24px;
  text-align: center;
  border: 1.5px dashed #e5e7eb;
  border-radius: $border-radius-lg;
  background: #fafafa;
}

.empty-icon {
  width: 72px;
  height: 72px;
  background: #eff6ff;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #409eff;
  margin-bottom: 18px;
}

.empty-title {
  font-size: 17px;
  font-weight: 600;
  color: #111827;
  margin: 0 0 8px;
}

.empty-desc {
  font-size: 13px;
  color: #9ca3af;
  line-height: 1.7;
  max-width: 340px;
  margin: 0 0 24px;
}

// ── 项目网格 ──────────────────────────────────────────────────
.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
}

// ── 项目卡片 ──────────────────────────────────────────────────
.project-card {
  position: relative;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: $border-radius-lg;
  overflow: hidden;
  display: flex;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);

  &:hover {
    border-color: #3b82f6;
    box-shadow: 0 4px 20px rgba(59, 130, 246, 0.12);
    transform: translateY(-2px);
  }

  &--disconnected {
    opacity: 0.7;
    &:hover { border-color: #d1d5db; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05); transform: none; }
  }
}

// 左侧竖条 — 更宽更明显
.card-accent {
  width: 4px;
  flex-shrink: 0;
  transition: width 0.2s;

  &--on  { background: linear-gradient(180deg, #22c55e 0%, #16a34a 100%); }
  &--off { background: #d1d5db; }

  .project-card:hover &--on { width: 5px; }
}

.card-inner {
  flex: 1;
  padding: 18px 18px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

// ── 卡片顶部 ──────────────────────────────────────────────────
.card-top {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.project-avatar {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3b82f6;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.1);
}

.project-title-group {
  flex: 1;
  min-width: 0;
}

.project-name {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: -0.2px;
}

.project-desc {
  font-size: 12px;
  color: #64748b;
  margin: 0;
  line-height: 1.5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

// ── 连接状态 badge ────────────────────────────────────────────
.connect-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
  letter-spacing: 0.02em;

  &--on {
    background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
    color: #15803d;
    border: 1px solid #86efac;
  }
  &--off {
    background: #f8fafc;
    color: #94a3b8;
    border: 1px solid #e2e8f0;
  }

  &__dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    animation: pulse 2s infinite;

    .connect-badge--on &  { background: #22c55e; }
    .connect-badge--off & { background: #cbd5e1; animation: none; }
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

// ── 挂载路径 ──────────────────────────────────────────────────
.mount-row {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #94a3b8;
}

.mount-path {
  font-size: 11px;
  font-family: 'SF Mono', 'Consolas', 'Monaco', 'Menlo', monospace;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  background: #f8fafc;
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid #f1f5f9;
}

.next-action {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 8px;
  align-items: start;
  padding: 9px 10px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #f8fbff;

  &--blocked {
    border-color: #fed7aa;
    background: #fff7ed;

    .next-action__label {
      color: #c2410c;
      background: #ffedd5;
    }
  }

  &--running {
    border-color: #fde68a;
    background: #fffbeb;

    .next-action__label {
      color: #a16207;
      background: #fef3c7;
    }
  }
}

.next-action__label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 22px;
  padding: 0 7px;
  border-radius: 6px;
  background: #e0f2fe;
  color: #0369a1;
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
}

.next-action__body {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;

  strong {
    color: #0f172a;
    font-size: 13px;
    line-height: 1.35;
  }

  span {
    color: #64748b;
    font-size: 11px;
    line-height: 1.5;
  }
}

// ── 技术栈标签 ────────────────────────────────────────────────
.tech-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tech-tag {
  display: inline-block;
  padding: 3px 9px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  border: 1px solid transparent;
  transition: all 0.15s;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }
}

.artifact-shelf {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px;
  border: 1px solid #e5eefb;
  border-radius: 8px;
  background: #f8fbff;
}

.artifact-shelf__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
}

.artifact-shelf__list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.artifact-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  color: #0f172a;
  text-decoration: none;
  font-size: 12px;

  &:hover .artifact-row__name {
    color: #1d4ed8;
  }
}

.artifact-row__type {
  flex-shrink: 0;
  padding: 1px 5px;
  border-radius: 4px;
  background: #e0f2fe;
  color: #0369a1;
  font-size: 10px;
  font-weight: 700;
}

.artifact-row__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.artifact-shelf__empty {
  margin: 0;
  color: #94a3b8;
  font-size: 11px;
}

// ── 卡片底部 ──────────────────────────────────────────────────
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
  margin-top: auto;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
}

// 活动热度指示器
.activity-heat {
  width: 40px;
  height: 4px;
  background: #e2e8f0;
  border-radius: 2px;
  overflow: hidden;
  position: relative;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(90deg, #f59e0b 0%, #ef4444 100%);
    opacity: 0.3;
  }
}

.heat-bar {
  height: 100%;
  background: linear-gradient(90deg, #22c55e 0%, #f59e0b 50%, #ef4444 100%);
  border-radius: 2px;
  transition: width 0.3s ease-out;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-ghost {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.15s;

  &:hover {
    background: #f8fafc;
    color: #475569;
    border-color: #cbd5e1;
    transform: translateY(-1px);
  }
}

.action-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);

  &:hover {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
    transform: translateY(-1px);
  }
  &:active { transform: translateY(0); }
}

// ── 新建卡片 ──────────────────────────────────────────────────
.card-new {
  border: 2px dashed #cbd5e1;
  border-radius: $border-radius-lg;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  cursor: pointer;
  min-height: 160px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    border-color: #3b82f6;
    background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(59, 130, 246, 0.12);

    .card-new__icon { background: #3b82f6; color: #fff; transform: scale(1.1); }
    .card-new__label { color: #2563eb; font-weight: 600; }
  }

  &__inner {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
  }

  &__icon {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    background: #e2e8f0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #94a3b8;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }

  &__label {
    font-size: 13px;
    color: #64748b;
    transition: all 0.2s;
    font-weight: 500;
  }
}

// ── 响应式 ────────────────────────────────────────────────────
@media (max-width: $breakpoint-mobile) {
  .projects-page { padding: 20px 16px; }
  .projects-grid { grid-template-columns: 1fr; }
  .page-header { flex-direction: column; align-items: flex-start; }
}
</style>
