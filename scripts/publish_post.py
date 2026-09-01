#!/usr/bin/env python3
"""Publish one standard blog Markdown file into this static site."""

from __future__ import annotations

import argparse
import html
import json
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://halfatree.page/"
PUBLIC_ASSET_VERSION = "pages-from-small-room-v3"
SECTION_NAMES = {"writing": "随笔", "essays": "文章", "arts": "艺文"}
SECTION_KEYS = {"写作": "writing", "文章": "essays", "艺文": "arts", **{key: key for key in SECTION_NAMES}}
EDITABLE_METADATA_FIELDS = {
    "标题": "title",
    "网址名": "slug",
    "栏目": "section",
    "首次发表": "date",
    "更新于": "updated",
    "摘要": "summary",
    "名片图片": "share_image",
    "话题": "topics",
    "标签": "tags",
}
SHARE_IMAGE_DIR = ROOT / "public" / "media" / "share"
SHARE_IMAGE_SIZE = (1200, 630)
POSTER_IMAGE_DIR = ROOT / "public" / "media" / "posters"
POSTER_IMAGE_SIZE = (1080, 1200)
SITE_DATA_PATH = ROOT / "site-data.js"
HERO_IMAGE_PATH = ROOT / "public" / "media" / "half-a-tree-canyon-hero.png"
CHINESE_FONT_PATHS = (
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
)


def validate_metadata(metadata: dict[str, object]) -> None:
    required = {"title", "slug", "date", "summary"}
    missing = [key for key in required if not metadata.get(key)]
    if missing:
        raise ValueError(f"Missing required metadata: {', '.join(missing)}")
    if metadata.get("section") and metadata["section"] not in SECTION_NAMES:
        raise ValueError("历史栏目只能使用 essays/文章或 arts/艺文；新文章请省略栏目")
    if not re.fullmatch(r"[a-z0-9-]+", str(metadata["slug"])):
        raise ValueError("slug may only contain lowercase letters, numbers, and hyphens")
    for key in ("date", "updated"):
        if metadata.get(key) and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(metadata[key])):
            raise ValueError(f"{key} must use YYYY-MM-DD")
    if metadata.get("updated") and str(metadata["updated"]) <= str(metadata["date"]):
        raise ValueError("更新日期必须晚于首次发表日期；首次发布时请留空")


def read_editable_metadata(raw: str) -> tuple[dict[str, object], str] | None:
    match = re.match(
        r"\A<!-- BLOG_METADATA_START -->\n(.*?)\n<!-- BLOG_METADATA_END -->\n?(.*)\Z",
        raw,
        re.S,
    )
    if not match:
        return None

    metadata: dict[str, object] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "：" not in line:
            continue
        label, value = line.split("：", 1)
        key = EDITABLE_METADATA_FIELDS.get(label.strip())
        if not key:
            continue
        value = value.strip()
        if key in {"tags", "topics"}:
            metadata[key] = [tag.strip().lstrip("#").strip() for tag in re.split(r"[，,、]", value) if tag.strip()]
        elif key == "section":
            metadata[key] = SECTION_KEYS.get(value, value)
        else:
            metadata[key] = value
    metadata["topics"] = metadata.get("topics") or metadata.get("tags") or []
    metadata.setdefault("section", "writing")
    validate_metadata(metadata)
    return metadata, match.group(2).strip()


def read_yaml_frontmatter(raw: str) -> tuple[dict[str, object], str] | None:
    match = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", raw, re.S)
    if not match:
        return None
    metadata: dict[str, object] = {}
    list_key: str | None = None
    for line in match.group(1).splitlines():
        if line.startswith("  - ") and list_key:
            metadata.setdefault(list_key, []).append(line[4:].strip().strip('"'))
        elif ":" in line and not line.lstrip().startswith("#"):
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"')
            if key in {"tags", "topics"} and not value:
                metadata[key] = []
                list_key = key
            elif key in {"tags", "topics"}:
                metadata[key] = [
                    item.strip().strip('"').strip("'")
                    for item in value.strip("[]").split(",")
                    if item.strip()
                ]
                list_key = None
            else:
                metadata[key] = value
                list_key = None
    metadata["topics"] = metadata.get("topics") or metadata.get("tags") or []
    metadata.setdefault("section", "writing")
    validate_metadata(metadata)
    return metadata, match.group(2).strip()


def read_post(path: Path) -> tuple[dict[str, object], str]:
    raw = path.read_text(encoding="utf-8")
    parsed = read_editable_metadata(raw) or read_yaml_frontmatter(raw)
    if not parsed:
        raise ValueError("Markdown must begin with an editable article-information block or YAML frontmatter.")
    return parsed


INLINE_PATTERN = re.compile(
    r"(`[^`]+`|\*\*.+?\*\*|\[[^\]]+\]\([^)]+\)|\*[^*]+\*)"
)


def render_inline(markdown: str) -> str:
    """Render the small inline-Markdown subset used by blog articles."""
    rendered: list[str] = []
    cursor = 0
    for match in INLINE_PATTERN.finditer(markdown):
        rendered.append(html.escape(markdown[cursor : match.start()]))
        token = match.group(0)
        link_match = re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", token)
        if token.startswith("**"):
            rendered.append(f"<strong>{html.escape(token[2:-2])}</strong>")
        elif token.startswith("`"):
            rendered.append(f"<code>{html.escape(token[1:-1])}</code>")
        elif link_match:
            label, target = link_match.groups()
            safe_target = target if target.startswith(("https://", "http://", "/", "#")) else "#"
            external = ' target="_blank" rel="noopener"' if safe_target.startswith("http") else ""
            rendered.append(
                f'<a href="{html.escape(safe_target, quote=True)}"{external}>'
                f"{html.escape(label)}</a>"
            )
        else:
            rendered.append(f"<em>{html.escape(token[1:-1])}</em>")
        cursor = match.end()
    rendered.append(html.escape(markdown[cursor:]))
    return "".join(rendered)


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def render_body(markdown: str) -> str:
    lines = [line.rstrip() for line in markdown.splitlines()]
    rendered: list[str] = []
    section_ids: dict[int, str] = {}
    toc_entries: list[tuple[str, str]] = []
    section_number = 0
    for line_index, line in enumerate(lines):
        heading_match = re.fullmatch(r"##\s+(.+)", line.strip())
        if heading_match:
            section_number += 1
            section_id = f"section-{section_number}"
            section_ids[line_index] = section_id
            toc_entries.append((section_id, heading_match.group(1)))

    index = 0
    while index < len(lines):
        block = lines[index].strip()
        if not block:
            index += 1
            continue
        if block == "[[TOC]]":
            items = "".join(
                f'<li><a href="#{section_id}">{render_inline(title)}</a></li>'
                for section_id, title in toc_entries
            )
            rendered.append(
                '<nav class="article-toc" aria-label="文章目录">'
                '<p class="article-toc-title">目录 <span>/ Contents</span></p>'
                f"<ol>{items}</ol></nav>"
            )
            index += 1
            continue
        if block.startswith("# "):
            index += 1
            continue
        image_match = re.fullmatch(r"!\[(.*?)\]\((.*?)\)(?:\{\.half\})?", block)
        if image_match:
            alt, source = image_match.groups()
            figure_class = "article-image article-image-half" if block.endswith("{.half}") else "article-image"
            caption = ""
            if index + 1 < len(lines) and lines[index + 1].strip().startswith("图片来源："):
                caption = (
                    f'<figcaption class="article-image-credit">'
                    f'{html.escape(lines[index + 1].strip())}</figcaption>'
                )
                index += 1
            rendered.append(
                f'<figure class="{figure_class}">'
                f'<img src="{html.escape(source, quote=True)}" '
                f'alt="{html.escape(alt, quote=True)}" loading="lazy" />'
                f"{caption}"
                "</figure>"
            )
        elif block.startswith("|") and index + 1 < len(lines) and is_table_separator(lines[index + 1].strip()):
            header = split_table_row(block)
            alignment = split_table_row(lines[index + 1].strip())
            rows: list[list[str]] = []
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(split_table_row(lines[index].strip()))
                index += 1
            column_count = len(header)
            table_class = "article-table is-wide" if column_count > 3 else "article-table"
            header_html = "".join(
                f'<th style="text-align:{"center" if cell.startswith(":") and cell.endswith(":") else "right" if cell.endswith(":") else "left"}">'
                f"{render_inline(value)}</th>"
                for value, cell in zip(header, alignment)
            )
            body_html = "".join(
                "<tr>"
                + "".join(
                    f"<td>{render_inline(row[cell_index]) if cell_index < len(row) else ''}</td>"
                    for cell_index in range(column_count)
                )
                + "</tr>"
                for row in rows
            )
            rendered.append(
                f'<div class="article-table-wrap"><table class="{table_class}">'
                f"<thead><tr>{header_html}</tr></thead><tbody>{body_html}</tbody>"
                "</table></div>"
            )
            continue
        elif block == "---":
            rendered.append('<hr class="article-divider" />')
        elif heading_match := re.fullmatch(r"(#{2,4})\s+(.+)", block):
            level = len(heading_match.group(1))
            title = heading_match.group(2)
            section_id = section_ids.get(index, "")
            id_attribute = f' id="{section_id}"' if section_id else ""
            rendered.append(f"<h{level}{id_attribute}>{render_inline(title)}</h{level}>")
        elif block.startswith("> "):
            quote = block[2:].strip()
            if quote.startswith("EN｜"):
                rendered.append(
                    f'<p class="article-translation" lang="en">{render_inline(quote[3:].strip())}</p>'
                )
            elif quote.startswith("说明｜"):
                rendered.append(
                    '<aside class="article-note"><strong>说明</strong>'
                    f"<p>{render_inline(quote[3:].strip())}</p></aside>"
                )
            elif quote.startswith("下载｜"):
                rendered.append(
                    '<aside class="article-download"><span>可下载版本</span>'
                    f"{render_inline(quote[3:].strip())}</aside>"
                )
            else:
                rendered.append(f"<blockquote><p>{render_inline(quote)}</p></blockquote>")
        elif re.match(r"^[-*]\s+", block):
            items: list[str] = []
            while index < len(lines) and re.match(r"^[-*]\s+", lines[index].strip()):
                items.append(re.sub(r"^[-*]\s+", "", lines[index].strip()))
                index += 1
            rendered.append("<ul>" + "".join(f"<li>{render_inline(item)}</li>" for item in items) + "</ul>")
            continue
        elif re.match(r"^\d+\.\s+", block):
            items = []
            while index < len(lines) and re.match(r"^\d+\.\s+", lines[index].strip()):
                items.append(re.sub(r"^\d+\.\s+", "", lines[index].strip()))
                index += 1
            rendered.append("<ol>" + "".join(f"<li>{render_inline(item)}</li>" for item in items) + "</ol>")
            continue
        else:
            rendered.append(f"<p>{render_inline(block)}</p>")
        index += 1
    return "\n          ".join(rendered)


def get_chinese_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for font_path in CHINESE_FONT_PATHS:
        if Path(font_path).exists():
            return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, width: int, lines: int) -> list[str]:
    result: list[str] = []
    current = ""
    for character in text.strip():
        candidate = current + character
        if current and draw.textlength(candidate, font=font) > width:
            result.append(current)
            current = character
            if len(result) == lines:
                break
        else:
            current = candidate
    if current and len(result) < lines:
        result.append(current)
    consumed = "".join(result)
    if len(consumed) < len(text.strip()) and result:
        result[-1] = result[-1].rstrip("，。；：、 ") + "…"
    return result


def image_source_path(source: str) -> Path:
    """Resolve a Markdown image path stored in this repository."""
    candidate = source.strip().strip("<>")
    if candidate.startswith("/"):
        path = ROOT / candidate.lstrip("/")
    else:
        path = ROOT / candidate
    if not path.is_file():
        raise ValueError(f"无法读取文章插图：{source}")
    return path


def article_cover_image(markdown: str, metadata: dict[str, object]) -> Path:
    """Select the image for share cards without guessing among multiple images."""
    chosen = str(metadata.get("share_image", "")).strip()
    if chosen:
        return image_source_path(chosen)

    sources = re.findall(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)", markdown)
    if not sources:
        return HERO_IMAGE_PATH
    if len(sources) == 1:
        return image_source_path(sources[0])

    numbered = "、".join(f"{index + 1}. {source}" for index, source in enumerate(sources))
    raise ValueError(
        "文章有多张插图，无法替你猜测名片图片。"
        f"请确认使用哪一张，并在 frontmatter 中加入 share_image: 图片路径。可选：{numbered}"
    )


def count_written_characters(markdown: str) -> int:
    """Count written characters, excluding whitespace and Markdown image/link syntax."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", markdown)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_#>`~-]", "", text)
    return len(re.sub(r"\s+", "", text))


def adaptive_image_panel(path: Path, size: tuple[int, int], overlay: tuple[int, int, int, int]) -> Image.Image:
    """Show the complete image and use a soft version of it to fill mismatched ratios."""
    image = Image.open(path).convert("RGB")
    fitted = ImageOps.contain(image, size, method=Image.Resampling.LANCZOS)
    backdrop = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(radius=26))
    frame = backdrop.convert("RGBA")
    frame.alpha_composite(Image.new("RGBA", size, overlay))
    offset = ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2)
    frame.alpha_composite(fitted.convert("RGBA"), offset)
    return frame.convert("RGB")


def share_image_url(metadata: dict[str, object]) -> str:
    return f"{SITE_URL}public/media/share/{metadata['slug']}.jpg?v={PUBLIC_ASSET_VERSION}"


def article_label(metadata: dict[str, object]) -> str:
    """Use the article's first topic on share images, with legacy section fallback."""
    topics = metadata.get("topics") or []
    if topics:
        return str(topics[0])
    return SECTION_NAMES[str(metadata.get("section", "writing"))]


def write_share_card(metadata: dict[str, object], cover_image: Path) -> None:
    """Create a standard 1200 × 630 social-preview JPEG for one article."""
    SHARE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    card = Image.new("RGB", SHARE_IMAGE_SIZE, (24, 34, 29)).convert("RGBA")
    card.alpha_composite(adaptive_image_panel(cover_image, (465, SHARE_IMAGE_SIZE[1]), (24, 34, 29, 54)).convert("RGBA"), (735, 0))
    panel = Image.new("RGBA", (735, SHARE_IMAGE_SIZE[1]), (250, 249, 244, 237))
    card.alpha_composite(panel, (0, 0))
    draw = ImageDraw.Draw(card)
    ink = (39, 47, 42, 255)
    muted = (88, 98, 90, 255)
    accent = (105, 121, 107, 255)
    label_font = get_chinese_font(22)
    title_font = get_chinese_font(48)
    summary_font = get_chinese_font(25)
    footer_font = get_chinese_font(23)

    draw.text((70, 65), f"{article_label(metadata)}  ·  半棵斋", font=label_font, fill=accent)
    title_lines = wrap_text(draw, str(metadata["title"]), title_font, 630, 3)
    title_y = 132
    for line in title_lines:
        draw.text((70, title_y), line, font=title_font, fill=ink)
        title_y += 67

    draw.line((70, 360, 650, 360), fill=(208, 208, 200, 255), width=2)
    summary_lines = wrap_text(draw, str(metadata["summary"]), summary_font, 575, 3)
    summary_y = 388
    for line in summary_lines:
        draw.text((70, summary_y), line, font=summary_font, fill=muted)
        summary_y += 38

    draw.text((70, 548), "半棵斋｜Half a Tree", font=footer_font, fill=ink)
    draw.text((70, 582), "Pages from a small room", font=label_font, fill=muted)
    card.convert("RGB").save(
        SHARE_IMAGE_DIR / f"{metadata['slug']}.jpg",
        format="JPEG",
        quality=90,
        optimize=True,
        progressive=True,
    )


def fetch_article_qr(url: str) -> Image.Image:
    query = urlencode({"size": "520x520", "format": "png", "data": url})
    with urlopen(f"https://api.qrserver.com/v1/create-qr-code/?{query}", timeout=30) as response:
        return Image.open(BytesIO(response.read())).convert("RGB")


def write_moments_poster(metadata: dict[str, object], cover_image: Path) -> None:
    """Create the vertical, QR-enabled image used for WeChat Moments sharing."""
    POSTER_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    poster = Image.new("RGB", POSTER_IMAGE_SIZE, (250, 249, 244))
    hero_panel = adaptive_image_panel(cover_image, (1080, 500), (24, 34, 29, 48))
    poster.paste(hero_panel, (0, 0))
    draw = ImageDraw.Draw(poster)
    ink = (39, 47, 42)
    muted = (88, 98, 90)
    accent = (105, 121, 107)
    brand_font = get_chinese_font(24)
    label_font = get_chinese_font(26)
    title_font = get_chinese_font(48)
    summary_font = get_chinese_font(28)
    hint_font = get_chinese_font(25)

    section = article_label(metadata)
    date = str(metadata["date"])
    year, month, day = date.split("-")
    draw.text((62, 558), f"{section}  ·  {year}年{int(month)}月{int(day)}日", font=label_font, fill=accent)

    title_lines = wrap_text(draw, str(metadata["title"]), title_font, 935, 3)
    title_y = 610
    for line in title_lines:
        draw.text((62, title_y), line, font=title_font, fill=ink)
        title_y += 64

    draw.text((62, title_y + 4), "半棵斋｜Half a Tree", font=brand_font, fill=accent)
    divider_y = max(815, title_y + 48)
    draw.line((62, divider_y, 1018, divider_y), fill=(211, 210, 202), width=2)
    summary_lines = wrap_text(draw, str(metadata["summary"]), summary_font, 640, 4)
    summary_y = divider_y + 34
    for line in summary_lines:
        draw.text((62, summary_y), line, font=summary_font, fill=muted)
        summary_y += 43

    qr = fetch_article_qr(f"{SITE_URL}articles/{metadata['slug']}.html")
    qr = qr.resize((230, 230), Image.Resampling.NEAREST)
    poster.paste(qr, (786, 930))
    draw.text((62, 1045), "扫码阅读全文", font=hint_font, fill=ink)
    draw.text((62, 1085), "或打开链接访问半棵斋", font=hint_font, fill=muted)

    poster.save(
        POSTER_IMAGE_DIR / f"{metadata['slug']}.jpg",
        format="JPEG",
        quality=92,
        optimize=True,
        progressive=True,
    )


def share_metadata(metadata: dict[str, object]) -> str:
    title = html.escape(str(metadata["title"]), quote=True)
    summary = html.escape(str(metadata["summary"]), quote=True)
    canonical = f"{SITE_URL}articles/{metadata['slug']}.html"
    image = share_image_url(metadata)
    return f'''<!-- 分享卡片元数据开始 -->
    <meta property="og:type" content="article" />
    <meta property="og:site_name" content="半棵斋｜Half a Tree" />
    <meta property="og:title" content="{title}｜半棵斋" />
    <meta property="og:description" content="{summary}" />
    <meta property="og:url" content="{canonical}" />
    <meta property="og:image" content="{image}" />
    <meta property="og:image:type" content="image/jpeg" />
    <meta property="og:image:width" content="1200" />
    <meta property="og:image:height" content="630" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="{title}｜半棵斋" />
    <meta name="twitter:description" content="{summary}" />
    <meta name="twitter:image" content="{image}" />
    <!-- 分享卡片元数据结束 -->'''


def refresh_share_metadata(metadata: dict[str, object]) -> None:
    """Update only an existing page's social metadata, preserving its article body."""
    page_path = ROOT / "articles" / f"{metadata['slug']}.html"
    page = page_path.read_text(encoding="utf-8")
    metadata_block = share_metadata(metadata)
    existing_block = r"\s*<!-- 分享卡片元数据开始 -->.*?<!-- 分享卡片元数据结束 -->"
    if re.search(existing_block, page, flags=re.S):
        updated = re.sub(existing_block, "\n    " + metadata_block, page, flags=re.S)
    else:
        description = r'(<meta name="description"[^>]* />)'
        updated, replacements = re.subn(description, r"\1\n    " + metadata_block, page, count=1)
        if replacements != 1:
            raise ValueError(f"Cannot find description metadata in {page_path}")
    page_path.write_text(updated, encoding="utf-8")


def write_article(metadata: dict[str, object], markdown: str) -> None:
    slug = str(metadata["slug"])
    date = str(metadata["date"])
    year, month, day = date.split("-")
    updated = str(metadata.get("updated", "")).strip()
    updated_meta = ""
    if updated and updated > date:
        updated_year, updated_month, updated_day = updated.split("-")
        updated_meta = (
            f'<span class="date-label">更新于</span>'
            f'<time datetime="{html.escape(updated, quote=True)}">'
            f"{updated_year}年{int(updated_month)}月{int(updated_day)}日"
            "</time>"
        )
    title = html.escape(str(metadata["title"]))
    topics = "".join(f"<span># {html.escape(topic)}</span>" for topic in metadata["topics"])
    template = (ROOT / "templates/article-page.html").read_text(encoding="utf-8")
    replacements = {
        "{{ARTICLE_SUMMARY}}": html.escape(str(metadata["summary"])),
        "{{ARTICLE_SHARE_METADATA}}": share_metadata(metadata),
        "{{ARTICLE_CANONICAL_URL}}": f"{SITE_URL}articles/{slug}.html",
        "{{ARTICLE_TITLE}}": title,
        "{{DATE_ISO}}": date,
        "{{DATE_DISPLAY}}": f"{year}年{int(month)}月{int(day)}日",
        "{{UPDATED_META}}": updated_meta,
        "{{ARTICLE_TOPICS}}": topics,
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


def update_site_data(metadata: dict[str, object], markdown: str) -> None:
    """Create or refresh one post in the shared Writing data source."""
    data = SITE_DATA_PATH.read_text(encoding="utf-8")
    slug = str(metadata["slug"])
    js = lambda value: json.dumps(value, ensure_ascii=False)
    lines = [
        "  {",
        f"    id: {js(slug)},",
        f"    url: {js(f'/articles/{slug}.html')},",
    ]
    if metadata.get("section") in {"essays", "arts"}:
        lines.append(f"    legacySection: {js(metadata['section'])},")
    lines.extend(
        [
            f"    title: {js(str(metadata['title']))},",
            f"    excerpt: {js(str(metadata['summary']))},",
            f"    date: {js(str(metadata['date']))},",
        ]
    )
    updated = str(metadata.get("updated", "")).strip()
    if updated and updated > str(metadata["date"]):
        lines.append(f"    updated: {js(updated)},")
    lines.extend(
        [
            f"    topics: {js(metadata['topics'])},",
            f"    wordCount: {count_written_characters(markdown)},",
            "  },",
        ]
    )
    entry = "\n".join(lines) + "\n"
    existing_entry = re.search(
        rf'  \{{\n    id: "{re.escape(slug)}",\n.*?\n  \}},\n',
        data,
        re.S,
    )
    if existing_entry:
        SITE_DATA_PATH.write_text(
            data[: existing_entry.start()] + entry + data[existing_entry.end() :],
            encoding="utf-8",
        )
        return
    SITE_DATA_PATH.write_text(
        data.replace("window.sitePosts = [\n", f"window.sitePosts = [\n{entry}", 1),
        encoding="utf-8",
    )


def update_rss(metadata: dict[str, object]) -> None:
    rss_path = ROOT / "rss.xml"
    rss = rss_path.read_text(encoding="utf-8")
    slug = str(metadata["slug"])
    url = f"{SITE_URL}articles/{slug}.html"
    if url in rss:
        return
    import datetime
    published = datetime.date.fromisoformat(str(metadata["date"]))
    categories = "\n".join(f"      <category>{html.escape(topic)}</category>" for topic in metadata["topics"])
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
    parser.add_argument(
        "--refresh-share",
        action="store_true",
        help="只更新已有文章的分享卡片和分享元数据，不重写正文。",
    )
    args = parser.parse_args()
    metadata, markdown = read_post(args.post)
    cover_image = article_cover_image(markdown, metadata)
    write_share_card(metadata, cover_image)
    write_moments_poster(metadata, cover_image)
    if args.refresh_share:
        refresh_share_metadata(metadata)
        return
    write_article(metadata, markdown)
    update_site_data(metadata, markdown)
    update_rss(metadata)


if __name__ == "__main__":
    main()
