# AutoDL Skills

`autodl-skills` is a single Node.js-backed Agent Skill for AutoDL. One CLI (`autodl.mjs`) covers both clouds through cloud-prefixed subcommands, plus a documentation-driven rclone sync workflow for moving code, weights, and logs over SSH.

## Skill

| Namespace | Cloud context | Default host | Host override | Token |
|---|---|---|---|---|
| `elastic` | AutoDL private cloud elastic deployment | `https://private.autodl.com` | `AUTODL_ELASTIC_HOST` | `AUTODL_ELASTIC_TOKEN` |
| `pro` | AutoDL public cloud container instance Pro | `https://api.autodl.com` | `AUTODL_PRO_HOST` | `AUTODL_PRO_TOKEN` |
| `sync` | Local ↔ container over SSH (rclone) | — | — | container SSH credentials |

Tokens are strictly namespaced. There is **no** shared `AUTODL_TOKEN` fallback: `elastic` reads `AUTODL_ELASTIC_TOKEN`, `pro` reads `AUTODL_PRO_TOKEN`, both only from `skills/autodl/.env`.

## Build And Test

```bash
npm install
npm run build
npm test
```

`npm run build` runs `tsc` and then copies the compiled output into `skills/autodl/dist/`, which the checked-in entrypoint imports. Run it after cloning or editing TypeScript.

## CLI

```bash
node skills/autodl/autodl.mjs --help
node skills/autodl/autodl.mjs elastic queue-submit deploy.json --interval 30 --timeout 3600
node skills/autodl/autodl.mjs pro status pro-xxxxxxxx
```

Configure `skills/autodl/.env` (copy from `.env.example`):

```env
AUTODL_ELASTIC_TOKEN=your_private_cloud_token_here
AUTODL_ELASTIC_HOST=https://private.autodl.com
AUTODL_PRO_TOKEN=your_public_cloud_token_here
AUTODL_PRO_HOST=https://api.autodl.com
```

- Elastic deployment configs use `dc_list`, `cuda_v_from`, and `cuda_v_to` (integer CUDA codes, e.g. `118` = 11.8).
- Pro API access requires personal or enterprise verification. Power off an instance before releasing it; the CLI does not power off implicitly.

## Sync (rclone over SSH)

Incrementally sync local data to an AutoDL container directly over SSH/SFTP, with no public-repo intermediary. The agent detects/installs `rclone`, derives SSH info from `elastic containers` / `pro snapshot`, and runs `rclone copy` (safe, no delete by default). See `skills/autodl/sync-reference.md`.

## Skill Eval Dataset

Offline skill-correctness cases live in `eval/skill-cases/`, covering elastic, pro, sync, and ambiguous-context prompts. Each case declares the expected skill (`autodl`), a `namespace` (`elastic`/`pro`/`sync`/`none`), required/forbidden content, forbidden actions, and a 10-point rubric.

```bash
node --test tests-ts/skill-eval-dataset.test.mjs
```

## Install Locally

Create one directory junction from this repository into `~/.agents/skills`:

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.agents\skills\autodl" -Target "C:\Users\chengyue\Documents\Code\autodl-elastic-deploy\skills\autodl"
```

The on-disk repository folder is intentionally left as `autodl-elastic-deploy`; only the project name and git remote are `autodl-skills`. Inspect existing junction targets before replacing them.

## Repository Layout

```text
skills/
  autodl/
    SKILL.md
    autodl.mjs
    .env.example
    api-reference.md
    examples.md
    sync-reference.md
    dist/
src/
  core/
  elastic/
  pro/
  main/        # top-level elastic|pro router
scripts/
  copy-dist.mjs
tests-ts/
eval/
  skill-cases/
```

## License

MIT
