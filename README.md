# kiwix-zhs-proxy

**Kiwix 离线维基百科的简体中文代理** · *Server-side Traditional→Simplified Chinese proxy for offline Kiwix Wikipedia*

把 Kiwix 官方中文维基 ZIM 离线包（繁体）在**服务端**实时转成简体，浏览器零脚本、零注入，电脑和手机直接浏览器访问。离线、免费、不登录、不依赖任何在线服务。

Convert Kiwix's official Chinese Wikipedia ZIM (Traditional Chinese) to **Simplified Chinese on the server side** — zero JS injection in the browser. Works fully offline: PC & phone just open a browser. No login, no online dependency.

---

**Languages**: [中文](#中文说明) · [English](#english)

---

## 中文说明

### 为什么需要它

- Kiwix 官方 `wikipedia_zh_all` 中文维基离线包是**繁体**（zh-Hant），阅读体验差。
- 常见做法是浏览器端注入脚本转简体，但会卡页面（"点第 4 个词条就卡死"）。
- 本方案把简繁转换搬到**服务端**：浏览器收到的就是简体 HTML，没有一行注入脚本，彻底绕开前端卡死问题。

### 工作原理

```
浏览器 ──> 本代理 (8080) ──> Kiwix 服务 (8090) ──> ZIM 离线包
              │
              └─ 仅对 /content/... 的 HTML 页面：
                 OpenCC(tw2sp) 转换文本节点 → 返回简体
                 静态资源（图片/CSS/JS）原样转发
```

- 转换只针对**文本节点**（`>文字<`），自动跳过 `<script>/<style>/<pre>/<code>/<textarea>/<title>` 等，不破坏脚本和样式。
- 内置 LRU 缓存（80 条），同一页面短时间重复访问不重复转换。

### 为什么不在打包阶段直接生成简体 ZIM？

一个自然的问题是：为什么不把离线包重新打包成简体版，一劳永逸？两个原因：

1. **官方 ZIM 是滚动更新**。维基百科离线包每月发布新版本，每重打包一次都要重新转换全部词条、重建索引，维护成本高、很快过期。
2. **实时转换成本足够低**。OpenCC 是原生 C++ 绑定，单个页面转换只要几十毫秒；配合 LRU 缓存，家庭场景完全无感。

另外：Nginx/Caddy 反向代理只解决"转发"，简繁转换仍要自己写；本代理 186 行把"转发 + 转换 + 缓存 + 日志"一体做完，部署更简单。

> **安全提示**：本项目仅供**家庭局域网**使用（电脑和手机连同一 Wi-Fi）。请勿把 8080 端口直接暴露到公网，也不要转发到不受信任的网络。

### 环境要求

| 组件 | 说明 |
|---|---|
| Python 3 | `pip install opencc-python-reimplemented` |
| Kiwix 工具 | `kiwix-serve.exe`（kiwix.org 下载，Windows/Linux/macOS 均有） |
| ZIM 文件 | `wikipedia_zh_all_maxi_2026-08.zim`（kiwix.org 下载，约 20~60 GB，含全部条目与图片） |

### 快速开始（Windows）

1. 编辑 `start.ps1` 顶部 3 行路径（或设置环境变量 `KIWIX_DIR`，见下）。
2. 运行：
   ```powershell
   powershell -ExecutionPolicy Bypass -File start.ps1
   ```
   自动完成：启动 `kiwix-serve`(8090) → 启动本代理(8080) → 打开浏览器。

3. 电脑浏览器打开（或手动输入）：
   ```
   http://127.0.0.1:8080/viewer#wikipedia_zh_all_maxi_2026-08/User%3AThe_other_Kiwix_guy/Landing
   ```

**不修改文件的方式**（适合 AI 自动部署 / 小白）：先设环境变量，再跑脚本
```powershell
$env:KIWIX_DIR = "D:\Kiwix"          # 你的 Kiwix 目录（含 kiwix-serve.exe、python、zim）
$env:ZIM_FILE  = "D:\Kiwix\zim\wikipedia_zh_all_maxi_2026-08.zim"
powershell -ExecutionPolicy Bypass -File start.ps1
```

### 手动启动

```bash
# 终端 1：启动 Kiwix 服务
kiwix-serve.exe --port=8090 wikipedia_zh_all_maxi_2026-08.zim

# 终端 2：启动简体代理
python kiwix_zhs_proxy.py
```

### 手机访问（同一 Wi-Fi）

手机浏览器直接访问电脑局域网 IP（无需装任何 App）：

```
http://192.168.1.11:8080/viewer#wikipedia_zh_all_maxi_2026-08/User%3AThe_other_Kiwix_guy/Landing
```

（把 `192.168.1.11` 换成你的电脑 IP，`ipconfig` 查看。Windows 防火墙需放行 8080 端口——首次访问浏览器弹窗点允许即可。）

### 配置（环境变量）

| 变量 | 默认值 | 作用 |
|---|---|---|
| `KIWIX_UPSTREAM` | `http://127.0.0.1:8090` | 上游 Kiwix 服务地址 |
| `KIWIX_PORT` | `8080` | 本代理监听端口 |
| `KIWIX_DEBUG=1` | 关 | 开启访问日志（写在脚本同目录 `proxy_access.log`） |
| `KIWIX_DIR` / `ZIM_FILE` | （start.ps1 内定义） | 一键启动时指定 Kiwix 目录与 ZIM 文件 |

### 踩坑记录（两个关键修复，做代理的人必看）

1. **CSP 头必须原样转发**。Kiwix 内容页带 `Content-Security-Policy: ... sandbox allow-scripts allow-same-origin ...`，它是 iframe 沙箱依据。丢了这个头 → iframe 内脚本异常 → 内容页加载后不渲染（地址栏变了、页面不动）。
2. **强制 `Connection: close`**。HTTP/1.1 keep-alive 转发大页面（如"沈阳市"条目 1.3MB）时响应体可能传不完整，浏览器按 Content-Length 死等 → iframe 永远转圈。每个响应显式关闭连接即可。

### 目录结构

```
kiwix-zhs-proxy/
├── kiwix_zhs_proxy.py   # 代理主脚本（单文件，仅依赖 opencc）
├── start.ps1            # 一键启动（kiwix-serve + 代理 + 打开浏览器）
├── stop.ps1             # 停止
├── LICENSE              # MIT
└── README.md
```

### License

MIT © 2026 FogToCloud

---

## English

### Why

- The official `wikipedia_zh_all` ZIM from Kiwix is **Traditional Chinese** (zh-Hant), tiring to read for simplified-Chinese users.
- Client-side JS conversion tends to freeze the page (e.g. stuck on the 4th link click).
- This proxy does the conversion **server-side**: the browser receives already-simplified HTML. Zero injected scripts → no front-end freezes.

### How it works

```
Browser ──> this proxy (8080) ──> Kiwix serve (8090) ──> ZIM offline file
              │
              └─ only for /content/... HTML pages:
                 OpenCC(tw2sp) converts text nodes → simplified
                 static assets (images/CSS/JS) pass through unchanged
```

Text nodes (`>text<`) are converted while `<script>/<style>/<pre>/<code>/<textarea>/<title>` blocks are skipped. A small LRU cache (80 entries) avoids repeated conversion.

### Why not convert at packaging time?

A natural question: why not re-package the ZIM into Simplified Chinese once and for all?

1. **Official ZIMs are rolling releases.** Wikipedia offline packs ship monthly; re-packaging means re-converting every article and rebuilding the index each time — high maintenance, quickly stale.
2. **Runtime conversion is cheap enough.** OpenCC is a native C++ binding; converting a single page takes tens of milliseconds. With the LRU cache it is imperceptible at home scale.

Also: Nginx/Caddy reverse proxies only solve forwarding — you still have to write the conversion yourself. This proxy (186 lines) bundles forward + convert + cache + logging in one file, simpler to deploy.

> **Security**: for **home LAN use only** (PC & phone on the same Wi-Fi). Do not expose port 8080 to the public internet.

### Requirements

| Component | Notes |
|---|---|
| Python 3 | `pip install opencc-python-reimplemented` |
| Kiwix tools | `kiwix-serve.exe` (download from kiwix.org) |
| ZIM file | `wikipedia_zh_all_maxi_2026-08.zim` (~20–60 GB, full articles + images) |

### Quick start (Windows)

Option A — edit 3 path lines at the top of `start.ps1`, then:
```powershell
powershell -ExecutionPolicy Bypass -File start.ps1
```
Option B — set env vars instead (great for AI / scripting):
```powershell
$env:KIWIX_DIR = "D:\Kiwix"
$env:ZIM_FILE  = "D:\Kiwix\zim\wikipedia_zh_all_maxi_2026-08.zim"
powershell -ExecutionPolicy Bypass -File start.ps1
```
Then open:
```
http://127.0.0.1:8080/viewer#wikipedia_zh_all_maxi_2026-08/User%3AThe_other_Kiwix_guy/Landing
```

### Phone access (same Wi-Fi)

No app needed — just open the PC's LAN IP in the phone browser:
```
http://192.168.1.11:8080/viewer#wikipedia_zh_all_maxi_2026-08/User%3AThe_other_Kiwix_guy/Landing
```
Allow port 8080 in Windows Firewall when prompted.

### Configuration (env vars)

| Var | Default | Purpose |
|---|---|---|
| `KIWIX_UPSTREAM` | `http://127.0.0.1:8090` | Upstream Kiwix address |
| `KIWIX_PORT` | `8080` | Proxy listen port |
| `KIWIX_DEBUG=1` | off | Write access log (`proxy_access.log` next to the script) |
| `KIWIX_DIR` / `ZIM_FILE` | (defined in start.ps1) | Kiwix dir & ZIM file for one-click start |

### Gotchas (two critical fixes if you write a similar proxy)

1. **Forward the CSP header verbatim.** Kiwix content pages carry `Content-Security-Policy: ... sandbox allow-scripts allow-same-origin ...`, the basis of the iframe sandbox. Dropping it breaks iframe scripts → content loads but never renders (URL hash changes, page stays frozen).
2. **Force `Connection: close`.** With HTTP/1.1 keep-alive, large responses (e.g. the 1.3 MB "Shenyang" article) may be truncated; the browser then waits forever for the missing bytes per Content-Length → infinite spinner. Close the connection per response.

### License

MIT © 2026 FogToCloud
