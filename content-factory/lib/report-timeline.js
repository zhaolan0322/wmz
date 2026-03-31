export const DEFAULT_REPORT_TIMELINE_LIMIT = 7;

export function getTimelineReportsByDate(reports) {
  const safeReports = Array.isArray(reports) ? reports : [];
  const deduped = new Map();

  safeReports.forEach((report) => {
    const dateKey = String(report?.reportDate || report?.date || "").trim();
    if (!dateKey || deduped.has(dateKey)) {
      return;
    }
    deduped.set(dateKey, report);
  });

  return [...deduped.values()];
}

export function getVisibleReportTimelineItems(reports, expanded, limit = DEFAULT_REPORT_TIMELINE_LIMIT) {
  const safeReports = getTimelineReportsByDate(reports);
  const safeLimit = Math.max(1, Number(limit) || DEFAULT_REPORT_TIMELINE_LIMIT);

  return expanded ? safeReports : safeReports.slice(0, safeLimit);
}

export function shouldShowReportTimelineMore(reports, limit = DEFAULT_REPORT_TIMELINE_LIMIT) {
  const safeReports = getTimelineReportsByDate(reports);
  const safeLimit = Math.max(1, Number(limit) || DEFAULT_REPORT_TIMELINE_LIMIT);
  return safeReports.length > safeLimit;
}
