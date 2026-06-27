# 此文件已删除
# DockerSandboxExecutor 已移除。KVM 级沙箱已覆盖 Docker 的所有场景。
# 详见 docs/tech-design/INTEGRATION-CUBESANDBOX.md
raise ImportError(
    "DockerSandboxExecutor 已移除。"
    "代码执行隔离统一由 E2B/CubeSandbox 负责（KVM 级隔离）。"
    "参考：docs/tech-design/INTEGRATION-CUBESANDBOX.md"
)
