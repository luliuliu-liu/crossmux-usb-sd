#pragma once
// Small host-side implementation of Arduino-ESP32's base64 helper.
// Basic Auth is used by the real OPDS client, so returning an empty string
// here makes authenticated simulator requests fail with HTTP 401.

#include <WString.h>

#include <cstddef>
#include <cstdint>
#include <string>

class base64 {
 public:
  static String encode(const uint8_t* data, size_t len) {
    static constexpr char alphabet[] =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string out;
    out.reserve(((len + 2) / 3) * 4);
    for (size_t i = 0; i < len; i += 3) {
      const uint32_t a = data[i];
      const uint32_t b = i + 1 < len ? data[i + 1] : 0;
      const uint32_t c = i + 2 < len ? data[i + 2] : 0;
      const uint32_t triple = (a << 16) | (b << 8) | c;
      out.push_back(alphabet[(triple >> 18) & 0x3f]);
      out.push_back(alphabet[(triple >> 12) & 0x3f]);
      out.push_back(i + 1 < len ? alphabet[(triple >> 6) & 0x3f] : '=');
      out.push_back(i + 2 < len ? alphabet[triple & 0x3f] : '=');
    }
    return String(out.c_str());
  }

  static String encode(const char* text) {
    if (!text) return String();
    return encode(reinterpret_cast<const uint8_t*>(text), std::char_traits<char>::length(text));
  }

  static String encode(const String& text) {
    return encode(text.c_str());
  }
};