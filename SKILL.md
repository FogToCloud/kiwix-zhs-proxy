---
name: kiwix-zhs-local-wiki
description: Deploy a fully offline, Simplified Chinese Wikipedia on a Windows PC (Kiwix + ~25GB ZIM package + local OpenCC proxy) and serve it over home Wi-Fi to phones/tablets with zero install on mobile. Use when the user wants 离线维基百科 / 中文维基百科简体 / Kiwix 本地部署, is tired of Traditional Chinese (繁体) Wikipedia, blocked mirrors, or wants a private family knowledge base without logging in.
---

# Offline Simplified Chinese Wikipedia on home LAN

You are deploying a personal, offline, **Simplified** Chinese Wikipedia that:

- runs entirely on one Windows PC, no external network needed after install;
- serves the whole home (phones, tablets, laptops) over the same Wi-Fi;
- requires **no app and zero storage on phones** — they just open a browser.

The stack is three open-source pieces:

1. **Kiwix** — official offline Wikipedia reader (`kiwix-serve`) on port `8090`.
2. **ZIM package** — the data file: `wikipedia_zh_all_maxi` (~25 GB, ~1.54 million articles). It is **Traditional Chinese** by default.
3. **zhs proxy** (`kiwix_zhs_proxy.py`, in this repo) — a small Python script on port `8080` that sits between the browser and Kiwix and converts every HTML page from Traditional to Simplified Chinese on the fly (OpenCC `tw2sp`), while images/CSS/JS pass through untouched.

The user opens `http://<PC-LAN-IP>:8080` and reads a Simplified Wikipedia.

## When NOT to use this skill

- User has no Windows PC they can keep on, or has < 25 GB free disk — stop and tell them, do not proceed.
- User wants to expose this server to the public internet — refuse. This proxy has **no auth**; it is for home LAN only (see Safety).
- User wants English/other-language Wikipedia — the proxy is Chinese-specific; point them to plain Kiwix.

## Pre-flight checks (do these first, report results to the user)

- OS: Windows (this flow targets Windows; Linux needs systemd unit, ask user).
- Disk: ≥ 25 GB free on the chosen drive.
- Python 3.9+ installed (`python --version`). Need `opencc-python-reimplemented` and `aiohttp`.
- Network: the 25 GB ZIM download can take hours; warn the user and pick a time when the PC can stay on. The ZIM comes from the official Kiwix download (download.kiwix.org). Do **not** download from random mirrors.

## Execution steps

### 1. Get the three pieces

- Kiwix Windows: from kiwix.org (kiwix-tools or Kiwix desktop).
- ZIM: `wikipedia_zh_all_maxi_*.zim` (the full all-articles package, NOT `nopic`/`mini`). ~24.8 GB.
- Proxy files from this repo: `kiwix_zhs_proxy.py` and `start.ps1`.

### 2. Directory layout

Put everything in one folder, e.g. `C:\Kiwix\`:

```
C:\Kiwix\
  kiwix-serve.exe        (or the Kiwix install)
  zim\wikipedia_zh_all_maxi_YYYY-MM.zim
  kiwix_zhs_proxy.py
  start.ps1
```

Tell the user the 25 GB lives on the **PC disk**; phones install nothing.

### 3. Configure the two ports

- Kiwix serves on `127.0.0.1:8090` by default.
- The zhs proxy must listen on `0.0.0.0:8080` (not `127.0.0.1`, otherwise the phone cannot reach it).
  - Set env var `KIWIX_HOST=0.0.0.0` (the bundled `start.ps1` already does this).
  - On first run, Windows Firewall will prompt — tell the user to check **Private networks** and Allow. If they miss it, add an inbound rule for TCP 8080.

### 4. Start

Run `start.ps1` (right-click → Run with PowerShell). It launches kiwix-serve and the proxy, then opens the browser.

### 5. Verify on the PC

Open `http://127.0.0.1:8080` — the Wikipedia home page must render in **Simplified Chinese**. If it is still Traditional, the proxy is not in the path. If pages are blank, see Pitfalls (CSP below).

### 6. Connect the phone

- On the PC run `ipconfig`, get the IPv4 address (e.g. `192.168.1.11`).
- Phone joins the same Wi-Fi, open `http://192.168.1.11:8080` in any browser. Done. No app install.

## Pitfalls (these all actually happened — check each)

1. **Phone can't connect.** Almost always the proxy is bound to `127.0.0.1`. Must be `0.0.0.0`. Second cause: Windows Firewall blocked 8080.
2. **Blank page after clicking a link, address bar changes but nothing renders.** You dropped or broke the upstream `Content-Security-Policy` / `Content-Type` headers when proxying. Copy Kiwix's response headers through unchanged except the HTML body.
3. **Big article loads forever / connection hangs.** Do not close the response early and set a wrong `Content-Length`. Stream the full upstream body to the client before closing; for large articles (1 MB+) the first open takes a few seconds — that is the ZIM read, not a crash.
4. **HEAD requests.** `do_HEAD` must return headers only, never a body.
5. **Encoding.** Pages are UTF-8; do not mangle non-ASCII when rewriting.
6. **Converted HTML must skip `<script>`, `<style>`, `<pre>`, inline code, and URL paths** — OpenCC `tw2sp` on raw HTML will corrupt JS strings and links. Only convert visible text nodes.
7. **First open of a long article is slow**, later loads are cached — tell the user so they don't think it's frozen.

## Acceptance criteria (only report success when ALL are true)

- [ ] `http://127.0.0.1:8080` on the PC shows a Simplified-Chinese Wikipedia home page.
- [ ] Click 3 different articles, navigate into them, and back — no stuck/hanging pages.
- [ ] A phone on the same Wi-Fi opens `http://<PC-IP>:8080` and reads the same Simplified page.
- [ ] Images and CSS load correctly (not just text).

## Safety / boundaries

- Bind `0.0.0.0` **only** so home devices can reach it. Never port-forward 8080 to the public internet — there is no login.
- The ZIM content is Wikipedia data under its own license (CC BY-SA / GFDL); personal offline use is fine, do not republish the whole ZIM.
- This is for a home LAN; remind the user the PC must be on (or set it to start with Windows) for phones to use it.

## Source

Code and setup script: search GitHub for `FogToCloud/kiwix-zhs-proxy`.
