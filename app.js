(() => {
  const posts = [...(window.sitePosts || [])].sort((a, b) => b.date.localeCompare(a.date));
  const params = new URLSearchParams(window.location.search);
  const selectedTopic = params.get("topic");
  const selectedYear = params.get("year");
  const selectedMonth = /^\d{2}$/.test(params.get("month") || "") ? params.get("month") : null;
  const legacySection = ["essays", "arts"].includes(params.get("section")) ? params.get("section") : null;
  const pageBase = window.location.pathname.startsWith("/now") ? "/now/" : "/";

  const topicList = document.querySelector("#topic-list");
  const archiveList = document.querySelector("#archive-list");
  const writingList = document.querySelector("#writing-list");
  const filterSummary = document.querySelector("#filter-summary");
  const clearFilter = document.querySelector("#clear-filter");

  function filterUrl(key, value) {
    const url = new URL(pageBase, window.location.origin);
    if (value) url.searchParams.set(key, value);
    return `${url.pathname}${url.search}`;
  }

  function archiveUrl(year, month = null) {
    const url = new URL(pageBase, window.location.origin);
    url.searchParams.set("year", year);
    if (month) url.searchParams.set("month", month);
    return `${url.pathname}${url.search}`;
  }

  function formatDate(date) {
    return date.replaceAll("-", ".");
  }

  function filteredPosts() {
    return posts.filter((post) => {
      const topicMatches = !selectedTopic || post.topics.includes(selectedTopic);
      const yearMatches = !selectedYear || post.date.startsWith(selectedYear);
      const monthMatches = !selectedMonth || post.date.slice(5, 7) === selectedMonth;
      const legacyMatches = !legacySection || post.legacySection === legacySection;
      return topicMatches && yearMatches && monthMatches && legacyMatches;
    });
  }

  function renderTopics() {
    if (!topicList) return;
    const counts = new Map();
    posts.forEach((post) => post.topics.forEach((topic) => counts.set(topic, (counts.get(topic) || 0) + 1)));
    topicList.innerHTML = counts.size ? [...counts.entries()]
      .sort((a, b) => a[0].localeCompare(b[0], "zh-CN"))
      .map(([topic, count]) => `
        <a class="topic-link${selectedTopic === topic ? " is-active" : ""}" href="${filterUrl("topic", topic)}"${selectedTopic === topic ? ' aria-current="page"' : ""}>
          <span>${topic}</span><small>${count}</small>
        </a>`)
      .join("") : `<p class="empty-state">暂无话题。</p>`;
  }

  function renderArchive() {
    if (!archiveList) return;
    const years = new Map();
    posts.forEach((post) => {
      const year = post.date.slice(0, 4);
      const month = post.date.slice(5, 7);
      const group = years.get(year) || { count: 0, months: new Map() };
      group.count += 1;
      group.months.set(month, (group.months.get(month) || 0) + 1);
      years.set(year, group);
    });
    archiveList.innerHTML = [...years.entries()]
      .sort((a, b) => b[0].localeCompare(a[0]))
      .map(([year, group]) => `
        <div class="archive-year-group">
          <a class="archive-link archive-year-link${selectedYear === year && !selectedMonth ? " is-active" : ""}" href="${archiveUrl(year)}"${selectedYear === year && !selectedMonth ? ' aria-current="page"' : ""}>
            <span>${year}</span><small>${group.count}</small>
          </a>
          <div class="archive-months">
            ${[...group.months.entries()]
              .sort((a, b) => b[0].localeCompare(a[0]))
              .map(([month, count]) => `<a class="archive-link archive-month-link${selectedYear === year && selectedMonth === month ? " is-active" : ""}" href="${archiveUrl(year, month)}"${selectedYear === year && selectedMonth === month ? ' aria-current="page"' : ""}><span>${Number(month)}月</span><small>${count}</small></a>`)
              .join("")}
          </div>
        </div>`)
      .join("");
  }

  function renderWriting() {
    if (!writingList) return;
    const activePosts = filteredPosts();
    writingList.innerHTML = activePosts.length ? activePosts.map((post) => `
      <article class="writing-item">
        <time datetime="${post.date}">${formatDate(post.date)}</time>
        <div>
          <h3><a href="${post.url}">${post.title}</a></h3>
          <p class="writing-topics">${post.topics.map((topic) => `<a href="${filterUrl("topic", topic)}">${topic}</a>`).join(" · ")}</p>
        </div>
      </article>`).join("") : `<p class="empty-state">没有符合条件的随笔。</p>`;
  }

  function renderFilterSummary() {
    if (!filterSummary) return;
    const labels = [];
    if (selectedTopic) labels.push(`话题：${selectedTopic}`);
    if (selectedYear) labels.push(`年份：${selectedYear}`);
    if (selectedMonth) labels.push(`月份：${Number(selectedMonth)}月`);
    if (legacySection) labels.push(`旧栏目：${legacySection === "essays" ? "文章" : "艺文"}`);
    filterSummary.textContent = labels.join(" · ");
    filterSummary.hidden = labels.length === 0;
    if (clearFilter) clearFilter.hidden = labels.length === 0;
  }

  function setStatistic(id, value) {
    const element = document.querySelector(`#${id}`);
    if (element) element.textContent = new Intl.NumberFormat("zh-CN").format(value);
  }

  function renderStatistics() {
    if (!window.siteStatistics) return;
    const summary = window.siteStatistics.summarize(posts);
    setStatistic("home-week-count", summary.currentWeekCount);
    setStatistic("home-month-count", summary.currentMonthCount);
    setStatistic("home-total-count", summary.totalCount);
    setStatistic("home-total-words", summary.totalWords);
  }

  renderTopics();
  renderArchive();
  renderWriting();
  renderFilterSummary();
  renderStatistics();
})();
