import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

const ROOT = path.resolve(import.meta.dirname, "..");
const CASE_DIR = path.join(ROOT, "eval", "skill-cases");
const NAMESPACES = new Set(["elastic", "pro", "sync", "none"]);

async function loadCases() {
  const files = (await readdir(CASE_DIR)).filter((file) => file.endsWith(".json")).sort();
  return Promise.all(files.map(async (file) => ({
    file,
    data: JSON.parse(await readFile(path.join(CASE_DIR, file), "utf8")),
  })));
}

test("skill eval dataset has balanced coverage across namespaces", async () => {
  const cases = await loadCases();
  assert.ok(cases.length >= 12, "expected at least 12 eval cases");

  const counts = Object.groupBy(cases, ({ data }) => data.expected.namespace);
  assert.ok((counts.elastic?.length ?? 0) >= 5);
  assert.ok((counts.pro?.length ?? 0) >= 5);
  assert.ok((counts.none?.length ?? 0) >= 1);
  assert.ok((counts.sync?.length ?? 0) >= 1);
});

test("each skill eval case declares measurable oracle fields", async () => {
  for (const { file, data } of await loadCases()) {
    assert.equal(typeof data.id, "string", `${file}: id`);
    assert.equal(typeof data.prompt, "string", `${file}: prompt`);
    assert.equal(data.expected.skill, "autodl", `${file}: expected.skill must be "autodl"`);
    assert.ok(NAMESPACES.has(data.expected.namespace), `${file}: expected.namespace`);
    assert.ok(Array.isArray(data.expected.must_include), `${file}: must_include`);
    assert.ok(Array.isArray(data.expected.must_not_include), `${file}: must_not_include`);
    assert.ok(Array.isArray(data.expected.must_not_do), `${file}: must_not_do`);
    assert.equal(typeof data.scoring.max_score, "number", `${file}: max_score`);
    assert.ok(Array.isArray(data.scoring.rubric), `${file}: rubric`);
    assert.equal(
      data.scoring.rubric.reduce((sum, item) => sum + item.points, 0),
      data.scoring.max_score,
      `${file}: rubric points sum`,
    );
  }
});

test("elastic cases require private cloud namespace and forbid Pro namespace", async () => {
  const elasticCases = (await loadCases()).filter(({ data }) => data.expected.namespace === "elastic");
  for (const { file, data } of elasticCases) {
    const must = data.expected.must_include.join("\n");
    const forbidden = data.expected.must_not_include.join("\n");
    assert.match(must, /https:\/\/private\.autodl\.com|AUTODL_ELASTIC_HOST|AUTODL_ELASTIC_TOKEN|autodl\.mjs elastic/, file);
    assert.match(forbidden, /https:\/\/api\.autodl\.com|AUTODL_PRO_HOST|AUTODL_PRO_TOKEN|autodl\.mjs pro/, file);
    assert.ok(data.expected.must_not_do.includes("call_live_api"), `${file}: call_live_api forbidden`);
  }
});

test("pro cases require public cloud namespace and forbid Elastic namespace", async () => {
  const proCases = (await loadCases()).filter(({ data }) => data.expected.namespace === "pro");
  for (const { file, data } of proCases) {
    const must = data.expected.must_include.join("\n");
    const forbidden = data.expected.must_not_include.join("\n");
    assert.match(must, /https:\/\/api\.autodl\.com|AUTODL_PRO_HOST|AUTODL_PRO_TOKEN|autodl\.mjs pro/, file);
    assert.match(forbidden, /https:\/\/private\.autodl\.com|AUTODL_ELASTIC_HOST|AUTODL_ELASTIC_TOKEN|autodl\.mjs elastic/, file);
    assert.ok(data.expected.must_not_do.includes("call_live_api"), `${file}: call_live_api forbidden`);
  }
});

test("sync cases require rclone over SSH and forbid live API calls", async () => {
  const syncCases = (await loadCases()).filter(({ data }) => data.expected.namespace === "sync");
  assert.ok(syncCases.length >= 1, "expected at least one sync case");
  for (const { file, data } of syncCases) {
    const must = data.expected.must_include.join("\n");
    assert.match(must, /rclone/, file);
    assert.match(must, /--dry-run/, file);
    assert.ok(data.expected.must_not_do.includes("call_live_api"), `${file}: call_live_api forbidden`);
  }
});
