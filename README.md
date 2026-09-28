# kiwix-zhs-proxy

**Kiwix 离线维基百科的简体中文代理** · *Server-side Traditional→Simplified Chinese proxy for offline Kiwix Wikipedia*

> **把整个维基百科搬进家里**：一台常年开机的设备（常开电脑 / NAS / 树莓派）存下全部中文维基，手机、电脑、平板连同一个 WiFi，浏览器打开就能看——**不依赖外部网络照查，还自动转简体**。

Kiwix 官方中文维基 ZIM 离线包是**繁体**，本项目在**服务端**实时转成简体，提供一套开箱即用的**中文维基百科简体**本地部署：浏览器零脚本、零注入、零卡顿。离线、免费、不登录、不依赖任何在线服务。

---

**Languages**: [中文](#中文说明) · [English](#english)

---

## 两种用法

把这套**离线维基百科**搬回家，只有两条路——图省心走方法 A，想自己动手走方法 B。**推荐方法 A**。

> 一句话先讲清：25G+ 离线包放在**电脑硬盘**上，手机 / 平板**不用装任何东西、零占用**，连同一个 WiFi 直接看。

### 方法 A（推荐）：把提示词丢给 AI，全程托管

不懂代码也没关系——把下面这段话原样发给任意 AI 助手（豆包 / ChatGPT / Claude 都行），下载、配置、启动、验证它全包了：

> 「我要把中文维基百科离线装进家里，全程你帮我完成：找 Kiwix 官方 Windows 版和 25G+ 全量包；从 GitHub 搜 FogToCloud/kiwix-zhs-proxy 下代理和一键启动脚本放进 Kiwix 目录改好路径；启动后打开浏览器验证简体首页；告诉我手机怎么连。」

### 方法 B：四步手动装好

1. **下载三件套**：Kiwix 阅读器 + 25G+ 离线包（实测 24.77GB）+ 本仓库代理脚本。
2. **扔进同一个文件夹**（Kiwix 目录）。
3. **右键 `start.ps1` → 用 PowerShell 运行**。
4. **手机连同一个 WiFi**，浏览器输入 `http://192.168.1.11:8080`（换成你电脑的实际 IP）。

装完效果：约 154 万条词条（1,547,241）躺在电脑硬盘里，全家设备连 WiFi 即开即看。更详细的步骤、原理与配置见下文。

---

## 最快捷方式：把这段话发给你的 AI 助手（复制即用）

本项目的作者就是这么装的——**全程托管给 AI，没有手写一行代码、没有手动敲一条命令**。你也可以：

> 我要把中文维基百科离线装进家里，全程由你（AI 助手）帮我自动完成，我不懂代码：
> 1. 帮我找到 Kiwix 官方 Windows 版下载地址，和官方中文维基离线包 `wikipedia_zh_all_maxi`（约 25GB，实测 24.77GB，文件名为 `wikipedia_zh_all_maxi_*.zim`）的下载地址，告诉我怎么下载。
> 2. 下载完成后，从 GitHub 仓库 `FogToCloud/kiwix-zhs-proxy` 获取 `kiwix_zhs_proxy.py`、`start.ps1` 和 `qrcode.min.js`，放进 Kiwix 目录，并自动把脚本里的路径改成我机器上的实际路径。
> 3. 帮我启动 Kiwix 服务和简体转换代理，然后打开浏览器验证能看到简体维基首页。
> 4. 告诉我手机怎么连家里 WiFi 访问（不用装任何 App），以及以后每次怎么一键启动。
>
> 要求：全程不要我懂代码，每一步都告诉我你做了什么、结果是什么，有问题就自己查资料解决。

复制上面这段给你的 AI 助手（豆包、ChatGPT、Claude 等都行），它会像帮我一样帮你装好。装完后手动方式见下文，原理见"工作原理"。

> **小提示**：如果手机连不上，多半是代理只绑了 `127.0.0.1`——让 AI 把启动参数里的 `KIWIX_HOST` 改成 `0.0.0.0` 再重启即可（仓库代理默认绑 `127.0.0.1`，详见下文"配置"表）。

**AI 时代装软件，就该这样**：不用啃文档、不用懂代码——把需求讲清楚，AI 自己调研、下载、配置、启动、修 bug，你只负责确认关键决策。想看这次部署的全过程实录（怎么调研选型、踩了哪三个坑、AI 怎么自己修好）→ [docs/ai-assisted-deployment.md](docs/ai-assisted-deployment.md)

## 先看效果（真实运行截图，全程离线）

电脑浏览器打开的简体维基首页：

![简体维基首页](https://aka.doubaocdn.com/s/CwylWRsTWU)

词条正文——「中华人民共和国」，全简体，带图带链接：

![词条正文简体](https://aka.doubaocdn.com/s/u4BtZzSASL)

整个中文维基（约 154 万条词条）就在这台电脑里，手机连 WiFi 就能看，无外部网络也能查。

---

## 中文说明

### 为什么需要它

看维基百科，拦着大多数人的有三件事：

1. **不想为查个资料去折腾网络代理**——看个词条担不必要的风险，没必要。
2. **官方中文版是繁体**——看着累，读起来费劲。
3. **手机 App 都要登录**——Kiwix 官方 App、各种镜像站，不是要账号就是要验证码。

所以这个项目把整个维基百科搬进了自己家里——**不折腾网络工具、不联网，打开浏览器就能看，全简体。**

### 上手：大学老师式步骤（照做就行）

**一台常年开机的设备就行**：常开电脑、NAS、树莓派都行。不需要懂代码，不需要会 Linux，全程鼠标操作。

需要下载三样东西：

- **Kiwix Windows 版**：官方离线阅读器，负责读 ZIM 包。去 `kiwix.org` 官网下载 Windows 版。
- **中文 ZIM 包**：整个中文维基百科的离线数据（约 25GB，实测 24.77GB）。从 Kiwix 官方 ZIM 镜像站下载，文件名类似 `wikipedia_zh_all_maxi_2026-08.zim`。
- **本代理程序**：这个仓库，把繁体转简体。

> 说明：官方中文 ZIM 包内容是繁体，代理程序在服务端实时转简体，浏览器拿到的就是干净的简体页面。为什么不直接找简体包？因为官方就没有简体 ZIM，只有繁体——这是 OpenZIM 项目的公开事实。

#### 第 1 步：解压 Kiwix 和 ZIM 包

把下载的 kiwix-tools 解压，把 ZIM 文件放进同一个文件夹，结构长这样：

```
C:\Kiwix\
├── kiwix-serve.exe      ← Kiwix 服务程序
├── zim\
│   └── wikipedia_zh_all_maxi_2026-08.zim   ← 中文离线包
├── kiwix_zhs_proxy.py   ← 本代理程序（从本仓库下载）
├── qrcode.min.js        ← 二维码库（/lan 入口页用，从本仓库下载）
└── start.ps1            ← 一键启动脚本（从本仓库下载）
```

#### 第 2 步：双击 start.ps1 启动

右键 `start.ps1` → 用 PowerShell 运行。脚本会依次做三件事：

1. 启动 Kiwix 服务（端口 8090，读取 ZIM 包）
2. 启动简体代理（端口 8080，繁转简）
3. 自动打开浏览器，进入「访问入口页」

**看到这个 = 成功：**

```
Kiwix 服务已启动: http://127.0.0.1:8090
简体代理已启动:   http://127.0.0.1:8080
浏览器已打开，开始看吧
```

#### 第 3 步：电脑上打开

浏览器输入：

```
http://127.0.0.1:8080
```

**看到简体维基首页 = 成功**（就是上面效果图 1 那个页面）。

#### 第 4 步：手机上打开（傻瓜方式：看「访问入口页」）

启动脚本会自动打开**「访问入口页」**（`http://127.0.0.1:8080/lan`），页面上：

- 列出电脑当前**所有可用地址**（WiFi / 热点各自的 IP，自动过滤虚拟网卡）
- 每个地址配一个**二维码**——手机扫码直接打开，不用手输 IP

手机连哪个网络，就扫哪张卡：

- **家里有 WiFi**：手机连 WiFi，扫「WiFi」那张卡的码。
- **没网 / 在外面**：手机开热点（不耗流量）→ 电脑连上手机热点 → 扫「热点」那张卡的码。
- **电脑本机**：直接打开 `http://127.0.0.1:8080`。

没有二维码库也不影响：地址文字照样列出，点「复制地址」即可。**任何网络、任何设备都能看，哪怕没有外网。**

> 手机端正常入口：打开 `http://<电脑IP>:8080` 后会先看到库列表（1 book(s)），点"维基百科"卡片即进入首页；想直达某词条，可用 `http://<电脑IP>:8080/viewer#wikipedia_zh_all_maxi_2026-08/<词条>`。缺库名的旧链接（`/content/<词条>`）代理会自动补全库名，不再 404。

### 代码长这样（无脑粘贴）

`start.ps1`（一键启动，完整版在仓库根目录）：

```powershell
# 一键启动：Kiwix + 简体代理
$KiwixPath  = "C:\Kiwix\kiwix-serve.exe"
$ZimFile    = "C:\Kiwix\zim\wikipedia_zh_all_maxi_2026-08.zim"
$ProxyScript = "C:\Kiwix\kiwix_zhs_proxy.py"

Start-Process $KiwixPath -ArgumentList "--port=8090 `"$ZimFile`""
Start-Process "python" -ArgumentList "`"$ProxyScript`""

Start-Sleep 3
Start-Process "http://127.0.0.1:8080/lan"
```

`kiwix_zhs_proxy.py`（核心转换逻辑，单文件，完整版在仓库根目录）：

```python
import opencc
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.request

converter = opencc.OpenCC('t2s')  # 繁体 → 简体

class Proxy(SimpleHTTPRequestHandler):
    def do_GET(self):
        # 1. 转发到本地 Kiwix (8090)
        url = 'http://127.0.0.1:8090' + self.path
        req = urllib.request.Request(url, headers=dict(self.headers))
        with urllib.request.urlopen(req) as resp:
            body = resp.read()
            # 2. 是 HTML 就转简体，其他原样转发
            if 'text/html' in resp.headers.get('Content-Type', ''):
                text = body.decode('utf-8', 'ignore')
                text = protect_and_convert(text)   # 保护 script/style/pre/code，只转正文
                body = text.encode('utf-8')
            # 3. 原样转发 CSP 安全头 + 关闭长连接
            self.send_response(200)
            for k, v in resp.headers.items():
                if k.lower() in ('content-security-policy', 'content-type'):
                    self.send_header(k, v)
            self.send_header('Connection', 'close')
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)

HTTPServer(('0.0.0.0', 8080), Proxy).serve_forever()
```

（上面是精简示意，完整逻辑含繁简转换的占位保护、缺库名自动补全、302 重定向原样转发、/lan 访问入口页等，直接去仓库复制 `kiwix_zhs_proxy.py`。）

### 我踩过的三个坑（卡了我一晚上）

1. **CSP 安全头不能丢。** Kiwix 返回的页面自带内容安全策略（`Content-Security-Policy`），代理必须原样转发。一开始把它丢了，结果地址栏在变、正文死活不显示——其实是浏览器安全机制把页面拦了。这个坑光看报错根本看不出来。
2. **大页面传一半就断。** HTTP 长连接传大页面会传一半断开、浏览器还在傻等，一直转圈。强制响应结束立即断开连接（`Connection: close`）问题解决，1.3MB 的大词条秒开。
3. **手机点词条/点卡片 404、页面加载异常。** 根因是代理用 urllib 自动"吞掉"了 Kiwix 的 302 重定向（Kiwix 对"只有库名"的路径会 302 到首页 `User:The other Kiwix guy/Landing`），直接把内容塞回给浏览器，但手机地址栏 URL 还是短路径，页面内相对链接解析错位 → 渲染出 404。修复：代理**不跟随重定向，把 302 原样转发给浏览器**，由浏览器自己跳转到完整路径（`/content/<库名>/<词条>`），URL 与内容一致；同时 `/content/<词条>` 缺库名自动补全、`/content/<库名>/` 尾斜杠归一化。手机实测全流程正常。

### 避坑清单（4 条）

1. **仅限家庭局域网**：代理绑定 `0.0.0.0` 是为了让手机能访问，**不要把 8080 端口映射到公网**，家里自己用就好。
2. **ZIM 包从官方源下载**：不要贪快从不明网站下，官方镜像站最稳。
3. **第一次加载稍慢**：手机第一次打开大词条要等几秒，之后有缓存就快了。
4. **手机打不开词条？** 先确认走的是 `http://<电脑IP>:8080`（不要带旧书签里的缺库名短链），必要时手机浏览器开无痕模式再试——旧的 404 页面可能被浏览器缓存。

### 工作原理

```
浏览器 ──> 本代理 (8080) ──> Kiwix 服务 (8090) ──> ZIM 离线包
              │
              ├─ /lan 访问入口页：列出本机所有可用地址 + 二维码
              └─ 仅对 /content/... 的 HTML 页面：
                 OpenCC(tw2sp) 转换文本节点 → 返回简体
                 静态资源（图片/CSS/JS）原样转发
```

- 转换只针对**文本节点**（`>文字<`），自动跳过 `<script>/<style>/<pre>/<code>/<textarea>/<title>` 等，不破坏脚本和样式。
- 内置 LRU 缓存（80 条），同一页面短时间重复访问不重复转换。
- Kiwix 对"只有库名"路径返回 302 → 代理原样转发给浏览器，浏览器自动跳到首页完整路径，手机上点击卡片/词条全程正常。
- `/lan` 入口页由代理动态生成：解析 `ipconfig` 自动列出本机所有可用 IPv4（自动过滤 WSL/Docker/VMware 等虚拟网卡），二维码由本地 `qrcode.min.js` 在浏览器端生成，全程离线零依赖。

### 为什么不在打包阶段直接生成简体 ZIM？

一个自然的问题是：为什么不把离线包重新打包成简体版，一劳永逸？两个原因：

1. **官方 ZIM 是滚动更新**。维基百科离线包每月发布新版本，每重打包一次都要重新转换全部词条、重建索引，维护成本高、很快过期。
2. **实时转换成本足够低**。OpenCC 是原生 C++ 绑定，单个页面转换只要几十毫秒；配合 LRU 缓存，家庭场景完全无感。

另外：Nginx/Caddy 反向代理只解决"转发"，简繁转换仍要自己写；本代理单文件把"转发 + 转换 + 缓存 + 日志"一体做完，部署更简单。

### 配置（环境变量）

| 变量 | 默认值 | 作用 |
|---|---|---|
| `KIWIX_UPSTREAM` | `http://127.0.0.1:8090` | 上游 Kiwix 服务地址 |
| `KIWIX_PORT` | `8080` | 本代理监听端口 |
| `KIWIX_HOST` | `127.0.0.1` | 监听地址；**手机要访问时设为 `0.0.0.0`**（启动会提示仅限内网） |
| `KIWIX_DEBUG=1` | 关 | 开启访问日志（写在脚本同目录 `proxy_access.log`） |
| `KIWIX_ZIM_ID` | `wikipedia_zh_all_maxi_2026-08` | 缺库名自动补全时使用的库名（换 ZIM 包时改这里） |
| `KIWIX_DIR` / `ZIM_FILE` | （start.ps1 内定义） | 一键启动时指定 Kiwix 目录与 ZIM 文件 |

### 目录结构

```
kiwix-zhs-proxy/
├── kiwix_zhs_proxy.py   # 代理主脚本（单文件，仅依赖 opencc）
├── start.ps1            # 一键启动（kiwix-serve + 代理 + 打开 /lan 访问入口页）
├── stop.ps1             # 停止
├── qrcode.min.js        # 二维码库（/lan 入口页用，MIT，可选——缺省时页面只显示地址文字）
├── requirements.txt     # Python 依赖（pip install -r requirements.txt）
├── Dockerfile           # 容器化运行代理（可选）
├── docker-compose.yml   # 一键全家桶：kiwix-serve + 代理（可选）
├── docs/
│   └── ai-assisted-deployment.md  # AI 托管部署实录（选型/踩坑/修复全过程）
├── SECURITY.md          # 安全边界与使用说明（仅限内网）
├── LICENSE              # MIT
└── README.md
```

### License

MIT © 2026 FogToCloud

---

## English

### See it in action (real offline screenshots)

Simplified-Chinese Wikipedia home page in a desktop browser:

![Simplified home](https://aka.doubaocdn.com/s/CwylWRsTWU)

Article body — "People's Republic of China" — fully Simplified Chinese:

![Simplified article](https://aka.doubaocdn.com/s/u4BtZzSASL)

### Why

- The official `wikipedia_zh_all` ZIM from Kiwix is **Traditional Chinese** (zh-Hant), tiring to read.
- Client-side JS conversion tends to freeze the page (e.g. stuck on the 4th link click).
- This proxy does the conversion **server-side**: the browser receives already-simplified HTML. Zero injected scripts → no front-end freezes.

### Step-by-step (no coding required)

1. Download **Kiwix Windows tools** and the **Chinese ZIM** (`wikipedia_zh_all_maxi_2026-08.zim`, ~25 GB, measured 24.77 GB) from kiwix.org. Download this repo's `kiwix_zhs_proxy.py`, `start.ps1` and `qrcode.min.js`.
2. Put them in one folder:
   ```
   C:\Kiwix\
   ├── kiwix-serve.exe
   ├── zim\wikipedia_zh_all_maxi_2026-08.zim
   ├── kiwix_zhs_proxy.py
   ├── qrcode.min.js
   └── start.ps1
   ```
3. Right-click `start.ps1` → Run with PowerShell. It starts Kiwix (8090), the proxy (8080), and opens the **access page** (`/lan`) in the browser.
4. Desktop: open `http://127.0.0.1:8080`.
5. Phone on the same Wi-Fi: open `http://<your-PC-IP>:8080` (find the IP with `ipconfig`). No app needed.

**Access page (easiest for phones)**: after launch, the browser opens `http://127.0.0.1:8080/lan`. It lists every usable address of this PC (Wi-Fi / hotspot, virtual adapters auto-filtered) with a QR code each — scan with your phone and you're in. Works on any network: home Wi-Fi, a phone hotspot (no data used), even with no internet at all.

Phone entry: open `http://<PC-IP>:8080` → you'll see the library list (1 book(s)) → tap the "维基百科" card to enter the home page. Direct link to an article: `http://<PC-IP>:8080/viewer#wikipedia_zh_all_maxi_2026-08/<article>`. Legacy links missing the ZIM name (`/content/<article>`) are auto-completed by the proxy, so no more 404.

### How it works

```
Browser ──> this proxy (8080) ──> Kiwix serve (8090) ──> ZIM offline file
              │
              ├─ /lan access page: lists all usable LAN addresses + QR codes
              └─ only for /content/... HTML pages:
                 OpenCC(tw2sp) converts text nodes → simplified
                 static assets (images/CSS/JS) pass through unchanged
```

Text nodes (`>text<`) are converted while `<script>/<style>/<pre>/<code>/<textarea>/<title>` blocks are skipped. A small LRU cache (80 entries) avoids repeated conversion.

Kiwix answers a bare "library-name-only" path (`/content/<zim>`) with a **302 redirect** to the home page (`User:The other Kiwix guy/Landing`). The proxy passes that 302 through to the browser verbatim (instead of following it internally), so the browser lands on the full path — URL and content stay in sync, and tapping cards/articles on a phone works reliably.

The `/lan` page is generated by the proxy itself: it parses `ipconfig`, lists every usable IPv4 (WSL/Docker/VMware virtual adapters auto-filtered), and renders QR codes in the browser with the bundled local `qrcode.min.js` — fully offline, zero Python dependencies.

### Why not convert at packaging time?

1. **Official ZIMs are rolling releases.** Wikipedia offline packs ship monthly; re-packaging means re-converting every article and rebuilding the index each time — high maintenance, quickly stale.
2. **Runtime conversion is cheap enough.** OpenCC is a native C++ binding; converting a single page takes tens of milliseconds. With the LRU cache it is imperceptible at home scale.

Also: Nginx/Caddy reverse proxies only solve forwarding — you still have to write the conversion yourself. This proxy (single file) bundles forward + convert + cache + logging in one file, simpler to deploy.

### Gotchas (three critical fixes)

1. **Forward the CSP header verbatim.** Kiwix content pages carry `Content-Security-Policy: ... sandbox allow-scripts allow-same-origin ...`, the basis of the iframe sandbox. Dropping it breaks iframe scripts → content loads but never renders (URL hash changes, page stays frozen).
2. **Force `Connection: close`.** With HTTP/1.1 keep-alive, large responses (e.g. the 1.3 MB article) may be truncated; the browser then waits forever per Content-Length → infinite spinner. Close the connection per response.
3. **404 / broken page on phone when tapping an article or the library card.** The old proxy followed Kiwix's 302 internally, so the browser URL stayed a short path while content was the home page → relative links mis-resolved → 404 rendering. Fixed by passing the 302 through to the browser (URL and content stay consistent), auto-completing the ZIM name on `/content/<article>`, and normalizing the trailing slash on `/content/<zim>/`.

### Security

For **home LAN use only** (PC & phone on the same Wi-Fi). Do not expose port 8080 to the public internet.

### Requirements & config

| Component | Notes |
|---|---|
| Python 3 | `pip install opencc-python-reimplemented` |
| Kiwix tools | `kiwix-serve.exe` (download from kiwix.org) |
| ZIM file | `wikipedia_zh_all_maxi_2026-08.zim` (~25 GB, measured 24.77 GB) |
| qrcode.min.js | bundled in this repo (MIT) — optional; without it the /lan page shows addresses without QR codes |

| Var | Default | Purpose |
|---|---|---|
| `KIWIX_UPSTREAM` | `http://127.0.0.1:8090` | Upstream Kiwix address |
| `KIWIX_PORT` | `8080` | Proxy listen port |
| `KIWIX_DEBUG=1` | off | Write access log (`proxy_access.log`) |
| `KIWIX_ZIM_ID` | `wikipedia_zh_all_maxi_2026-08` | ZIM name used when auto-completing missing library name |
| `KIWIX_DIR` / `ZIM_FILE` | (in start.ps1) | One-click start paths |

### License

MIT © 2026 FogToCloud
