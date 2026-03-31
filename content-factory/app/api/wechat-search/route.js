import { NextResponse } from "next/server";
import https from "node:https";
import { saveSearchResultsAsSnapshots } from "../../../lib/report-storage.mjs";

const SEARCH_ENDPOINT = "https://cn8n.com/p4/fbmain/monitor/v3/kw_search";
const DEFAULT_PERIOD = 7;
const SEARCH_TOKEN = process.env.WX_SEARCH_TOKEN || "";

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
    let totalCount = 0;
    let totalPage = 1;

    do {
      const payload = await fetchWeChatSearchPage({ keyword, page });
      const data = payload?.data ?? {};
      const pageItems = Array.isArray(data.data) ? data.data : [];

      totalCount = Number(data.total ?? pageItems.length);
      totalPage = Number(data.total_page ?? 1);

      results.push(...pageItems);

      if (limit && results.length >= limit) {
        break;
      }

      page += 1;
    } while (page <= totalPage);

    const slicedResults = limit ? results.slice(0, limit) : results;
    const fetchedAt = Date.now();

    const mappedItems = slicedResults.map((item, index) => mapWeChatResult(item, keyword, index, fetchedAt));

    await saveSearchResultsAsSnapshots({
      categoryId,
      keyword,
      items: mappedItems,
      sourceLabel: "公众号",
      fetchedAt,
    });

    return NextResponse.json({
      code: 0,
      msg: "ok",
      data: {
        sourceLabel: "公众号",
        totalCount,
        items: mappedItems,
      },
    });
  } catch (error) {
    return NextResponse.json(
      {
        msg: error instanceof Error ? error.message : "公众号检索失败，请稍后重试。",
      },
      { status: 502 },
    );
  }
}

async function fetchWeChatSearchPage({ keyword, page }) {
  const payload = await postJson(SEARCH_ENDPOINT, {
    kw: keyword,
    sort_type: 1,
    mode: 1,
    period: DEFAULT_PERIOD,
    page,
    any_kw: "",
    ex_kw: "",
    verifycode: "",
    type: 1,
  });

  if (Number(payload?.code ?? 0) !== 0) {
    throw new Error(payload?.msg || payload?.message || "公众号检索接口调用失败。");
  }

  return payload;
}

function mapWeChatResult(item, keyword, index, fetchedAt) {
  const publishTimestamp = normalizeTimestamp(item.publish_time, item.update_time);
  const displayTimestamp = Number(fetchedAt || Date.now());
  const stats = [
    item.read ? `${item.read} 阅读` : "",
    item.praise ? `${item.praise} 点赞` : "",
    item.looking ? `${item.looking} 在看` : "",
  ]
    .filter(Boolean)
    .join(" · ");

  return {
    id: `wechat-search-${item.ghid || item.wx_id || "item"}-${publishTimestamp}-${index}`,
    time: formatTimelineTime(displayTimestamp),
    platform: "公众号",
    heat: formatHeat(item.read, item.praise, item.looking),
    title: sanitizeApiText(item.title || "公众号检索结果", 88),
    author: sanitizeApiText(item.wx_name || item.wx_id || "公众号", 40),
    match: sanitizeApiText(`检索关键词：${keyword}${item.classify ? ` · 分类：${item.classify}` : ""}`, 80),
    tag: "NEW",
    description: compactText(item.content) || sanitizeApiText(stats, 60) || "已从公众号接口拉取到一条新内容。",
    sortTimestamp: displayTimestamp,
    isNewResult: true,
    link: item.url || item.short_link || "",
    firstFetchedAt: displayTimestamp,
  };
}

function normalizeTimestamp(publishTime, updateTime) {
  const raw = Number(publishTime || updateTime || Date.now());
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

function formatHeat(read, praise, looking) {
  const score = Number(read || 0) / 1000 + Number(praise || 0) / 100 + Number(looking || 0) / 50;
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
    return Promise.reject(new Error("Missing required environment variable: WX_SEARCH_TOKEN"));
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
              reject(new Error(parsed?.msg || parsed?.message || "公众号检索接口调用失败。"));
              return;
            }

            resolve(parsed);
          } catch (error) {
            const statusCode = response.statusCode ?? 500;
            const normalizedRaw = String(raw || "").replace(/\s+/g, " ").trim();

            if (statusCode >= 500) {
              reject(new Error(`公众号上游接口暂时异常（HTTP ${statusCode}），请稍后重试。`));
              return;
            }

            reject(
              new Error(
                normalizedRaw
                  ? `公众号检索接口返回了非 JSON 响应：${normalizedRaw.slice(0, 80)}`
                  : "公众号检索接口返回了无法解析的响应。",
              ),
            );
          }
        });
      },
    );

    request.on("error", (error) => reject(error));
    request.on("timeout", () => request.destroy(new Error("公众号检索请求超时，请稍后再试。")));
    request.write(payload);
    request.end();
  });
}
