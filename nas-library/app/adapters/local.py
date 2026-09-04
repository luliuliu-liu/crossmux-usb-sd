"""本地 EPUB 书库适配器。

扫描 LIBRARY_ROOT 下的 EPUB 文件，作为"本地书库"数据源。
设备端可从此源下载正文并阅读（has_epub=true）。
"""

from __future__ import annotations

import hashlib
import zipfile
import re
from pathlib import Path
from xml.etree import ElementTree as ET

from .. import config, db
from ..models import BookDetail, BookRecord, SyncStats

NS = {"opf": "http://www.idpf.org/2007/opf", "dc": "http://purl.org/dc/elements/1.1/"}


def _epub_meta(path: Path) -> tuple[str, str]:
    """从 EPUB 的 container.xml → OPF 里提取 (title, author)。"""
    try:
        with zipfile.ZipFile(path) as z:
            container = ET.fromstring(z.read("META-INF/container.xml"))
            rootfile = container.find(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile")
            if rootfile is None:
                return path.stem, ""
            opf_path = rootfile.get("full-path", "")
            opf = ET.fromstring(z.read(opf_path))
            title = opf.findtext("dc:title", default=path.stem, namespaces=NS).strip()
            author = opf.findtext("dc:creator", default="", namespaces=NS).strip()
            return title or path.stem, author
    except Exception:
        return path.stem, ""


class LocalAdapter:
    name = "library"

    def sync(self) -> SyncStats:
        stats = SyncStats(source=self.name, status="ok")
        found: set[str] = set()
        for path in sorted(config.LIBRARY_ROOT.rglob("*.epub")):
            rel = str(path.relative_to(config.LIBRARY_ROOT))
            digest = hashlib.sha1(rel.encode()).hexdigest()[:16]
            book_id = f"lib:{digest}"
            title, author = _epub_meta(path)
            db.upsert_book(
                book_id=book_id,
                source=self.name,
                source_book_id=rel,
                title=title,
                author=author,
                has_epub=True,
                epub_path=str(path),
            )
            found.add(book_id)
            stats.books += 1

        # 清理已被移出书库的条目
        for b in db.list_books(self.name):
            if b["id"] not in found:
                db.delete_book(b["id"])
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
                    has_epub=True,
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
            has_epub=True,
            summary=b["summary"],
        )

    def epub_path(self, book_id: str) -> Path | None:
        b = db.get_book(book_id)
        if not b or b["source"] != self.name or not b["epub_path"]:
            return None
        p = Path(b["epub_path"])
        return p if p.exists() else None


def register() -> None:
    from . import register as _register

    _register(LocalAdapter())