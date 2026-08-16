#!/usr/bin/env python3
"""Publish one standard blog Markdown file into this static site."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://shenglaiyin42.github.io/Blog_half-a-tree/"
SECTION_NAMES = {"essays": "文章", "arts": "艺文"}


def read_post(path: Path) -> tuple[dict[str, object], str]:
    raw = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", raw, re.S)
    if not match:
        raise ValueError("Markdown must begin with YAML frontmatter.")
    metadata: dict[str, object] = {}
    tags: list[str] = []
    in_tags = False
    for line in match.group(1).splitlines():
        if line.startswith("  - "):
            tags.append(line[4:].strip().strip('"'))
            continue
        in_tags = line.startswith("tags:")
        if in_tags:
            metadata["tags"] = tags
            continue
        if ":" in line and not line.lstrip().startswith("#"):
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"')
    metadata["tags"] = tags
    required = {"title", "slug", "section", "date", "summary"}
    missing = [key for key in required if not metadata.get(key)]
    if missing:
        raise ValueError(f"Missing required frontmatter: {', '.join(missing)}")
    if metadata["section"] not in SECTION_NAMES:
        raise ValueError("section must be essays or arts")
    if not re.fullmatch(r"[a-z0-9-]+", str(metadata["slug"])):
        raise ValueError("slug may only contain lowercase letters, numbers, and hyphens")
    return metadata, match.group(2).strip()


def render_body(markdown: str) -> str:
    blocks = [line.strip() for line in markdown.splitlines() if line.strip()]
    rendered = []
    for block in blocks:
        if block.startswith("**") and block.endswith("**"):
            rendered.append(f"<p><strong>{html.escape(block[2:-2])}</strong></p>")
        else:
            rendered.append(f"<p>{html.escape(block)}</p>")
    return "\n          ".join(rendered)


def write_article(metadata: dict[str, object], markdown: str) -> None:
    slug = str(metadata["slug"])
    section = str(metadata["section"])
    date = str(metadata["date"])
    year, month, day = date.split("-")
    title = html.escape(str(metadata["title"]))
    tags = "".join(f"<span># {html.escape(tag)}</span>" for tag in metadata["tags"])
    template = (ROOT / "templates/article-page.html").read_text(encoding="utf-8")
    replacements = {
        "{{ARTICLE_SUMMARY}}": html.escape(str(metadata["summary"])),
        "{{ARTICLE_CANONICAL_URL}}": f"{SITE_URL}articles/{slug}.html",
        "{{ARTICLE_TITLE}}": title,
        "{{SECTION_ID}}": section,
        "{{SECTION_NAME}}": SECTION_NAMES[section],
        "{{DATE_ISO}}": date,
        "{{DATE_DISPLAY}}": f"{year}年{int(month)}月{int(day)}日",
        "{{ARTICLE_TAGS}}": tags,
        "{{ARTICLE_BODY}}": render_body(markdown),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    (ROOT / "articles" / f"{slug}.html").write_text(template, encoding="utf-8")
    redirect_dir = ROOT / "articles" / slug
    redirect_dir.mkdir(exist_ok=True)
    (redirect_dir / "index.html").write_text(
        "<!doctype html>\n<html lang=\"zh-CN\"><head><meta charset=\"UTF-8\" />"
        f"<meta http-equiv=\"refresh\" content=\"0; url=../{slug}.html\" />"
        f"<link rel=\"canonical\" href=\"../{slug}.html\" />"
        f"<script>window.location.replace(\"../{slug}.html\");</script>"
        "<title>正在转到文章｜半棵斋</title></head>"
        f"<body><p><a href=\"../{slug}.html\">打开文章</a></p></body></html>\n",
        encoding="utf-8",
    )


def update_index(metadata: dict[str, object]) -> None:
    app_path = ROOT / "app.js"
    app = app_path.read_text(encoding="utf-8")
    slug = str(metadata["slug"])
    if f'id: "{slug}"' in app:
        return
    tags = ", ".join(f'"{tag}"' for tag in metadata["tags"])
    entry = f'''  {{
    id: "{slug}",
    url: "./articles/{slug}.html",
    section: "{metadata["section"]}",
    sectionName: "{SECTION_NAMES[str(metadata["section"])]}",
    title: "{metadata["title"]}",
    excerpt: "{metadata["summary"]}",
    date: "{metadata["date"]}",
    tags: [{tags}],
  }},
'''
    app_path.write_text(app.replace("const posts = [\n", f"const posts = [\n{entry}", 1), encoding="utf-8")


def update_rss(metadata: dict[str, object]) -> None:
    rss_path = ROOT / "rss.xml"
    rss = rss_path.read_text(encoding="utf-8")
    slug = str(metadata["slug"])
    url = f"{SITE_URL}articles/{slug}.html"
    if url in rss:
        return
    import datetime
    published = datetime.date.fromisoformat(str(metadata["date"]))
    categories = "\n".join(f"      <category>{html.escape(tag)}</category>" for tag in metadata["tags"])
    item = f'''    <item>
      <title>{html.escape(str(metadata["title"]))}</title>
      <link>{url}</link>
      <guid isPermaLink="true">{url}</guid>
      <pubDate>{published.strftime("%a, %d %b %Y")} 12:00:00 -0500</pubDate>
      <description>{html.escape(str(metadata["summary"]))}</description>
{categories}
    </item>
'''
    rss_path.write_text(rss.replace("    <language>zh-CN</language>\n", f"    <language>zh-CN</language>\n{item}", 1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("post", type=Path)
    args = parser.parse_args()
    metadata, markdown = read_post(args.post)
    write_article(metadata, markdown)
    update_index(metadata)
    update_rss(metadata)


if __name__ == "__main__":
    main()
