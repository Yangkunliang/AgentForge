# TASK-050 产品需求：授权工作区执行器

## 背景

TASK-049 已把 `task_split` 升级为结构化 TaskGraph，但 TaskNode 仍只是计划。现有 Artifact Delivery 只能把单个 Artifact 写到单个路径，缺少 TaskNode 归属、多文件 Patch、统一基线校验和失败回滚，不能作为开发阶段的可靠执行事实源。

## 用户目标

全栈开发工程师可以在真正写入代码库前检查一个 TaskNode 将修改哪些文件和具体 diff；确认后，平台只在该项目已授权的主代码库内应用变更，并能回答每个文件的基线、结果、备份和失败恢复情况。

## 范围

- 一个 TaskNode 可创建多个版本的 `WorkspaceChangeSet`，每个版本包含多个 `FilePatch`。
- Patch 路径必须在 TaskNode 的 `target_files` 中，且必须通过 Agent Bridge 路径和敏感文件校验。
- 第一版只允许写入同 Project 的 `connected + local + primary` Mount。
- Preview 读取当前文件基线、生成 unified diff 并持久化，不写文件。
- Apply 必须显式确认，并在任何写入前重新校验全部文件基线。
- 多文件正常失败时回滚已经写入的文件，并保存结构化 ApplyReport。
- Preview、拒绝、冲突、失败和成功均写入不含源码正文的 AuditLog。
- 所有读取 API 按当前用户隔离。

## 非目标

- 不执行测试、构建或 lint 命令；由 TASK-051 VerificationGate 负责。
- 不根据 ApplyReport 自动推进 Pipeline 或完成 TaskNode；由 TASK-052 PipelineOrchestrator 负责。
- 不写 GitHub、Upload、reference 或 docs Mount；远程 PR 继续使用现有 GitHub Delivery。
- 不支持删除文件、重命名文件或二进制文件；第一版只支持 UTF-8 文本 create/update。
- 不让 LLM 直接获得任意 filesystem 或 shell 权限。

## 验收标准

1. 当前用户可以为所属 TaskNode 和 writable Mount 创建多文件 Preview，响应包含稳定 change_set id、每个文件的 diff 和基线指纹。
2. 跨用户、跨 Project、非 primary、非 local、非 connected Mount 均被拒绝。
3. 未声明在 `TaskNode.target_files` 中的路径、敏感路径、重复路径、超限内容均被拒绝且不生成半成品。
4. 未确认 Apply 不写文件；任一基线变化时全部文件都不写并返回 409。
5. 多文件 Apply 成功后返回不含源码正文的 ApplyReport；正常写入异常会回滚已写文件并记录失败报告。
6. 已 applied 的 ChangeSet 重试返回原报告，不重复写盘；failed ChangeSet 必须重新 Preview。

