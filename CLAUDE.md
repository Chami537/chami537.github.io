# 个人网站

Chami 的个人主页。前端纯手写 HTML/CSS/JS 零框架零依赖；后端 Python Flask 做无头 CMS + 微型 SSG。

## 技术栈
- **前端**：纯静态 HTML + 内联 CSS + 内联 JS，零框架零依赖
- **后端**：Python Flask + Markdown + Pillow（`requirements.txt`）
- **部署**：GitHub Pages `chami537.github.io`（自动从 master 分支部署）
- 无构建工具，无包管理器

## 结构
- `index.html` — 主站首页，5 个 section + Photography Grid/Map 双视图
- `admin.html` — 管理面板（localhost:5000 访问）
- `manage.py` — Flask 后端 + 微型 SSG，管理所有内容
- `manage.bat` — 一键启动脚本
- `tools/` — 独立工具
  - `gps_panel.py` — 可视化 GPS 标注面板（照片坐标 + 日期编辑）
  - `process_images.py` — 自动化图像流水线（原片 → 缩略图 + EXIF）
- `templates/` — Jinja2 模板
  - `essay.html` — 随笔页模板
- `data/` — JSON 数据文件（work / photos / music / essays / about / contact / friends / tracks）
- `md/` — 随笔 Markdown 源文件（正源，git 追踪）
- `essays/` — 生成的随笔 HTML（构建产物，gitignore）
- `images/` — `lg/` `md/` `sm/` 三级缩略图 + `essays/` 随笔配图
- `raw_photos/` — 摄影原片（gitignore）
- `music/` — 5 首 MP3
- `tracks/` — GPX 轨迹文件
- `archive.html` / `map.html` / `rss.xml` / `sitemap.xml` — SSG 构建产物（gitignore）
- `.github/workflows/` — CI/CD 自动构建部署
- 配色：5 色体系（红黄蓝绿紫）+ 滚动进度条（五色渐变）+ 导航高亮

## 编辑须知
- **前端**：改 `index.html`（CSS 在 `<style>`，JS 在 `<script>`）
- **管理面板**：改 `admin.html`
- **后端/内容逻辑**：改 `manage.py`
- **运行管理面板**：`python manage.py`（localhost:5000）
- 内容（照片/作品/随笔元数据等）通过管理面板操作，数据存入 `data/`
- GitHub Pages 自动从 master 分支部署

## 待办
- 可选：拆分 CSS/JS 到独立文件
