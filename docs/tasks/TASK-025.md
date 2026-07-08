# TASK-025：zip Delivery Package

**状态**：done
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

- [x] 设计 Artifact 到 zip 文件树的映射规则，支持单文件和多文件 manifest
- [x] 新增 zip Delivery preview，展示包内路径、文件数量、总字节数和 sha256
- [x] 新增 zip Delivery apply，生成只读下载包并保存 report
- [x] 下载接口校验 Artifact/Project 权限，不暴露服务器临时路径
- [x] 后端测试覆盖 zip 内容、manifest、sha256、权限隔离和过期清理
- [x] 前端 Artifact Viewer 支持 zip Delivery 下载入口

## acceptance

- [x] zip 不写入用户本地目录或远程仓库
- [x] zip 内路径不能包含绝对路径或 `..`
- [x] Delivery report 能说明包内文件和校验信息

## 实现摘要

- 新增 `agent_forge.delivery.zip_package`，preview 阶段只计算包结构、总字节数和 deterministic zip sha256，不落地下载文件。
- apply 阶段必须显式 `confirm_write=true`，生成 `manifest.json`、`delivery-report.md` 和 `files/<relative path>`，并保存 `delivery_channel=zip` 的 Delivery report。
- zip 下载接口复用 Artifact 所属 Project 权限校验，仅返回服务端包文件流，不在响应或 report 中暴露服务器临时路径。
- 包内路径拒绝空路径、绝对路径、`..`、反斜杠、Windows 盘符、控制字符和重复路径。
- 新增 `DELIVERY_PACKAGE_DIR` 与 `DELIVERY_PACKAGE_TTL_HOURS`，apply 前清理过期 zip，避免无限堆积。
- Artifact Viewer 新增“zip 包”交付模式，支持预览、生成和下载 zip。

## 验证

- `uv run --extra dev pytest tests/api/test_zip_delivery.py`
- `uv run --extra dev pytest tests/api/test_delivery.py tests/api/test_github_delivery.py tests/api/test_zip_delivery.py tests/api/test_github_mount.py`
- `npm run build`
- `npm run test:e2e -- artifact-viewer.spec.ts --project=chromium`
- `uv run --extra dev pytest`
- `PYTHONPATH=/Users/yangkl/AgentForge/src uv run --extra dev uvicorn api.main:app --host 127.0.0.1 --port 18088`

## 不做

- 不做大型制品仓库。
- 不支持后台长期保留无限 zip 文件。
- 不把 upload Mount 当成本地路径处理。
