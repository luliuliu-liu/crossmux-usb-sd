#!/usr/bin/env python3
"""本地 OPDS 2.0 测试服务器 — 供 CrossMux 模拟器离线验证 OPDS 链路。

用法：
    python3 scripts/opds_test_server.py [--port 8084] [--dir ../test/fixtures]

提供：
    /opds               目录根（book 列表，直接列出 fixtures 下的 EPUB）
    /books/<文件名>.epub  EPUB 下载

模拟器里把 OPDS 服务器配成 http://127.0.0.1:8084/opds 即可。
生成标准的 OPDS 1.2/2.0 兼容 Atom feed（title/author/link rel=acquisition）。
"""

import argparse
import html
import http.server
import os
import urllib.parse
from pathlib import Path

OPDS_NS = "http://opds-spec.org/2010/catalog"
ATOM_NS = "http://www.w3.org/2005/Atom"
DC_NS = "http://purl.org/dc/terms/"


def _book_meta(path: Path):
    """极简元数据：从文件名推断 title/author（测试够用）。"""
    stem = path.stem
    if " - " in stem:
        author, title = stem.split(" - ", 1)
    else:
        author, title = "", stem
    return title, author


class OpdsHandler(http.server.BaseHTTPRequestHandler):
    fixtures_dir: Path = None  # type: ignore[assignment]

    def log_message(self, fmt, *args):
        print(f"[opds-test] {self.address_string()} {fmt % args}")

    def _send_xml(self, body: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "application/atom+xml;charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)

        if path == "/opds" or path == "/opds/":
            self._serve_root()
        elif path.startswith("/books/"):
            self._serve_book(Path(path.removeprefix("/books/")))
        elif path == "/healthz":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_root(self):
        entries = []
        for epub in sorted(self.fixtures_dir.glob("*.epub")):
            title, author = _book_meta(epub)
            href = f"books/{urllib.parse.quote(epub.name)}"
            author_xml = f"<author><name>{html.escape(author)}</name></author>" if author else ""
            entries.append(
                f'<entry><title>{html.escape(title)}</title>{author_xml}'
                f'<id>urn:uuid:{epub.stem}</id>'
                f'<link rel="http://opds-spec.org/acquisition" type="application/epub+zip" '
                f'href="{html.escape(href)}"/></entry>'
            )
        body = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            f'<feed xmlns="{ATOM_NS}" xmlns:dc="{DC_NS}">'
            "<id>urn:uuid:local-test</id><title>CrossMux Local Test Shelf</title>"
            f'<link rel="self" href="/opds"/>{"".join(entries)}</feed>'
        ).encode("utf-8")
        self._send_xml(body)

    def _serve_book(self, rel: Path):
        # 防路径穿越
        full = (self.fixtures_dir / rel.name).resolve()
        if not str(full).startswith(str(self.fixtures_dir.resolve())) or not full.exists():
            self.send_response(404)
            self.end_headers()
            return
        data = full.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/epub+zip")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8084)
    parser.add_argument("--dir", type=str, default=None,
                        help="EPUB 目录（默认 crossmux/test/fixtures）")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent
    fixtures = Path(args.dir).resolve() if args.dir else (base / "test" / "fixtures").resolve()
    if not fixtures.exists():
        print(f"EPUB dir not found: {fixtures}")
        raise SystemExit(1)

    OpdsHandler.fixtures_dir = fixtures
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), OpdsHandler)
    print(f"OPDS test server on http://127.0.0.1:{args.port}/opds")
    print(f"serving: {fixtures}")
    server.serve_forever()


if __name__ == "__main__":
    main()
