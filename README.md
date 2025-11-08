<h1 align="center">💦 BPB Panel</h1>

### 🌏 Readme in [Farsi](README_fa.md)

<p align="center">
  <img src="docs/assets/images/Panel.jpg">
</p>
<br>

## Introduction
This project is dedicated to developing a user panel for the [Cloudflare-workers/pages proxy script](https://github.com/yonggekkk/Cloudflare-workers-pages-vless) created by [yonggekkk](https://github.com/yonggekkk). The panel offers two deployment options: 
- **Worker** deployment
- **Pages** deployment
<br>

🌟 If you found **BPB Panel** valuable, Your donations make all the difference 🌟
- **USDT (BEP20):** `0x111EFF917E7cf4b0BfC99Edffd8F1AbC2b23d158`

## Features

1. **Free**: No cost involved.
2. **User-Friendly Panel:** Designed for easy navigation, configuration and usage.
3. **Support Fragment:** Provides support for fragment functionality.
4. **Block Ads. and Porn (Optional)**
5. **Bypass Iran and LAN (Optional)**
6. **Full routing rules:** Bypassing Iran, Blocking Ads, Malwares, Phishing... for Sing-box.
7. **Chain Proxy:** Capable of adding a chain proxy to fix IP.
8. **Supports Wide Range of Clients:** Offers subscription links for Xray and Sing-box core clients.
9. **Subscription Link (JSON):** Provides subscription link for JSON configs.
10. **Password-Protected Panel:** Secure your panel with password protection.
11. **Custom Cloudflare Clean IP:** Ability to use online scanner and setting up clean IP-domains.
12. **Warp configs:** Provides Warp and Warp on Warp subscription.
<br>

## How to use:
- [Installation (Pages)](docs/pages_installation_fa.md)

- [Installation (Worker)](docs/worker_installation_fa.md)

- [How to use](docs/configuration_fa.md)

- [FAQ](docs/faq.md)
<br>

## Supported Clients
| Client  | Version | Fragment |
| :-------------: | :-------------: | :-------------: |
| **v2rayNG**  | 1.8.19 or higher  | :heavy_check_mark: |
| **v2rayN**  | 6.42 or higher  | :heavy_check_mark: |
| **Nekobox**  |   | :x: |
| **Sing-box**  | 1.8.10 or higher  | :x: |
| **Streisand**  |   | :heavy_check_mark: |
| **V2Box**  |   | :x: |
| **Shadowrocket**  |   | :x: |
| **Nekoray**  |   | :heavy_check_mark: |
| **Hiddify**  |   | :x: |


---

## Stargazers Over Time
[![Stargazers Over Time](https://starchart.cc/bia-pain-bache/BPB-Worker-Panel.svg?variant=adaptive)](https://starchart.cc/bia-pain-bache/BPB-Worker-Panel)

---

### Special Thanks
- CF-vless code author [3Kmfi6HP](https://github.com/3Kmfi6HP/EDtunnel)
- CF preferred IP program author [badafans](https://github.com/badafans/Cloudflare-IP-SpeedTest), [XIU2](https://github.com/XIU2/CloudflareSpeedTest)

---

For a detailed tutorial on the core script, please refer to [Yongge’s blog and video tutorials](https://ygkkk.blogspot.com/2023/07/cfworkers-vless.html).

---

## Utility Scripts

### YouTube Keyword Insights

The repository now includes a helper script for researching YouTube content ideas. It can collect keyword suggestions, high-performing video titles, channel tags, and trending topics without requiring the official YouTube Data API.

```bash
cd scripts
node youtube_insights.js --keyword "旅行 vlog" --region TW --language zh-TW
```

#### 使用指南（中文）

1. **安装 Node.js**：脚本基于原生 Node.js API 开发，推荐使用 Node.js 18 或更新版本。
2. **进入脚本目录**：在仓库根目录执行 `cd scripts`。
3. **运行脚本**：执行 `node youtube_insights.js --keyword "你的關鍵詞"` 即可开始分析。
4. **可选参数**：
   - `--region`：设置结果的区域代码，例如 `TW`（台湾）、`US`（美国）。
   - `--language`：设置界面语言代码，例如 `zh-TW`（繁体中文）、`en`（英文）。
   - `--results`：指定要分析的热门视频数量，默认 `5`。
   - `--trending`：指定要抓取的趋势视频数量，默认 `10`。
   - `--hot-keywords`：指定要返回的热门关键词数量，默认 `20`。
5. **查看结果**：脚本会输出一份 JSON 报告，其中包含：
   - `suggestions`：YouTube 提示的相关关键词。
   - `topVideos`：搜索结果中热门视频的标题、频道、观看数、标签等信息。
   - `bestVideo`：根据观看数挑选出的表现最佳视频。
   - `trending.hotKeywords`：趋势视频中出现频率最高的关键词。

> 示例输出会直接打印在终端中，可使用 `> output.json` 将结果保存为文件以便进一步分析。

#### Supported options

| Flag | Description |
| ---- | ----------- |
| `-k`, `--keyword` | Keyword or phrase to analyze (required). |
| `--region` | Two-letter region code used to localize results. |
| `--language` | Interface language code for localized responses. |
| `--results` | Number of top videos to inspect (default: 5). |
| `--trending` | Number of trending videos to fetch (default: 10). |
| `--hot-keywords` | Number of aggregated hot keywords to return (default: 20). |

The script prints a JSON report summarizing keyword suggestions, related searches, detailed video metadata (including tags), and popular trending keywords for rapid research.
