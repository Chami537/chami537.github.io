# Chami537.github.io

Chami 的个人主页。 HTML/CSS/JS，零框架零依赖；Python Flask 做无头 CMS + 微型 SSG。

**[chami537.github.io](https://chami537.github.io)**

## Directory Map

- `index.html`, `admin.html`, `404.html` — GitHub Pages / Flask preview entry files.
- `assets/css/`, `assets/js/` — hand-written frontend styles and scripts.
- `backend/` — Flask CMS, API routes, SSG helpers, upload validation.
- `templates/` — Jinja2 templates for essays, archive, map, RSS, sitemap.
- `data/`, `md/` — editable site content sources.
- `images/`, `music/`, `tracks/` — public media served by the site.
- `tools/`, `tests/`, `.github/` — maintenance scripts, pytest suite, CI.
- `essays/`, `archive.html`, `map.html`, `rss.xml`, `sitemap.xml` — generated build output.

## Essay Tags

普通随笔保持轻量标签，例如 `生活, 随笔` 或 `摄影, 深圳`。

技术文章在 Admin 的 Essay 表单里用结构化字段填写：主类选 `技术`，再填技术主题和内容类型。首页第一层只展示主类；`安全`、`项目复盘`、`题解` 这类标签只作为 `技术` 下的子筛选出现。系统仍会保存为兼容旧数据的三段式标签：`技术` + 技术主题 + 内容类型，例如：

- `技术, Kotlin, 学习日志`
- `技术, Git, 踩坑`
- `技术, LeetCode, 题解, 滑动窗口`
- `技术, Flask, 安全, 项目复盘`
