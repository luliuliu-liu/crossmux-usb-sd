"""微信读书数据源适配器。

对接腾讯官方「微信读书 Skill」Agent Gateway：
  POST https://i.weread.qq.com/api/agent/gateway
  Authorization: Bearer wrk-xxxxx
  body: {api_name, skill_version, ...业务参数}

API Key 在 https://weread.qq.com/r/weread-skills 扫码登录后获取，配置到
WEREAD_API_KEY 环境变量即可。

注意：官方 API 不提供整本正文（DRM），故本源的书籍 has_epub=false，
设备端对这类书只展示 书架/笔记/划线/章节/进度，不可打开阅读。
"""

from __future__ import annotations

import requests

from .. import config, db
from ..models import BookDetail, BookRecord, ChapterRow, NoteRow, SyncStats

# 微信读书官方 Skill 能力对应的 gateway api_name（与 CrossMux 设备端同源）
API_SHELF = "/shelf/sync"            # 书架
API_NOTES = "/book/bookmarklist"     # 划线/想法
API_CHAPTERS = "/book/chapterinfo"   # 章节信息
API_BOOKINFO = "/book/info"          # 书籍详情（备用）


class WereadError(RuntimeError):
    """网关返回的业务错误。"""

    def __init__(self, errcode: int, errmsg: str):
        super().__init__(f"weread errcode={errcode} {errmsg}")
        self.errcode = errcode
        self.errmsg = errmsg


def _post(api_name: str, body: dict) -> dict:
    if not config.WEREAD_API_KEY:
        raise WereadError(-1, "WEREAD_API_KEY 未配置")
    payload = {"api_name": api_name, "skill_version": config.WEREAD_SKILL_VERSION, **body}
    resp = requests.post(
        config.WEREAD_GATEWAY_URL,
        json=payload,
        headers={"Authorization": f"Bearer {config.WEREAD_API_KEY}"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("upgrade_info"):
        raise WereadError(-2, f"skill 版本过旧，需升级: {data['upgrade_info'].get('message', '')}")
    if data.get("errcode", 0) != 0:
        raise WereadError(int(data.get("errcode", -1)), str(data.get("errmsg", data.get("errMsg", "unknown"))))
    return data


class WereadAdapter:
    name = "weread"

    def sync(self) -> SyncStats:
        stats = SyncStats(source=self.name, status="ok")
        try:
            shelf = _post(API_SHELF, {})
        except WereadError as e:
            stats.status = "error"
            stats.message = str(e)
            return stats

        books = shelf.get("books") or []
        for b in books:
            book_id = f"weread:{b['bookId']}"
            db.upsert_book(
                book_id=book_id,
                source=self.name,
                source_book_id=b.get("bookId", ""),
                title=b.get("title", ""),
                author=b.get("author", ""),
                category=b.get("category", ""),
                has_epub=False,
                cover_url="",
                progress=0.0,
                read_update_time=b.get("readUpdateTime", 0),
            )
            stats.books += 1
            # 拉笔记 + 章节（每本书两个请求，失败不中断整体）
            try:
                notes = _post(API_NOTES, {"bookId": b["bookId"]}).get("updated", [])
                db.replace_notes(
                    book_id,
                    [NoteRow(
                        bookmark_id=str(n.get("bookmarkId", "")),
                        mark_text=n.get("markText", ""),
                        range=n.get("range", ""),
                        chapter_uid=int(n.get("chapterUid", 0) or 0),
                        create_time=int(n.get("createTime", 0) or 0),
                    ) for n in notes],
                )
                stats.notes += len(notes)
            except (requests.RequestException, WereadError):
                db.replace_notes(book_id, [])

            try:
                chs = _post(API_CHAPTERS, {"bookId": b["bookId"]}).get("chapters", [])
                db.replace_chapters(
                    book_id,
                    [ChapterRow(
                        chapter_uid=int(c.get("chapterUid", 0) or 0),
                        chapter_idx=int(c.get("chapterIdx", i) or i),
                        title=c.get("title", ""),
                        word_count=int(c.get("wordCount", 0) or 0),
                        paid=int(c.get("paid", 0) or 0),
                    ) for i, c in enumerate(chs)],
                )
            except (requests.RequestException, WereadError):
                db.replace_chapters(book_id, [])
        return stats

    def list_books(self) -> list[BookRecord]:
        out = []
        for b in db.list_books(self.name):
            out.append(
                BookRecord(
                    id=b["id"],
                    title=b["title"],
                    author=b["author"],
                    category=b["category"],
                    source=self.name,
                    has_epub=False,
                    progress=b["progress"],
                    read_update_time=b["read_update_time"],
                    cover_url=b["cover_url"],
                )
            )
        return out

    def get_book(self, book_id: str) -> BookDetail | None:
        b = db.get_book(book_id)
        if not b or b["source"] != self.name:
            return None
        return BookDetail(
            id=b["id"],
            title=b["title"],
            author=b["author"],
            category=b["category"],
            source=self.name,
            has_epub=False,
            summary=b["summary"],
            notes=db.get_notes(book_id),
            chapters=db.get_chapters(book_id),
        )


def register() -> None:
    from . import register as _register

    _register(WereadAdapter())