"""数据源适配器接口。

新数据源（二期京东读书）只需实现 SourceAdapter 并注册进 SOURCES，
设备端协议无需任何改动 —— 这就是"统一入口"架构的红利。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import BookRecord, BookDetail, SyncStats


@runtime_checkable
class SourceAdapter(Protocol):
    name: str  # "library" | "weread" | ...

    def sync(self) -> SyncStats:
        """拉取该数据源的最新数据并写入 NAS SQLite。返回统计。"""

    def list_books(self) -> list[BookRecord]:
        """该数据源的书架条目（读 NAS 本地缓存，不发网络请求）。"""

    def get_book(self, book_id: str) -> BookDetail | None:
        """详情 + 笔记 + 章节（读 NAS 本地缓存）。"""


SOURCES: dict[str, SourceAdapter] = {}


def register(adapter: SourceAdapter) -> None:
    SOURCES[adapter.name] = adapter


def get(name: str) -> SourceAdapter | None:
    return SOURCES.get(name)