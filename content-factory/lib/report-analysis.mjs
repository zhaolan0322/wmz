import { createStructuredCompletion, getSiliconflowConfig, resolveConfiguredModelId } from "./siliconflow-client.mjs";
import { appendRunLog, getSnapshotArticles, listSnapshotCategories, saveGeneratedReport } from "./report-storage.mjs";

const MAX_ARTICLES_TOTAL = 30;
const MAX_ARTICLES_PER_KEYWORD = 5;
const MIN_INSIGHT_COUNT = 5;

export async function runDailyReportAnalysis({ categoryId, targetDate = getPreviousDateKey() }) {
  const categoryIds = categoryId ? [categoryId] : await listSnapshotCategories();
  const reports = [];
  const skipped = [];

  for (const id of categoryIds) {
    const articles = await getSnapshotArticles({ categoryId: id, targetDate });
    if (!articles.length) {
      skipped.push({ categoryId: id, targetDate, reason: "前一天没有可分析的数据。" });
      continue;
    }

    const report = await buildReport({
      mode: "daily",
      categoryId: id,
      targetDate,
      articles,
    });
    await saveGeneratedReport(report);
    reports.push(report);
  }

  await appendRunLog({
    mode: "daily",
    targetDate,
    categoryIds,
    reportCount: reports.length,
    skipped,
  });

  return { reports, skipped };
}

export async function runKeywordReportAnalysis({ categoryId, keyword, targetDate }) {
  if (!categoryId) {
    throw new Error("缺少分类 ID。");
  }

  const normalizedKeyword = String(keyword ?? "").trim();
  if (!normalizedKeyword) {
    throw new Error("缺少定向分析关键词。");
  }

  const analysisDate = targetDate || getLatestSnapshotDateHint();
  const articles = await getSnapshotArticles({
    categoryId,
    targetDate: analysisDate,
    keyword: normalizedKeyword,
  });

  if (!articles.length) {
    throw new Error("当前关键词在指定日期下没有可分析的数据。");
  }

  const report = await buildReport({
    mode: "keyword",
    categoryId,
    targetDate: analysisDate,
    keyword: normalizedKeyword,
    articles,
  });

  await saveGeneratedReport(report);
  await appendRunLog({
    mode: "keyword",
    targetDate: analysisDate,
    categoryId,
    keyword: normalizedKeyword,
    reportId: report.id,
  });

  return report;
}

async function buildReport({ mode, categoryId, targetDate, keyword = "", articles }) {
  const resolvedModel = await resolveConfiguredModelId();
  const selectedArticles = selectTopArticles(articles, keyword);
  const extractedArticles = await summarizeArticles(selectedArticles, { mode, categoryId, targetDate, keyword, model: resolvedModel });
  const insightPayload = await generateInsights(extractedArticles, { mode, categoryId, targetDate, keyword, model: resolvedModel });

  const insights = ensureMinimumInsights(insightPayload?.insights ?? [], extractedArticles);
  const generatedAt = new Date().toISOString();
  const generatedAtTs = Date.now();
  const suggestedPlatform = pickSuggestedPlatform(selectedArticles, insights);
  const summary = normalizeShortText(
    insightPayload?.summary || `${keyword || "昨日"}相关内容的热点已经形成更清晰的选题结构，适合继续深挖。`,
    80,
  );
  const hotSummary = normalizeShortText(
    insightPayload?.hotSummary || "系统已基于 top 文章的摘要、关键词、亮点和证据做了二次洞察聚合。",
    180,
  );

  return {
    id: buildReportId({ mode, categoryId, targetDate, keyword }),
    categoryId,
    reportDate: targetDate,
    date: targetDate,
    label: formatReportLabel(targetDate),
    mode,
    keywordTarget: keyword,
    generatedAt,
    generatedAtTs,
    sourceCount: articles.length,
    analyzedCount: selectedArticles.length,
    model: resolvedModel || getSiliconflowConfig().model,
    summary,
    hotSummary,
    topicCount: insights.length,
    hotContentCount: selectedArticles.length,
    metrics: {
      hotContent: selectedArticles.length,
      topics: insights.length,
      highPriority: insights.filter((item) => String(item.priority).includes("高")).length,
      suggestedPlatform,
    },
    topics: insights.map((insight, index) => ({
      id: `${buildReportId({ mode, categoryId, targetDate, keyword })}-topic-${index + 1}`,
      title: normalizeShortText(insight.title, 42),
      reason: normalizeShortText(insight.insight || insight.reason, 140),
      growth: normalizeShortText(insight.suggested_angle || insight.growth, 140),
      priority: normalizePriority(insight.priority),
      source: buildTopicSource(insight, extractedArticles),
      whyNow: normalizeShortText(insight.why_now || "", 120),
      evidenceArticles: Array.isArray(insight.evidence_articles) ? insight.evidence_articles : [],
      relatedKeywords: Array.isArray(insight.related_keywords) ? insight.related_keywords : [],
      targetPlatform: normalizeShortText(insight.target_platform || suggestedPlatform, 20),
    })),
    articleSummaries: extractedArticles,
  };
}

function selectTopArticles(articles, keyword) {
  const sorted = [...articles].sort((left, right) => Number(right.heat || 0) - Number(left.heat || 0));
  if (keyword) {
    return sorted.slice(0, Math.min(10, sorted.length));
  }

  const grouped = new Map();
  for (const article of sorted) {
    const groupKey = String(article.keyword || "未归类");
    if (!grouped.has(groupKey)) {
      grouped.set(groupKey, []);
    }
    if (grouped.get(groupKey).length < MAX_ARTICLES_PER_KEYWORD) {
      grouped.get(groupKey).push(article);
    }
  }

  return [...grouped.values()].flat().slice(0, MAX_ARTICLES_TOTAL);
}

async function summarizeArticles(articles, context) {
  const shapeHint = {
    articles: [
      {
        article_id: "snapshot-id",
        summary: "文章摘要",
        keywords: ["关键词1", "关键词2"],
        facts: ["关键信息 1", "关键信息 2"],
        highlights: ["亮点 1", "亮点 2"],
        angles: ["延展角度 1", "延展角度 2"],
      },
    ],
  };

  const response = await createStructuredCompletion({
    systemPrompt:
      "你是一名中文内容策略分析师。请从输入文章中抽取结构化事实、关键词、亮点和可延展内容角度。不要编造不存在的信息。",
    userPrompt: buildArticleExtractionPrompt(articles, context),
    jsonShapeHint: shapeHint,
    model: context.model,
  });

  const items = Array.isArray(response?.articles) ? response.articles : [];
  const extractedById = new Map(items.map((item) => [String(item.article_id), item]));

  return articles.map((article) => {
    const extracted = extractedById.get(String(article.id)) || {};
    return {
      articleId: article.id,
      platform: article.platform,
      title: article.title,
      author: article.author,
      keyword: article.keyword,
      heat: article.heat,
      summary: normalizeShortText(extracted.summary || article.description, 180),
      keywords: normalizeStringArray(extracted.keywords, 8),
      facts: normalizeStringArray(extracted.facts, 5),
      highlights: normalizeStringArray(extracted.highlights, 5),
      angles: normalizeStringArray(extracted.angles, 5),
    };
  });
}

async function generateInsights(extractedArticles, context) {
  const shapeHint = {
    summary: "日报摘要",
    hotSummary: "热点摘要",
    insights: [
      {
        title: "结构化选题洞察标题",
        insight: "洞察结论",
        why_now: "为什么现在值得做",
        evidence_articles: ["文章标题 A", "文章标题 B"],
        suggested_angle: "建议切入角度",
        target_platform: "小红书",
        priority: "高优先级",
        related_keywords: ["关键词A", "关键词B"],
      },
    ],
  };

  return createStructuredCompletion({
    systemPrompt:
      "你是一名内容选题分析师。请基于文章结构化摘要，输出至少 5 条中文结构化选题洞察。每条洞察必须具体、有证据、有建议角度，不要空泛。",
    userPrompt: buildInsightPrompt(extractedArticles, context),
    jsonShapeHint: shapeHint,
    model: context.model,
  });
}

function ensureMinimumInsights(insights, extractedArticles) {
  const normalized = insights
    .map((item) => ({
      title: normalizeShortText(item.title, 42),
      insight: normalizeShortText(item.insight, 140),
      why_now: normalizeShortText(item.why_now, 120),
      evidence_articles: normalizeStringArray(item.evidence_articles, 4),
      suggested_angle: normalizeShortText(item.suggested_angle, 140),
      target_platform: normalizeShortText(item.target_platform, 20),
      priority: normalizePriority(item.priority),
      related_keywords: normalizeStringArray(item.related_keywords, 6),
    }))
    .filter((item) => item.title && item.insight);

  if (normalized.length >= MIN_INSIGHT_COUNT) {
    return normalized.slice(0, 8);
  }

  const fallback = [...normalized];
  for (const article of extractedArticles) {
    if (fallback.length >= MIN_INSIGHT_COUNT) break;

    fallback.push({
      title: normalizeShortText(`${article.platform}：${article.title}`, 42),
      insight: normalizeShortText(article.summary, 140),
      why_now: normalizeShortText(article.highlights[0] || article.facts[0] || "该文章在当前样本中具备可延展信号。", 120),
      evidence_articles: [article.title],
      suggested_angle: normalizeShortText(article.angles[0] || "继续拆解这篇文章背后的具体方法和场景。", 140),
      target_platform: article.platform,
      priority: "观察中",
      related_keywords: article.keywords.slice(0, 4),
    });
  }

  return fallback.slice(0, Math.max(MIN_INSIGHT_COUNT, fallback.length));
}

function buildTopicSource(insight, extractedArticles) {
  const evidenceTitles = Array.isArray(insight.evidence_articles) ? insight.evidence_articles.filter(Boolean) : [];
  if (evidenceTitles.length) {
    return evidenceTitles.slice(0, 2).join(" / ");
  }

  const firstArticle = extractedArticles[0];
  return firstArticle ? `${firstArticle.platform} · ${firstArticle.title}` : "AI 自动聚合";
}

function pickSuggestedPlatform(articles, insights) {
  const insightPlatform = insights.find((item) => item?.target_platform)?.target_platform;
  if (insightPlatform) return insightPlatform;

  const platformCounter = new Map();
  articles.forEach((article) => {
    const key = article.platform || "未知平台";
    platformCounter.set(key, (platformCounter.get(key) || 0) + 1);
  });
  return [...platformCounter.entries()].sort((left, right) => right[1] - left[1])[0]?.[0] || "小红书";
}

function buildArticleExtractionPrompt(articles, context) {
  return `分析模式：${context.mode}\n分类：${context.categoryId}\n日期：${context.targetDate}\n定向关键词：${context.keyword || "无"}\n\n请对下面文章逐条做结构化抽取：\n${JSON.stringify(
    articles.map((article) => ({
      article_id: article.id,
      keyword: article.keyword,
      platform: article.platform,
      title: article.title,
      author: article.author,
      heat: article.heat,
      match: article.match,
      description: article.description,
    })),
    null,
    2,
  )}`;
}

function buildInsightPrompt(extractedArticles, context) {
  return `分析模式：${context.mode}\n分类：${context.categoryId}\n日期：${context.targetDate}\n定向关键词：${context.keyword || "无"}\n\n请基于这些文章摘要生成至少 5 条结构化选题洞察：\n${JSON.stringify(
    extractedArticles,
    null,
    2,
  )}`;
}

function normalizeStringArray(value, limit = 6) {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => normalizeShortText(item, 36))
    .filter(Boolean)
    .slice(0, limit);
}

function normalizeShortText(value, maxLength = 120) {
  const normalized = String(value ?? "")
    .replace(/\s+/g, " ")
    .trim();
  if (!normalized) return "";
  return normalized.length > maxLength ? `${normalized.slice(0, maxLength)}...` : normalized;
}

function normalizePriority(value) {
  const raw = normalizeShortText(value, 16);
  if (!raw) return "观察中";
  if (raw.includes("高")) return "高优先级";
  if (raw.includes("中")) return "中优先级";
  if (raw.includes("低")) return "低优先级";
  return raw;
}

function buildReportId({ mode, categoryId, targetDate, keyword }) {
  return [mode, categoryId, targetDate, keyword].filter(Boolean).join("-");
}

function formatReportLabel(dateKey) {
  const [, month = "01", day = "01"] = String(dateKey).split("-");
  return `${month}/${day}`;
}

function getPreviousDateKey() {
  const now = new Date();
  now.setDate(now.getDate() - 1);
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function getLatestSnapshotDateHint() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
