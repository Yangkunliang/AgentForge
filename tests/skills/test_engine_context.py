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
