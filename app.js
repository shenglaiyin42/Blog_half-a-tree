const posts = [
  {
    id: "heroes-and-the-decline-of-civilization",
    url: "./articles/heroes-and-the-decline-of-civilization.html",
    section: "arts",
    sectionName: "艺文",
    title: "所谓英雄，或许正是文明衰落的开始——《奥德赛》",
    excerpt: "诺兰的《奥德赛》不只是一个英雄历经艰险、终于回家的故事。它更像是一个关于文明衰落的寓言：当人与人之间最基本的原则被不断打破，暴力又以英雄之名被传颂，毁灭最终也会被下一代继承。",
    date: "2026-08-16",
    tags: ["电影"],
  },
  {
    id: "a-suffocating-self-exoneration",
    url: "./articles/a-suffocating-self-exoneration.html",
    section: "arts",
    sectionName: "艺文",
    title: "一场让人愤怒且窒息的“自我洗白”-《万物只是自然生长》",
    excerpt: "读李翊云的《万物只是自然生长》，我的心情从一开始的不安，到最后变成了极度的反感和恶心。作为一个母亲，两个孩子相继选择相同的方式自杀，这难道不是家庭出了大问题吗？可身为作家的母亲在书里仅仅反思了她自己的",
    date: "2026-08-15",
    tags: ["读书"],
  },
];

const sectionLabels = {
  essays: { zh: "文章", en: "ESSAYS" },
  arts: { zh: "艺文", en: "ARTS & CULTURE" },
};

let selectedSection = "essays";
let selectedTopic = null;
let selectedArchive = null;

const requestedSection = new URLSearchParams(window.location.search).get("section");
if (requestedSection && sectionLabels[requestedSection]) {
  selectedSection = requestedSection;
}

const postList = document.querySelector("#post-list");
const topicList = document.querySelector("#topic-list");
const archiveList = document.querySelector("#archive-list");
const resultTitle = document.querySelector("#result-title");
const resultKicker = document.querySelector("#result-kicker");
const clearFilter = document.querySelector("#clear-filter");

function formatDate(date) {
  return new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "long", day: "numeric" }).format(new Date(`${date}T12:00:00`));
}

function archiveKey(date) {
  return date.slice(0, 7);
}

function archiveLabel(key) {
  const [year, month] = key.split("-");
  return `${year} 年 ${Number(month)} 月`;
}

function filteredPosts() {
  return posts.filter((post) => {
    const isGlobalFilter = selectedTopic || selectedArchive;
    const sectionMatches = isGlobalFilter || post.section === selectedSection;
    const topicMatches = !selectedTopic || post.tags.includes(selectedTopic);
    const archiveMatches = !selectedArchive || archiveKey(post.date) === selectedArchive;
    return sectionMatches && topicMatches && archiveMatches;
  });
}

function renderTopics() {
  const counts = new Map();
  posts.forEach((post) => post.tags.forEach((tag) => counts.set(tag, (counts.get(tag) || 0) + 1)));
  topicList.innerHTML = counts.size ? [...counts.entries()]
    .sort((a, b) => a[0].localeCompare(b[0], "zh-CN"))
    .map(([tag, count]) => `
      <button class="filter-link ${selectedTopic === tag ? "is-selected" : ""}" data-topic="${tag}" type="button">
        <span># ${tag}</span><span class="count">${count}</span>
      </button>`)
    .join("") : `<p class="sidebar-empty">暂无标签</p>`;
}

function renderArchives() {
  const groups = new Map();
  posts.forEach((post) => {
    const key = archiveKey(post.date);
    groups.set(key, (groups.get(key) || 0) + 1);
  });
  const archives = [...groups.entries()].sort((a, b) => b[0].localeCompare(a[0]));
  let currentYear = null;
  archiveList.innerHTML = archives.length ? archives.map(([key, count]) => {
    const year = key.slice(0, 4);
    const yearLabel = year !== currentYear ? `<p class="archive-year">${year}</p>` : "";
    currentYear = year;
    return `${yearLabel}
      <button class="filter-link ${selectedArchive === key ? "is-selected" : ""}" data-archive="${key}" type="button">
        <span>${archiveLabel(key)}</span><span class="count">${count}</span>
      </button>`;
  }).join("") : `<p class="sidebar-empty">暂无归档</p>`;
}

function renderPosts() {
  const activePosts = filteredPosts();
  const section = sectionLabels[selectedSection];
  if (selectedTopic) {
    resultTitle.textContent = `标签 · #${selectedTopic}`;
    resultKicker.textContent = "topic";
  } else if (selectedArchive) {
    resultTitle.textContent = `归档 · ${archiveLabel(selectedArchive)}`;
    resultKicker.textContent = "archive";
  } else {
    resultTitle.textContent = section.zh;
    resultKicker.textContent = section.en;
  }
  clearFilter.hidden = !selectedTopic && !selectedArchive;
  postList.innerHTML = activePosts.length ? activePosts.map((post) => `
    <article class="post-card">
      <div class="post-meta"><span class="post-section">${post.sectionName}</span><time datetime="${post.date}">${formatDate(post.date)}</time></div>
      <h3><a href="${post.url}">${post.title}</a></h3>
      <p class="excerpt">${post.excerpt}</p>
      <div class="post-tags">${post.tags.map((tag) => `<button type="button" class="post-tag" data-topic="${tag}">#${tag}</button>`).join("")}</div>
    </article>`).join("") : `<p class="empty-state">文章将在这里出现。</p>`;
}

function render() {
  document.querySelectorAll(".nav-link").forEach((button) => button.classList.toggle("is-active", button.dataset.section === selectedSection));
  renderTopics();
  renderArchives();
  renderPosts();
}

document.addEventListener("click", (event) => {
  const sectionButton = event.target.closest("[data-section]");
  const topicButton = event.target.closest("[data-topic]");
  const archiveButton = event.target.closest("[data-archive]");

  if (sectionButton) {
    selectedSection = sectionButton.dataset.section;
    selectedTopic = null;
    selectedArchive = null;
    render();
  }
  if (topicButton) {
    selectedTopic = topicButton.dataset.topic;
    selectedArchive = null;
    render();
  }
  if (archiveButton) {
    selectedArchive = archiveButton.dataset.archive;
    selectedTopic = null;
    render();
  }
});

clearFilter.addEventListener("click", () => {
  selectedTopic = null;
  selectedArchive = null;
  render();
});

render();
