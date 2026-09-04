"""NAS 书库网关 — FastAPI 入口。

设备端（阅星瞳 X3 / CrossMux fork）是瘦客户端，只认这套 API。
所有数据源（微信读书/本地书库/…）在 NAS 侧收敛为统一书架。

API 一览：
  GET  /api/health                      健康检查
  GET  /api/books?source=               统一书架（多源合并）
  GET  /api/books/{book_id}             详情+笔记+章节
  GET  /api/books/{book_id}/download    下载 EPUB（仅 has_epub=true）
  POST /api/sync                        触发同步 {source: optional}
  POST /api/progress                    进度回传 {book_id, progress}
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import config, db
from .adapters import SOURCES, get as get_adapter
from .adapters import local as local_adapter
from .adapters import weread as weread_adapter
from .models import BookDetail, BookRecord, ProgressUpdate, SyncRequest, SyncStats

app = FastAPI(title="NAS 书库网关", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    db.init()
    local_adapter.register()
    weread_adapter.register()


# --------------------------------------------------------------------------- health

@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "sources": list(SOURCES.keys()),
        "weread_key_configured": bool(config.WEREAD_API_KEY),
    }


# --------------------------------------------------------------------------- books

@app.get("/api/books")
def list_books(source: str | None = None) -> dict:
    """统一书架。source 缺省 = 全部数据源合并。"""
    records: list[BookRecord] = []
    for name in SOURCES:
        if source and name != source:
            continue
        records.extend(SOURCES[name].list_books())
    # 最近阅读优先
    records.sort(key=lambda r: r.read_update_time, reverse=True)
    return {"books": [r.model_dump() for r in records]}


@app.get("/api/books/{book_id}")
def book_detail(book_id: str) -> dict:
    for name in SOURCES:
        detail = SOURCES[name].get_book(book_id)
        if detail:
            return detail.model_dump()
    raise HTTPException(status_code=404, detail="book not found")


@app.get("/api/books/{book_id}/download")
def download_epub(book_id: str):
    """下载 EPUB 正文（仅本地书库源提供）。"""
    adapter = local_adapter.LocalAdapter()
    path = adapter.epub_path(book_id)
    if not path:
        raise HTTPException(status_code=404, detail="no epub available for this book")
    return FileResponse(
        path,
        media_type="application/epub+zip",
        filename=Path(path).name,
    )


# --------------------------------------------------------------------------- sync / progress

class _SyncBody(BaseModel):
    source: str | None = None


@app.post("/api/sync")
def sync(body: _SyncBody | None = None) -> dict:
    """触发同步。source 缺省 = 全部数据源。"""
    source = (body.source if body else None) or None
    results: list[SyncStats] = []
    for name in SOURCES:
        if source and name != source:
            continue
        try:
            results.append(SOURCES[name].sync())
        except Exception as e:  # noqa: BLE001 —— 单个源失败不影响整体
            results.append(SyncStats(source=name, status="error", message=str(e)))
    return {"results": [r.model_dump() for r in results]}


@app.post("/api/progress")
def update_progress(body: ProgressUpdate) -> dict:
    """设备端阅读进度回传。"""
    db.update_progress(body.book_id, body.progress, body.read_update_time)
    return {"status": "ok", "book_id": body.book_id, "progress": body.progress}


# --------------------------------------------------------------------------- run

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)