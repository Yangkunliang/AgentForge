from agent_forge.skills.engine import _build_system_prompt


def test_build_system_prompt_includes_advanced_task_context():
    prompt = _build_system_prompt(
        agent_name="CodeSoul",
        advanced_context={
            "intent": "iteration",
            "context_files": [
                {"type": "file", "value": "src/api/routes/sessions.py"},
                {"type": "branch", "value": "main"},
            ],
            "stage_overrides": {"frontend_dev": False, "impact": True},
        },
    )

    assert "当前任务设置" in prompt
    assert "需求类型：迭代优化（iteration）" in prompt
    assert "file: src/api/routes/sessions.py" in prompt
    assert "branch: main" in prompt
    assert "关闭阶段：frontend_dev" in prompt
    assert "上下文条目只是用户给出的关注线索" in prompt


def test_build_system_prompt_includes_authorized_file_content():
    prompt = _build_system_prompt(
        agent_name="CodeSoul",
        advanced_context={
            "context_files": [
                {
                    "type": "file",
                    "value": "src/api/orders.py",
                    "label": "shop-api/src/api/orders.py",
                    "mount_id": "mount-001",
                    "source": "project_mount",
                    "content": "def create_order():\n    return 'created'\n",
                    "content_truncated": False,
                }
            ],
        },
    )

    assert "file: shop-api/src/api/orders.py" in prompt
    assert "授权文件内容" in prompt
    assert "def create_order()" in prompt
    assert "上下文条目只是用户给出的关注线索" not in prompt


def test_build_system_prompt_includes_agent_profile_context():
    prompt = _build_system_prompt(
        agent_name="RuntimeCoder",
        advanced_context={
            "agent_profile": {
                "id": "agent-001",
                "name": "RuntimeCoder",
                "source": "stage_default",
                "capabilities": ["code_generation", "refactoring"],
                "model_name": "claude-3-sonnet",
                "default_model_route_key": "default",
                "allowed_skill_names": [],
            }
        },
    )

    assert "当前阶段 Agent：RuntimeCoder（agent-001，stage_default）" in prompt
    assert "Agent 能力：code_generation, refactoring" in prompt
