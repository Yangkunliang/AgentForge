"""Embedder — 调用 LiteLLM 生成 embedding，支持内容分块"""

from __future__ import annotations

import logging
from typing import Any

from agent_forge.config import settings

logger = logging.getLogger("agent_forge.memory.embedder")


def _get_embedding_client() -> Any:
    """获取 LiteLLM embedding 客户端（延迟导入避免依赖缺失）"""
    import litellm
    return litellm


def embed(text: str, model: str | None = None) -> list[float]:
    """调用 LiteLLM 生成单段文本 embedding

    Args:
        text: 待嵌入的文本
        model: embedding 模型，默认使用 settings.embedding_model

    Returns:
        embedding 向量（float 列表）
    """
    if not text or not text.strip():
        return []

    model = model or settings.embedding_model
    litellm = _get_embedding_client()

    try:
        response = litellm.embedding(
            model=model,
            input=text,
        )
        # LiteLLM embedding 返回结构: {data: [{embedding: [...]}], model: "..."}
        data = response.get("data", [])
        if not data:
            logger.warning("Empty embedding response for model %s", model)
            return []
        return data[0].get("embedding", [])
    except Exception as e:
        logger.error("Embedding failed for model %s: %s", model, e)
        raise


def embed_chunks(chunks: list[str], model: str | None = None) -> list[list[float]]:
    """批量生成多个 chunk 的 embedding

    Args:
        chunks: 文本片段列表
        model: embedding 模型

    Returns:
        每个 chunk 的 embedding 列表
    """
    return [embed(chunk, model) for chunk in chunks if chunk.strip()]


def chunk_text(text: str, max_size: int | None = None) -> list[str]:
    """将长文本按段落分块

    优先按段落（双换行）分割，超出 max_size 时按字符截断。

    Args:
        text: 输入文本
        max_size: 每块最大字符数，默认 settings.embedding_chunk_size

    Returns:
        分块列表（过滤空块）
    """
    max_size = max_size or settings.embedding_chunk_size

    if not text or not text.strip():
        return []

    if len(text) <= max_size:
        return [text]

    # 优先按段落分割
    paragraphs = text.split("\n\n")

    if len(paragraphs) == 1:
        # 没有段落分隔，按字符截断
        return _split_by_chars(text, max_size)

    # 合并段落到不超过 max_size 的块
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if para_len > max_size:
            # 单段落超长，递归分块
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0
            chunks.extend(_split_by_chars(para, max_size))
            continue

        if current_len + para_len + 2 > max_size and current:
            chunks.append("\n\n".join(current))
            current = [para]
            current_len = para_len
        else:
            current.append(para)
            current_len += para_len + 2

    if current:
        chunks.append("\n\n".join(current))

    return chunks if chunks else [text]


def _split_by_chars(text: str, max_size: int) -> list[str]:
    """按固定字符数截断文本"""
    overlap = min(settings.embedding_chunk_overlap, max_size - 1) if max_size > 1 else 0
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + max_size
        chunk = text[start:end]
        chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks
