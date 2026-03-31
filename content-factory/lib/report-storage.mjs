import { promises as fs } from "node:fs";
import path from "node:path";

const DATA_DIR = path.join(process.cwd(), "data");
const SNAPSHOT_DIR = path.join(DATA_DIR, "article-snapshots");
const REPORT_DIR = path.join(DATA_DIR, "report-analyses");
const RUN_DIR = path.join(DATA_DIR, "report-runs");
const CONFIG_FILE = path.join(DATA_DIR, "report-config.json");

const DEFAULT_CONFIG = {
  dailyRunTime: "08:30",
  enabled: true,
  model: "Pro/zai-org/GLM-4.7",
  baseUrl: "https://api.siliconflow.cn/v1",
};

export async function getReportConfig() {
  await ensureDir(DATA_DIR);
  const config = await readJson(CONFIG_FILE, DEFAULT_CONFIG);
  return { ...DEFAULT_CONFIG, ...config };
}

export async function saveReportConfig(config) {
  const nextConfig = { ...(await getReportConfig()), ...config };
  await writeJson(CONFIG_FILE, nextConfig);
  return nextConfig;
}

export async function saveSearchResultsAsSnapshots({ categoryId, keyword, items, sourceLabel, fetchedAt }) {
  if (!categoryId || !keyword || !Array.isArray(items) || !items.length) {
    return [];
  }

  const snapshotDate = formatDateKey(fetchedAt || Date.now());
  const filePath = getSnapshotFilePath(categoryId, snapshotDate);
  const existingItems = await readJson(filePath, []);
  const deduped = new Map(existingItems.map((item) => [buildSnapshotKey(item), item]));
  const appended = [];

  for (const item of items) {
    const snapshotItem = normalizeSnapshotItem({
      categoryId,
      keyword,
      sourceLabel,
      fetchedAt,
      item,
    });

    const key = buildSnapshotKey(snapshotItem);
    if (!deduped.has(key)) {
      deduped.set(key, snapshotItem);
      appended.push(snapshotItem);
    }
  }

  await writeJson(filePath, [...deduped.values()]);
  return appended;
}

export async function getSnapshotArticles({ categoryId, targetDate, keyword }) {
  if (!categoryId || !targetDate) {
    return [];
  }

  const filePath = getSnapshotFilePath(categoryId, targetDate);
  const items = await readJson(filePath, []);

  return items.filter((item) => {
    if (!keyword) return true;
    return String(item.keyword ?? "").trim().toLowerCase() === String(keyword).trim().toLowerCase();
  });
}

export async function listRecentSnapshotStates({ categoryId, limit = 7 }) {
  if (!categoryId) return [];

  const categoryDir = path.join(SNAPSHOT_DIR, categoryId);

  try {
    const entries = await fs.readdir(categoryDir);
    const dateFiles = entries
      .filter((name) => name.endsWith(".json"))
      .map((name) => name.replace(/\.json$/i, ""))
      .sort((left, right) => String(right).localeCompare(String(left)))
      .slice(0, limit);

    const grouped = await Promise.all(
      dateFiles.map(async (dateKey) => ({
        date: dateKey,
        items: await readJson(getSnapshotFilePath(categoryId, dateKey), []),
      })),
    );

    return grouped
      .map(({ date, items }) => ({
        date,
        keyword: "",
        returnedCount: items.length,
        totalCount: items.length,
        sourceLabel: items.length === 1 ? items[0].platform || "" : "",
        results: items.map((item) => ({
          id: item.id,
          time: formatSnapshotTime(item.fetchedAtTs || item.sortTimestamp),
          platform: item.platform,
          heat: item.heat,
          title: item.title,
          author: item.author,
          match: item.match,
          description: item.description,
          tag: "",
          isNewResult: false,
          seenAt: item.seenAt || item.fetchedAtTs || item.sortTimestamp,
          firstFetchedAt: item.firstFetchedAt || item.fetchedAtTs || item.sortTimestamp,
          sortTimestamp: item.sortTimestamp || item.fetchedAtTs || Date.now(),
          link: item.link || "",
          keyword: item.keyword || "",
        })),
      }))
      .filter((state) => state.results.length);
  } catch {
    return [];
  }
}

export async function listSnapshotCategories() {
  try {
    const entries = await fs.readdir(SNAPSHOT_DIR, { withFileTypes: true });
    return entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name);
  } catch {
    return [];
  }
}

export async function saveGeneratedReport(report) {
  if (!report?.id || !report?.categoryId || !report?.reportDate || !report?.mode) {
    throw new Error("报告缺少必要字段，无法保存。");
  }

  const filePath = getReportFilePath(report.categoryId, report.mode, report.reportDate, report.id);
  await writeJson(filePath, report);
  return report;
}

export async function listGeneratedReports(categoryId) {
  if (!categoryId) return [];

  const dailyReports = await listReportsByMode(categoryId, "daily");
  const keywordReports = await listReportsByMode(categoryId, "keyword");

  return [...dailyReports, ...keywordReports].sort((left, right) => {
    const leftTime = Number(left.generatedAtTs ?? Date.parse(left.generatedAt ?? 0) ?? 0);
    const rightTime = Number(right.generatedAtTs ?? Date.parse(right.generatedAt ?? 0) ?? 0);
    if (rightTime !== leftTime) return rightTime - leftTime;
    return String(right.reportDate).localeCompare(String(left.reportDate));
  });
}

export async function appendRunLog(entry) {
  const dateKey = formatDateKey(Date.now());
  const filePath = path.join(RUN_DIR, `${dateKey}.json`);
  const items = await readJson(filePath, []);
  items.push({ ...entry, loggedAt: new Date().toISOString() });
  await writeJson(filePath, items);
}

function getSnapshotFilePath(categoryId, dateKey) {
  return path.join(SNAPSHOT_DIR, categoryId, `${dateKey}.json`);
}

function getReportFilePath(categoryId, mode, dateKey, reportId) {
  return path.join(REPORT_DIR, categoryId, mode, `${dateKey}--${slugify(reportId)}.json`);
}

async function listReportsByMode(categoryId, mode) {
  const dirPath = path.join(REPORT_DIR, categoryId, mode);
  try {
    const entries = await fs.readdir(dirPath);
    const reports = await Promise.all(
      entries.filter((name) => name.endsWith(".json")).map((name) => readJson(path.join(dirPath, name), null)),
    );
    return reports.filter(Boolean);
  } catch {
    return [];
  }
}

function normalizeSnapshotItem({ categoryId, keyword, sourceLabel, fetchedAt, item }) {
  const fetchedAtTs = Number(fetchedAt || item?.firstFetchedAt || item?.sortTimestamp || Date.now());

  return {
    id: item?.id || `snapshot-${Date.now()}`,
    categoryId,
    keyword,
    platform: item?.platform || sourceLabel || "",
    title: sanitizeSnapshotText(item?.title, 120),
    author: sanitizeSnapshotText(item?.author, 64),
    match: sanitizeSnapshotText(item?.match, 120),
    description: sanitizeSnapshotText(item?.description, 400),
    heat: Number(item?.heat || 0),
    link: item?.link || "",
    fetchedAt: new Date(fetchedAtTs).toISOString(),
    fetchedAtTs,
    firstFetchedAt: Number(item?.firstFetchedAt || fetchedAtTs),
    sortTimestamp: Number(item?.sortTimestamp || fetchedAtTs),
  };
}

function buildSnapshotKey(item) {
  return [item.categoryId, item.keyword, item.platform, item.author, item.title]
    .map((value) => String(value ?? "").trim().toLowerCase())
    .join("|");
}

function sanitizeSnapshotText(value, maxLength = 200) {
  const normalized = String(value ?? "")
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/\r?\n/g, " ")
    .replace(/\\n/g, " ")
    .replace(/\\r|\\t/g, " ")
    .replace(/^\s*---+\s*/g, "")
    .replace(/\s+---+\s+/g, " ")
    .replace(/^\s*#+\s*/g, "")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1")
    .replace(/\s{2,}/g, " ")
    .trim();

  if (!normalized) return "";
  return normalized.length > maxLength ? `${normalized.slice(0, maxLength)}...` : normalized;
}

async function readJson(filePath, fallbackValue) {
  try {
    const raw = await fs.readFile(filePath, "utf8");
    return JSON.parse(raw);
  } catch {
    return fallbackValue;
  }
}

async function writeJson(filePath, value) {
  await ensureDir(path.dirname(filePath));
  await fs.writeFile(filePath, JSON.stringify(value, null, 2), "utf8");
}

async function ensureDir(dirPath) {
  await fs.mkdir(dirPath, { recursive: true });
}

function slugify(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fa5-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

function formatDateKey(input) {
  const date = new Date(input);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatSnapshotTime(input) {
  const date = new Date(input || Date.now());
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${month}/${day} ${hours}:${minutes}`;
}
