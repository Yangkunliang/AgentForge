# my-first-skill

一个 AgentForge Skill 脚手架示例（最小可装）。

## 结构

- `agentforge-skill.yaml` — 技能清单（声明 tools 与 executor 入口）
- `executor.py` — 工具真正执行的代码（`entry_point: executor:run`）

## 使用

1. 编辑 `agentforge-skill.yaml`：补充 `description`、按需增减 `tools`。
2. 在 `executor.py` 的 `run` 函数里实现你的逻辑（参数对应 tools 的 parameters）。
3. 把本目录 push 到 GitHub 公开仓库，即可在 AgentForge 的 Skill 市场被搜索并一键安装。

> 字段约定：最少需声明 1 个 tool，否则安装时会报错。

也可以用 CLI 一键生成自己的脚手架：

```bash
python -m agent_forge.cli skill init <你的skill名> -o ./skills
```
