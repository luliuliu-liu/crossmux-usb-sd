#pragma once

#include <string>

/**
 * NAS 书库网关地址配置。
 *
 * 存储格式：/.crosspoint/nas_server.txt，一行形如
 *   http://192.168.1.100:8000
 * 末尾不带斜杠，脚本读取后自行拼接 /api/... 路径。
 *
 * 明文存储（非敏感凭据；NAS 在局域网内，且设备本身无加密存储需求）。
 * 与 WeReadKeyStore 不同，这里不需要 XOR 混淆 —— 地址不是凭据。
 */

namespace NasConfigStore {

constexpr const char* kPath = "/.crosspoint/nas_server.txt";

/** 返回当前配置的 NAS 地址（无尾部斜杠），未配置时为空串。 */
const std::string& load();

/**
 * 校验并保存 NAS 地址。
 * 合法形式：http://host[:port] 或 https://host[:port]，不含尾部斜杠。
 * 返回 false 表示格式不合法或写盘失败。
 */
bool save(const std::string& url);

/** 是否已配置地址。 */
bool has();

/** 清除配置。 */
void clear();

}  // namespace NasConfigStore