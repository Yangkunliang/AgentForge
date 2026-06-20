# TASK-004 任务清单

## 任务概述

实现 Skill 管理 API、Dashboard API、费用统计 API 和数据导出 API。

## 任务拆解

### 阶段 1：Skill 管理 API

| # | 任务 | 优先级 | 状态 |
|---|------|--------|------|
| 1.1 | 实现 Skill 安装 API（POST /api/v1/skills/install） | 高 | ⬜ |
| 1.2 | 实现安装进度查询 API（GET /api/v1/skills/install/{install_id}） | 高 | ⬜ |
| 1.3 | 实现已安装 Skill 列表 API（GET /api/v1/skills） | 高 | ⬜ |
| 1.4 | 实现 Skill 卸载 API（DELETE /api/v1/skills/{skill_name}） | 高 | ⬜ |

### 阶段 2：Dashboard API

| # | 任务 | 优先级 | 状态 |
|---|------|--------|------|
| 2.1 | 实现 Dashboard 概览 API（GET /api/v1/dashboard） | 高 | ⬜ |
| 2.2 | 实现任务统计聚合 | 高 | ⬜ |
| 2.3 | 实现费用趋势计算 | 高 | ⬜ |

### 阶段 3：费用统计 API

| # | 任务 | 优先级 | 状态 |
|---|------|--------|------|
| 3.1 | 实现每日费用查询 API（GET /api/v1/cost） | 高 | ⬜ |
| 3.2 | 实现模型费用分布统计 | 高 | ⬜ |

### 阶段 4：数据导出 API

| # | 任务 | 优先级 | 状态 |
|---|------|--------|------|
| 4.1 | 实现发起导出 API（POST /api/v1/exports） | 高 | ⬜ |
| 4.2 | 实现导出状态查询 API（GET /api/v1/exports/{export_id}） | 高 | ⬜ |
| 4.3 | 实现导出文件下载 API（GET /api/v1/exports/{export_id}/download） | 高 | ⬜ |
| 4.4 | 实现数据脱敏逻辑 | 中 | ⬜ |

### 阶段 5：测试与文档

| # | 任务 | 优先级 | 状态 |
|---|------|--------|------|
| 5.1 | 编写单元测试 | 高 | ⬜ |
| 5.2 | 更新 README.md 迭代状态 | 中 | ⬜ |
| 5.3 | 提交代码 | 中 | ⬜ |

## 验收标准

- ✅ Skill API 支持异步安装和进度追踪
- ✅ Dashboard API 返回完整的统计数据
- ✅ 费用统计 API 精确追踪各模型成本
- ✅ 导出 API 支持 JSONL 格式和数据脱敏
- ✅ 所有 API 通过单元测试（覆盖率 > 80%）