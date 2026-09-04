#pragma once

#include <ArduinoJson.h>

#include <string>

/**
 * NAS 书库网关客户端。
 *
 * 以统一入口的形态访问 NAS 网关：设备端只认识这一套协议，
 * 不感知书架数据来自微信读书还是本地书库。
 *
 * 端点约定（与 nas-library 服务一致）：
 *   GET  /api/books
 *   GET  /api/books/{id}
 *   GET  /api/books/{id}/download
 *   POST /api/sync
 *   POST /api/progress
 *
 * fetch 为同步阻塞调用，Activity 应在独立 FreeRTOS 任务中调用，
 * 保证主渲染循环不被阻塞。
 */
namespace NasClient {

enum class Err {
  Ok = 0,
  NoWifi,       // WiFi.status() != WL_CONNECTED
  NoServer,     // NasConfigStore 未配置地址
  Http,         // TCP / TLS / 非 200
  Parse,        // body 不是合法 JSON
};

/**
 * GET /api/books，书架列表写入 outResp（{"books":[...]}）。
 * `filter` 非空时用 ArduinoJson Filter 只保留需要的字段。
 */
Err getShelf(JsonDocument& outResp, const JsonDocument* filter = nullptr);

/**
 * GET /api/books/{id}，书详情（含 notes / chapters）写入 outResp。
 * `filter` 同上。
 */
Err getBook(const std::string& bookId, JsonDocument& outResp, const JsonDocument* filter = nullptr);

/**
 * POST /api/sync，触发 NAS 侧同步。body 为请求体（可空）。
 * 响应（{"results":[...]}）写入 outResp。
 */
Err syncAll(JsonDocument& outResp);

/**
 * 构造书籍 EPUB 下载 URL。由调用方配合 HttpDownloader::downloadToFile
 * 使用，流式写盘，避免整本书进内存。
 */
std::string downloadUrl(const std::string& bookId);

/** Err → 可读名称（用于日志）。 */
const char* errorName(Err err);

}  // namespace NasClient