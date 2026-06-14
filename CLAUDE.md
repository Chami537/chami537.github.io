# 个人网站

许夏源的个人主页，纯手写 HTML/CSS/JS，零框架零依赖。

## 技术栈
- 纯静态 HTML + 内联 CSS + 内联 JS
- 无构建工具，无包管理器
- 部署在 GitHub Pages（手动推送 `index.html`）

## 结构
- `index.html` — 唯一文件，包含全部内容（Hero / Work / Photos / Music / Contact）
- 4 个 section：Work(red)、Photos(blue)、Music(green)、Contact(purple)
- 滚动进度条 + 导航高亮
- 配色：5 色体系（红蓝黄绿紫）

## 编辑须知
- 改任何内容都在 `index.html` 里
- CSS 在 `<style>` 标签内，JS 在 `<script>` 标签内
- 没有 .git，需要手动初始化或部署

## 待办
- 可选：拆分 CSS/JS 到独立文件
