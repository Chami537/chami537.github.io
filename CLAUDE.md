# 个人网站

Chami 的个人主页。前端纯手写 HTML/CSS/JS 零框架零依赖；后端 Python Flask 做无头 CMS + 微型 SSG。

## 技术栈
- **前端**：纯静态 HTML + 内联 CSS + 内联 JS，零框架零依赖
- **后端**：Python Flask + Jinja2 + Markdown + Pillow（`requirements.txt`）
- **部署**：GitHub Pages `chami537.github.io`（自动从 master 分支部署）
- 无构建工具，无包管理器

## 结构
- `index.html` — 主站首页，8 个 section（hero/about/work/stack/essays/photos/music/contact）
- `admin.html` — 管理面板（localhost:5000 访问）
- `manage.py` — CLI 入口（42 行），`python manage.py [build|sync-photos|set-gps]`
- `manage.bat` — 一键启动脚本
- `scripts/` — 辅助脚本（`gps_panel.bat`）
- **后端** `backend/`（1842 行单体 → 6 文件包）：
  - `data.py` — `load_json` / `atomic_write_json`
  - `app.py` — Flask 创建 + 静态文件路由
  - `routes.py` — 全部 41 个 `/api/*` CRUD 端点
  - `ssg.py` — Essay 辅助 + SSG 生成器（Jinja2 模板）
  - `photo_api.py` — 照片标签/日期/GPS PUT 端点
  - 导入链：`manage → backend.app → backend.routes → backend.ssg → backend.data`（单向无循环）
- `tools/` — 独立工具
  - `gps_panel.py` — 可视化 GPS 标注面板（端口 5001）
  - `process_images.py` — 图像流水线（全量同步模式）
- `templates/` — Jinja2 模板
  - `essay.html` — 随笔页模板
  - `rss.xml` — RSS 订阅源模板
  - `sitemap.xml` — 站点地图模板
  - `archive.html` — 归档页模板（年份分组 + 标签筛选 + 搜索）
  - `map.html` — 摄影足迹地图模板（Leaflet + GPX 轨迹）
- `data/` — JSON 数据文件（work / photos / music / essays / about / contact / friends / tracks / stack）
- `md/` — 随笔 Markdown 源文件（正源，git 追踪）
- `essays/` — 生成的随笔 HTML（构建产物，gitignore）
- `images/` — `lg/` `md/` `sm/` 三级缩略图 + `essays/` 随笔配图
- `raw_photos/` — 摄影原片（gitignore）
- `music/` — MP3 文件
- `tracks/` — GPX 轨迹文件
- `archive.html` / `map.html` / `rss.xml` / `sitemap.xml` — SSG 构建产物（gitignore）
- `.github/workflows/` — CI/CD（`python manage.py build`）
- 配色：**6 色体系**（红橙黄蓝绿紫）+ 滚动进度条（6 色渐变）+ 导航高亮

## 编辑须知
- **前端**：改 `index.html`（CSS 在 `<style>`，JS 在 `<script>`）
- **管理面板**：改 `admin.html`
- **后端**（`backend/`）：
  - 数据工具 → `backend/data.py`
  - Flask 路由 → `backend/routes.py`
  - SSG / 随笔逻辑 → `backend/ssg.py`
  - 静态文件路由 → `backend/app.py`
  - 照片 API → `backend/photo_api.py`
  - CLI 入口 → `manage.py`（根目录）
- **运行管理面板**：`python manage.py`（localhost:5000）
- `python manage.py build` — 生成全站静态文件（CI 也用）
- `python manage.py sync-photos` — 从 raw_photos/ 全量同步照片 EXIF 到 photos.json
- 内容（照片/作品/随笔元数据等）通过管理面板操作，数据存入 `data/`
- GitHub Pages 自动从 master 分支部署

## 存档

### 新增（2026-06-29）
- `index.css` / `index.js` — index.html 的 CSS/JS 已拆分到独立文件
- `templates/includes/` — 模板共享组件（base.css, nav, footer, theme-init, theme.js）
- essay.html 从 Python `.format()` 升级到 Jinja2 渲染（统一模板引擎）
- `_cache_bust_index()` — build 时自动给 CSS/JS 链接加 `?v=<timestamp>`
- 随笔重生成只同步受影响文章（不再全量循环）

## 待办
- 可选：Admin 面板登录鉴权（纯本地跑，物理机密码即 Auth，暂不需要）

## Claude Code 八荣八耻
- 以瞎猜接口为耻，以认真查询为荣
- 以模糊执行为耻，以寻求确认为荣
- 以臆想业务为耻，以人类确认为荣
- 以创造接口为耻，以复用现有为荣
- 以跳过验证为耻，以主动测试为荣
- 以破坏架构为耻，以遵循规范为荣
- 以假装理解为耻，以诚实无知为荣
- 以盲目修改为耻，以谨慎重构为荣


## 2026-07-01 11:38
refactor: test auto-save


## 2026-07-01 11:54
test
