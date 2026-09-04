#!/usr/bin/env python3
"""生成模拟器/固件联调用的测试 EPUB。

产出（到 crossmux/test/fixtures/）：
- 测试-中文小说.epub   中文多章节、带目录
- test-english-book.epub 英文多章节、带封面 SVG
- test-cover-book.epub   带内嵌封面图片
"""

import base64
import io
import zipfile
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "test" / "fixtures"
OUT.mkdir(parents=True, exist_ok=True)

# 1x1 白底 PNG 占位封面
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _chapter_xhtml(title: str, paras: list[str]) -> str:
    body = "\n".join(f"<p>{p}</p>" for p in paras)
    return (
        f'<?xml version="1.0" encoding="utf-8"?>\n'
        f'<html xmlns="http://www.w3.org/1999/xhtml">\n<head><title>{title}</title></head>\n'
        f'<body><h1>{title}</h1>{body}</body>\n</html>'
    )


def build_epub(path: Path, title: str, author: str, lang: str, chapters: list[tuple[str, list[str]]],
               cover: bool = False):
    files = {}
    files["mimetype"] = "application/epub+zip"
    files["META-INF/container.xml"] = (
        '<?xml version="1.0"?>\n<container version="1.0" '
        'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
        "</rootfiles></container>"
    )

    manifest = []
    spine = []
    for i, (t, _) in enumerate(chapters):
        name = f"chap{i}.xhtml"
        manifest.append(f'<item id="c{i}" href="{name}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="c{i}"/>')
        files[f"OEBPS/{name}"] = _chapter_xhtml(t, _)

    if cover:
        files["OEBPS/cover.png"] = PNG_1PX
        manifest.append('<item id="cov" href="cover.png" media-type="image/png" properties="cover-image"/>')

    nav = ['<nav xmlns:epub="http://www.idpf.org/2007/ops" epub:type="toc" id="toc"><ol>']
    for i, (t, _) in enumerate(chapters):
        nav.append(f'<li><a href="chap{i}.xhtml">{t}</a></li>')
    nav.append("</ol></nav>")
    files["OEBPS/nav.xhtml"] = (
        '<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops"><head/><body>' + "".join(nav) + "</body></html>"
    )
    manifest.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')

    opf = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">'
        f'<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f'<dc:identifier id="uid">urn:uuid:{abs(hash(path.name))}</dc:identifier>'
        f'<dc:title>{title}</dc:title><dc:creator>{author}</dc:creator><dc:language>{lang}</dc:language>'
        "</metadata>"
        f'<manifest><item id="opf" href="content.opf" media-type="application/oebps-package+xml"/>'
        f'{"".join(manifest)}</manifest>'
        f'<spine toc="nav">{"".join(spine)}</spine></package>'
    )
    files["OEBPS/content.opf"] = opf

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mimetype", files["mimetype"], compress_type=zipfile.ZIP_STORED)
        for name in sorted(k for k in files if k != "mimetype"):
            z.writestr(name, files[name])
    print(f"generated: {path} ({path.stat().st_size} bytes)")


zh_paras = lambda n: [f"这是用于测试的第 {i} 段中文正文内容，用于验证中文排版、自动换行与翻页。"
                      for i in range(n)]

build_epub(OUT / "测试-中文小说.epub", "测试中文小说", "测试作者", "zh",
           [("第一章 起点", zh_paras(20)), ("第二章 发展", zh_paras(20)),
            ("第三章 高潮", zh_paras(20)), ("第四章 结局", zh_paras(20))], cover=True)

build_epub(OUT / "test-english-book.epub", "Test English Book", "Test Author", "en",
           [("Chapter One", [f"Paragraph {i} for English layout testing." for i in range(12)]),
            ("Chapter Two", [f"Paragraph {i} for English layout testing." for i in range(12)]),
            ("Chapter Three", [f"Paragraph {i} for English layout testing." for i in range(12)])])

build_epub(OUT / "test-cover-book.epub", "Cover Book", "Cover Author", "en",
           [("Start", ["Cover test book."])], cover=True)

print("done")
