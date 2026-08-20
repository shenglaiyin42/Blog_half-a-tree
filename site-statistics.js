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

  function summarize(entries, now = new Date()) {
    const today = blogToday(now);
    const currentWeekKey = weekStart(today);
    const currentMonthKey = today.slice(0, 7);
    const datedEntries = entries.filter((entry) => /^\d{4}-\d{2}-\d{2}$/.test(entry.date || ""));
    const currentWeekEntries = datedEntries.filter((entry) => weekStart(entry.date) === currentWeekKey);
    const currentMonthEntries = datedEntries.filter((entry) => entry.date.startsWith(currentMonthKey));
    const wordTotal = (items) => items.reduce((sum, entry) => sum + (entry.wordCount || 0), 0);

    return {
      currentWeekKey,
      currentMonthKey,
      currentWeekCount: currentWeekEntries.length,
      currentWeekWords: wordTotal(currentWeekEntries),
      currentMonthCount: currentMonthEntries.length,
      currentMonthWords: wordTotal(currentMonthEntries),
      totalCount: entries.length,
      totalWords: wordTotal(entries),
    };
  }

  window.siteStatistics = { summarize, weekLabel, monthLabel };
})();
