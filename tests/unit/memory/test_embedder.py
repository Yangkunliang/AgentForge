"""测试 chunk_text 和 embed 函数"""

import pytest
from agent_forge.memory.embedder import chunk_text


def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_short():
    text = "short text"
    assert chunk_text(text) == [text]


def test_chunk_text_exact_size():
    text = "a" * 512  # exactly embedding_chunk_size
    result = chunk_text(text)
    assert result == [text]


def test_chunk_text_long_by_paragraphs():
    text = "para1\n\npara2\n\npara3\n\npara4"
    result = chunk_text(text, max_size=30)
    assert len(result) >= 1
    # Should be split at paragraph boundaries
    for chunk in result:
        assert len(chunk) <= 30


def test_chunk_text_long_by_chars():
    text = "a" * 2000
    result = chunk_text(text, max_size=500)
    assert len(result) >= 3  # 2000/500 = 4 chunks with overlap
    for chunk in result:
        assert len(chunk) <= 500


def test_chunk_text_long_paragraph_recursive():
    """单段落超长时按字符截断"""
    text = "a" * 3000  # 超长单段落
    result = chunk_text(text, max_size=500)
    # Should be split into ~3000/450 ≈ 7 chunks (with overlap)
    assert len(result) >= 3
    total_len = sum(len(c) for c in result)
    assert total_len >= 2500  # 应覆盖大部分内容


def test_chunk_text_with_small_size():
    text = "hello world\n\nfoo bar\n\nbaz"
    result = chunk_text(text, max_size=10)
    # Should handle gracefully
    assert len(result) >= 1
