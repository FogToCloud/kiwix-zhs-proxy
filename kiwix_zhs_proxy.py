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
访问入口页：      http://<电脑IP>:8080/lan   （自动列出本机所有可用地址 + 二维码，手机扫码即开）

环境变量（可选）：
    KIWIX_UPSTREAM  上游 Kiwix 服务地址，默认 http://127.0.0.1:8090
    KIWIX_PORT      本代理监听端口，默认 8080
    KIWIX_HOST      监听地址，默认 127.0.0.1（仅本机）；手机要访问时设为 0.0.0.0
    KIWIX_DEBUG=1   开启访问日志（写入本脚本同目录 proxy_access.log）
    KIWIX_ZIM_ID    缺库名自动补全时使用的库名，默认 wikipedia_zh_all_maxi_2026-08

前置：Kiwix 服务 (kiwix-serve) 已在本机运行（见 README）。
"""
import http.server
import socketserver
import urllib.request
import sys
import re
import os
import time
import subprocess
import html

UPSTREAM = os.environ.get("KIWIX_UPSTREAM", "http://127.0.0.1:8090")
PORT = int(os.environ.get("KIWIX_PORT", "8080"))
HOST = os.environ.get("KIWIX_HOST", "127.0.0.1")
DEBUG = os.environ.get("KIWIX_DEBUG", "") == "1"
_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxy_access.log")

# 内容页路径前缀（Kiwix serve 的 ZIM 内容都挂在 /content/ 下）
CONTENT_PREFIX = "/content/"
# 默认 ZIM 库名：手机端某些入口会生成缺库名的 /content/<词条> 链接，
# 代理自动补全库名再转发，避免 404。
ZIM_ID = os.environ.get("KIWIX_ZIM_ID", "wikipedia_zh_all_maxi_2026-08")

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


# 禁止 urllib 自动跟随重定向：把 302 原样转发给浏览器，由浏览器自行跳转，
# 保证地址栏/iframe URL 正确（/content/<库名>/<词条>），避免代理层跟随后内容错位。
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

_OPENER = urllib.request.build_opener(_NoRedirect)


# ---- /lan 访问入口页：自动列出本机所有局域网地址 + 二维码（纯本地，零 Python 依赖）----
_LAN_QRCODE_JS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qrcode.min.js")

def _lan_ips():
    """解析 ipconfig 输出，返回 [(适配器名, IPv4), ...]，
    排除回环地址与常见虚拟网卡（WSL/Docker/VMware 等手机连不上的）。"""
    _SKIP_ADAPTOR = ("wsl", "vehternet", "docker", "vmware", "virtualbox",
                     "loopback", "vgate", "unknown", "hyper-v")
    out = None
    for enc in ("gbk", "utf-8", "cp936"):
        try:
            out = subprocess.check_output(["ipconfig"], encoding=enc, errors="replace")
            break
        except Exception:
            continue
    if out is None:
        return []
    ips, adaptor = [], ""
    for raw in out.splitlines():
        line = raw.strip()
        if not line:
            continue
        # 段落标题（行首无缩进）作为适配器名；属性行（含 IPv4）行首有缩进
        if raw[:1] in (" ", "\t", "\u3000"):
            if "IPv4" in line:
                m = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", line)
                if m and not m.group(1).startswith("127."):
                    ad = adaptor or "网络"
                    if any(k in ad.lower() for k in _SKIP_ADAPTOR):
                        continue
                    ips.append((ad, m.group(1)))
        else:
            adaptor = line
    return ips


_LAN_PAGE_HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>离线维基百科 · 访问入口</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; background: #f4f6f8; color: #1f2328; padding: 32px 16px 48px; }
  .wrap { max-width: 560px; margin: 0 auto; }
  h1 { font-size: 22px; margin-bottom: 8px; color: #0f172a; }
  .sub { color: #64748b; font-size: 14px; line-height: 1.7; margin-bottom: 24px; }
  .card { background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(15,23,42,.05); }
  .tag { display: inline-block; background: #eef2ff; color: #3730a3; font-size: 12px; padding: 3px 10px; border-radius: 20px; margin-bottom: 10px; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .url { display: block; font-size: 18px; font-weight: 600; color: #2563eb; text-decoration: none; word-break: break-all; margin: 6px 0 14px; }
  .qr { width: 200px; height: 200px; margin: 0 auto 14px; }
  .copy { display: block; width: 100%; padding: 10px; border: 0; border-radius: 10px; background: #0f172a; color: #fff; font-size: 15px; cursor: pointer; }
  .copy:active { opacity: .8; }
  .tips { background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 20px; font-size: 14px; line-height: 1.9; color: #334155; }
  .tips h3 { font-size: 15px; margin-bottom: 8px; color: #0f172a; }
  .tips code { background: #f1f5f9; padding: 1px 6px; border-radius: 6px; }
  .warn { color: #b91c1c; margin-top: 10px; font-size: 13px; }
  .empty { color: #94a3b8; text-align: center; padding: 12px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>离线维基百科 · 访问入口</h1>
  <p class="sub">手机 / 平板 / 电脑打开下面任一地址即可查 154 万条词条（全简体，无需外网）。<br>扫二维码直接打开，或点「复制地址」。</p>
  {CARDS}
  <div class="tips">
    <h3>三种使用方式</h3>
    <p><b>① 家里有 WiFi</b>：手机连 WiFi，扫「WiFi」那张卡的二维码。</p>
    <p><b>② 没网 / 在外面</b>：手机开热点（不耗流量）→ 电脑连上手机热点 → 扫「热点」那张卡的二维码。</p>
    <p><b>③ 电脑本机</b>：直接打开 <code>http://127.0.0.1:{PORT}</code>。</p>
    <p class="warn">仅限家庭内网使用，不要把端口映射到公网。</p>
  </div>
</div>
<script>{QRCODE_JS}</script>
<script>
(function(){
  document.querySelectorAll('.card').forEach(function(card){
    var url = card.getAttribute('data-url');
    if (typeof QRCode !== 'undefined') {
      new QRCode(card.querySelector('.qr'), {text: url, width: 200, height: 200});
    }
    var btn = card.querySelector('.copy');
    btn.addEventListener('click', function(){
      var done = function(){ btn.textContent = '已复制'; setTimeout(function(){ btn.textContent = '复制地址'; }, 1500); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(done, done);
      } else {
        var t = document.createElement('textarea'); t.value = url; document.body.appendChild(t);
        t.select(); try { document.execCommand('copy'); } catch(e){} document.body.removeChild(t); done();
      }
    });
  });
})();
</script>
</body>
</html>"""

_LAN_CARD_HTML = """<div class="card" data-url="{url}">
  <span class="tag">{adaptor}</span>
  <a class="url" href="{url}">{url}</a>
  <div class="qr"></div>
  <button class="copy">复制地址</button>
</div>"""


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self):
        # 强制关闭连接：避免 keep-alive 连接上大响应体（>1MB）传输不完整，
        # 浏览器按 Content-Length 等待剩余字节导致 iframe 一直加载。
        self.close_connection = True
        self._handle(write_body=True)

    def do_HEAD(self):
        # HEAD 只回响应头（含 Content-Length），不写 body。
        self.close_connection = True
        self._handle(write_body=False)

    def _serve_lan_page(self):
        cards = []
        for adaptor, ip in _lan_ips():
            url = "http://%s:%d" % (ip, PORT)
            cards.append(_LAN_CARD_HTML.format(adaptor=html.escape(adaptor), ip=ip, url=url))
        if not cards:
            cards.append('<div class="empty">未检测到局域网地址，本机请直接用 <code>http://127.0.0.1:%d</code></div>' % PORT)
        qrcode_js = ""
        if os.path.exists(_LAN_QRCODE_JS_FILE):
            try:
                with open(_LAN_QRCODE_JS_FILE, "r", encoding="utf-8") as f:
                    qrcode_js = f.read()
            except Exception:
                qrcode_js = ""
        page = (_LAN_PAGE_HTML
                .replace("{CARDS}", "\n".join(cards))
                .replace("{QRCODE_JS}", qrcode_js)
                .replace("{PORT}", str(PORT)))
        body = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, write_body=True):
        raw_path = self.path            # 原始路径（含 query）
        path = raw_path.split("?")[0]   # 纯路径，用于判断
        query = raw_path[len(path):]    # 保留 ?query

        # /lan 访问入口页：列出所有可用地址 + 二维码，不转发上游
        if path == "/lan":
            self._serve_lan_page()
            return

        # 容错：/content/<词条> 缺 ZIM 库名时，自动补全为 /content/<ZIM_ID>/<词条>
        # 注意：第一段已是库名（如 /content/wikipedia_zh_all_maxi_2026-08）时不补全，原样转发；
        #       带尾斜杠的库名路径（/content/<库名>/）视为同一库名，去掉尾斜杠。
        if path.startswith(CONTENT_PREFIX):
            rest = path[len(CONTENT_PREFIX):]
            if rest.endswith("/"):
                rest = rest.rstrip("/")
                path = CONTENT_PREFIX + rest
            if rest and "/" not in rest and rest != ZIM_ID:
                path = CONTENT_PREFIX + ZIM_ID + "/" + rest
            raw_path = path + query

        # 转发到 Kiwix 内容服务
        url = UPSTREAM + raw_path
        headers = {
            "User-Agent": self.headers.get("User-Agent", "Mozilla/5.0"),
            "Accept": self.headers.get("Accept", "*/*"),
            "Accept-Language": self.headers.get("Accept-Language", "zh-CN,zh;q=0.9"),
            # 让上游直接回原始字节，避免代理层解压缩带来的复杂性与内容长度不确定
            "Accept-Encoding": "identity",
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            resp = _OPENER.open(req, timeout=60)
            status = resp.status

            # 重定向（302 等）原样转发给浏览器，由浏览器自行跟随：
            # 1) 浏览器地址栏/iframe 的 URL 保持正确（/content/<库名>/<词条>），
            # 2) 避免代理层跟随后 URL 与内容错位导致的 404/加载异常。
            if status in (301, 302, 303, 307, 308):
                loc = resp.headers.get("Location", "")
                if DEBUG:
                    try:
                        with open(_LOG_FILE, "a", encoding="utf-8") as _lf:
                            _lf.write("[%s] %s -> %d REDIRECT-> %s\n"
                                      % (time.strftime("%H:%M:%S"), self.path, status, loc))
                    except Exception:
                        pass
                self.send_response(status)
                self.send_header("Location", loc)
                self.send_header("Content-Length", "0")
                self.send_header("Connection", "close")
                self.end_headers()
                try:
                    resp.close()
                except Exception:
                    pass
                return

            body = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            converted = False

            # 只对 HTML 内容页做服务端简繁转换
            if (path.startswith(CONTENT_PREFIX)
                    and "html" in ctype.lower()
                    and body):
                cache_key = path
                cached = cache_get(cache_key)
                if cached is not None:
                    body = cached
                    converted = True
                else:
                    conv = get_converter()
                    if conv is None:
                        # 转换器不可用时不静默返回繁体：fail fast，明确报错
                        self.send_error(500, "简体转换不可用：OpenCC 未安装或加载失败")
                        return
                    text = body.decode("utf-8", errors="replace")
                    text = convert_html_text(text, conv)
                    body = text.encode("utf-8")
                    converted = True
                    cache_put(cache_key, body)

            self.send_response(status)
            # 可选访问日志（KIWIX_DEBUG=1 时开启）
            if DEBUG:
                try:
                    with open(_LOG_FILE, "a", encoding="utf-8") as _lf:
                        _lf.write("[%s] %s -> %d len=%d UA=%s AL=%s\n"
                                  % (time.strftime("%H:%M:%S"), self.path, status, len(body),
                                     self.headers.get("User-Agent", "")[:60],
                                     self.headers.get("Accept-Language", "")))
                except Exception:
                    pass
            # 转发除长度/编码/连接外的头。
            # 注意：CSP 头必须原样转发（Kiwix 内容页的 sandbox 指令依赖它，
            # 丢弃后 iframe 内脚本行为异常，导致内容页加载后不渲染）。
            skip = ("content-length", "transfer-encoding", "connection",
                    "content-encoding", "keep-alive", "date")
            # 转换过的 body 不再匹配上游 ETag：丢弃 ETag 避免浏览器复用错误的缓存；
            # 未转换的静态资源（图片/CSS/JS）原样转发 ETag/Cache-Control，保持浏览器缓存生效。
            if converted:
                skip = skip + ("etag",)
            sent = set()
            for k, v in resp.headers.items():
                if k.lower() in skip:
                    continue
                lk = k.lower()
                if lk in sent:
                    continue  # 去重（上游可能重复发 Content-Type/Date 等）
                sent.add(lk)
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            if write_body:
                self.wfile.write(body)
        except urllib.error.HTTPError as e:
            # 上游重定向（302 等）在 NoRedirect 下以 HTTPError 形式抛出：
            # 同样原样转发 Location 给浏览器，由浏览器自行跳转。
            if e.code in (301, 302, 303, 307, 308):
                loc = e.headers.get("Location", "")
                if DEBUG:
                    try:
                        with open(_LOG_FILE, "a", encoding="utf-8") as _lf:
                            _lf.write("[%s] %s -> %d REDIRECT-> %s\n"
                                      % (time.strftime("%H:%M:%S"), self.path, e.code, loc))
                    except Exception:
                        pass
                self.send_response(e.code)
                self.send_header("Location", loc)
                self.send_header("Content-Length", "0")
                self.send_header("Connection", "close")
                self.end_headers()
                return
            self.send_response(e.code)
            self.end_headers()
            if write_body:
                self.wfile.write(e.read())
        except Exception as e:
            self.send_error(502, "Upstream error: %s" % e)


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    if HOST == "0.0.0.0":
        print("\n[警告] 正在绑定 0.0.0.0：同一 WiFi 下的手机/平板可通过 http://<本机IP>:%d 访问。" % PORT, file=sys.stderr)
        print("        仅限家庭内网使用，不要把端口映射到公网！\n", file=sys.stderr)
    try:
        httpd = ThreadingHTTPServer((HOST, PORT), ProxyHandler)
    except OSError as e:
        print("端口 %d 被占用：%s" % (PORT, e), file=sys.stderr)
        sys.exit(1)
    print("Kiwix 简体代理（服务端转换版）运行中： http://%s:%d/viewer  ->  %s" % (HOST, PORT, UPSTREAM))
    sys.stderr.flush()
    httpd.serve_forever()
