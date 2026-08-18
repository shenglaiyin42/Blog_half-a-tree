(() => {
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

  function blogToday(now = new Date()) {
    const parts = new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      timeZone: BLOG_TIME_ZONE,
    }).formatToParts(now);
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

  function summarize(posts, now = new Date()) {
    const today = blogToday(now);
    const currentWeekKey = weekStart(today);
    const currentMonthKey = today.slice(0, 7);
    const currentWeekPosts = posts.filter((post) => weekStart(post.date) === currentWeekKey);
    const currentMonthPosts = posts.filter((post) => post.date.startsWith(currentMonthKey));
    const wordTotal = (items) => items.reduce((sum, post) => sum + (post.wordCount || 0), 0);

    return {
      currentWeekKey,
      currentMonthKey,
      currentWeekCount: currentWeekPosts.length,
      currentWeekWords: wordTotal(currentWeekPosts),
      currentMonthCount: currentMonthPosts.length,
      currentMonthWords: wordTotal(currentMonthPosts),
      totalCount: posts.length,
      totalWords: wordTotal(posts),
    };
  }

  window.siteStatistics = { summarize, weekLabel, monthLabel };
})();
