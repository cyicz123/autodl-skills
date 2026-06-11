# AutoDL Skills TypeScript Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the existing `autodl-elastic-deploy` skill from Python to TypeScript and add a sibling `autodl-instance-pro` skill in the same repository.

**Architecture:** Keep two independent skill folders under `skills/`, each with its own `SKILL.md`, `.env.example`, reference docs, runnable JavaScript entrypoint, host, and token namespace. Share TypeScript source and tests through a repo-level `src/` package, but pass an explicit runtime context into every command so private-cloud elastic deployment and public-cloud Pro API calls can run side by side without sharing hidden global host/token state.

**Tech Stack:** Node.js 22+, TypeScript, native `fetch`, Node built-in test runner, no runtime npm dependencies.

---

## Repository Shape

Create or modify these paths:

- Create `package.json`, `tsconfig.json`, `src/`, and `tests-ts/` at repo root.
- Replace Python implementation in `skills/autodl-elastic-deploy/queue_submit.py` with a TS-authored compiled entrypoint `skills/autodl-elastic-deploy/autodl-elastic.mjs`.
- Create sibling skill folder `skills/autodl-instance-pro/` with `SKILL.md`, `.env.example`, `autodl-pro.mjs`, `api-reference.md`, and `examples.md`.
- Keep legacy Python files/tests until the TS equivalent is green, then remove `queue_submit.py`, `pyproject.toml`, `requirements-dev.txt`, and Python `tests/`.
- Update root `README.md` to explain the repository contains two AutoDL skills.

Do not use one shared AutoDL host or one shared primary token variable for both skills. Treat each skill as a separate cloud context:

| Skill | Cloud context | Default host | Host env override | Primary token env | Compatibility token fallback |
| --- | --- | --- | --- | --- | --- |
| `autodl-elastic-deploy` | AutoDL private cloud elastic deployment | `https://private.autodl.com` | `AUTODL_ELASTIC_HOST` | `AUTODL_ELASTIC_TOKEN` | `AUTODL_TOKEN` |
| `autodl-instance-pro` | AutoDL public cloud container instance Pro | `https://api.autodl.com` | `AUTODL_PRO_HOST` | `AUTODL_PRO_TOKEN` | `AUTODL_TOKEN` |

Each CLI must read only its own skill-local `.env` file, never a sibling skill's `.env`. The fallback `AUTODL_TOKEN` exists only for backward compatibility and must lose to the skill-specific token variable when both are present.

## Task 1: Add TypeScript Project Skeleton

**Files:**
- Create: `package.json`
- Create: `tsconfig.json`
- Create: `src/core/errors.ts`
- Create: `src/core/token.ts`
- Create: `src/core/http.ts`
- Create: `src/core/cli.ts`
- Test: `tests-ts/core.test.mjs`

- [ ] **Step 1: Write failing tests for common utilities**

Test cases:
- `loadRuntimeContext(options)` resolves host/token from explicit skill settings.
- Elastic context uses `AUTODL_ELASTIC_HOST`, `AUTODL_ELASTIC_TOKEN`, and default host `https://private.autodl.com`.
- Pro context uses `AUTODL_PRO_HOST`, `AUTODL_PRO_TOKEN`, and default host `https://api.autodl.com`.
- Skill-specific token env vars win over `AUTODL_TOKEN`.
- Skill-local `.env` files are isolated; loading elastic context must not read `skills/autodl-instance-pro/.env`, and loading Pro context must not read `skills/autodl-elastic-deploy/.env`.
- `.env` parsing ignores blank lines, comments, unknown keys, and preserves values containing `=`.
- HTTP wrapper sends `Authorization` and `Content-Type: application/json`.
- HTTP wrapper returns parsed JSON for `code: "Success"`.
- HTTP wrapper throws structured `api_error` for non-2xx, invalid JSON, fetch errors, or `code !== "Success"`.
- CLI error printer writes JSON to stdout and exits with the intended code.

Run:

```bash
node --test tests-ts/core.test.mjs
```

Expected: fail because `dist/core/*.mjs` does not exist yet.

- [ ] **Step 2: Add package and compiler config**

Use this minimal shape:

```json
{
  "type": "module",
  "scripts": {
    "build": "tsc",
    "test": "npm run build && node --test tests-ts/*.test.mjs",
    "check": "tsc --noEmit"
  },
  "devDependencies": {
    "typescript": "^5.8.0"
  }
}
```

Set `tsconfig.json` to compile `src/**/*.ts` into `dist/`, target ES2022 or newer, use `module: "NodeNext"`, `moduleResolution: "NodeNext"`, `strict: true`, and emit declarations only if useful.

- [ ] **Step 3: Implement common utilities**

Implement:
- `loadRuntimeContext({ skillDir, defaultHost, hostEnvName, tokenEnvName, fallbackTokenEnvName = "AUTODL_TOKEN", env = process.env })`.
- `loadToken` as an internal helper only if useful; callers must use `loadRuntimeContext` so host and token stay paired to the correct skill.
- `loadHost` with env override, `.env` fallback, then default host.
- `readJsonFile(path)`.
- `requestJson({ host, method, path, token, body, fetchImpl })`.
- `printJson`, `printErrorAndExit`, and small argument helpers.

Do not log tokens. Error JSON must use:

```json
{
  "status": "error",
  "error_type": "api_error",
  "message": "...",
  "details": {}
}
```

- [ ] **Step 4: Verify**

Run:

```bash
npm test
```

Expected: core tests pass.

- [ ] **Step 5: Commit**

```bash
git add package.json tsconfig.json src tests-ts
git commit -m "build: add typescript test harness"
```

## Task 2: Port Elastic Queue Submission To TypeScript

**Files:**
- Create: `src/elastic/schema.ts`
- Create: `src/elastic/api.ts`
- Create: `src/elastic/queue.ts`
- Create: `src/elastic/cli.ts`
- Create compiled output: `skills/autodl-elastic-deploy/autodl-elastic.mjs`
- Modify: `skills/autodl-elastic-deploy/SKILL.md`
- Test: `tests-ts/elastic.test.mjs`

- [ ] **Step 1: Write failing elastic behavior tests**

Cover the existing Python behavior:
- Valid config returns no validation errors.
- `ReplicaSet` and `Job` require `replica_num`; `Job` also requires `parallelism_num`; `Container` does not require `replica_num`.
- `container_template` requires `dc_list`, `gpu_name_set`, `gpu_num`, `cuda_v_from`, `cuda_v_to`, CPU/memory/price ranges, `cmd`, and `image_uuid`.
- Deprecated legacy configs with `cuda_v` but no `cuda_v_from/cuda_v_to` fail with a clear migration message.
- Range inversions, empty GPU list, and `gpu_num < 1` fail locally.
- Elastic API calls use `https://private.autodl.com` by default.
- `AUTODL_ELASTIC_HOST` overrides only elastic calls and does not affect Pro calls.
- `AUTODL_ELASTIC_TOKEN` wins over `AUTODL_TOKEN`.
- Image pagination calls `POST /api/v1/dev/image/private/list`.
- GPU stock for queue checks calls `POST /api/v1/dev/machine/region/gpu_stock` when `dc_list` is present.
- Immediate success outputs `status: "success"`, `deployment_uuid`, and `waited_seconds`.
- Timeout outputs `error_type: "timeout"`.
- Three submit failures output `error_type: "submission_error"`.

Run:

```bash
npm test
```

Expected: fail because elastic modules are missing.

- [ ] **Step 2: Implement elastic validation and API helpers**

Use the private-cloud elastic deployment runtime context:
- Default host: `https://private.autodl.com`.
- Host override: `AUTODL_ELASTIC_HOST` or `AUTODL_ELASTIC_HOST=...` in `skills/autodl-elastic-deploy/.env`.
- Token: `AUTODL_ELASTIC_TOKEN`, then fallback `AUTODL_TOKEN`.

Use elastic deployment fields from the existing skill and official elastic docs:
- Top-level: `name`, `deployment_type`, `replica_num`, `parallelism_num`, `reuse_container`, `reuse_container_scope`.
- Template: `dc_list`, `service_6006_port_protocol`, `service_6008_port_protocol`, `cuda_v_from`, `cuda_v_to`, `gpu_name_set`, `gpu_num`, CPU/memory/price ranges, `image_uuid`, `cmd_before_shutdown`, `cmd`.

Normalize private image records as:

```ts
{ uuid: image.image_uuid ?? "", name: image.image_name ?? image.name ?? "" }
```

Normalize GPU stock records into:

```ts
Record<string, { idle: number; total: number }>
```

- [ ] **Step 3: Implement elastic CLI**

Commands:

```bash
node skills/autodl-elastic-deploy/autodl-elastic.mjs queue-submit <config.json> [--interval 30] [--timeout 0]
node skills/autodl-elastic-deploy/autodl-elastic.mjs images [--page-index 1] [--page-size 100]
node skills/autodl-elastic-deploy/autodl-elastic.mjs deployments [--page-index 1] [--page-size 10]
node skills/autodl-elastic-deploy/autodl-elastic.mjs containers --deployment-uuid <uuid> [--page-index 1] [--page-size 10]
node skills/autodl-elastic-deploy/autodl-elastic.mjs events --deployment-uuid <uuid> [--offset N]
node skills/autodl-elastic-deploy/autodl-elastic.mjs stop-container <container_uuid> [--decrease-one-replica-num] [--no-cache]
node skills/autodl-elastic-deploy/autodl-elastic.mjs set-replicas <deployment_uuid> <replica_num>
node skills/autodl-elastic-deploy/autodl-elastic.mjs stop-deployment <deployment_uuid>
node skills/autodl-elastic-deploy/autodl-elastic.mjs delete-deployment <deployment_uuid>
node skills/autodl-elastic-deploy/autodl-elastic.mjs blacklist <container_uuid> [--comment "..."]
node skills/autodl-elastic-deploy/autodl-elastic.mjs list-blacklist
node skills/autodl-elastic-deploy/autodl-elastic.mjs gpu-stock --region <region_sign> [--json <filters.json>]
```

Keep `queue-submit` as the emphasized path for creating deployments with polling. Other commands should be thin wrappers around documented endpoints.

- [ ] **Step 4: Copy compiled entrypoint into skill folder**

After `npm run build`, create a small checked-in `autodl-elastic.mjs` entrypoint in the skill folder that imports `../../dist/elastic/cli.mjs` if the repo is used from source, or alternatively compile directly into `skills/autodl-elastic-deploy/autodl-elastic.mjs`.

Pick one approach and ensure the skill works after cloning the repository and running `npm install && npm run build`.

- [ ] **Step 5: Update elastic skill docs**

Update `SKILL.md`:
- Change examples from `python queue_submit.py` to `node autodl-elastic.mjs queue-submit`.
- Keep elastic HOST as private cloud by default: `https://private.autodl.com`.
- Document `AUTODL_ELASTIC_HOST` for private cloud endpoint overrides.
- Document token order: `AUTODL_ELASTIC_TOKEN`, then `AUTODL_TOKEN`, then skill-local `.env`.
- Update config examples to use `dc_list`, `cuda_v_from`, and `cuda_v_to`.
- Keep current error-handling guidance for `validation_error`, `image_not_found`, `gpu_type_not_found`, `submission_error`, `timeout`, `token_missing`, and `config_error`.

- [ ] **Step 6: Verify**

Run:

```bash
npm test
node skills/autodl-elastic-deploy/autodl-elastic.mjs --help
python C:\Users\chengyue\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills/autodl-elastic-deploy
```

Expected: all pass; help command exits 0 and does not require a token.

- [ ] **Step 7: Commit**

```bash
git add src tests-ts skills/autodl-elastic-deploy package.json tsconfig.json
git commit -m "feat: port autodl elastic skill to typescript"
```

## Task 3: Add Sibling AutoDL Instance Pro Skill

**Files:**
- Create: `skills/autodl-instance-pro/SKILL.md`
- Create: `skills/autodl-instance-pro/.env.example`
- Create: `skills/autodl-instance-pro/api-reference.md`
- Create: `skills/autodl-instance-pro/examples.md`
- Create: `skills/autodl-instance-pro/autodl-pro.mjs`
- Create: `src/pro/api.ts`
- Create: `src/pro/schema.ts`
- Create: `src/pro/cli.ts`
- Test: `tests-ts/pro.test.mjs`

- [ ] **Step 1: Write failing Pro API tests**

Cover:
- Create request validates required fields: `req_gpu_amount`, `expand_system_disk_by_gb`, `gpu_spec_uuid`, `image_uuid`, `cuda_v_from`.
- `req_gpu_amount` must be 1 through 4.
- `expand_system_disk_by_gb` must be 0 through 500.
- `create --json config.json` calls `POST /api/v1/dev/instance/pro/create`.
- `snapshot <uuid>` calls `GET /api/v1/dev/instance/pro/snapshot` with body `{ instance_uuid }`.
- `status <uuid>` calls `GET /api/v1/dev/instance/pro/status` with body `{ instance_uuid }`.
- `list`, `power-on`, `power-off`, `release`, `save-image`, and `list-images` call the documented endpoints.
- `power-on` always sends `payload: "gpu"` and includes `start_command` only when provided.
- `release` does not silently power off first; docs tell the agent to power off before release.
- Pro API calls use `https://api.autodl.com` by default.
- `AUTODL_PRO_HOST` overrides only Pro calls and does not affect elastic calls.
- `AUTODL_PRO_TOKEN` wins over `AUTODL_TOKEN`.

Run:

```bash
npm test
```

Expected: fail because Pro modules are missing.

- [ ] **Step 2: Implement Pro API wrapper and CLI**

Commands:

```bash
node skills/autodl-instance-pro/autodl-pro.mjs create --json <config.json>
node skills/autodl-instance-pro/autodl-pro.mjs snapshot <instance_uuid>
node skills/autodl-instance-pro/autodl-pro.mjs status <instance_uuid>
node skills/autodl-instance-pro/autodl-pro.mjs list [--page-index 1] [--page-size 10]
node skills/autodl-instance-pro/autodl-pro.mjs power-on <instance_uuid> [--start-command "..."]
node skills/autodl-instance-pro/autodl-pro.mjs power-off <instance_uuid>
node skills/autodl-instance-pro/autodl-pro.mjs release <instance_uuid>
node skills/autodl-instance-pro/autodl-pro.mjs save-image <instance_uuid> --name <image_name>
node skills/autodl-instance-pro/autodl-pro.mjs list-images [--page-index 1] [--page-size 10]
```

Use official Pro endpoints from `https://www.autodl.com/docs/instance_pro_api/`:
- `POST /api/v1/dev/instance/pro/create`
- `GET /api/v1/dev/instance/pro/snapshot`
- `GET /api/v1/dev/instance/pro/status`
- `POST /api/v1/dev/instance/pro/list`
- `POST /api/v1/dev/instance/pro/power_on`
- `POST /api/v1/dev/instance/pro/power_off`
- `POST /api/v1/dev/instance/pro/release`
- `POST /api/v1/dev/instance/pro/image/save`
- `POST /api/v1/dev/instance/pro/image/private/list`

- [ ] **Step 3: Write Pro skill docs**

`SKILL.md` frontmatter:

```yaml
---
name: autodl-instance-pro
description: Use when managing AutoDL public cloud container instance Pro resources, including creating instances, listing instances, checking status/details, power on/off, release, save images, and list private images through AutoDL Pro API.
---
```

Body must include:
- API host: `https://api.autodl.com`.
- Host override: `AUTODL_PRO_HOST`.
- Token flow: `AUTODL_PRO_TOKEN`, then `AUTODL_TOKEN`, then skill-local `.env`.
- A warning that using Pro API requires personal or enterprise verification.
- Release workflow: power off first, then release.
- Reference tables for GPU spec IDs and public base image UUID examples.
- CLI examples only; do not include Python snippets.

- [ ] **Step 4: Verify**

Run:

```bash
npm test
node skills/autodl-instance-pro/autodl-pro.mjs --help
python C:\Users\chengyue\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills/autodl-instance-pro
```

Expected: all pass; help command exits 0 and does not require a token.

- [ ] **Step 5: Commit**

```bash
git add src tests-ts skills/autodl-instance-pro
git commit -m "feat: add autodl instance pro skill"
```

## Task 4: Remove Python Packaging After TS Parity

**Files:**
- Delete: `skills/autodl-elastic-deploy/queue_submit.py`
- Delete: `pyproject.toml`
- Delete: `requirements-dev.txt`
- Delete: `tests/`
- Modify: `.gitignore`
- Modify: `README.md`

- [ ] **Step 1: Write a failing repository hygiene test**

Add a test that asserts no active skill instructions reference `queue_submit.py`, `pytest`, `requirements-dev.txt`, or `pyproject.toml`.

Run:

```bash
npm test
```

Expected: fail while legacy references remain.

- [ ] **Step 2: Remove Python artifacts**

Delete old Python code and tests only after Tasks 2 and 3 are green. Keep `.env.example`, `api-reference.md`, `examples.md`, and `SKILL.md`.

- [ ] **Step 3: Update README**

README must describe:
- `skills/autodl-elastic-deploy`: private-cloud elastic deployment skill using `https://private.autodl.com`, `AUTODL_ELASTIC_HOST`, and `AUTODL_ELASTIC_TOKEN`.
- `skills/autodl-instance-pro`: public cloud container instance Pro skill.
- Build/test flow:

```bash
npm install
npm run build
npm test
```

- How to symlink or install either skill into `~/.agents/skills`.

- [ ] **Step 4: Verify**

Run:

```bash
npm test
rg "queue_submit.py|pytest|requirements-dev|pyproject.toml" README.md skills tests-ts src
```

Expected: tests pass; `rg` has no stale operational references except migration notes if deliberately kept.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove python implementation after ts migration"
```

## Task 5: Final Validation And Skill Installation Check

**Files:**
- Modify only if validation finds issues.

- [ ] **Step 1: Run full checks**

```bash
npm run build
npm test
node skills/autodl-elastic-deploy/autodl-elastic.mjs --help
node skills/autodl-instance-pro/autodl-pro.mjs --help
python C:\Users\chengyue\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills/autodl-elastic-deploy
python C:\Users\chengyue\.codex\skills\.system\skill-creator\scripts\quick_validate.py skills/autodl-instance-pro
```

- [ ] **Step 2: Check local skill directory compatibility**

If installing locally from this repo, ensure these paths can be used:

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.agents\skills\autodl-elastic-deploy" -Target "C:\Users\chengyue\Documents\Code\autodl-elastic-deploy\skills\autodl-elastic-deploy"
New-Item -ItemType Junction -Path "$env:USERPROFILE\.agents\skills\autodl-instance-pro" -Target "C:\Users\chengyue\Documents\Code\autodl-elastic-deploy\skills\autodl-instance-pro"
```

Do not overwrite existing installed skills without checking current targets first.

- [ ] **Step 3: Forward-test skill usage**

Use a fresh agent/thread or minimal context and ask:
- “Use `$autodl-elastic-deploy` to create a queued ReplicaSet from this config, but do not call live APIs.”
- “Use `$autodl-instance-pro` to check the status of `pro-abc123`, but do not call live APIs.”
- “With both `AUTODL_ELASTIC_HOST` and `AUTODL_PRO_HOST` set, explain which host each skill will call, but do not call live APIs.”

Expected:
- The agent selects the correct skill.
- The agent uses Node CLI commands.
- The agent keeps elastic private-cloud host/token separate from Pro public-cloud host/token.
- The agent refuses live API calls without token/user confirmation.
- The agent does not mention Python.

- [ ] **Step 4: Final commit**

```bash
git status --short
git commit -m "docs: validate autodl skill migration" --allow-empty
```

Only use `--allow-empty` if all validations passed and there are no file changes from Task 5.

## Acceptance Criteria

- `autodl-elastic-deploy` remains a skill folder and is TypeScript-backed.
- `autodl-instance-pro` exists as a sibling skill folder in the same repository.
- Both skills use Node.js 22+ and checked-in JS entrypoints produced from TypeScript.
- No runtime dependency is required beyond Node.js for skill users.
- Host and token loading are explicit per skill, allowing both skills to be installed and used in parallel.
- Elastic defaults to `https://private.autodl.com`, `AUTODL_ELASTIC_HOST`, and `AUTODL_ELASTIC_TOKEN`; Pro defaults to `https://api.autodl.com`, `AUTODL_PRO_HOST`, and `AUTODL_PRO_TOKEN`.
- `AUTODL_TOKEN` remains only as a backward-compatible fallback and never overrides skill-specific token variables.
- Tests mock network calls; no live AutoDL API call is made during test runs.
- Official docs are reflected: elastic deployment uses `dc_list`, `cuda_v_from`, and `cuda_v_to`; Pro API covers create/snapshot/status/list/power/release/image commands.
