# TASK-026：Upload Mount 上下文兜底

**状态**：todo
**优先级**：P2
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-STRENGTHENING
**依赖**：TASK-022

## 目标

为无法连接本地目录或 GitHub 的用户提供手动上传关键文件的兜底 Mount。Upload Mount 只代表用户主动上传的文件集合，不推断本地路径，也不允许写回用户机器。

## related_requirements

- CDW-02：代码库访问必须用户主动授权
- CDW-06：Agent 能读取用户授权的真实代码库上下文
- CDW-10：交付方式覆盖本地、远程和兜底上传

## 技术子项

- [ ] 新增 upload Mount 文件上传 API，保存文件 manifest、大小、MIME、sha256 和相对路径
- [ ] Bridge 文件列表/读取支持 `mount_type=upload`，读取范围限定在上传 manifest 内
- [ ] ContextPicker 支持浏览 upload Mount 文件
- [ ] 上传文件大小、数量和扩展名限制可配置，并有用户可读错误
- [ ] 后端测试覆盖路径穿越、跨用户隔离、manifest 缺失、超限和 UTF-8 文本读取
- [ ] 前端创建/管理 Project Mount 时支持 upload 兜底方式

## acceptance

- [ ] upload Mount 不访问用户本地路径
- [ ] Agent 只能读取用户上传且属于当前 Project 的文件
- [ ] 审计日志记录上传、读取和删除，不记录文件内容

## 不做

- 不实现浏览器目录后台同步。
- 不把 upload Mount 用作写回目标。
- 不长期保存用户未关联 Project 的临时文件。
