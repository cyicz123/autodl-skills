# AutoDL Skills Unification + rclone SSH Sync Implementation Plan

> **For agentic workers:** Implement this plan task-by-task. Each step uses checkbox (`- [ ]`) syntax for tracking. Follow the repo's existing test-first style (write/adjust failing tests, then implement, then verify with `npm test`).

**Goal:** Merge the two separate skills (`autodl-elastic-deploy`, `autodl-instance-pro`) into a single unified skill `skills/autodl/` exposing one CLI `autodl.mjs` with cloud-prefixed subcommands (`elastic <cmd>` / `pro <cmd>`), drop the `AUTODL_TOKEN` compatibility fallback, rename the project to `autodl-skills`, and add an rclone-based incremental SSH sync capability documented entirely in the skill (no new TS code path). The sync replaces the current "需要一个公共仓库" workflow with direct local↔container transfer over SSH/SFTP.

**Tech Stack:** Node.js 22+, TypeScript, native `fetch`, Node built-in test runner, no runtime npm dependencies. Sync relies on the external `rclone` binary (detected/installed by the agent, not bundled).

---

## Decision Record (agreed via grill-me)

**Restructure / rename**
- One skill `skills/autodl/`; one entrypoint `autodl.mjs`; subcommands `elastic <cmd>` / `pro <cmd>`. Cloud prefix is **required** (no bare aliases).
- One `SKILL.md`, one `.env`, one checked-in `skills/autodl/dist/`.
- Rename project to `autodl-skills`: internal naming (README, skill dir, doc references, `package.json` `name`) **and** the git remote. Do **not** rename the local working-directory folder (would break the session); that is a manual step the user may do later.
- Token model: keep only `AUTODL_ELASTIC_TOKEN` and `AUTODL_PRO_TOKEN` namespaces. **Remove the `AUTODL_TOKEN` fallback entirely.** `elastic` uses `AUTODL_ELASTIC_HOST`/`AUTODL_ELASTIC_TOKEN` (default `https://private.autodl.com`); `pro` uses `AUTODL_PRO_HOST`/`AUTODL_PRO_TOKEN` (default `https://api.autodl.com`).

**Sync (doc-only, rclone)**
- Delivery: documentation only. No `autodl.mjs sync` subcommand, no `src/sync`. The agent detects/installs `rclone` and runs it directly.
- Resource coverage: elastic containers (SSH from `containers` → `info.ssh_command`/`info.root_password`) and pro instances (SSH from `snapshot` → `ssh_command`/`proxy_host`/`root_password`/`ssh_port`). SSH info is auto-derived.
- Auth: ephemeral env var + on-the-fly `:sftp:` backend; password passed through `rclone obscure`; never write a config file, never put the plaintext password on the command line / shell history.
- Semantics: default `rclone copy` (no remote deletion). `rclone sync` (mirror, deletes) is opt-in and **must** run `--dry-run` first, show the deletions, and get explicit confirmation.
- Direction: push (local→container) is primary; pull (container→local for logs/weights/artifacts) is documented.
- Remote path: **no default**; the calling agent supplies it (from its own AGENTS.md/context).
- Excludes: default set `.git`, `__pycache__`, `*.pyc`, `.ipynb_checkpoints`, `node_modules`, `.DS_Store`; user can extend/override via `--exclude` / `--filter-from`.
- Host key: skip strict checking (do not configure `known_hosts`) because AutoDL containers are ephemeral.
- Install policy: agent **always shows the install command and asks for confirmation** before installing; never silent.
- Install matrix: Windows (`winget install Rclone.Rclone` primary; `scoop`/`choco`/manual zip+PATH fallback), Linux (`curl https://rclone.org/install.sh | sudo bash` primary; `apt`/`dnf` fallback), macOS (`brew install rclone`).
- Performance defaults: `--progress --transfers 4 --checkers 8 --multi-thread-streams 4 --stats 10s`; mention `--bwlimit` for throttling.

**Docs / tests / eval**
- Docs are English-primary; `frontmatter` `description` is bilingual (CN + EN) for retrieval.
- Doc structure: `SKILL.md` (concise overview of elastic + pro + a short Sync section/entry) + `api-reference.md` (elastic + pro endpoints) + `examples.md` (elastic/pro/sync examples) + dedicated `sync-reference.md` (full rclone detail).
- Update all affected tests and eval cases; add one sync dry-run eval case.

---

## Target Repository Shape

```text
skills/
  autodl/
    SKILL.md
    autodl.mjs              # entrypoint -> ./dist/main/cli.mjs
    .env.example            # both AUTODL_ELASTIC_* and AUTODL_PRO_*
    api-reference.md        # elastic + pro endpoints (pro snapshot SSH fields added)
    examples.md             # elastic + pro + sync examples
    sync-reference.md       # full rclone-over-SSH sync guide
    dist/                   # copied from root dist/ at build time
src/
  core/                     # token.mts loses the AUTODL_TOKEN default fallback
  elastic/                  # unchanged API/queue; cli help text reworded for `elastic` prefix
  pro/
  main/
    cli.mts                 # NEW top-level router: elastic | pro dispatch + help
scripts/
  copy-dist.mjs             # NEW cross-platform copy root dist/ -> skills/autodl/dist/
tests-ts/
eval/
  skill-cases/              # updated; expected.skill -> "autodl" + namespace field; + sync case
```

Old `skills/autodl-elastic-deploy/` and `skills/autodl-instance-pro/` are deleted.

---

## Task 1: Core Router + Remove `AUTODL_TOKEN` Fallback

**Files:**
- Modify: `src/core/token.mts`
- Create: `src/main/cli.mts`
- Modify: `src/elastic/cli.mts` (help text + token_missing message)
- Modify: `src/pro/cli.mts` (help text + token_missing message)
- Modify: `tests-ts/core.test.mjs`

- [ ] **Step 1: Adjust token fallback semantics (test-first)**
  - In `tests-ts/core.test.mjs`, change the test "skill-specific token wins over AUTODL_TOKEN fallback" to assert that `AUTODL_TOKEN` is **ignored**: with `env: { AUTODL_TOKEN: "compat-token" }` and no `AUTODL_PRO_TOKEN`, `context.token` is `undefined`. Keep a test asserting the specific token resolves normally.
  - Run `node --test tests-ts/core.test.mjs` and expect failure.

- [ ] **Step 2: Implement**
  - In `src/core/token.mts`: remove the `?? "AUTODL_TOKEN"` default. Only apply a fallback when `options.fallbackTokenEnvName` is explicitly provided; otherwise resolve token from `env[tokenEnvName] ?? skillEnv[tokenEnvName]` only.
  - `src/elastic/cli.mts` and `src/pro/cli.mts`: do not pass `fallbackTokenEnvName`. Update `token_missing` messages to drop `AUTODL_TOKEN` (e.g. elastic: `.env 中未找到 AUTODL_ELASTIC_TOKEN`; pro: `.env not found: AUTODL_PRO_TOKEN`).

- [ ] **Step 3: Implement top-level router `src/main/cli.mts`**
  - `main(argv, io)` reads `argv[0]` as namespace.
  - `elastic` → call elastic `main(argv.slice(1), io)`; `pro` → call pro `main(argv.slice(1), io)`.
  - No args / `--help` / `-h` → print top-level help listing both namespaces, noting `sync` is documentation-driven (rclone) and not a subcommand.
  - Unknown namespace → structured `config_error`.
  - Keep the `import.meta.url === process.argv[1]` self-exec guard.

- [ ] **Step 4: Reword sub-CLI help** so usage lines read `node autodl.mjs elastic <cmd>` / `node autodl.mjs pro <cmd>` instead of `autodl-elastic.mjs` / `autodl-pro.mjs`.

- [ ] **Step 5: Verify** `npm test` (core green). Build emits `dist/main/cli.mjs`.

## Task 2: Create Unified `skills/autodl/` And Delete Old Skill Folders

**Files:**
- Create: `skills/autodl/autodl.mjs`, `skills/autodl/.env.example`
- Create: `scripts/copy-dist.mjs`; Modify: `package.json`
- Delete: `skills/autodl-elastic-deploy/`, `skills/autodl-instance-pro/`

- [ ] **Step 1: Entrypoint** `skills/autodl/autodl.mjs`:

```js
#!/usr/bin/env node
import { main } from "./dist/main/cli.mjs";

process.exitCode = await main(process.argv.slice(2));
```

- [ ] **Step 2: Unified `.env.example`** containing both namespaces (no `AUTODL_TOKEN`):

```env
AUTODL_ELASTIC_TOKEN=your_private_cloud_token_here
AUTODL_ELASTIC_HOST=https://private.autodl.com
AUTODL_PRO_TOKEN=your_public_cloud_token_here
AUTODL_PRO_HOST=https://api.autodl.com
```

- [ ] **Step 3: Build-time dist copy.** Add `scripts/copy-dist.mjs` that recursively copies root `dist/` → `skills/autodl/dist/` (use `node:fs` `cp` with `{ recursive: true }`, cross-platform). Update `package.json`:
  - `"build": "tsc && node scripts/copy-dist.mjs"`
  - keep `"test": "npm run build && node --test tests-ts/*.test.mjs"`.

- [ ] **Step 4: Delete** both old skill directories (including their stale `dist/` copies). Confirm `defaultSkillDir()` (`dist/<area>/cli.mjs` → `../..`) still resolves to `skills/autodl/` so `.env` is read from `skills/autodl/.env`.

- [ ] **Step 5: Verify** `npm run build` then `node skills/autodl/autodl.mjs --help`, `node skills/autodl/autodl.mjs elastic --help`, `node skills/autodl/autodl.mjs pro --help` all exit 0 without a token.

## Task 3: Author Unified Skill Docs (`SKILL.md`, `api-reference.md`, `examples.md`)

**Files:**
- Create: `skills/autodl/SKILL.md`
- Create: `skills/autodl/api-reference.md`
- Create: `skills/autodl/examples.md`

- [ ] **Step 1: `SKILL.md`** (English-primary). Frontmatter `name: autodl`; `description` bilingual covering elastic private-cloud deploy, pro public-cloud instances, and rclone SSH sync trigger words (AutoDL, 弹性部署, 公有云, 实例, 同步, sync, rclone, 增量同步).
  - Sections: Overview (two clouds + one sync); per-cloud Host/Host-override/Token table (no `AUTODL_TOKEN`); Dry-run checklist (merged, both clouds, must say `not executed` / `no live API call`); CLI quick reference using `node <SKILL_DIR>/autodl.mjs elastic ...` and `... pro ...`; concise **Sync** section that links to `sync-reference.md`; error_type table.
  - Preserve the doc-quality anchors (see Task 5) such as CUDA integer-code wording, `after 3 submit failures` / `不要直接重试`, pro power-on payload, save-image payload.

- [ ] **Step 2: `api-reference.md`** — merge elastic + pro endpoint references into one file with clear "Elastic (private cloud)" and "Pro (public cloud)" sections. Include the pro `snapshot` response with `ssh_command`, `proxy_host`, `root_password`, `ssh_port` (Task 4).

- [ ] **Step 3: `examples.md`** — merged elastic + pro CLI examples updated to the `autodl.mjs elastic|pro` form, plus a Sync examples block (push/pull, copy vs sync, dry-run).

- [ ] **Step 4: Verify** `npm test` (after Task 5 updates) and skill-doc-quality assertions pass.

## Task 4: Add Pro Snapshot SSH Fields To Reference

**Files:** Modify `skills/autodl/api-reference.md` (pro section).

- [ ] Document the pro `GET /api/v1/dev/instance/pro/snapshot` response fields used for sync: `ssh_command`, `proxy_host` (ssh address), `root_password` (ssh password), `ssh_port`. Source: `https://www.autodl.com/docs/instance_pro_api/`. State that elastic SSH comes from `containers` (`info.ssh_command` / `info.root_password`) and pro SSH comes from `snapshot`.

## Task 5: Write `sync-reference.md` (rclone Over SSH)

**Files:** Create `skills/autodl/sync-reference.md`.

- [ ] **Step 1: Detection & install** (agent always shows command, asks first; never silent):
  - Detect: `rclone version` (exit 0 = installed).
  - Windows: `winget install Rclone.Rclone` (primary); fallback `scoop install rclone`, `choco install rclone`, or manual zip from rclone.org + add to PATH.
  - Linux: `curl https://rclone.org/install.sh | sudo bash` (primary); fallback `apt install rclone` / `dnf install rclone`.
  - macOS: `brew install rclone`.

- [ ] **Step 2: Obtain SSH connection info.**
  - Elastic: `node <SKILL_DIR>/autodl.mjs elastic containers --deployment-uuid <uuid>` → parse `info.ssh_command` (`ssh -p <port> root@<host>`) + `info.root_password`.
  - Pro: `node <SKILL_DIR>/autodl.mjs pro snapshot <instance_uuid>` → use `ssh_command` / `proxy_host` / `ssh_port` / `root_password`.
  - Show host/port/user parsing rules from `ssh -p <port> <user>@<host>`.

- [ ] **Step 3: Auth via ephemeral env + on-the-fly backend.** Document the pattern (no config file, no plaintext on command line):
  - Obscure once: set an obscured password into an env var, e.g. `RCLONE_SFTP_PASS` derived from `rclone obscure "<root_password>"`.
  - Use a connection-string remote referencing env values, e.g. backend `:sftp,host=<host>,port=<port>,user=root:` while password is supplied via the `RCLONE_SFTP_*` environment.
  - Document the Windows (PowerShell `$env:`) and POSIX (`export`) variants, and that the variable holds the obscured value only.
  - Host key: do not set `known_hosts` (strict checking skipped) for ephemeral hosts.

- [ ] **Step 4: Push / pull semantics.**
  - Push (default, safe): `rclone copy <localDir> :sftp,...:<REMOTE_PATH> <defaults> <excludes>`.
  - Pull: `rclone copy :sftp,...:<REMOTE_PATH> <localDir> ...`.
  - Mirror (opt-in, dangerous): `rclone sync ...` — **must** run `--dry-run` first, present added/changed/**deleted** files, get explicit confirmation, then run for real.
  - `REMOTE_PATH` has no default; the agent supplies it from its AGENTS.md.

- [ ] **Step 5: Defaults.**
  - Excludes (default): `--exclude ".git/**" --exclude "__pycache__/**" --exclude "*.pyc" --exclude ".ipynb_checkpoints/**" --exclude "node_modules/**" --exclude ".DS_Store"`; user may add `--exclude`/`--filter-from`.
  - Performance: `--progress --transfers 4 --checkers 8 --multi-thread-streams 4 --stats 10s`; `--bwlimit <rate>` optional.
  - Note Windows path quirks (drive letters / backslashes) for the local side.

- [ ] **Step 6: Dry-run discipline** consistent with the skill's dry-run checklist: when asked to only show commands, print the full rclone command, state `not executed` / `no live API call`, and do not run it.

## Task 6: Update Tests For The Refactor

**Files:** `tests-ts/elastic.test.mjs`, `tests-ts/pro.test.mjs`, `tests-ts/skill-doc-quality.test.mjs`, `tests-ts/hygiene.test.mjs` (verify only).

- [ ] **Step 1: `pro.test.mjs` / `elastic.test.mjs`** — remove/adjust any assertion depending on the `AUTODL_TOKEN` fallback and on the old `token_missing` message text. If they invoke `main`, ensure they still call the per-cloud `main` directly (router not required for unit tests). Update any path/name strings.

- [ ] **Step 2: `skill-doc-quality.test.mjs`** — rewrite to read unified docs:
  - Read `skills/autodl/SKILL.md`, `skills/autodl/examples.md`, `skills/autodl/sync-reference.md`.
  - Keep elastic anchors (`https://private.autodl.com`, `AUTODL_ELASTIC_TOKEN`, container/list + region gpu_stock + deployment endpoints, CUDA integer-code wording, `after 3 submit failures`, `不要直接重试`, the `inference-service` / `cuda_v_from: 118` / `cuda_v_to: 122` example) and pro anchors (`https://api.autodl.com`, `AUTODL_PRO_TOKEN`, `node <SKILL_DIR>/autodl.mjs pro create --json <config.json>`, `validation_error`, power-on/save-image payloads).
  - Add sync anchors: `rclone`, `rclone obscure`, `rclone copy`, `--dry-run`, install commands (`winget install Rclone.Rclone`, `https://rclone.org/install.sh`, `brew install rclone`), and the dry-run phrases `not executed` / `no live API call`.
  - Remove references to `AUTODL_TOKEN` as a documented fallback.

- [ ] **Step 3: `hygiene.test.mjs`** — no code change expected; confirm it still passes against `skills/autodl` (no stale Python terms).

- [ ] **Step 4: Verify** `npm test`.

## Task 7: Update Eval Dataset + Add Sync Case

**Files:** all `eval/skill-cases/*.json`, `tests-ts/skill-eval-dataset.test.mjs`; create `eval/skill-cases/elastic-sync-dry-run.json`.

- [ ] **Step 1: Schema migration.** In every case set `expected.skill = "autodl"` and add `expected.namespace` ∈ `{ "elastic", "pro", "sync", "none" }`. Update `must_include` command strings from `autodl-elastic.mjs` / `autodl-pro.mjs` to `autodl.mjs elastic` / `autodl.mjs pro`. Remove expectations that the answer must mention `AUTODL_TOKEN` as a fallback (token-precedence cases now assert only the namespaced token).

- [ ] **Step 2: Rewrite `skill-eval-dataset.test.mjs`.**
  - "balanced coverage": assert `>= 12` cases; group by `expected.namespace`; require `elastic >= 5`, `pro >= 5`, `none >= 1`, and `sync >= 1`.
  - Oracle-field test: keep, plus assert `expected.skill === "autodl"` and `expected.namespace` is one of the allowed values.
  - Namespace assertions: elastic cases' `must_include` match private host/`AUTODL_ELASTIC_*`/`autodl.mjs elastic` and `must_not_include` match pro markers (and vice versa); both forbid `call_live_api`.

- [ ] **Step 3: Add `elastic-sync-dry-run.json`** (`expected.namespace: "sync"`, `expected.skill: "autodl"`). Prompt: user asks to incrementally push a local dir to an elastic container over SSH, dry-run only. `must_include`: `rclone`, `rclone copy`, `--dry-run`, deriving SSH from `autodl.mjs elastic containers`, `rclone obscure`, `not executed`, `no live API call`. `must_not_include`: writing the plaintext password on the command line; using a public git repo as intermediary. `must_not_do`: `call_live_api`, `run_sync_without_confirmation`. Provide a rubric summing to `max_score`.

- [ ] **Step 4: Verify** `npm test`.

## Task 8: Rename Project To `autodl-skills` + README

**Files:** `README.md`, `package.json`.

- [ ] **Step 1: `package.json`** add `"name": "autodl-skills"` (and `"private": true` if appropriate).
- [ ] **Step 2: Rewrite `README.md`** for a single unified skill: title `AutoDL Skills`, repo name `autodl-skills`, one skill `skills/autodl/` with `elastic` / `pro` subcommands and the rclone sync feature; updated build/test (`npm install && npm run build && npm test`); single junction install:

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.agents\skills\autodl" -Target "C:\Users\chengyue\Documents\Code\autodl-elastic-deploy\skills\autodl"
```

  Note the local folder is intentionally not renamed; the junction target path therefore still uses the existing folder name.
- [ ] **Step 3: Verify** `npm test`; `rg "autodl-elastic-deploy|autodl-instance-pro|AUTODL_TOKEN" README.md skills src tests-ts eval` returns only intentional historical mentions (ideally none in active docs).

## Task 9: git Remote Rename (manual GitHub step) + origin Update

- [ ] **Step 1:** Ask the user to rename the repository to `autodl-skills` on GitHub (Settings → Rename). This cannot be done from here.
- [ ] **Step 2:** After they confirm, update the local remote: `git remote set-url origin <new-url>` and verify with `git remote -v`. Do not force-push or rename branches.

## Task 10: Final Validation

- [ ] `npm run build && npm test` all green.
- [ ] `node skills/autodl/autodl.mjs --help`, `... elastic --help`, `... pro --help` exit 0 without a token.
- [ ] Forward-test prompts (no live API):
  - "Use the autodl skill to create a queued ReplicaSet from this config, dry-run only." → uses `autodl.mjs elastic queue-submit`, private host/`AUTODL_ELASTIC_TOKEN`, refuses live call.
  - "Check status of `pro-abc123`, dry-run only." → uses `autodl.mjs pro status`, public host/`AUTODL_PRO_TOKEN`.
  - "Incrementally sync `./runs` to my elastic container over SSH." → derives SSH from `elastic containers`, detects rclone (asks before install), uses `rclone copy` with obscured password and default excludes; offers `--dry-run` first; does not use a public repo.

## Acceptance Criteria

- Single skill `skills/autodl/` with one `autodl.mjs` CLI; `elastic` / `pro` subcommands work; `sync` is documented (rclone), not a subcommand.
- `AUTODL_TOKEN` fallback removed; only `AUTODL_ELASTIC_TOKEN` / `AUTODL_PRO_TOKEN` remain; both clouds usable from one `.env`.
- Pro `api-reference.md` documents snapshot SSH fields; sync auto-derives SSH for both clouds.
- `sync-reference.md` covers detection/install matrix (Win/Linux/macOS), obscure-based ephemeral SFTP auth, copy default vs sync(+mandatory dry-run/confirm), push/pull, no default remote path, default excludes, host-key skip, and performance flags.
- All tests pass; eval dataset migrated to `expected.skill: "autodl"` + `namespace`, includes a sync dry-run case; no live AutoDL API calls in tests.
- Project named `autodl-skills` internally and on the git remote; local working-directory folder intentionally unchanged.
