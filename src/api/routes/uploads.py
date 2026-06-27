"""图片上传路由"""
from __future__ import annotations

import uuid
from pathlib import Path, PurePosixPath

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

from middleware.auth import get_current_user
from agent_forge.models import User

router = APIRouter()

# 上传目录（项目根目录下的 uploads/）
UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# 允许的图片类型
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class UploadResponse(BaseModel):
    url: str
    filename: str
    size: int


@router.post("/upload", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> UploadResponse:
    """上传图片，返回访问 URL"""
    # 验证文件类型（初步过滤）
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.content_type}")

    # 读取文件内容
    content = await file.read()

    # 验证文件大小
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"文件过大，最大支持 {MAX_FILE_SIZE // 1024 // 1024}MB")

    # 净化文件名：使用 PurePosixPath 去除路径遍历攻击（如 ../../../etc/passwd.jpg）
    safe_name = PurePosixPath(file.filename or "").name
    if not safe_name:
        raise HTTPException(status_code=400, detail="无效的文件名")

    # 从净化后的文件名提取扩展名，进一步清理
    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else "jpg"
    ext = ext.replace(".", "")  # 防止 ..jpg 等畸形扩展名

    # 魔数验证：确认文件实际内容匹配声称的格式
    MAGIC_HEADERS = {
        b"\xff\xd8\xff": "jpg",
        b"\x89PNG\r\n\x1a\n": "png",
        b"GIF87a": "gif",
        b"GIF89a": "gif",
        b"\x89WEBP": "webp",
    }
    magic_valid = False
    actual_ext = ext
    for magic_bytes, expected_ext in MAGIC_HEADERS.items():
        if content.startswith(magic_bytes):
            magic_valid = True
            actual_ext = expected_ext
            break
    if not magic_valid:
        raise HTTPException(status_code=400, detail="无效的图片文件")

    # 生成唯一文件名
    filename = f"{uuid.uuid4().hex}.{actual_ext}"

    # 保存到 uploads 目录
    filepath = UPLOAD_DIR / filename
    filepath.write_bytes(content)

    # 返回访问 URL
    url = f"/api/v1/uploads/{filename}"

    return UploadResponse(
        url=url,
        filename=filename,
        size=len(content),
    )


@router.get("/uploads/{filename}")
async def get_uploaded_image(filename: str):
    """获取已上传的图片"""
    filepath = UPLOAD_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(filepath)
