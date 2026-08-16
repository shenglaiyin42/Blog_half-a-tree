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
  const articleSlug = new URL(pageUrl).pathname.split("/articles/").pop()?.replace(/\.html$/, "");
  const posterUrl = articleSlug
    ? new URL(`public/media/posters/${articleSlug}.jpg`, publicSiteBase).href
    : null;

  const sharePanel = document.createElement("section");
  sharePanel.className = "article-share";
  sharePanel.setAttribute("aria-label", "分享文章");
  sharePanel.innerHTML = `
    <p class="share-label">SHARE / 分享</p>
    <div class="share-actions">
      <button class="share-button" type="button" data-share="copy">Copy Link</button>
      <a class="share-button" href="${xUrl.href}" target="_blank" rel="noopener noreferrer">Twitter</a>
      <a class="share-button" href="${blueskyUrl.href}" target="_blank" rel="noopener noreferrer">Bluesky</a>
      <button class="share-button" type="button" data-share="wechat">微信朋友圈</button>
    </div>
    <p class="share-status" aria-live="polite"></p>`;
  articleBody.after(sharePanel);

  const status = sharePanel.querySelector(".share-status");

  function openMomentsPoster() {
    if (!posterUrl) {
      status.textContent = "暂时无法找到文章海报。";
      return;
    }
    const dialog = document.createElement("div");
    dialog.className = "moments-poster-dialog";
    dialog.innerHTML = `
      <div class="moments-poster-backdrop" data-poster-close></div>
      <section class="moments-poster-panel" role="dialog" aria-modal="true" aria-label="朋友圈文章海报">
        <button class="moments-poster-close" type="button" aria-label="关闭海报预览" data-poster-close>×</button>
        <p class="share-label">MOMENTS / 朋友圈海报</p>
        <img src="${posterUrl}" alt="${title} 的朋友圈分享海报" />
        <p>手机上可长按图片保存，或下载后发布到朋友圈。</p>
        <div class="moments-poster-actions">
          <a class="share-button" href="${posterUrl}" download="${articleSlug}-朋友圈海报.jpg">下载海报</a>
          <button class="share-button" type="button" data-share="poster-copy">复制文章链接</button>
        </div>
      </section>`;
    document.body.append(dialog);
    const close = () => dialog.remove();
    dialog.addEventListener("click", (event) => {
      if (event.target.closest("[data-poster-close]")) close();
      if (event.target.closest('[data-share="poster-copy"]')) copy(pageUrl, "链接已复制，可与海报一起发布。");
    });
    document.addEventListener("keydown", function onKeydown(event) {
      if (event.key !== "Escape") return;
      close();
      document.removeEventListener("keydown", onKeydown);
    });
  }
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
    if (action === "wechat") openMomentsPoster();
  });
})();
