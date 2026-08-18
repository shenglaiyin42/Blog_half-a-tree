# 半棵斋个人博客

这是“半棵斋｜Half a Tree”的静态个人博客仓库。

正式网站：[半棵斋](https://halfatree.page/)

## 仓库内容

- `content/posts/`：已发布文章的 Markdown 原稿；这是文章正文的唯一正式来源。
- `content/originals/`：收到时保留的原始文稿备份。
- `articles/`：公开文章页面由发布流程生成；请不要把它作为日常改稿的位置。
- `文章模板.md`：项目当前唯一的文章模板；所有新文章都从这份文件生成。
- `发布指南.md`：发布和修改文章的说明。
- `site-data.js`：Writing、Topics、Archive 与 Statistics 共用的唯一文章数据源，由发布脚本自动更新。
- `now/`：当前 Topics 与全部 Writing 页面。
- `site-statistics.js`：首页简洁统计所使用的日期与字数计算逻辑。

## 写作与修改原则

请始终编辑 `content/posts/` 中对应的 Markdown 文件。完成后运行发布流程，网站首页、Now、文章页、Topics、Archive、Statistics 和 RSS 会一并更新。

创建新文章时，必须直接使用根目录的 `文章模板.md`。不要复制、恢复或另行维护旧版 YAML 模板；发布程序对旧格式的支持只用于兼容历史文章。

直接修改公开 HTML 页面也会使网站立刻更新，但下次发布 Markdown 时会被重新生成的页面覆盖。若曾在 HTML 中临时改动，请同时把相同改动同步回 Markdown 原稿。

网站不再以传统栏目组织内容。每篇文章统一进入 Writing，并通过一个或多个 Topics 横向关联。历史文章中的 `essays`、`arts` 和 `tags` 字段只作为兼容数据保留。

## 技术文件说明

少数英文文件名和字段名是网站及 GitHub Pages 正常运行所必需的技术标识，例如 `README.md`、`.html`、`.js`、`.css`，以及 Markdown 里的 `title`、`date`。它们不会显示为网站正文；其余面向阅读和使用的说明均以中文维护。
