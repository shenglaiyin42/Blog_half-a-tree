# 半棵斋文章发布规范

请复制 [`templates/post-template.md`](templates/post-template.md) 并填写。每篇文章只需提供这一份 Markdown 文件。

## 必填信息

- `title`：文章标题。
- `section`：`essays`（文章）、`arts`（艺文）、`thoughts`（想法）或 `rants`（吐槽）。
- `date`：`YYYY-MM-DD` 格式的发布日期。
- `summary`：约 100 字的列表页摘要。
- `tags`：标签名称列表；不写 `#`。

## 发布约定

- 正文从 YAML 分隔线后的第一行开始；不要重复写一级标题。
- `slug` 可留空，发布时自动生成公开网址名。
- 原始 Markdown 会原样保存在本地和仓库的内容目录中。
- 页面会自动使用当前的标题、日期、栏目、标签、预览、全文排版及分享按钮；不需要额外设置。
