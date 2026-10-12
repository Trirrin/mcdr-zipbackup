import fnmatch
import os
from typing import List, Optional


def normalize_exclude_pattern(pattern: str) -> Optional[str]:
    """归一化单个排除模式；返回 None 表示无效（为空或为绝对路径）"""
    norm = pattern.replace('\\', '/')
    if norm.startswith('/') or (len(norm) > 1 and norm[0].isalpha() and norm[1] == ':'):
        # 绝对路径无法匹配相对 server_path 的路径
        return None
    while norm.startswith('./'):
        norm = norm[2:]
    norm = norm.strip('/')
    return norm if norm.strip() else None


def should_exclude(target_path: str, server_path: str, exclude_patterns: List[str]) -> bool:
    """检查文件或目录是否应该被排除

    - 不含 '/' 的模式按名称匹配任意层级的文件或目录（如 'recordings', '*.tmp'）
    - 含 '/' 的模式相对 server_path 匹配（需含世界名前缀，如 'world/recordings'），
      同时支持匹配任意父目录下的同路径结构（如 'region/*.mca' 命中 'world/region/' 下的文件）
    - 使用 fnmatchcase 保证各平台一致区分大小写
    """
    if not exclude_patterns:
        return False
    # 统一路径分隔符为 '/' 便于跨平台匹配
    norm_target = os.path.normpath(target_path).replace('\\', '/')
    try:
        rel_to_server = os.path.relpath(target_path, server_path).replace('\\', '/')
    except ValueError:
        # Windows 上跨盘符时无法计算相对路径，退化为绝对路径匹配
        rel_to_server = norm_target
    rel_parts = rel_to_server.split('/')

    for raw_pattern in exclude_patterns:
        norm_pat = normalize_exclude_pattern(raw_pattern)
        if norm_pat is None:
            continue
        if '/' not in norm_pat:
            # 名称模式：匹配任意层级的同名文件或目录
            if any(fnmatch.fnmatchcase(part, norm_pat) for part in rel_parts):
                return True
        else:
            # 路径模式：相对 server_path 匹配，或匹配任意父目录下的同路径结构
            if (fnmatch.fnmatchcase(rel_to_server, norm_pat)
                    or fnmatch.fnmatchcase(rel_to_server, f'{norm_pat}/*')
                    or fnmatch.fnmatchcase(rel_to_server, f'*/{norm_pat}')
                    or fnmatch.fnmatchcase(rel_to_server, f'*/{norm_pat}/*')):
                return True
    return False
