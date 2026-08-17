(() => {
  const posts = [...(window.statisticsPosts || [])].sort((a, b) => b.date.localeCompare(a.date));
  const number = new Intl.NumberFormat("zh-CN");
  const BLOG_TIME_ZONE = "America/Chicago";
  const dateFormatter = new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });

  function dateValue(date) {
    return new Date(`${date}T12:00:00Z`);
  }

  function weekStart(date) {
    const value = dateValue(date);
    const day = value.getUTCDay() || 7;
    value.setUTCDate(value.getUTCDate() - day + 1);
    return value.toISOString().slice(0, 10);
  }

  function blogToday() {
    const parts = new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      timeZone: BLOG_TIME_ZONE,
    }).formatToParts(new Date());
    const values = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
    return `${values.year}-${values.month}-${values.day}`;
  }

  function dateLabel(date) {
    return dateFormatter.format(dateValue(date));
  }

  function weekLabel(start) {
    const end = dateValue(start);
    end.setUTCDate(end.getUTCDate() + 6);
    return `${dateLabel(start)}—${dateLabel(end.toISOString().slice(0, 10))}`;
  }

  function monthLabel(key) {
    const [year, month] = key.split("-");
    return `${year}年${Number(month)}月`;
  }

  function groupedBy(keyFunction) {
    const groups = new Map();
    posts.forEach((post) => {
      const key = keyFunction(post.date);
      const group = groups.get(key) || { count: 0, words: 0 };
      group.count += 1;
      group.words += post.wordCount || 0;
      groups.set(key, group);
    });
    return [...groups.entries()].sort((a, b) => b[0].localeCompare(a[0]));
  }

  function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  }

  function setNumber(id, value) {
    const element = document.getElementById(id);
    if (!element) return;
    const unit = element.querySelector("span");
    element.textContent = value;
    if (unit) element.append(unit);
  }

  function renderRows(targetId, groups, labelFunction) {
    const target = document.getElementById(targetId);
    if (!target) return;
    target.innerHTML = groups.length ? groups.map(([key, group]) => `
      <div class="stats-row">
        <time datetime="${key}">${labelFunction(key)}</time>
        <span><strong class="stats-number">${number.format(group.count)}</strong> 篇</span>
        <span><strong class="stats-number">${number.format(group.words)}</strong> 字</span>
      </div>`).join("") : `<p class="sidebar-empty">暂无数据</p>`;
  }

  const weekly = groupedBy(weekStart);
  const monthly = groupedBy((date) => date.slice(0, 7));
  const totalWords = posts.reduce((sum, post) => sum + (post.wordCount || 0), 0);
  const today = blogToday();
  const currentWeekKey = weekStart(today);
  const currentMonthKey = today.slice(0, 7);
  const currentWeek = new Map(weekly).get(currentWeekKey) || { count: 0, words: 0 };
  const currentMonth = new Map(monthly).get(currentMonthKey) || { count: 0, words: 0 };

  setNumber("stats-week-count", number.format(currentWeek.count));
  setNumber("stats-week-words", number.format(currentWeek.words));
  setNumber("stats-month-count", number.format(currentMonth.count));
  setNumber("stats-month-words", number.format(currentMonth.words));
  setNumber("stats-total-count", number.format(posts.length));
  setNumber("stats-total-words", number.format(totalWords));
  setText("stats-current-week", weekLabel(currentWeekKey));
  setText("stats-current-month", monthLabel(currentMonthKey));
  renderRows("stats-weekly-list", weekly, weekLabel);
  renderRows("stats-monthly-list", monthly, monthLabel);
})();
