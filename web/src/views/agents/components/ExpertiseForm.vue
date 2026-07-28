<script setup lang="ts">
import { reactive, ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { AgentExpertise } from '@/types'
import { agentsApi } from '@/api/modules/agents'
import StringListEditor from './StringListEditor.vue'
import KeyedGroupEditor from './KeyedGroupEditor.vue'

const props = defineProps<{ modelValue?: AgentExpertise }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: AgentExpertise): void }>()

const state = reactive({
  role_title: '',
  summary: '',
  communication_style: '',
  conventions: {} as Record<string, string[]>,
  review_checklist: [] as string[],
  tech_preferences: {} as Record<string, string[]>,
  anti_patterns: [] as string[],
  debugging_heuristics: [] as string[],
})

// AI 辅助抽取相关状态
const extracting = ref(false)
const sourceText = ref('')
const roleHint = ref('')

onMounted(() => {
  const e = props.modelValue || {}
  state.role_title = e.role_title || ''
  state.summary = e.summary || ''
  state.communication_style = e.communication_style || ''
  state.conventions = e.conventions || {}
  state.review_checklist = e.review_checklist || []
  state.tech_preferences = e.tech_preferences || {}
  state.anti_patterns = e.anti_patterns || []
  state.debugging_heuristics = e.debugging_heuristics || []
})

watch(
  state,
  () => {
    emit('update:modelValue', {
      role_title: state.role_title || undefined,
      summary: state.summary || undefined,
      communication_style: state.communication_style || undefined,
      conventions: state.conventions,
      review_checklist: state.review_checklist,
      tech_preferences: state.tech_preferences,
      anti_patterns: state.anti_patterns,
      debugging_heuristics: state.debugging_heuristics,
    })
  },
  { deep: true },
)

// 把 LLM 抽取的草稿合并进表单：已有值优先，新信号追加而非覆盖
function applyDraft(d: AgentExpertise) {
  if (d.role_title) state.role_title = d.role_title
  if (d.summary) state.summary = d.summary
  if (d.communication_style) state.communication_style = d.communication_style
  if (d.conventions && Object.keys(d.conventions).length) {
    state.conventions = { ...state.conventions, ...d.conventions }
  }
  if (d.review_checklist?.length) {
    state.review_checklist = [...new Set([...state.review_checklist, ...d.review_checklist])]
  }
  if (d.tech_preferences && Object.keys(d.tech_preferences).length) {
    state.tech_preferences = { ...state.tech_preferences, ...d.tech_preferences }
  }
  if (d.anti_patterns?.length) {
    state.anti_patterns = [...new Set([...state.anti_patterns, ...d.anti_patterns])]
  }
  if (d.debugging_heuristics?.length) {
    state.debugging_heuristics = [
      ...new Set([...state.debugging_heuristics, ...d.debugging_heuristics]),
    ]
  }
}

async function onExtract() {
  if (sourceText.value.trim().length < 20) {
    ElMessage.warning('请至少粘贴 20 字以上的工作素材（PR review / 提交记录 / 技术讨论）')
    return
  }
  extracting.value = true
  try {
    const res = await agentsApi.extractExpertise({
      source_text: sourceText.value,
      role_hint: roleHint.value || undefined,
    })
    applyDraft(res.data)
    ElMessage.success('已根据素材蒸馏出专家模型草稿，请检查后保存')
  } catch (e: any) {
    ElMessage.error(e?.message || '抽取失败，请重试')
  } finally {
    extracting.value = false
  }
}
</script>

<template>
  <div class="expertise-form">
    <el-card shadow="never" class="ef-extract">
      <template #header>
        <div class="ef-extract__header">
          <span>🪄 AI 辅助抽取</span>
          <el-tag size="small" type="info">把你的经验一键蒸馏成草稿</el-tag>
        </div>
      </template>
      <el-input
        v-model="sourceText"
        type="textarea"
        :rows="6"
        placeholder="粘贴你的真实工作素材：代码评审意见（PR review）、提交记录、技术讨论、编码规范等。越具体，蒸馏出的标准越贴近你。"
      />
      <div class="ef-extract__row">
        <el-input
          v-model="roleHint"
          class="ef-extract__hint"
          placeholder="可选：角色提示，如「资深全栈工程师，偏工程化」"
        />
        <el-button
          type="primary"
          :loading="extracting"
          @click="onExtract"
        >
          {{ extracting ? '蒸馏中…' : 'AI 抽取为草稿' }}
        </el-button>
      </div>
      <p class="ef-extract__tip">
        抽取结果会合并进下方表单（不覆盖你已填写的内容）。确认无误后，在 Agent 编辑页点击「保存」即可持久化。
      </p>
    </el-card>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="专家模型（能力蒸馏）"
      description="填写你的工程标准、审查清单与技术偏好。保存后，Agent 在每个阶段执行时都会按这些标准推理——这是把你的判断力灌进 Agent 的核心入口。"
    />

    <el-form label-width="120px" class="ef-form">
      <el-form-item label="角色定位">
        <el-input v-model="state.role_title" placeholder="如：资深全栈工程师 / 后端架构师" />
      </el-form-item>

      <el-form-item label="能力概述">
        <el-input
          v-model="state.summary"
          type="textarea"
          :rows="3"
          placeholder="一句话概括你的经验与强项，例如：10 年 Web 全栈，偏工程化与可观测性"
        />
      </el-form-item>

      <el-form-item label="编码规范">
        <KeyedGroupEditor
          v-model="state.conventions"
          placeholder="如：函数用 camelCase"
          add-label="添加规范分类"
        />
      </el-form-item>

      <el-form-item label="代码审查必查项">
        <StringListEditor
          v-model="state.review_checklist"
          placeholder="如：空指针 / 边界条件、SQL 注入风险"
          add-label="添加审查项"
        />
      </el-form-item>

      <el-form-item label="技术栈偏好">
        <KeyedGroupEditor
          v-model="state.tech_preferences"
          placeholder="如：FastAPI"
          add-label="添加偏好分类"
        />
      </el-form-item>

      <el-form-item label="反模式 / 雷区">
        <StringListEditor
          v-model="state.anti_patterns"
          placeholder="如：不要在循环里查数据库"
          add-label="添加反模式"
        />
      </el-form-item>

      <el-form-item label="调试套路">
        <StringListEditor
          v-model="state.debugging_heuristics"
          placeholder="如：先看日志和复现步骤，再二分定位改动"
          add-label="添加调试经验"
        />
      </el-form-item>

      <el-form-item label="输出风格">
        <el-input
          v-model="state.communication_style"
          type="textarea"
          :rows="2"
          placeholder="如：结论先行，给可复制的命令"
        />
      </el-form-item>
    </el-form>
  </div>
</template>

<style scoped lang="scss">
.expertise-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.ef-extract {
  &__header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
  }
  &__row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 12px;
  }
  &__hint {
    flex: 1;
  }
  &__tip {
    margin: 10px 0 0;
    font-size: 12px;
    color: var(--el-text-color-secondary);
    line-height: 1.6;
  }
}
.ef-form {
  margin-top: 4px;
  :deep(.el-form-item__content) {
    max-width: 720px;
  }
}
</style>
