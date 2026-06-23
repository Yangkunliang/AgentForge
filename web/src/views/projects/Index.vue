<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

interface Project {
  id: string
  name: string
  description: string
  techStacks: string[]
  connected: boolean
  lastActive: string
  sessionCount: number
  mountType: 'local' | 'github' | 'upload'
  mountPath: string
}

const projects = ref<Project[]>([
  {
    id: '1',
    name: '我的电商后端',
    description: '基于 FastAPI 的电商订单管理系统',
    techStacks: ['FastAPI', 'PostgreSQL', 'Redis'],
    connected: true,
    lastActive: '2 小时前',
    sessionCount: 12,
    mountType: 'local',
    mountPath: '~/work/shop-api',
  },
  {
    id: '2',
    name: '客户管理系统',
    description: 'CRM 客户关系管理平台',
    techStacks: ['Vue 3', 'Django', 'MySQL'],
    connected: true,
    lastActive: '昨天',
    sessionCount: 5,
    mountType: 'github',
    mountPath: 'github.com/me/crm',
  },
  {
    id: '3',
    name: '数据可视化大屏',
    description: '实时数据监控展示平台',
    techStacks: ['React', 'ECharts', 'WebSocket'],
    connected: false,
    lastActive: '3 天前',
    sessionCount: 2,
    mountType: 'local',
    mountPath: '~/work/dashboard',
  },
])

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
function getActivityHeat(sessionCount: number, lastActive: string): number {
  const timeMap: Record<string, number> = {
    '小时前': 1,
    '昨天': 0.8,
    '天前': 0.5,
  }
  const timeMultiplier = Object.entries(timeMap).find(([key]) => lastActive.includes(key))?.[1] ?? 0.3
  return Math.min(sessionCount * timeMultiplier * 0.2, 1)
}

function handleNewProject() {
  router.push('/projects/create')
}
function handleContinueChat(_project: Project) {
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
    <div v-if="projects.length === 0" class="empty-state">
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
        :class="{ 'project-card--disconnected': !project.connected }"
      >
        <!-- 左侧彩色竖条 — 已连接绿色，未连接灰色 -->
        <div class="card-accent" :class="project.connected ? 'card-accent--on' : 'card-accent--off'"></div>

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
            <div class="connect-badge" :class="project.connected ? 'connect-badge--on' : 'connect-badge--off'">
              <span class="connect-badge__dot"></span>
              {{ project.connected ? '已连接' : '未连接' }}
            </div>
          </div>

          <!-- 挂载路径 -->
          <div class="mount-row">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path v-if="project.mountType === 'local'" d="M3 7a2 2 0 0 1 2-2h3l2 2h9a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/>
              <path v-else d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>
            </svg>
            <span class="mount-path">{{ project.mountPath }}</span>
          </div>

          <!-- 技术栈标签 -->
          <div class="tech-tags">
            <span
              v-for="tag in project.techStacks"
              :key="tag"
              class="tech-tag"
              :style="{
                background: tagColor(tag).bg,
                color: tagColor(tag).color,
                borderColor: tagColor(tag).border
              }"
            >{{ tag }}</span>
          </div>

          <!-- 底部：meta + 操作 -->
          <div class="card-footer">
            <div class="card-meta">
              <span class="meta-item">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                {{ project.lastActive }}
              </span>
              <span class="meta-item">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                {{ project.sessionCount }} 次对话
              </span>
              <!-- 活动热度指示器 -->
              <div class="activity-heat" :title="`活动热度: ${Math.round(getActivityHeat(project.sessionCount, project.lastActive) * 100)}%`">
                <div class="heat-bar" :style="{ width: `${getActivityHeat(project.sessionCount, project.lastActive) * 100}%` }"></div>
              </div>
            </div>
            <div class="card-actions">
              <button class="action-ghost" title="项目设置">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="3"/>
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                </svg>
              </button>
              <button class="action-primary" @click="handleContinueChat(project)">
                开始对话
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
