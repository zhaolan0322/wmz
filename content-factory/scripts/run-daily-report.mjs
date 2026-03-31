import { getReportConfig } from "../lib/report-storage.mjs";
import { runDailyReportAnalysis } from "../lib/report-analysis.mjs";

async function main() {
  const config = await getReportConfig();

  if (config.enabled === false) {
    console.log("[daily-report] skipped: schedule disabled");
    return;
  }

  const targetDate = parseArgValue("--date");
  const categoryId = parseArgValue("--category");
  const result = await runDailyReportAnalysis({ categoryId, targetDate });

  console.log(
    JSON.stringify(
      {
        ok: true,
        targetDate: targetDate || "previous-day",
        categoryId: categoryId || "all",
        reportCount: result.reports.length,
        skippedCount: result.skipped.length,
      },
      null,
      2,
    ),
  );
}

function parseArgValue(name) {
  const prefix = `${name}=`;
  const matched = process.argv.find((arg) => arg.startsWith(prefix));
  return matched ? matched.slice(prefix.length) : "";
}

main().catch((error) => {
  console.error("[daily-report] failed", error);
  process.exitCode = 1;
});
