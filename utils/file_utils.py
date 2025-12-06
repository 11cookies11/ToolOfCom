from __future__ import annotations

from pathlib import Path
from typing import Dict


def get_file_meta(ctx) -> Dict[str, object]:
    """从上下文获取文件路径并返回元信息（大小、块数）。"""
    path = ctx.vars.get("file_path") or ctx.vars.get("file") or ctx.vars.get("path")
    if not path:
        raise ValueError("未提供 file_path")
    file_path = Path(path)
    size = file_path.stat().st_size
    block_count = (size + 127) // 128
    return {"path": str(file_path), "size": size, "block_count": block_count}


def read_block(path: str, block_no: int, block_size: int = 128) -> bytes:
    """读取指定块号（从1开始），不足补0x1A。"""
    file_path = Path(path)
    offset = (block_no - 1) * block_size
    data = b""
    with file_path.open("rb") as f:
        f.seek(offset)
        data = f.read(block_size)
    if len(data) < block_size:
        data = data + b"\x1A" * (block_size - len(data))
    return data
