#include "NasClient.h"

#include <Arduino.h>
#include <Logging.h>
#include <WiFi.h>

#include "NasConfigStore.h"
#include "network/HttpDownloader.h"

namespace NasClient {

namespace {
// 拼接 URL：去除尾部斜杠后接路径。Base 已被 NasConfigStore 校验为
// http(s)://host[:port] 无尾部斜杠。
std::string join(const std::string& base, const char* path) {
  std::string url = base;
  url += path;
  return url;
}
}  // namespace

Err getShelf(JsonDocument& outResp, const JsonDocument* filter) {
  if (WiFi.status() != WL_CONNECTED) return Err::NoWifi;
  const std::string base = NasConfigStore::load();
  if (base.empty()) return Err::NoServer;

  const std::string url = join(base, "/api/books");
  bool parseFailed = false;
  const bool ok = HttpDownloader::getJson(
      url,
      [&](Stream& bodyStream) {
        const bool useFilter = filter != nullptr && filter->size() > 0;
        const DeserializationError err =
            useFilter ? deserializeJson(outResp, bodyStream, DeserializationOption::Filter(*filter))
                      : deserializeJson(outResp, bodyStream);
        if (err) {
          LOG_ERR("NAS", "getShelf parse error: %s", err.c_str());
          parseFailed = true;
          return false;
        }
        return true;
      },
      /*timeoutMs=*/10000);
  if (!ok) return parseFailed ? Err::Parse : Err::Http;
  return Err::Ok;
}

Err getBook(const std::string& bookId, JsonDocument& outResp, const JsonDocument* filter) {
  if (WiFi.status() != WL_CONNECTED) return Err::NoWifi;
  const std::string base = NasConfigStore::load();
  if (base.empty()) return Err::NoServer;

  const std::string url = join(base, ("/api/books/" + bookId).c_str());
  bool parseFailed = false;
  const bool ok = HttpDownloader::getJson(
      url,
      [&](Stream& bodyStream) {
        const bool useFilter = filter != nullptr && filter->size() > 0;
        const DeserializationError err =
            useFilter ? deserializeJson(outResp, bodyStream, DeserializationOption::Filter(*filter))
                      : deserializeJson(outResp, bodyStream);
        if (err) {
          LOG_ERR("NAS", "getBook parse error: %s", err.c_str());
          parseFailed = true;
          return false;
        }
        return true;
      },
      /*timeoutMs=*/10000);
  if (!ok) return parseFailed ? Err::Parse : Err::Http;
  return Err::Ok;
}

Err syncAll(JsonDocument& outResp) {
  if (WiFi.status() != WL_CONNECTED) return Err::NoWifi;
  const std::string base = NasConfigStore::load();
  if (base.empty()) return Err::NoServer;

  const std::string url = join(base, "/api/sync");
  // NAS 网关兼容：空 body 触发全量同步。
  bool parseFailed = false;
  const bool ok = HttpDownloader::postJson(
      url, /*payload=*/"{}", /*bearerToken=*/"",
      [&](Stream& bodyStream) {
        const DeserializationError err = deserializeJson(outResp, bodyStream);
        if (err) {
          LOG_ERR("NAS", "syncAll parse error: %s", err.c_str());
          parseFailed = true;
          return false;
        }
        return true;
      },
      /*timeoutMs=*/15000);
  if (!ok) return parseFailed ? Err::Parse : Err::Http;
  return Err::Ok;
}

std::string downloadUrl(const std::string& bookId) {
  return join(NasConfigStore::load(), ("/api/books/" + bookId + "/download").c_str());
}

const char* errorName(Err err) {
  switch (err) {
    case Err::Ok:
      return "Ok";
    case Err::NoWifi:
      return "NoWifi";
    case Err::NoServer:
      return "NoServer";
    case Err::Http:
      return "Http";
    case Err::Parse:
      return "Parse";
  }
  return "Unknown";
}

}  // namespace NasClient