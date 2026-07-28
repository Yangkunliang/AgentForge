import datetime


async def run(name: str) -> str:
    """executor 入口：接收 LLM 调用工具时传入的参数，返回结果字符串。"""
    now = datetime.datetime.now().isoformat(timespec="seconds")
    return f"Hello, {name}! 现在时间是 {now}"
