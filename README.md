# kiwix-zhs-proxy

**Kiwix 离线维基百科的简体中文代理** —— 把 Kiwix 官方中文维基 ZIM 包（繁体）在**服务端**转成简体，浏览器零脚本、零注入，电脑和手机浏览器直接就能用。

## 为什么需要它

- Kiwix 官方 `wikipedia_zh_all` 中文维基离线包内容是**繁体**（zh-Hant / zh-TW 变体），看着累。
- 之前尝试在浏览器端用脚本转简体，会注入 JS、偶发"点第 4 个词条就卡死"。
- 本方案把简繁转换搬到**服务端**：浏览器收到的就是简体 HTML，页面里没有一行注入脚本，彻底绕开前端卡死问题。

## 工作原理

```
浏览器 ──> 本代理 (8080) ──> Kiwix 服务 (8090) ──> ZIM 离线包
              │
              └─ 仅对 /content/... 的 HTML 页面：
                 OpenCC(tw2sp) 转换文本节点 → 返回简体
                 静态资源（图片/CSS/JS）原样转发
```

- 转换只针对**文本节点**（`>文字<`），自动跳过 `<script>/<style>/<pre>/<code>/<textarea>/<title>` 等，不会破坏脚本和样式。
- 带一个简单 LRU 缓存（80 条），同一页面短时间内重复访问不重复转换。

## 环境要求

| 组件 | 说明 |
|---|---|
| Python 3 | 需要 `pip install opencc-python-reimplemented`（或 `opencc`） |
| Kiwix 工具 | `kiwix-serve.exe`（Windows 版，从 kiwix.org 下载） |
| ZIM 文件 | `wikipedia_zh_all_maxi_2026-08.zim`（在 kiwix.org 下载，几十 GB） |

## 快速开始（Windows）

1. 按你的环境修改 `start.ps1` 顶部的路径变量（Kiwix 安装目录、ZIM 文件位置）。
2. 右键 `start.ps1` → 用 PowerShell 运行，或：
   ```powershell
   powershell -ExecutionPolicy Bypass -File start.ps1
   ```
   脚本会自动：启动 `kiwix-serve`(8090) → 启动本代理(8080) → 打开浏览器。

3. 电脑浏览器打开（也可以自己输入）：
   ```
   http://127.0.0.1:8080/viewer#wikipedia_zh_all_maxi_2026-08/User%3AThe_other_Kiwix_guy/Landing
   ```

### 手动启动（不想用脚本时）

```bash
# 终端 1：启动 Kiwix 服务
kiwix-serve.exe --port=8090 wikipedia_zh_all_maxi_2026-08.zim

# 终端 2：启动简体代理
python kiwix_zhs_proxy.py
```

## 手机访问（同一 Wi-Fi）

手机浏览器直接访问电脑的局域网 IP：

```
http://192.168.1.11:8080/viewer#wikipedia_zh_all_maxi_2026-08/User%3AThe_other_Kiwix_guy/Landing
```

（把 `192.168.1.11` 换成你电脑的实际 IP，Windows 下用 `ipconfig` 查看；手机无需装任何 App，浏览器即可。）

> 注意：Windows 防火墙需放行 8080 端口（首次启动浏览器访问时会弹窗，允许即可；或手动在防火墙入站规则里添加）。

## 配置

| 环境变量 | 默认值 | 作用 |
|---|---|---|
| `KIWIX_UPSTREAM` | `http://127.0.0.1:8090` | 上游 Kiwix 服务地址 |
| `KIWIX_PORT` | `8080` | 本代理监听端口 |
| `KIWIX_DEBUG=1` | 关 | 开启访问日志（写在本脚本同目录 `proxy_access.log`） |

## 踩坑记录（本项目的两个关键修复）

代理转发响应头时有两个细节，做错会导致 Kiwix viewer 出现"页面一直加载 / 内容不切换"：

1. **CSP 头必须原样转发**。Kiwix 内容页响应带 `Content-Security-Policy: ... sandbox allow-scripts allow-same-origin ...`，它是 iframe 内容沙箱的依据。丢了这个头，iframe 内脚本行为异常 → 内容页加载后不渲染（地址栏 hash 变了、页面不动）。
2. **强制 `Connection: close`**。用 HTTP/1.1 keep-alive 复用连接转发大页面（如"沈阳市"条目 1.3MB）时响应体可能传不完整，浏览器按 Content-Length 死等剩余字节 → iframe 永远转圈。每个响应显式关闭连接即可。

## 停止

```powershell
powershell -ExecutionPolicy Bypass -File stop.ps1
```
或在任务管理器结束 `kiwix-serve` 与 `python`（代理）进程。

## 目录结构

```
kiwix-zhs-proxy/
├── kiwix_zhs_proxy.py   # 代理主脚本（单文件，无第三方 Web 框架）
├── start.ps1            # 一键启动（kiwix-serve + 代理 + 打开浏览器）
├── stop.ps1             # 停止
└── README.md
```

## License

MIT
