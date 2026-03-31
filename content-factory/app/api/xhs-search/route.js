import { NextResponse } from "next/server";
import https from "node:https";
import { saveSearchResultsAsSnapshots } from "../../../lib/report-storage.mjs";

const SEARCH_ENDPOINT = "https://cn8n.com/p2/xhs/search_note_app";
const SEARCH_TOKEN = process.env.XHS_SEARCH_TOKEN || process.env.WX_SEARCH_TOKEN || "";

export async function POST(request) {
  try {
    const body = await request.json();
    const keyword = String(body?.keyword ?? "").trim();
    const categoryId = String(body?.categoryId ?? "").trim();
    const limitMode = body?.limitMode === "limited" ? "limited" : "all";
    const limit = limitMode === "limited" ? Math.max(1, Number.parseInt(body?.limit || "1", 10) || 1) : null;

    if (!keyword) {
      return NextResponse.json({ msg: "缺少检索关键词。" }, { status: 400 });
    }

    const results = [];
    let page = 1;
    let hasMore = true;

    while (hasMore) {
      const payload = await fetchXhsSearchPage({ keyword, page });
      const items = Array.isArray(payload?.data?.items) ? payload.data.items : [];
      results.push(...items);

      if (!items.length || (limit && results.length >= limit)) {
        hasMore = false;
      } else {
        page += 1;
      }
    }

    const slicedResults = limit ? results.slice(0, limit) : results;
    const fetchedAt = Date.now();

    const mappedItems = slicedResults.map((item, index) => mapXhsResult(item, keyword, index, fetchedAt));

    await saveSearchResultsAsSnapshots({
      categoryId,
      keyword,
      items: mappedItems,
      sourceLabel: "小红书",
      fetchedAt,
    });

    return NextResponse.json({
      code: 0,
      msg: "ok",
      data: {
        sourceLabel: "小红书",
        totalCount: results.length,
        items: mappedItems,
      },
    });
  } catch (error) {
    return NextResponse.json(
      {
        msg: error instanceof Error ? error.message : "小红书检索失败，请稍后重试。",
      },
      { status: 502 },
    );
  }
}

async function fetchXhsSearchPage({ keyword, page }) {
  const payload = await postJson(SEARCH_ENDPOINT, {
    keyword,
    page,
    sort: "",
    note_type: "",
    note_time: "",
    note_range: "",
  });

  if (Number(payload?.code ?? 0) !== 0) {
    throw new Error(payload?.msg || payload?.message || "小红书检索接口调用失败。");
  }

  return payload;
}

function mapXhsResult(item, keyword, index, fetchedAt) {
  const note = item?.note ?? {};
  const user = note?.user ?? {};
  const publishTimestamp = normalizeTimestamp(note.timestamp, fetchedAt);
  const displayTimestamp = Number(fetchedAt || Date.now());
  const stats = [
    note.liked_count ? `${note.liked_count} 点赞` : "",
    note.comments_count ? `${note.comments_count} 评论` : "",
    note.collected_count ? `${note.collected_count} 收藏` : "",
  ]
    .filter(Boolean)
    .join(" · ");

  return {
    id: `xhs-search-${user.userid || "user"}-${publishTimestamp}-${index}`,
    time: formatTimelineTime(displayTimestamp),
    platform: "小红书",
    heat: formatHeat(note.liked_count, note.comments_count, note.collected_count),
    title: sanitizeApiText(note.title || note.desc || "小红书检索结果", 88),
    author: sanitizeApiText(user.nickname || user.userid || "小红书用户", 40),
    match: sanitizeApiText(`检索关键词：${keyword}`, 80),
    tag: "NEW",
    description: compactText(note.desc) || sanitizeApiText(stats, 60) || "已从小红书接口拉取到一条新内容。",
    sortTimestamp: displayTimestamp,
    isNewResult: true,
    firstFetchedAt: displayTimestamp,
    link: "",
    avatar: user.images || "",
  };
}

function normalizeTimestamp(rawValue, fallbackValue) {
  const raw = Number(rawValue || fallbackValue || Date.now());
  if (raw > 10_000_000_000) return raw;
  return raw * 1000;
}

function formatTimelineTime(timestamp) {
  const date = new Date(timestamp);
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${month}/${day} ${hours}:${minutes}`;
}

function formatHeat(likedCount, commentsCount, collectedCount) {
  const score = Number(likedCount || 0) / 1000 + Number(commentsCount || 0) / 120 + Number(collectedCount || 0) / 150;
  return score ? score.toFixed(1) : "NEW";
}

function compactText(content) {
  const normalized = sanitizeApiText(content, 72);
  if (!normalized) return "";
  return normalized;
}

function sanitizeApiText(value, maxLength = 72) {
  const normalized = String(value || "")
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

function postJson(url, body) {
  if (!SEARCH_TOKEN) {
    return Promise.reject(new Error("Missing required environment variable: XHS_SEARCH_TOKEN or WX_SEARCH_TOKEN"));
  }

  return new Promise((resolve, reject) => {
    const payload = JSON.stringify(body);
    const request = https.request(
      url,
      {
        method: "POST",
        family: 4,
        timeout: 30000,
        headers: {
          Authorization: `Bearer ${SEARCH_TOKEN}`,
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(payload),
        },
      },
      (response) => {
        let raw = "";

        response.on("data", (chunk) => {
          raw += chunk;
        });

        response.on("end", () => {
          try {
            const parsed = JSON.parse(raw);

            if ((response.statusCode ?? 500) >= 400) {
              reject(new Error(parsed?.msg || parsed?.message || "小红书检索接口调用失败。"));
              return;
            }

            resolve(parsed);
          } catch {
            const statusCode = response.statusCode ?? 500;
            const normalizedRaw = String(raw || "").replace(/\s+/g, " ").trim();

            if (statusCode >= 500) {
              reject(new Error(`小红书上游接口暂时异常（HTTP ${statusCode}），请稍后重试。`));
              return;
            }

            reject(
              new Error(
                normalizedRaw
                  ? `小红书检索接口返回了非 JSON 响应：${normalizedRaw.slice(0, 80)}`
                  : "小红书检索接口返回了无法解析的响应。",
              ),
            );
          }
        });
      },
    );

    request.on("error", (error) => reject(error));
    request.on("timeout", () => request.destroy(new Error("小红书检索请求超时，请稍后再试。")));
    request.write(payload);
    request.end();
  });
}
