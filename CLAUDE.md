# 个人网站

Chami 的个人主页。前端纯手写 HTML/CSS/JS 零框架零依赖；后端 Python Flask 做无头 CMS + 微型 SSG。

## 技术栈
- **前端**：纯静态 HTML + CSS + JS，零框架零依赖
- **后端**：Python Flask + Jinja2 + Markdown + Pillow（`requirements.txt`）
- **部署**：GitHub Pages `chami537.github.io`（自动从 master 分支部署）
- 无构建工具，无包管理器
- **测试**：pytest（46 个用例）

## 结构

### 前端
- `index.html` — 主站首页，8 个 section
- `index.css` / `index.js` — 主站样式/逻辑
- `admin.html` — 管理面板（localhost:5000，需登录）
- `admin.css` — 管理面板样式
- `admin.js` — 管理面板核心（认证 + 全局 + 标签页 + About/README + Tracks）
- `admin-content.js` — Work/Contact/Friends/Music/Stack/Git CRUD
- `admin-essays.js` — 随笔列表 + 标签系统 + 置顶 + Markdown 编辑器
- `admin-photos.js` — 照片网格 + 照片标签 + 地图编辑器
- `.editorconfig` — 编辑器统一配置

### 后端 `backend/`
- `data.py` — `load_json` / `atomic_write_json` + 路径常量 + EXIF 格式化
- `crud.py` — 共享 CRUD 辅助（index 式和 id 式两套）
- `app.py` — Flask 创建 + 静态文件路由 + 鉴权守卫
- `auth.py` — 登录/登出（session + 密码，默认 "chami"，`ADMIN_PASSWORD` 环境变量覆盖）
- `ssg.py` — Essay 辅助 + SSG 生成器（Jinja2 模板）
- `routes/` — 41 个 `/api/*` CRUD 端点（10 个子模块：about/contact/essays/friends/git_api/music/photos/readme/stack/work）
- 导入链：`manage → routes → ssg → data`（单向）；`routes/*` 子模块反向 `import app` 注册 `@app.route`，形成 Flask 模式三角引用（非循环依赖 bug）

### 模板 `templates/`
- `essay.html` — 随笔页模板
- `rss.xml` / `sitemap.xml` / `archive.html` / `map.html` — SSG 构建产物模板
- `includes/` — 共享组件（base.css / nav / footer / theme-init / theme.js）

### 数据与资源
- `data/` — JSON 数据文件（about / contact / essays / friends / music / photos / stack / tracks / work）
- `md/` — 随笔 Markdown 源文件（正源，git 追踪）
- `essays/` — 生成的随笔 HTML（构建产物，gitignore）
- `images/` — `lg/` `md/` `sm/` 三级缩略图 + `essays/` 随笔配图
- `raw_photos/` — 摄影原片（gitignore）
- `music/` — MP3 文件
- `tracks/` — GPX 轨迹文件
- `archive.html` / `map.html` / `rss.xml` / `sitemap.xml` — SSG 构建产物（gitignore）

### 工具与 CI
- `manage.py` — CLI 入口，`python manage.py [build|sync-photos|set-gps]`
- `manage.bat` — 一键启动脚本
- `tools/process_images.py` — 图像流水线（全量同步）
- `tests/` — pytest（46 个用例，test_routes.py + test_ssg.py + conftest.py）
- `.github/workflows/` — CI/CD（pytest → build → deploy）

## 配色
6 色体系（红橙黄蓝绿紫）+ 滚动进度条（6 色渐变）+ 导航高亮

## 编辑须知
- **前端**：`index.html` + `index.css` + `index.js`
- **管理面板**：`admin.html` + `admin.css` + `admin-*.js` 四个模块
- **后端**：`backend/` 包
  - 数据工具 → `backend/data.py`
  - CRUD 辅助 → `backend/crud.py`
  - Flask 路由 → `backend/routes/*.py`
  - SSG / 随笔逻辑 → `backend/ssg.py`
  - 静态文件 + 鉴权 → `backend/app.py`
  - CLI 入口 → `manage.py`
- **运行管理面板**：`python manage.py`（localhost:5000，密码登录）
- `python manage.py build` — 生成全站静态文件 + cache bust + GitHub stars
- `python manage.py sync-photos` — 从 raw_photos/ 全量同步照片 EXIF
- 内容通过管理面板操作，数据存入 `data/`
- GitHub Pages 自动从 master 分支部署

## 存档

### 2026-07-02
- `admin.js` 拆分为 4 文件（core/content/essays/photos）
- Admin 内联样式 → `admin.css` CSS 类（+90/-44 行）
- `_parse_date()` 加 `include_time` 参数，消除 `_sync_essay_html` 日期二次解析
- fix: `request` 导入缺失、登录浮层默认显示、登录触发 beforeunload
- feat: Admin 面板登录鉴权（Flask session + 密码，`TESTING` 模式跳过）
- `list_essays` 预计算 `date_display`，`index.js` 删除手写 MONTHS 数组（-13 行）
- `requirements.txt` 加 `python-multipart`
- `backend/crud.py` — 共享 CRUD 辅助（`list_all` / `create_item` / `update_item_by_index` / `update_item_by_id` / `delete_item_by_index` / `delete_item_by_id`）
- contact/friends/work/music 4 文件 188→125 行（+crud.py 56 行）
- 删标签导航 YAGNI（`_build_tag_nav_json` + 客户端 JS ~52 行）
- 补 `test_toggle_pin` + `test_cache_bust_assets`（测试 41→46）
- 加 `.editorconfig`
- `_cache_bust_index()` → `_cache_bust_assets()`（支持多 JS 文件）
- 音乐播放器自动连续播放（`musicEndHandler` 播完自动 click 下一首）
- 补 auth 测试 5 条 + Music/Work CRUD 测试 2 条（测试 46→53）

### 2026-06-29
- `index.css` / `index.js` — index.html 的 CSS/JS 已拆分到独立文件
- `templates/includes/` — 模板共享组件
- essay.html 升级到 Jinja2 渲染
- `_cache_bust_assets()` — build 时给 CSS/JS 链接加 `?v=<timestamp>`
- 随笔重生成只同步受影响文章
- `backend/photo_api.py` 合并到 `backend/routes/photos.py`
- `tools/gps_panel.py` + 相关 `.bat` 文件删除（功能由 admin 照片编辑器替代）
- admin.js 拖拽去重（`_dragStart`/`_dragOver`/`_dragEnd` + `_dragState`）
- `_parse_date()` 用 `datetime.strptime` 替代手工拆字符串
- `atomic_write()` 合并进 `atomic_write_json()`（消除单调用者死包装）
- `routes/__init__.py` 通配符导入 → 显式模块导入
- `manage.py` 复用 `data.py` 路径常量
- `deleteTagGlobal()` 死代码删除

## Claude Code 八荣八耻
- 以瞎猜接口为耻，以认真查询为荣
- 以模糊执行为耻，以寻求确认为荣
- 以臆想业务为耻，以人类确认为荣
- 以创造接口为耻，以复用现有为荣
- 以跳过验证为耻，以主动测试为荣
- 以破坏架构为耻，以遵循规范为荣
- 以假装理解为耻，以诚实无知为荣
- 以盲目修改为耻，以谨慎重构为荣



