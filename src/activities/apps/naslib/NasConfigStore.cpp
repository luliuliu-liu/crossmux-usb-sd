#include "NasConfigStore.h"

#include <HalStorage.h>
#include <Logging.h>

namespace NasConfigStore {

namespace {
bool g_loaded = false;
std::string g_cached;

// 只接受 http:// 或 https:// 开头且无尾部斜杠的地址。
bool isWellFormed(const std::string& url) {
  if (url.empty() || url.length() > 128) return false;
  if (url.compare(0, 7, "http://") != 0 && url.compare(0, 8, "https://") != 0) return false;
  if (url.find(' ') != std::string::npos) return false;
  if (url.back() == '/') return false;
  return true;
}

void ensureLoadedFromDisk() {
  if (g_loaded) return;
  g_loaded = true;
  if (!Storage.exists(kPath)) {
    g_cached.clear();
    return;
  }
  String raw = Storage.readFile(kPath);
  std::string url(raw.c_str());
  // 去掉可能的尾部换行。
  while (!url.empty() && (url.back() == '\n' || url.back() == '\r' || url.back() == ' ' || url.back() == '\t')) {
    url.pop_back();
  }
  if (!isWellFormed(url)) {
    LOG_ERR("NAS", "Stored NAS url invalid; ignoring");
    g_cached.clear();
    return;
  }
  g_cached = std::move(url);
}

}  // namespace

const std::string& load() {
  ensureLoadedFromDisk();
  return g_cached;
}

bool save(const std::string& url) {
  if (!isWellFormed(url)) {
    LOG_ERR("NAS", "save(): url not well-formed");
    return false;
  }
  Storage.ensureDirectoryExists("/.crosspoint");
  if (!Storage.writeFile(kPath, String(url.c_str()))) {
    LOG_ERR("NAS", "save(): writeFile failed");
    return false;
  }
  g_cached = url;
  g_loaded = true;
  LOG_DBG("NAS", "NAS server url saved");
  return true;
}

bool has() {
  ensureLoadedFromDisk();
  return !g_cached.empty();
}

void clear() {
  g_cached.clear();
  g_loaded = true;
  if (Storage.exists(kPath)) {
    Storage.remove(kPath);
  }
}

}  // namespace NasConfigStore