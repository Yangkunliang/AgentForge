# TASK-025：zip Delivery Package

**状态**：todo
**优先级**：P2
**创建日期**：2026-07-08
**关联 Epic**：EPIC-CORE-STRENGTHENING
**依赖**：TASK-022

## 目标

当用户不希望平台写入本地或远程仓库时，将 Artifact 导出为可下载 zip 包，包含文件内容、manifest、Delivery report 和校验信息。

## related_requirements

- CDW-07：结果回到项目
- CDW-10：交付方式覆盖本地、远程和兜底上传

## 技术子项

- [ ] 设计 Artifact 到 zip 文件树的映射规则，支持单文件和多文件 manifest
- [ ] 新增 zip Delivery preview，展示包内路径、文件数量、总字节数和 sha256
- [ ] 新增 zip Delivery apply，生成只读下载包并保存 report
- [ ] 下载接口校验 Artifact/Project 权限，不暴露服务器临时路径
- [ ] 后端测试覆盖 zip 内容、manifest、sha256、权限隔离和过期清理
- [ ] 前端 Artifact Viewer 支持 zip Delivery 下载入口

## acceptance

- [ ] zip 不写入用户本地目录或远程仓库
- [ ] zip 内路径不能包含绝对路径或 `..`
- [ ] Delivery report 能说明包内文件和校验信息

## 不做

- 不做大型制品仓库。
- 不支持后台长期保留无限 zip 文件。
- 不把 upload Mount 当成本地路径处理。
