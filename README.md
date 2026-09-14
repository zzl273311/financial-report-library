# 财报分析 · 报告库

**线上地址：<https://zzl273311.github.io/financial-report-library/>**

一个纯静态的上市公司财报分析报告浏览平台。左侧按「公司 → 期次」列出报告，点击后右侧直接呈现该期次的完整分析报告。

无需构建、无后端、无依赖，可直接双击 `index.html` 打开，也可托管到 GitHub Pages。

---

## 界面

```
┌──────────────────────┬──────────────────────────────────────────────┐
│ 财报分析 · 报告库       │  招商银行 600036.SH / 2006—2026H1    [刷新][PDF][新窗口] │
│ ──────────────────── │ ──────────────────────────────────────────── │
│ 🔍 搜索公司/代码/期次    │                                              │
│ 5 家公司 · 5 份报告     │            （报告正文 iframe）                │
│ ──────────────────── │                                              │
│ ▸ 招商银行             │                                              │
│    2006 — 2026H1     │                                              │
│ ▸ 江苏银行             │                                              │
│ ▸ 藏格矿业             │                                              │
│ ▸ 五粮液 × 贵州茅台     │                                              │
│ ▸ 英矽智能             │                                              │
└──────────────────────┴──────────────────────────────────────────────┘
```

- **左侧栏**：公司分组（可折叠），每组下按报告期次排列；显示期次、周期说明、生成日期、PDF 页数。
- **搜索**：公司名 / 股票代码 / 期次 / 标签 / 摘要全文匹配，`⌘K`（或 `Ctrl+K`）聚焦，`Esc` 清空。
- **顶部工具条**：`刷新` 重载当前报告、`PDF` 下载同版 PDF、`新窗口` 全屏打开报告。
- **路由**：使用 URL hash，形如 `#/cmb/cmb-2006-2026h1`，可直接分享单份报告的链接。
- **欢迎页**：未选择报告时展示全部报告卡片（含核心指标与摘要）。
- **响应式**：窄屏（≤880px）左侧栏收起为抽屉，由工具条左上角按钮呼出。

---

## 目录结构

```
report-platform/
├── index.html                  平台外壳（左侧栏 + 工具条 + iframe）
├── assets/
│   ├── style.css               样式（Kami 羊皮纸配色，与报告正文一致）
│   └── app.js                  交互逻辑（渲染、搜索、hash 路由）
├── data/
│   └── reports.js              报告清单（唯一需要编辑的数据文件）
├── reports/<slug>/            报告 HTML（自包含单文件）
├── docs/<slug>/               报告 PDF（下载用）
├── .nojekyll                   禁用 GitHub Pages 的 Jekyll 处理
└── README.md
```

当前收录（`<slug>` 即目录名）：

| slug | 公司 / 组合 | 代码 | 期次 | 报告页数 |
|---|---|---|---|---|
| `cmb` | 招商银行 | 600036.SH / 03968.HK | 2006 — 2026H1 | 18 |
| `jsbank` | 江苏银行 | 600919.SH | 2011 — 2026H1 | 14 |
| `zangge` | 藏格矿业 | 000408.SZ | 2015 — 2026H1 | 7 |
| `wuliangye-moutai` | 五粮液 × 贵州茅台 | 000858.SZ / 600519.SH | 2016 — 2026H1 | 21 |
| `insilico` | 英矽智能 | HKEX: 3696 | IPO — 2026H1 | 5 |

---

## 本地预览

### 方式一：直接打开（零依赖）

双击 `index.html` 即可。报告用 `<script>` 而非 `fetch` 加载清单，因此 `file://` 协议下也能工作。若个别浏览器拦截了 `file://` 下的 iframe，页面底部会出现提示条。

### 方式二：本地服务器（推荐）

```bash
cd report-platform
python3 -m http.server 8080
# 打开 http://localhost:8080
```

---

## 新增一份报告

1. 把报告 HTML 复制到 `reports/<slug>/`，PDF（可选）复制到 `docs/<slug>/`。
2. 打开 `data/reports.js`，在对应公司的 `reports` 数组里追加一条：

```js
{
  id: "cmb-2024q3",                       // 全局唯一，用于 hash 路由
  title: "招商银行 2024 年三季报分析",       // 工具条标题
  period: "2024Q3",                       // 左侧栏显示的期次
  periodNote: "单季度 · 含同比拆解",          // 期次下方的说明
  publishedAt: "2026-09-14",              // 生成日期
  html: "reports/cmb/xxx.html",           // 相对路径
  pdf: "docs/cmb/xxx.pdf",                // 可省略；省略则不显示 PDF 按钮
  pages: 12,                              // 可省略
  tags: ["净息差", "拨备"],                 // 参与搜索
  metrics: [                              // 欢迎页卡片上的四个核心指标，可省略
    { value: "3,375亿", label: "2025 营业收入", note: "+0.01%" }
  ],
  summary: "……"                            // 欢迎页卡片摘要，可省略
}
```

若是一个全新的公司，则在 `companies` 数组里新增一项（`id` 必须唯一，且与 `reports/<slug>/` 目录名一致）。

> `reports/<slug>/` 目录名建议用 ASCII，避免个别静态服务器对中文路径的 URL 编码处理差异。

---

## 部署到 GitHub Pages

```bash
cd report-platform
git init -b main
git add -A
git commit -m "feat: 财报分析报告库"
git remote add origin git@github.com:<用户名>/<仓库名>.git
git push -u origin main
```

本仓库的 Pages 已启用（`main` 分支 root 目录），线上地址：

**<https://zzl273311.github.io/financial-report-library/>**

仓库：<https://github.com/zzl273311/financial-report-library>

换到新仓库时，在 GitHub 仓库 **Settings → Pages** 里：Source 选 `Deploy from a branch`，Branch 选 `main`，目录选 `/ (root)`，保存后等 1–2 分钟。

`.nojekyll` 已就位，可确保 `reports/`、`assets/` 等目录被原样发布。仓库根目录的 `index.html` 会被 Pages 作为首页。

更新报告时：替换 `reports/` 下的文件、改 `data/reports.js`，然后 `git add -A && git commit -m "..." && git push` 即可，Pages 会自动重新构建。

---

## 说明

- 报告 HTML 为自包含单文件，只引用外部思源仓耳今楷字体 CDN（`cdn.jsdelivr.net/gh/tw93/Kami`），断网时会回退到系统衬线字体。
- 平台自身不收集任何数据，所有内容均为静态文件。
