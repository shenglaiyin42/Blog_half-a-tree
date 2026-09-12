# 半棵斋个人博客

这是“半棵斋｜Half a Tree”的静态个人博客仓库。

正式网站：[半棵斋](https://halfatree.page/)

## 仓库内容

- `content/posts/`：已发布文章的 Markdown 原稿；这是文章正文的唯一正式来源。
- `content/archived/`：已经从公开页面撤下、但仍需保留的历史内容原稿。
- `content/originals/`：收到时保留的原始文稿备份。
- `articles/`：公开文章页面由发布流程生成；请不要把它作为日常改稿的位置。
- `文章模板.md`：项目当前唯一的文章模板；所有新文章都从这份文件生成。
- `发布指南.md`：发布和修改文章的说明。
- `site-data.js`：Pages、Topics、Archive 与 Statistics 共用的唯一文章数据源，由发布脚本自动更新。
- `now/`：“现在”页面；以时间倒序显示紧凑的近况文章流，源 Markdown 保存在 `content/posts/`。
- `site-statistics.js`：首页简洁统计所使用的日期与字数计算逻辑；文章、Now 条目与 About 正文均按独立内容计入，主页列表和话题筛选不重复计数。

## 写作与修改原则

请始终编辑 `content/posts/` 中对应的 Markdown 文件。完成后运行发布流程，网站首页、文章页、Topics、Archive、Statistics 和 RSS 会一并更新。

创建新文章时，必须直接使用根目录的 `文章模板.md`。不要复制、恢复或另行维护旧版 YAML 模板；发布程序对旧格式的支持只用于兼容历史文章。

直接修改公开 HTML 页面也会使网站立刻更新，但下次发布 Markdown 时会被重新生成的页面覆盖。若曾在 HTML 中临时改动，请同时把相同改动同步回 Markdown 原稿。

网站不再以传统栏目组织内容。每篇文章统一进入 Pages / 记录，并通过一个或多个 Topics 横向关联。历史文章中的 `essays`、`arts` 和 `tags` 字段只作为兼容数据保留。

## 私有访问统计

访问统计使用 Cloudflare Web Analytics，与首页的写作篇数、字数统计分开，也不依赖评论服务。数据不公开展示。

- 查看入口：Cloudflare 账户 → Analytics → Web analytics → halfatree.page。
- 查看全站：选择 Page views（浏览量）或 Visits（访问），并选择日期范围。
- 查看单篇文章：按 Path（路径）筛选对应的 `/articles/文章标识.html`。
- 统计从接入后开始，不会补回过去的访问。可查询范围和数据保留期限以 Cloudflare 后台及官方限制为准，不代表永久累计。
- 首页、关于、现在、名片页面和所有正式文章使用 `site-analytics.js`；文章模板已包含入口，以后发布文章自动接入。
- 本地预览、直接打开的文件及文章旧地址跳转页不采集，避免测试和跳转重复计数。
- Cloudflare 中采用「Enable with JS Snippet installation」，不要同时开启自动注入。脚本内为公开站点标识，不是账户 API 密钥。
- 新增独立页面时，在 `</body>` 前加入 `<script defer src="/site-analytics.js"></script>`；发布前运行 `node scripts/check_analytics.cjs` 验证。

## 技术文件名称

少数英文文件名和字段名是网站及 GitHub Pages 正常运行所必需的技术标识，例如 `README.md`、`.html`、`.js`、`.css`，以及 Markdown 里的 `title`、`date`。它们不会显示为网站正文；其余面向阅读和使用的说明均以中文维护。
