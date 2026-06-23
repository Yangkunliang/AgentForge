export type IntentType = 'new_feature' | 'iteration' | 'ui_adjust' | 'bug_fix'

export interface Stage {
  id: string
  label: string
  optional?: boolean
}

export interface IntentConfig {
  stages: Stage[]
  skippedStages: string[]
  quickActions: Array<{ id: string; label: string; prompt: string; highlighted?: boolean }>
  placeholder: string
}

const pipelineConfig: Record<IntentType, IntentConfig> = {
  new_feature: {
    stages: [
      { id: 'analysis', label: '需求分析' },
      { id: 'design', label: '架构设计' },
      { id: 'db_api', label: 'DB & API' },
      { id: 'task_split', label: '任务拆解' },
      { id: 'ui_prototype', label: 'UI 原型' },
      { id: 'backend_dev', label: '后端开发' },
      { id: 'frontend_dev', label: '前端开发' },
      { id: 'testing', label: '测试交付' },
    ],
    skippedStages: [],
    quickActions: [
      { id: 'define_scope', label: '定义需求范围', prompt: '帮我梳理这个新功能的需求范围和验收标准。', highlighted: true },
      { id: 'tech_design', label: '技术方案设计', prompt: '帮我设计这个功能的技术方案，包括架构图和关键类设计。' },
      { id: 'api_design', label: 'API 接口设计', prompt: '帮我设计这个功能的 RESTful API 接口规范。' },
      { id: 'estimate', label: '工作量评估', prompt: '帮我评估实现这个功能所需的时间和资源。' },
    ],
    placeholder: '描述你的新功能需求，例如：添加用户权限管理模块...',
  },
  iteration: {
    stages: [
      { id: 'diff', label: '需求 Diff' },
      { id: 'impact', label: '影响评估', optional: true },
      { id: 'backend_dev', label: '后端开发' },
      { id: 'frontend_dev', label: '前端开发', optional: true },
      { id: 'regression', label: '回归测试' },
    ],
    skippedStages: [],
    quickActions: [
      { id: 'analyze_diff', label: '分析需求变更', prompt: '帮我分析这次需求变更的具体内容和影响范围。', highlighted: true },
      { id: 'code_review', label: '代码审查', prompt: '帮我审查这次变更涉及的代码，确保质量。' },
      { id: 'risk_assess', label: '风险评估', prompt: '帮我评估这次迭代可能带来的风险和应对措施。' },
    ],
    placeholder: '描述你的迭代需求，例如：优化订单列表加载性能...',
  },
  ui_adjust: {
    stages: [
      { id: 'prototype_diff', label: '原型 Diff' },
      { id: 'frontend_dev', label: '前端开发' },
      { id: 'visual', label: '视觉验收' },
    ],
    skippedStages: ['需求分析', '架构设计', '后端开发'],
    quickActions: [
      { id: 'design_spec', label: '设计规范', prompt: '帮我制定这个 UI 调整的设计规范和交互细节。', highlighted: true },
      { id: 'component_build', label: '组件开发', prompt: '帮我实现这个 UI 组件，包括响应式适配。' },
      { id: 'style_refine', label: '样式优化', prompt: '帮我优化这个页面的样式和视觉效果。' },
    ],
    placeholder: '描述你的 UI 调整需求，例如：修改首页布局，增加暗色模式...',
  },
  bug_fix: {
    stages: [
      { id: 'locate', label: '问题定位' },
      { id: 'impact_scope', label: '影响范围分析' },
      { id: 'fix', label: '修复' },
      { id: 'regression', label: '回归测试' },
    ],
    skippedStages: ['需求分析', '架构设计', 'UI 原型'],
    quickActions: [
      { id: 'debug_log', label: '日志分析', prompt: '帮我分析这段错误日志，找出问题根源。', highlighted: true },
      { id: 'reproduce', label: '复现步骤', prompt: '帮我梳理这个 Bug 的复现步骤和条件。' },
      { id: 'fix_verify', label: '修复验证', prompt: '帮我验证这个修复是否正确，有无遗漏。' },
    ],
    placeholder: '描述你的 Bug 或重构需求，例如：修复登录页面输入框验证问题...',
  },
}

export function usePipeline() {
  function getConfig(intent: IntentType): IntentConfig {
    return pipelineConfig[intent]
  }

  const intentLabels: Record<IntentType, { label: string; icon: string }> = {
    new_feature: { label: '全新功能', icon: '✨' },
    iteration: { label: '迭代优化', icon: '🔄' },
    ui_adjust: { label: 'UI 调整', icon: '🎨' },
    bug_fix: { label: 'Bug 修复', icon: '🐛' },
  }

  return {
    getConfig,
    intentLabels,
    pipelineConfig,
  }
}
