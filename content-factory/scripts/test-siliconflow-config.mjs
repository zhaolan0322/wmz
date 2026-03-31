import assert from "node:assert/strict";
import { getSiliconflowConfig, resolveConfiguredModelId } from "../lib/siliconflow-client.mjs";

const config = getSiliconflowConfig();
assert.equal(
  config.model,
  "Pro/zai-org/GLM-4.7",
  `Expected default SiliconFlow model to be Pro/zai-org/GLM-4.7, got ${config.model}`,
);

const resolved = await resolveConfiguredModelId();
assert.equal(
  resolved,
  "Pro/zai-org/GLM-4.7",
  `Expected resolved SiliconFlow model to be Pro/zai-org/GLM-4.7, got ${resolved}`,
);

console.log("siliconflow config test passed");
