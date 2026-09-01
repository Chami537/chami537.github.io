# Chami537.github.io

Chami 的个人主页，以及配套的本地内容管理与静态发布工具。

前端全部使用原生 HTML、CSS 和 JavaScript；后端由 Python Flask 提供带登录保护的管理面板、内容 API 与微型静态站点生成器（SSG）。发布后的站点托管在 GitHub Pages，不依赖在线后端。

[访问网站](https://chami537.github.io)

## 功能

- 展示个人介绍、项目、技术栈、随笔、摄影、轨迹和音乐。
- 在本地管理面板中编辑站点内容、上传媒体并预览结果。
- 使用 Markdown 编写随笔，生成独立文章页、归档、RSS、Sitemap 和地图页面。
- 支持随笔分层标签、置顶、密码保护、加密存储与浏览器端解密。
- 扫描项目内 Markdown 或可选的 Obsidian Vault，预览并选择要同步的本地改动。
- 处理照片缩略图、EXIF、GPS、照片故事与地图展示。
- 可选接入 DeepSeek，提供写作辅助、风格分析和站点内容审查。
- 构建前执行站点健康检查，CI 通过 pytest 和 Playwright 浏览器冒烟测试后部署。

## 技术栈

- 前端：HTML、CSS、原生 JavaScript
- 后端：Python 3.11、Flask、Jinja2、Markdown、Pillow、cryptography
- 测试：pytest、Playwright Chromium（CI 浏览器冒烟）
- 部署：GitHub Actions、GitHub Pages

项目没有前端框架、打包器或 npm 运行时依赖。

## 快速开始

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py
```

启动后访问：

- 管理面板：<http://127.0.0.1:5000>
- 网站预览：<http://127.0.0.1:5000/index.html>

建议先在项目根目录创建 `.env` 并设置管理密码：

```dotenv
ADMIN_PASSWORD=replace-with-a-strong-password
FLASK_SECRET_KEY=replace-with-a-random-secret
```

`.env` 只用于本地配置，不应提交到仓库。

## 常用命令

```powershell
# 启动管理面板和本地预览
python manage.py

# 增量构建静态站点
python manage.py build

# 强制重建全部随笔
python manage.py build --force

# 从 raw_photos/ 处理并同步照片
python manage.py sync-photos

# 写入照片 GPS
python manage.py set-gps <filename> <lat> <lng>

# 运行完整测试
python -m pytest -q
```

`python manage.py build` 会先执行健康检查，然后生成文章与 feeds、刷新静态资源 cache bust，并尝试更新 GitHub stars。构建可能修改内容或生成文件，提交前请检查 `git status` 和 diff。

## 环境变量

| 变量 | 用途 |
| --- | --- |
| `ADMIN_PASSWORD` | 管理面板登录密码 |
| `FLASK_SECRET_KEY` | Flask session 签名密钥；未设置时每次启动随机生成 |
| `DEEPSEEK_API_KEY` | 启用 AI 编辑与内容审查 |
| `OBSIDIAN_VAULT_DIR` | 可选的 Obsidian Vault 路径 |
| `TRUSTED_ORIGINS` | 允许执行写操作的来源，使用逗号分隔 |
| `SESSION_COOKIE_SECURE` | 设为 `1`/`true` 时只通过 HTTPS 发送 session cookie |
| `BROWSER_SMOKE_REQUIRED` | 设为 `1` 时浏览器测试不可跳过；CI 已启用 |

## 内容工作流

### 管理面板

运行 `python manage.py` 并登录后，可以管理随笔、照片、项目、音乐、轨迹、社交链接和其他首页内容。结构化内容写入 `data/`，随笔正文写入 `md/`。

### 本地 Markdown 与 Obsidian

在 `md/*.md` 中修改已注册随笔后，可从管理面板扫描本地改动、查看来源并选择同步。若设置 `OBSIDIAN_VAULT_DIR`，面板也会尝试按现有文章标题匹配 Vault 根目录中的 Markdown 笔记。

同步不会自动创建缺少元数据的文章。密码保护文章的本地源必须保持为项目认可的密文格式，避免明文进入可发布文件。

### 随笔标签

普通随笔使用轻量标签，例如 `生活, 随笔` 或 `摄影, 深圳`。

技术文章在管理面板中填写主类、技术主题和内容类型，最终仍保存为兼容旧数据的标签列表，例如：

- `技术, Kotlin, 学习日志`
- `技术, Git, 踩坑`
- `技术, LeetCode, 题解, 滑动窗口`
- `技术, Flask, 安全, 项目复盘`

首页第一层展示主类；技术主题和内容类型作为第二层筛选。

## 目录结构

```text
.
├── index.html / admin.html       # 公开主页与本地管理面板
├── assets/css/ / assets/js/      # 手写前端资源
├── backend/                      # Flask、API、业务服务、SSG 与存储层
├── templates/                    # Jinja2 页面与 feeds 模板
├── data/                         # 结构化内容源
├── md/                           # 随笔 Markdown 正源
├── images/ / music/ / tracks/    # 公开媒体
├── raw_photos/                   # 本地摄影原片（不提交）
├── tools/                        # 图片处理工具
├── tests/                        # pytest 与浏览器测试
└── .github/workflows/            # 构建、测试、部署与 stars 更新
```

`essays/`、`archive.html`、`map.html`、`rss.xml` 和 `sitemap.xml` 由构建生成，通常不作为手工编辑的内容源。

## 测试与部署

本地完整测试：

```powershell
python -m pytest -q
```

修改前端 JavaScript 时，还可以先做语法检查：

```powershell
node --check assets/js/<changed-file>.js
```

推送到 `master` 后，GitHub Actions 会依次执行：

1. 构建站点并运行强制 Playwright Chromium 冒烟测试。
2. 运行 pytest（构建产物测试除外）。
3. 再次构建并验证静态产物。
4. 部署到 GitHub Pages。

另一个定时工作流每天刷新 `data/work.json` 中的 GitHub stars，因而本地推送前可能需要先同步远端更新。
