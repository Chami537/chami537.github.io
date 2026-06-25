# 个人网站

Chami 的个人主页。前端纯手写 HTML/CSS/JS 零框架零依赖；后端 Python Flask 做无头 CMS + 微型 SSG。

## 技术栈
- **前端**：纯静态 HTML + 内联 CSS + 内联 JS，零框架零依赖
- **后端**：Python Flask + Markdown + Pillow（`requirements.txt`）
- **部署**：GitHub Pages `chami537.github.io`（自动从 master 分支部署）
- 无构建工具，无包管理器

## 结构
- `index.html` — 主站首页，5 个 section：Work(red) / Essays(yellow) / Photos(blue) / Music(green) / Contact(purple)
- `admin.html` — 管理面板（localhost:5000 访问）
- `manage.py` — Flask 后端 + 微型 SSG，管理照片/随笔/关于/友链/作品/联系方式
- `manage_launcher.py` / `manage.bat` — 一键启动脚本
- `data/` — JSON 数据文件（work / photos / music / essays / about / contact / friends）
- `essays/` — 生成的随笔 HTML
- `images/` — 原图 + `lg/` `md/` `sm/` 三级缩略图 + `essays/` 截图
- `music/` — 5 首 MP3
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
