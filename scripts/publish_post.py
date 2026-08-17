#!/usr/bin/env python3
"""Publish one standard blog Markdown file into this static site."""

from __future__ import annotations

import argparse
import html
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://halfatree.page/"
PUBLIC_ASSET_VERSION = "article-image-selection-v2"
SECTION_NAMES = {"essays": "文章", "arts": "艺文"}
SHARE_IMAGE_DIR = ROOT / "public" / "media" / "share"
SHARE_IMAGE_SIZE = (1200, 630)
POSTER_IMAGE_DIR = ROOT / "public" / "media" / "posters"
POSTER_IMAGE_SIZE = (1080, 1200)
STATISTICS_DATA_PATH = ROOT / "statistics-data.js"
HERO_IMAGE_PATH = ROOT / "public" / "media" / "half-a-tree-canyon-hero.png"
CHINESE_FONT_PATHS = (
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
)


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
        image_match = re.fullmatch(r"!\[(.*?)\]\((.*?)\)(?:\{\.half\})?", block)
        if image_match:
            alt, source = image_match.groups()
            figure_class = "article-image article-image-half" if block.endswith("{.half}") else "article-image"
            rendered.append(
                f'<figure class="{figure_class}">'
                f'<img src="{html.escape(source, quote=True)}" '
                f'alt="{html.escape(alt, quote=True)}" loading="lazy" />'
                "</figure>"
            )
        elif block.startswith("**") and block.endswith("**"):
            rendered.append(f"<p><strong>{html.escape(block[2:-2])}</strong></p>")
        else:
            rendered.append(f"<p>{html.escape(block)}</p>")
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

    draw.text((70, 65), f"{SECTION_NAMES[str(metadata['section'])]}  ·  半棵斋", font=label_font, fill=accent)
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
    draw.text((70, 582), "Notes from a small room", font=label_font, fill=muted)
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

    section = SECTION_NAMES[str(metadata["section"])]
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
    section = str(metadata["section"])
    date = str(metadata["date"])
    year, month, day = date.split("-")
    updated = str(metadata.get("updated", "")).strip()
    updated_meta = ""
    if updated:
        updated_year, updated_month, updated_day = updated.split("-")
        updated_meta = (
            f'<span class="date-label">更新于</span>'
            f'<time datetime="{html.escape(updated, quote=True)}">'
            f"{updated_year}年{int(updated_month)}月{int(updated_day)}日"
            "</time>"
        )
    title = html.escape(str(metadata["title"]))
    tags = "".join(f"<span># {html.escape(tag)}</span>" for tag in metadata["tags"])
    template = (ROOT / "templates/article-page.html").read_text(encoding="utf-8")
    replacements = {
        "{{ARTICLE_SUMMARY}}": html.escape(str(metadata["summary"])),
        "{{ARTICLE_SHARE_METADATA}}": share_metadata(metadata),
        "{{ARTICLE_CANONICAL_URL}}": f"{SITE_URL}articles/{slug}.html",
        "{{ARTICLE_TITLE}}": title,
        "{{SECTION_ID}}": section,
        "{{SECTION_NAME}}": SECTION_NAMES[section],
        "{{DATE_ISO}}": date,
        "{{DATE_DISPLAY}}": f"{year}年{int(month)}月{int(day)}日",
        "{{UPDATED_META}}": updated_meta,
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
'''
    if metadata.get("updated"):
        entry += f'    updated: "{metadata["updated"]}",\n'
    entry += '''    tags: [{tags}],
  }},
'''.replace("{tags}", tags)
    app_path.write_text(app.replace("const posts = [\n", f"const posts = [\n{entry}", 1), encoding="utf-8")


def update_statistics_data(metadata: dict[str, object], markdown: str) -> None:
    """Add the newly published post's count to the statistics data source."""
    if not STATISTICS_DATA_PATH.exists():
        STATISTICS_DATA_PATH.write_text("window.statisticsPosts = [\n];\n", encoding="utf-8")
    data = STATISTICS_DATA_PATH.read_text(encoding="utf-8")
    slug = str(metadata["slug"])
    if f'id: "{slug}"' in data:
        return
    entry = (
        "  {\n"
        f'    id: "{slug}",\n'
        f'    date: "{metadata["date"]}",\n'
        f"    wordCount: {count_written_characters(markdown)},\n"
        "  },\n"
    )
    STATISTICS_DATA_PATH.write_text(
        data.replace("window.statisticsPosts = [\n", f"window.statisticsPosts = [\n{entry}", 1),
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
    update_index(metadata)
    update_statistics_data(metadata, markdown)
    update_rss(metadata)


if __name__ == "__main__":
    main()
