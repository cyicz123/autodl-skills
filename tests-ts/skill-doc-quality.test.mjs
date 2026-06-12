import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

const ROOT = path.resolve(import.meta.dirname, "..");

async function readSkill(relativePath) {
  return readFile(path.join(ROOT, relativePath), "utf8");
}

function assertIncludesAll(text, snippets) {
  const missing = snippets.filter((snippet) => !text.includes(snippet));
  assert.deepEqual(missing, []);
}

async function readCombinedDocs() {
  const skill = await readSkill("skills/autodl/SKILL.md");
  const examples = await readSkill("skills/autodl/examples.md");
  const sync = await readSkill("skills/autodl/sync-reference.md");
  return `${skill}\n${examples}\n${sync}`;
}

test("unified skill teaches dry-run, elastic, and pro essentials", async () => {
  const combined = await readCombinedDocs();

  assertIncludesAll(combined, [
    "dry-run",
    "no live API call",
    "not executed",
    // elastic
    "https://private.autodl.com",
    "AUTODL_ELASTIC_TOKEN",
    "/api/v1/dev/deployment/container/list",
    "/api/v1/dev/machine/region/gpu_stock",
    "/api/v1/dev/deployment",
    "`cuda_v_from` / `cuda_v_to` are integer codes",
    "not semantic version strings",
    "do not write `\"11.8\"`, `\"12.1\"`, or `\"12.8\"`",
    "\"name\": \"inference-service\"",
    "\"cuda_v_from\": 118",
    "\"cuda_v_to\": 122",
    "after 3 submit failures",
    "不要直接重试",
    // pro
    "https://api.autodl.com",
    "AUTODL_PRO_TOKEN",
    "node <SKILL_DIR>/autodl.mjs pro create --json <config.json>",
    "validation_error",
    "/api/v1/dev/instance/pro/power_on",
    "\"instance_uuid\": \"pro-xxxxxxxx\"",
    "\"payload\": \"gpu\"",
    "\"start_command\": \"bash /root/start.sh\"",
    "/api/v1/dev/instance/pro/image/save",
    "\"image_name\": \"my-saved-image\"",
  ]);
});

test("unified skill teaches the rclone SSH sync workflow", async () => {
  const combined = await readCombinedDocs();

  assertIncludesAll(combined, [
    "rclone",
    "rclone version",
    "rclone obscure",
    "rclone copy",
    "rclone sync",
    "--dry-run",
    "winget install Rclone.Rclone",
    "https://rclone.org/install.sh",
    "brew install rclone",
    "RCLONE_SFTP_PASS",
    ":sftp:",
  ]);
});

test("unified skill no longer offers AUTODL_TOKEN as a usable fallback", async () => {
  const combined = await readCombinedDocs();
  for (const phrase of ["fallback `AUTODL_TOKEN`", "fallback AUTODL_TOKEN", "`AUTODL_TOKEN`)"]) {
    assert.ok(!combined.includes(phrase), `docs must not present AUTODL_TOKEN as a fallback: ${phrase}`);
  }
  assert.ok(
    (await readSkill("skills/autodl/SKILL.md")).includes("no shared `AUTODL_TOKEN` fallback"),
    "SKILL.md should state there is no AUTODL_TOKEN fallback",
  );
});
