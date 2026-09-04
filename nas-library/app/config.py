"""NAS 书库网关配置。

所有配置均可通过环境变量覆盖，便于在 NAS 上以 Docker/Systemd 方式部署：

- LIBRARY_ROOT: 本地 EPUB 书库根目录（local adapter 扫描）
- WEREAD_API_KEY: 微信读书 Agent Gateway 的 wrk- 密钥
- DATA_DIR: SQLite 数据库与缓存放目录
"""

from __future__ import annotations

import os
from pathlib import Path

# 项目根
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据目录（数据库、缓存）
DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 本地书库根目录
LIBRARY_ROOT = Path(os.environ.get("LIBRARY_ROOT", str(DATA_DIR / "library")))
LIBRARY_ROOT.mkdir(parents=True, exist_ok=True)

# SQLite 数据库
DB_PATH = Path(os.environ.get("DB_PATH", str(DATA_DIR / "library.db")))

# 微信读书 gateway
WEREAD_API_KEY = os.environ.get("WEREAD_API_KEY", "")
WEREAD_GATEWAY_URL = os.environ.get("WEREAD_GATEWAY_URL", "https://i.weread.qq.com/api/agent/gateway")
WEREAD_SKILL_VERSION = "1.0.3"  # 需与微信读书官方 Skill 版本对齐

# 启用哪些数据源（逗号分隔）
ENABLED_SOURCES = os.environ.get("ENABLED_SOURCES", "library,weread").split(",")