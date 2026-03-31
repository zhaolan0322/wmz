import assert from "node:assert/strict";
import { createStructuredCompletion } from "../lib/siliconflow-client.mjs";

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

    return {
      ok: true,
      json: async () => ({
        choices: [
          {
            message: {
              content: JSON.stringify({
                ok: true,
                summary: "retry succeeded",
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
  const payload = await createStructuredCompletion({
    systemPrompt: "test",
    userPrompt: "test",
    jsonShapeHint: { ok: true, summary: "text" },
  });

  assert.equal(chatAttempts, 2, "Expected SiliconFlow chat request to retry once after transient failure");
  assert.equal(payload.summary, "retry succeeded", "Expected retry result to be returned");
  console.log("siliconflow retry test passed");
} finally {
  globalThis.fetch = originalFetch;
}
