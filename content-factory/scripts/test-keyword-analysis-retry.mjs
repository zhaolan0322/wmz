import assert from "node:assert/strict";
import { runKeywordReportAnalysis } from "../lib/report-analysis.mjs";

const originalFetch = globalThis.fetch;

let chatAttempts = 0;
globalThis.fetch = async (url) => {
  if (String(url).endsWith("/models")) {
    return {
      ok: true,
      json: async () => ({
        data: [{ id: "Pro/zai-org/GLM-4.7" }],
      }),
    };
  }

  if (String(url).endsWith("/chat/completions")) {
    chatAttempts += 1;

    if (chatAttempts === 1) {
      throw new TypeError("fetch failed");
    }

    if (chatAttempts === 2) {
      return {
        ok: true,
        json: async () => ({
          choices: [
            {
              message: {
                content: JSON.stringify({
                  articles: [
                    {
                      article_id: "x1",
                      summary: "文章摘要",
                      keywords: ["skill"],
                      facts: ["事实"],
                      highlights: ["亮点"],
                      angles: ["角度"],
                    },
                  ],
                }),
              },
            },
          ],
        }),
      };
    }

    return {
      ok: true,
      json: async () => ({
        choices: [
          {
            message: {
              content: JSON.stringify({
                summary: "总结成功",
                hotSummary: "热点总结",
                insights: [
                  {
                    title: "选题一",
                    insight: "洞察一",
                    why_now: "原因一",
                    evidence_articles: ["文章 A"],
                    suggested_angle: "角度一",
                    target_platform: "公众号",
                    priority: "高优先级",
                    related_keywords: ["skill"],
                  },
                  {
                    title: "选题二",
                    insight: "洞察二",
                    why_now: "原因二",
                    evidence_articles: ["文章 B"],
                    suggested_angle: "角度二",
                    target_platform: "小红书",
                    priority: "中优先级",
                    related_keywords: ["skill"],
                  },
                  {
                    title: "选题三",
                    insight: "洞察三",
                    why_now: "原因三",
                    evidence_articles: ["文章 C"],
                    suggested_angle: "角度三",
                    target_platform: "小红书",
                    priority: "中优先级",
                    related_keywords: ["skill"],
                  },
                  {
                    title: "选题四",
                    insight: "洞察四",
                    why_now: "原因四",
                    evidence_articles: ["文章 D"],
                    suggested_angle: "角度四",
                    target_platform: "小红书",
                    priority: "低优先级",
                    related_keywords: ["skill"],
                  },
                  {
                    title: "选题五",
                    insight: "洞察五",
                    why_now: "原因五",
                    evidence_articles: ["文章 E"],
                    suggested_angle: "角度五",
                    target_platform: "小红书",
                    priority: "低优先级",
                    related_keywords: ["skill"],
                  },
                ],
              }),
            },
          },
        ],
      }),
    };
  }

  throw new Error(`Unexpected URL: ${url}`);
};

try {
  const report = await runKeywordReportAnalysis({
    categoryId: "claude-code",
    keyword: "skill",
    targetDate: "2026-03-31",
  });

  assert.equal(chatAttempts, 3, "Expected keyword analysis to retry once and then complete both model calls");
  assert.equal(report.model, "Pro/zai-org/GLM-4.7");
  assert.equal(report.summary, "总结成功");
  assert.equal(report.topicCount, 5);
  console.log("keyword analysis retry test passed");
} finally {
  globalThis.fetch = originalFetch;
}
