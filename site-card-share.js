(() => {
  const button = document.querySelector("#site-card-share");
  const status = document.querySelector("#site-card-share-status");
  const cardUrl = new URL("./card/half-a-tree-site-card.jpg?v=halfatree-page-v1", window.location.href);
  let cardFilePromise;

  const setStatus = (message) => {
    if (status) status.textContent = message;
  };

  const getCardFile = () => {
    if (!cardFilePromise) {
      cardFilePromise = fetch(cardUrl)
        .then((response) => {
          if (!response.ok) throw new Error("无法读取网站名片");
          return response.blob();
        })
        .then((blob) => new File([blob], "半棵斋网站名片.jpg", { type: "image/jpeg" }));
    }
    return cardFilePromise;
  };

  const downloadCard = () => {
    const link = document.createElement("a");
    link.href = cardUrl.href;
    link.download = "半棵斋网站名片.jpg";
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  button?.addEventListener("click", async () => {
    button.disabled = true;
    setStatus("正在准备名片…");

    try {
      const file = await getCardFile();
      const shareData = {
        files: [file],
        title: "半棵斋｜Half a Tree",
        text: "半棵斋个人博客",
      };

      if (navigator.share && (!navigator.canShare || navigator.canShare(shareData))) {
        await navigator.share(shareData);
        setStatus("点击分享名片");
      } else {
        downloadCard();
        setStatus("此设备不支持直接分享，已开始下载名片");
      }
    } catch (error) {
      if (error?.name === "AbortError") {
        setStatus("点击分享名片");
      } else {
        downloadCard();
        setStatus("无法直接分享，已开始下载名片");
      }
    } finally {
      button.disabled = false;
    }
  });
})();
