# 阅读器侧 Agent 工作说明

本文件仅由阅读器侧 Agent 维护，NAS 侧 Agent 不修改。

## 负责范围

- CrossMux 固件与 X3 设备端代码
- 阅读器 UI、Activity 和输入交互
- OPDS/HTTP NAS 客户端
- EPUB 流式下载到 SD 卡
- 阅读器打开已下载内容
- 阅读进度上报协议的客户端实现
- SDL2/WASM 本地模拟器
- 固件构建、刷机前验证

## 不负责范围

- `../nas-server/` 内部实现
- Calibre-Web 二次开发
- 微信读书/京东读书服务端适配器
- NAS 数据库、Dockerfile 和 AMD64 镜像

## 协作约定

- 不修改 `../nas-server/`。
- 优先使用 NAS 侧提供的标准 OPDS 接口。
- OPDS 不足时，依赖 NAS 侧明确提供的稳定 HTTP API；不在此文件记录 NAS 侧运行状态。
- NAS 侧接口变更由 NAS Agent 在 `nas-server/` 自己的文档中记录；阅读器侧只记录已确认使用的接口。
- 不在模拟器和真机验证通过前刷写设备。

## 当前工作状态

- CrossMux 开发仓库：`luliuliu-liu/crossmux-usb-sd`
- 当前目标设备：阅星瞳/Xteink X3（ESP32-C3）
- 本地模拟器：`simulator/simulator.sh`，支持 macOS SDL2
- 当前优先级：等待/确认 NAS 侧 OPDS 契约后，实现阅读器侧统一书库入口
