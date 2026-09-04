"""统一数据模型。

设备端是瘦客户端，只认识这套 JSON 结构。所有数据源(微信读书/本地书库/…
京东读书二期)都必须收敛到 BookRecord / BookDetail 上，设备端不感知来源。

字段刻意贴近 CrossMux WeRead Activity 已解析的 JSON 命名，
设备端可最大程度复用现有渲染与解析代码。
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

# 数据源标识
SourceName = Literal["library", "weread"]  # 二期: "jdread"


class BookRecord(BaseModel):
    """统一书架条目（列表用，字段最精简，RAM 友好）。"""

    id: str                  # 统一 id: "weread:{bookId}" / "lib:{相对路径hash}"
    title: str
    author: str = ""
    category: str = ""
    source: SourceName       # 数据源标识
    has_epub: bool           # 是否有正文可下载（微信读书官方 API 无正文 → False）
    progress: float = 0.0    # 0.0 ~ 1.0，进度回传用
    read_update_time: int = 0  # 最近阅读时间戳(秒)，0 = 未读过
    cover_url: str = ""      # 封面 URL（设备端可选展示）


class NoteRow(BaseModel):
    """划线/想法。"""

    bookmark_id: str = ""
    mark_text: str = ""
    range: str = ""
    chapter_uid: int = 0
    create_time: int = 0


class ChapterRow(BaseModel):
    """章节目录。"""

    chapter_uid: int = 0
    chapter_idx: int = 0
    title: str = ""
    word_count: int = 0
    paid: int = 0


class BookDetail(BaseModel):
    """书籍详情 / 笔记 / 章节（都是从 NAS 拉，设备端只渲染）。"""

    id: str
    title: str
    author: str = ""
    category: str = ""
    source: SourceName
    has_epub: bool
    summary: str = ""
    notes: list[NoteRow] = []
    chapters: list[ChapterRow] = []


class ProgressUpdate(BaseModel):
    """设备端进度回传。"""

    book_id: str
    progress: float           # 0.0 ~ 1.0
    read_update_time: int = 0  # 可选时间戳


class SyncRequest(BaseModel):
    """同步请求：source 缺省 = 全部。"""

    source: Optional[str] = None  # "library" | "weread" | None(=all)


class SyncStats(BaseModel):
    """一次同步的结果统计。"""

    source: str
    status: str            # "ok" | "error"
    books: int = 0
    notes: int = 0
    message: str = ""