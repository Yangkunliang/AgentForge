# 核心能力增强任务清单

**日期**：2026-07-08
**Epic**：EPIC-CORE-STRENGTHENING

## 排期原则

核心闭环 MVP 已完成后，后续不是三选一，而是按风险和价值顺序持续增强：

1. **服务端可信交付巩固**：先保证写回用户项目时安全、可审计、可恢复。
2. **核心交互设计复盘**：再让用户清楚知道下一步该做什么。
3. **交付能力扩展**：最后扩到 GitHub PR、zip 和 upload 等更完整场景。

## 用户故事覆盖矩阵

| 用户故事 | 覆盖任务 |
|----------|----------|
| CDW-08：写回必须可审计、可解释、可恢复 | TASK-020 |
| CDW-09：核心工作流下一步动作必须可见 | TASK-021 |
| CDW-10：交付方式覆盖本地、远程和兜底上传 | TASK-022、TASK-023、TASK-024、TASK-025、TASK-026 |

## 任务索引

| 状态 | 任务 | 优先级 | 目标 | 依赖 |
|------|------|--------|------|------|
| done | TASK-020：服务端可信交付巩固 | P0 | preview/apply 一致性、失败落库、审计日志和启动/迁移验证 | TASK-019 |
| done | TASK-021：核心交互设计复盘与关键入口优化 | P1 | Project/Chat/Stage/Artifact/Delivery 下一步动作可见 | TASK-020 |
| done | TASK-022：交付能力扩展设计与实现 | P2 | GitHub PR、zip、upload 等交付扩展设计与拆分 | TASK-021 |
| done | TASK-023：GitHub OAuth Mount 授权底座 | P1 | 用户主动授权 GitHub repo，token 服务端加密存储 | TASK-022 |
| todo | TASK-024：GitHub PR Delivery | P1 | branch、commit、PR、base ref 校验、失败报告和审计 | TASK-023 |
| todo | TASK-025：zip Delivery Package | P2 | 生成可下载 zip、manifest、sha256 和 Delivery report | TASK-022 |
| todo | TASK-026：Upload Mount 上下文兜底 | P2 | 上传文件 manifest、授权读取、ContextPicker 接入 | TASK-022 |

## 依赖图

```text
TASK-019
  -> TASK-020
    -> TASK-021
      -> TASK-022
        -> TASK-023
          -> TASK-024
        -> TASK-025
        -> TASK-026
```

## 防遗忘机制

- TASK-020 已完成；合并 main 后立即开启 TASK-021。
- TASK-021 已完成。
- TASK-022 已完成并拆出 TASK-023～TASK-026；合并 main 后立即开启 TASK-023。
- TASK-023 已完成；合并 main 后立即开启 TASK-024。
