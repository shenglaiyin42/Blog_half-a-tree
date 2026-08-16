(() => {
  const article = document.querySelector("article");
  const articleBody = document.querySelector(".article-body");
  const title = document.querySelector(".article-title")?.textContent.trim();
  const summary = document.querySelector('meta[name="description"]')?.content.trim() || "";

  if (!article || !articleBody || !title || document.querySelector(".article-share")) return;

  const canonicalUrl = document.querySelector('link[rel="canonical"]')?.href;
  const publicSiteBase = "https://shenglaiyin42.github.io/Blog_half-a-tree/";
  const localArticlePath = window.location.pathname.split("/articles/")[1];
  const pageUrl = canonicalUrl || (localArticlePath
    ? new URL(`articles/${localArticlePath}`, publicSiteBase).href
    : window.location.href);
  const shareText = [title, summary, pageUrl].filter(Boolean).join("\n");
  const xUrl = new URL("https://x.com/intent/post");
  xUrl.searchParams.set("text", shareText);
  const blueskyUrl = new URL("https://bsky.app/intent/compose");
  blueskyUrl.searchParams.set("text", shareText);

  const sharePanel = document.createElement("section");
  sharePanel.className = "article-share";
  sharePanel.setAttribute("aria-label", "分享文章");
  sharePanel.innerHTML = `
    <p class="share-label">SHARE / 分享</p>
    <div class="share-actions">
      <button class="share-button" type="button" data-share="copy">Copy Link</button>
      <a class="share-button" href="${xUrl.href}" target="_blank" rel="noopener noreferrer">Twitter</a>
      <a class="share-button" href="${blueskyUrl.href}" target="_blank" rel="noopener noreferrer">Bluesky</a>
      <button class="share-button" type="button" data-share="substack">Substack</button>
      <button class="share-button" type="button" data-share="wechat">微信朋友圈</button>
    </div>
    <p class="share-status" aria-live="polite"></p>`;
  articleBody.after(sharePanel);

  const status = sharePanel.querySelector(".share-status");
  async function copy(value, message) {
    let copied = false;
    if (navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(value);
        copied = true;
      } catch {
        copied = false;
      }
    }
    if (!copied) {
      const helper = document.createElement("textarea");
      helper.value = value;
      helper.setAttribute("readonly", "");
      helper.style.position = "fixed";
      helper.style.opacity = "0";
      document.body.append(helper);
      helper.select();
      copied = document.execCommand("copy");
      helper.remove();
    }
    if (copied) {
      status.textContent = message;
    } else {
      status.textContent = "复制失败，请手动复制浏览器地址。";
    }
  }

  sharePanel.addEventListener("click", (event) => {
    const action = event.target.closest("[data-share]")?.dataset.share;
    if (action === "copy") copy(pageUrl, "链接已复制。");
    if (action === "wechat") copy(pageUrl, "链接已复制；请打开微信，在朋友圈粘贴分享。");
    if (action === "substack") {
      copy(shareText, "标题、摘要和链接已复制；请在 Substack 编辑器中粘贴。");
      window.open("https://substack.com/publish/post", "_blank", "noopener,noreferrer");
    }
  });
})();
