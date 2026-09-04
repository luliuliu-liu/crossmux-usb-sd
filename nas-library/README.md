# NAS 书库网关

统一书库数据源网关：把微信读书（官方 Agent Gateway）、本地 EPUB 书库等
数据源收敛为一个统一书架 API，阅星瞳 X3 / CrossMux fork 设备端只认这套
协议，不感知数据来源。

## 快速开始

```bash
pip install -r requirements.txt

# 微信读书 API Key（可选，https://weread.qq.com/r/weread-skills 扫码获取）
export WEREAD_API_KEY=wrk-xxxxxxxx

# 本地书库目录（把 EPUB 丢进去即可）
export LIBRARY_ROOT=./data/library

# 启动
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 + 数据源列表 |
| GET | `/api/books` | 统一书架（多源合并，`?source=` 过滤） |
| GET | `/api/books/{id}` | 详情 + 笔记 + 章节 |
| GET | `/api/books/{id}/download` | 下载 EPUB（仅本地书库源） |
| POST | `/api/sync` | 触发同步 `{"source": "weread"\|"library"\|null}` |
| POST | `/api/progress` | 进度回传 `{"book_id","progress","read_update_time"}` |

## 数据源

- `library`：扫描 `LIBRARY_ROOT/*.epub`，可下载正文阅读
- `weread`：微信读书官方 Agent Gateway（需 `WEREAD_API_KEY`），
  提供书架/笔记/划线/章节/进度，**无正文下载**（DRM）

## 架构

```
┌──────────────┐   WiFi/HTTP   ┌───────────────────────────────┐
│  阅星瞳 X3     │◄────────────►│ NAS: 书库网关 (FastAPI)         │
│ CrossMux fork │  JSON API    │ /api/books 统一书架(多源合并)    │
│  ├ 书库入口    │              │ /api/books/{id} 详情/笔记/章节   │
│  ├ EPUB 引擎   │              │ /api/books/{id}/download       │
│  └ 笔记视图    │              │ /api/sync /api/progress        │
└──────────────┘              ├───────────────────────────────┤
                               │ weread adapter (官方 gateway)   │
                               │ local adapter  (本地 EPUB 书库)  │
                               │ jdread adapter (二期)           │
                               └───────────────────────────────┘
```
