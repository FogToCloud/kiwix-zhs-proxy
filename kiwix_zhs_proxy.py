# -*- coding: utf-8 -*-
"""
Kiwix 简体中文代理（服务端简繁转换版）
=======================================
Kiwix 官方中文维基 ZIM 包是繁体，本代理在【服务端】把内容页文本转成简体：
  - /content/... 内容页：返回前用 OpenCC (tw2sp) 转换文本节点
  - /viewer 及静态资源：原样转发，不注入任何脚本
因此浏览器端零注入、零脚本，没有客户端 JS 卡死问题，手机/电脑浏览器直接可用。

用法：
    python kiwix_zhs_proxy.py
电脑浏览器访问：  http://127.0.0.1:8080/viewer#wikipedia_zh_all_maxi_2026-08/User%3AThe_other_Kiwix_guy/Landing
手机浏览器访问：  http://<电脑局域网IP>:8080/viewer#...(同上路径)

环境变量（可选）：
    KIWIX_UPSTREAM  上游 Kiwix 服务地址，默认 http://127.0.0.1:8090
    KIWIX_PORT      本代理监听端口，默认 8080
    KIWIX_DEBUG=1   开启访问日志（写入本脚本同目录 proxy_access.log）

前置：Kiwix 服务 (kiwix-serve) 已在本机运行（见 README）。
"""
import http.server
import socketserver
import urllib.request
import sys
import re
import os
import time

UPSTREAM = os.environ.get("KIWIX_UPSTREAM", "http://127.0.0.1:8090")
PORT = int(os.environ.get("KIWIX_PORT", "8080"))
DEBUG = os.environ.get("KIWIX_DEBUG", "") == "1"
_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxy_access.log")

# 内容页路径前缀（Kiwix serve 的 ZIM 内容都挂在 /content/ 下）
CONTENT_PREFIX = "/content/"

# ---- OpenCC 转换器（服务端，原生 C++ 绑定，大页面约几十毫秒）----
_converter = None
def get_converter():
    global _converter
    if _converter is None:
        try:
            import opencc
            _converter = opencc.OpenCC("tw2sp")
        except Exception as e:
            sys.stderr.write("OpenCC 加载失败: %s\n" % e)
            _converter = False
    return _converter or None

# ---- 简单 LRU 缓存：避免同一页面短时间内重复转换 ----
_CACHE_MAX = 80
_cache = {}
_cache_order = []

def cache_get(key):
    return _cache.get(key)

def cache_put(key, val):
    if key in _cache:
        _cache_order.remove(key)
    _cache[key] = val
    _cache_order.append(key)
    if len(_cache_order) > _CACHE_MAX:
        old = _cache_order.pop(0)
        _cache.pop(old, None)

# ---- HTML 文本节点转换（跳过 script/style/pre/code 等，避免破坏脚本与样式）----
_SKIP_TAGS = re.compile(
    r"<(script|style|pre|code|textarea|title|noscript|template)(\s[^>]*)?>.*?</\1>",
    re.IGNORECASE | re.DOTALL)
_TEXT_MARK = re.compile(r">([^<>]+)<")

def convert_html_text(html_text, converter):
    """把 HTML 中文本节点的繁体转简体。用占位符保护需要跳过的块。"""
    placeholders = []
    def stash(m):
        placeholders.append(m.group(0))
        return "\x00%d\x00" % (len(placeholders) - 1)
    protected = _SKIP_TAGS.sub(stash, html_text)
    def convert_chunk(m):
        content = m.group(1)
        # 只转换含中文的片段，避免无谓调用
        if not re.search(r"[\u4e00-\u9fff]", content):
            return m.group(0)
        conv = converter.convert(content)
        return ">" + conv + "<"
    converted = _TEXT_MARK.sub(convert_chunk, protected)
    # 还原被保护的块
    for i, orig in enumerate(placeholders):
        converted = converted.replace("\x00%d\x00" % i, orig)
    return converted


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self):
        # 强制关闭连接：避免 keep-alive 连接上大响应体（>1MB）传输不完整，
        # 浏览器按 Content-Length 等待剩余字节导致 iframe 一直加载。
        self.close_connection = True
        self._handle()
        return

    do_HEAD = do_GET

    def _handle(self):
        path = self.path.split("?")[0]

        # 转发到 Kiwix 内容服务
        url = UPSTREAM + self.path
        headers = {
            "User-Agent": self.headers.get("User-Agent", "Mozilla/5.0"),
            "Accept": self.headers.get("Accept", "*/*"),
            "Accept-Language": self.headers.get("Accept-Language", "zh-CN,zh;q=0.9"),
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=60)
            body = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            status = resp.status

            # 只对 HTML 内容页做服务端简繁转换
            if (path.startswith(CONTENT_PREFIX)
                    and "html" in ctype.lower()
                    and body):
                cache_key = self.path
                cached = cache_get(cache_key)
                if cached is not None:
                    body = cached
                else:
                    conv = get_converter()
                    if conv:
                        text = body.decode("utf-8", errors="replace")
                        text = convert_html_text(text, conv)
                        body = text.encode("utf-8")
                        cache_put(cache_key, body)

            self.send_response(status)
            # 可选访问日志（KIWIX_DEBUG=1 时开启）
            if DEBUG:
                try:
                    with open(_LOG_FILE, "a", encoding="utf-8") as _lf:
                        _lf.write("[%s] %s -> %d len=%d\n"
                                  % (time.strftime("%H:%M:%S"), self.path, status, len(body)))
                except Exception:
                    pass
            # 转发除长度/编码/连接外的头。
            # 注意：CSP 头必须原样转发（Kiwix 内容页的 sandbox 指令依赖它，
            # 丢弃后 iframe 内脚本行为异常，导致内容页加载后不渲染）。
            skip = ("content-length", "transfer-encoding", "connection",
                    "content-encoding", "keep-alive", "etag", "date")
            sent = set()
            for k, v in resp.headers.items():
                if k.lower() in skip:
                    continue
                lk = k.lower()
                if lk in sent:
                    continue  # 去重（上游可能重复发 Content-Type/Date 等）
                sent.add(lk)
                self.send_header(k, v)
            # 转换过的 body 不再匹配上游 ETag：统一不转发 ETag（已在上方 skip），
            # 让代理响应不带缓存验证字段，避免浏览器复用错误的缓存。
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_error(502, "Upstream error: %s" % e)


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    try:
        httpd = ThreadingHTTPServer(("0.0.0.0", PORT), ProxyHandler)
    except OSError as e:
        print("端口 %d 被占用：%s" % (PORT, e), file=sys.stderr)
        sys.exit(1)
    print("Kiwix 简体代理（服务端转换版）运行中： http://127.0.0.1:%d/viewer  ->  %s" % (PORT, UPSTREAM))
    sys.stderr.flush()
    httpd.serve_forever()
