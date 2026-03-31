const DEFAULT_BASE_URL = process.env.SILICONFLOW_BASE_URL || "https://api.siliconflow.cn/v1";
const DEFAULT_API_KEY = process.env.SILICONFLOW_API_KEY || "";
const DEFAULT_MODEL = process.env.SILICONFLOW_MODEL || "Pro/zai-org/GLM-4.7";
const CHAT_TIMEOUT_MS = Number(process.env.SILICONFLOW_CHAT_TIMEOUT_MS || 45000);
const MODELS_TIMEOUT_MS = Number(process.env.SILICONFLOW_MODELS_TIMEOUT_MS || 15000);
const CHAT_MAX_RETRIES = Number(process.env.SILICONFLOW_CHAT_MAX_RETRIES || 2);
const CHAT_RETRY_DELAY_MS = Number(process.env.SILICONFLOW_CHAT_RETRY_DELAY_MS || 800);
const FALLBACK_MODELS = [
  process.env.SILICONFLOW_FALLBACK_MODEL || "Pro/zai-org/GLM-5",
  "deepseek-ai/DeepSeek-V3.2",
  "Pro/deepseek-ai/DeepSeek-V3.2",
  "Qwen/Qwen3.5-122B-A10B",
].filter(Boolean);
const MODEL_CACHE_TTL_MS = 10 * 60 * 1000;

let cachedModelIds = null;
let cachedModelIdsAt = 0;

export async function createStructuredCompletion({
  systemPrompt,
  userPrompt,
  jsonShapeHint,
  temperature = 0.2,
  model: preferredModel,
}) {
  assertEnvValue(DEFAULT_API_KEY, "SILICONFLOW_API_KEY");
  const resolvedModel = preferredModel || (await resolveConfiguredModelId());
  const candidateModels = [resolvedModel, ...FALLBACK_MODELS.filter((model) => model !== resolvedModel)];
  let lastError = null;

  for (const model of candidateModels) {
    for (let attempt = 0; attempt <= CHAT_MAX_RETRIES; attempt += 1) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort("chat-timeout"), CHAT_TIMEOUT_MS);
      let response;
      let payload;

      try {
        response = await fetch(`${DEFAULT_BASE_URL}/chat/completions`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${DEFAULT_API_KEY}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model,
            temperature,
            messages: [
              { role: "system", content: systemPrompt },
              {
                role: "user",
                content: `${userPrompt}\n\n请只返回 JSON，不要输出 markdown 代码块。\nJSON 结构示例：\n${JSON.stringify(jsonShapeHint, null, 2)}`,
              },
            ],
            response_format: { type: "json_object" },
          }),
          cache: "no-store",
          signal: controller.signal,
        });

        payload = await response.json();
      } catch (error) {
        if (isAbortLikeError(error)) {
          throw new Error(`大模型分析超时（>${Math.round(CHAT_TIMEOUT_MS / 1000)} 秒），请稍后重试。`);
        }

        if (shouldRetryTransientError(error) && attempt < CHAT_MAX_RETRIES) {
          await sleep(CHAT_RETRY_DELAY_MS * (attempt + 1));
          continue;
        }

        throw normalizeFetchError(error);
      } finally {
        clearTimeout(timeout);
      }

      if (!response.ok) {
        const message = payload?.error?.message || payload?.message || "SiliconFlow 调用失败。";
        lastError = new Error(message);

        if (shouldRetryTransientStatus(response.status) && attempt < CHAT_MAX_RETRIES) {
          await sleep(CHAT_RETRY_DELAY_MS * (attempt + 1));
          continue;
        }

        if (shouldRetryWithFallbackModel(response.status, message, model, candidateModels)) {
          break;
        }
        throw lastError;
      }

      const content = payload?.choices?.[0]?.message?.content;
      if (!content) {
        lastError = new Error("SiliconFlow 返回内容为空。");
        if (attempt < CHAT_MAX_RETRIES) {
          await sleep(CHAT_RETRY_DELAY_MS * (attempt + 1));
          continue;
        }
        if (model !== candidateModels[candidateModels.length - 1]) {
          break;
        }
        throw lastError;
      }

      try {
        return JSON.parse(extractJson(content));
      } catch {
        lastError = new Error("SiliconFlow 返回的结构化内容无法解析。");
        if (attempt < CHAT_MAX_RETRIES) {
          await sleep(CHAT_RETRY_DELAY_MS * (attempt + 1));
          continue;
        }
        if (model !== candidateModels[candidateModels.length - 1]) {
          break;
        }
        throw lastError;
      }
    }
  }

  throw lastError || new Error("SiliconFlow 调用失败。");
}

export function getSiliconflowConfig() {
  return {
    baseUrl: DEFAULT_BASE_URL,
    model: DEFAULT_MODEL,
  };
}

export async function resolveConfiguredModelId() {
  return resolveModelId(DEFAULT_MODEL);
}

function extractJson(content) {
  const raw = String(content ?? "").trim();
  if (raw.startsWith("{") || raw.startsWith("[")) {
    return raw;
  }

  const fenceMatch = raw.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenceMatch?.[1]) {
    return fenceMatch[1].trim();
  }

  const strippedFencePrefix = raw.replace(/^```(?:json)?\s*/i, "").trim();
  if (strippedFencePrefix.startsWith("{") || strippedFencePrefix.startsWith("[")) {
    return sliceLikelyJson(strippedFencePrefix);
  }

  const firstObjectBrace = raw.indexOf("{");
  const lastObjectBrace = raw.lastIndexOf("}");
  if (firstObjectBrace !== -1 && lastObjectBrace > firstObjectBrace) {
    return raw.slice(firstObjectBrace, lastObjectBrace + 1).trim();
  }

  const firstArrayBrace = raw.indexOf("[");
  const lastArrayBrace = raw.lastIndexOf("]");
  if (firstArrayBrace !== -1 && lastArrayBrace > firstArrayBrace) {
    return raw.slice(firstArrayBrace, lastArrayBrace + 1).trim();
  }

  return raw;
}

function sliceLikelyJson(raw) {
  const firstObjectBrace = raw.indexOf("{");
  const lastObjectBrace = raw.lastIndexOf("}");
  if (firstObjectBrace !== -1 && lastObjectBrace > firstObjectBrace) {
    return raw.slice(firstObjectBrace, lastObjectBrace + 1).trim();
  }

  const firstArrayBrace = raw.indexOf("[");
  const lastArrayBrace = raw.lastIndexOf("]");
  if (firstArrayBrace !== -1 && lastArrayBrace > firstArrayBrace) {
    return raw.slice(firstArrayBrace, lastArrayBrace + 1).trim();
  }

  return raw;
}

async function resolveModelId(requestedModel) {
  const normalizedRequested = String(requestedModel ?? "").trim();
  if (!normalizedRequested) {
    throw new Error("SiliconFlow 模型名称为空。");
  }

  const modelIds = await listAvailableModelIds();
  if (modelIds.has(normalizedRequested)) {
    return normalizedRequested;
  }

  const proVariant = normalizedRequested.startsWith("Pro/") ? normalizedRequested : `Pro/${normalizedRequested}`;
  if (modelIds.has(proVariant)) {
    return proVariant;
  }

  return proVariant;
}

function shouldRetryWithFallbackModel(status, message, currentModel, candidateModels) {
  if (currentModel === candidateModels[candidateModels.length - 1]) {
    return false;
  }

  const normalizedMessage = String(message || "").toLowerCase();
  return (
    status === 401 ||
    status === 403 ||
    normalizedMessage.includes("private") ||
    normalizedMessage.includes("access") ||
    normalizedMessage.includes("permission")
  );
}

function shouldRetryTransientStatus(status) {
  return status === 408 || status === 409 || status === 425 || status === 429 || status >= 500;
}

function shouldRetryTransientError(error) {
  const message = String(error?.message || error || "").toLowerCase();
  const code = String(error?.code || error?.cause?.code || "").toLowerCase();

  return (
    message.includes("fetch failed") ||
    message.includes("network") ||
    message.includes("socket") ||
    code === "econnreset" ||
    code === "etimedout" ||
    code === "eai_again"
  );
}

function normalizeFetchError(error) {
  if (shouldRetryTransientError(error)) {
    return new Error("SiliconFlow 网络请求失败，请稍后重试。");
  }

  return error instanceof Error ? error : new Error(String(error || "SiliconFlow 调用失败。"));
}

async function listAvailableModelIds() {
  assertEnvValue(DEFAULT_API_KEY, "SILICONFLOW_API_KEY");
  if (cachedModelIds && Date.now() - cachedModelIdsAt < MODEL_CACHE_TTL_MS) {
    return cachedModelIds;
  }

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort("models-timeout"), MODELS_TIMEOUT_MS);
    let response;
    try {
      response = await fetch(`${DEFAULT_BASE_URL}/models`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${DEFAULT_API_KEY}`,
        },
        cache: "no-store",
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeout);
    }

    if (!response.ok) {
      throw new Error("SiliconFlow models 接口调用失败。");
    }

    const payload = await response.json();
    const modelIds = new Set(
      Array.isArray(payload?.data) ? payload.data.map((item) => String(item?.id ?? "").trim()).filter(Boolean) : [],
    );

    cachedModelIds = modelIds;
    cachedModelIdsAt = Date.now();
    return modelIds;
  } catch {
    const fallbackIds = new Set([DEFAULT_MODEL, `Pro/${DEFAULT_MODEL}`]);
    cachedModelIds = fallbackIds;
    cachedModelIdsAt = Date.now();
    return fallbackIds;
  }
}

function isAbortLikeError(error) {
  return (
    error?.name === "AbortError" ||
    String(error?.message || "").toLowerCase().includes("abort") ||
    String(error || "").toLowerCase().includes("abort")
  );
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function assertEnvValue(value, name) {
  if (!String(value || "").trim()) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
}
