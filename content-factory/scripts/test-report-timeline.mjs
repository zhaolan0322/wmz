import assert from "node:assert/strict";
import {
  DEFAULT_REPORT_TIMELINE_LIMIT,
  getTimelineReportsByDate,
  getVisibleReportTimelineItems,
  shouldShowReportTimelineMore,
} from "../lib/report-timeline.js";

const reports = [
  { id: "report-1", reportDate: "2026-03-31" },
  { id: "report-2", reportDate: "2026-03-30" },
  { id: "report-3", reportDate: "2026-03-30" },
  { id: "report-4", reportDate: "2026-03-29" },
  { id: "report-5", reportDate: "2026-03-28" },
  { id: "report-6", reportDate: "2026-03-27" },
  { id: "report-7", reportDate: "2026-03-26" },
  { id: "report-8", reportDate: "2026-03-25" },
  { id: "report-9", reportDate: "2026-03-24" },
];

assert.deepEqual(
  getTimelineReportsByDate(reports).map((item) => item.id),
  ["report-1", "report-2", "report-4", "report-5", "report-6", "report-7", "report-8", "report-9"],
  "Expected timeline to keep only the first report for each unique date",
);

assert.equal(DEFAULT_REPORT_TIMELINE_LIMIT, 7, "Expected report timeline limit to stay at 7");
assert.equal(
  getVisibleReportTimelineItems(reports, false).length,
  7,
  "Expected collapsed report timeline to show only 7 items",
);
assert.deepEqual(
  getVisibleReportTimelineItems(reports, false).map((item) => item.id),
  ["report-1", "report-2", "report-4", "report-5", "report-6", "report-7", "report-8"],
  "Expected collapsed report timeline to keep the first 7 unique dates",
);
assert.equal(shouldShowReportTimelineMore(reports), true, "Expected more button when reports exceed 7");
assert.equal(
  getVisibleReportTimelineItems(reports, true).length,
  8,
  "Expected expanded report timeline to show all items",
);
assert.equal(
  shouldShowReportTimelineMore(reports.slice(0, 8)),
  false,
  "Expected no more button when unique date count is 7 or less",
);

console.log("report timeline test passed");
