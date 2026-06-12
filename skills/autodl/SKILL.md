---
name: autodl
description: Manage AutoDL GPU resources across both clouds and sync local data to containers over SSH. Covers private-cloud elastic deployment (ReplicaSet/Job/Container, scaling, lifecycle, images, GPU stock, events, blacklist), public-cloud container instance Pro (create/snapshot/status/list/power/release/save-image), and rclone-based incremental SSH/SFTP sync of code, weights, and logs. 通过 AutoDL 私有云弹性部署与公有云容器实例 Pro 管理 GPU 容器，并用 rclone 通过 SSH 增量同步代码/权重/日志。当用户提到 AutoDL、弹性部署、公有云实例、GPU 容器调度、私有云部署、增量同步、sync、rclone 时使用。
---

# AutoDL Skills

One CLI (`autodl.mjs`) for two AutoDL clouds, plus a documentation-driven rclone sync workflow.

| Area | Cloud context | Default host | Host override | Token |
|---|---|---|---|---|
| `elastic` | Private cloud elastic deployment | `https://private.autodl.com` | `AUTODL_ELASTIC_HOST` | `AUTODL_ELASTIC_TOKEN` |
| `pro` | Public cloud container instance Pro | `https://api.autodl.com` | `AUTODL_PRO_HOST` | `AUTODL_PRO_TOKEN` |
| `sync` | Local ↔ container over SSH (rclone) | — | — | uses container SSH credentials |

- **Auth**: request header `Authorization: <token>`.
- **Tokens are strictly namespaced**: `elastic` uses `AUTODL_ELASTIC_TOKEN`, `pro` uses `AUTODL_PRO_TOKEN`. There is no shared `AUTODL_TOKEN` fallback. Tokens are read only from this skill's local `.env`.
- **CLI**: `node <SKILL_DIR>/autodl.mjs <elastic|pro> <command> ...`
- **Pro requires** personal or enterprise verification.

If `.env` is missing, copy `.env.example` to `.env` and fill in `AUTODL_ELASTIC_TOKEN` / `AUTODL_PRO_TOKEN`.

## Dry-run Response Requirement

When the user asks to only show commands / dry-run / review / do not execute / show the payload first, do not call the AutoDL API. The answer must say `not executed` and `no live API call`, and include:

- The CLI command, e.g. `node <SKILL_DIR>/autodl.mjs elastic containers --deployment-uuid <uuid>` or `node <SKILL_DIR>/autodl.mjs pro create --json <config.json>`
- Host: elastic default `https://private.autodl.com` (or `AUTODL_ELASTIC_HOST`); pro default `https://api.autodl.com` (or `AUTODL_PRO_HOST`)
- Token namespace: `AUTODL_ELASTIC_TOKEN` or `AUTODL_PRO_TOKEN`
- The API endpoint, e.g. create deployment `POST /api/v1/dev/deployment`, list containers `POST /api/v1/dev/deployment/container/list`, region stock `POST /api/v1/dev/machine/region/gpu_stock`, pro create `POST /api/v1/dev/instance/pro/create`, pro power-on `POST /api/v1/dev/instance/pro/power_on`, pro save-image `POST /api/v1/dev/instance/pro/image/save`
- The relevant request body / config snippet

The same discipline applies to `sync`: print the full `rclone` command, state `not executed` and `no live API call`, and do not run it.

---

## Elastic (Private Cloud)

### Core concepts

| Type | Meaning |
|---|---|
| `ReplicaSet` | Keep a target number of running replicas |
| `Job` | Run containers until a target count completes; needs `replica_num` and `parallelism_num` |
| `Container` | A single container, e.g. one debug/run |

Container lifecycle is driven by `cmd`. Prefer foreground `python app.py`; for background work keep the parent alive with `sleep infinity`. For conda, call the interpreter path directly, e.g. `/root/miniconda3/envs/my-env/bin/python app.py`.

### CLI quick reference

```bash
node <SKILL_DIR>/autodl.mjs elastic queue-submit <config.json> [--interval 30] [--timeout 0]
node <SKILL_DIR>/autodl.mjs elastic images [--page-index 1] [--page-size 100]
node <SKILL_DIR>/autodl.mjs elastic deployments [--page-index 1] [--page-size 10]
node <SKILL_DIR>/autodl.mjs elastic containers --deployment-uuid <uuid> [--page-index 1] [--page-size 10]
node <SKILL_DIR>/autodl.mjs elastic events --deployment-uuid <uuid> [--offset N]
node <SKILL_DIR>/autodl.mjs elastic stop-container <container_uuid> [--decrease-one-replica-num] [--no-cache]
node <SKILL_DIR>/autodl.mjs elastic set-replicas <deployment_uuid> <replica_num>
node <SKILL_DIR>/autodl.mjs elastic stop-deployment <deployment_uuid>
node <SKILL_DIR>/autodl.mjs elastic delete-deployment <deployment_uuid>
node <SKILL_DIR>/autodl.mjs elastic blacklist <container_uuid> [--comment "..."]
node <SKILL_DIR>/autodl.mjs elastic list-blacklist
node <SKILL_DIR>/autodl.mjs elastic gpu-stock --region <region_sign> [--json <filters.json>]
```

`queue-submit` is the recommended deployment entrypoint: it validates the config locally, checks the image, checks GPU stock, polls while GPU is insufficient, then submits when resources are ready.

### CUDA fields

Create requests use the range fields `cuda_v_from` and `cuda_v_to`. `cuda_v_from` / `cuda_v_to` are integer codes, not semantic version strings: `118` means CUDA 11.8, `122` means CUDA 12.2; do not write `"11.8"`, `"12.1"`, or `"12.8"`. The legacy `cuda_v` field is rejected by local validation with a migration message.

---

## Pro (Public Cloud)

### CLI quick reference

```bash
node <SKILL_DIR>/autodl.mjs pro create --json <config.json>
node <SKILL_DIR>/autodl.mjs pro snapshot <instance_uuid>
node <SKILL_DIR>/autodl.mjs pro status <instance_uuid>
node <SKILL_DIR>/autodl.mjs pro list [--page-index 1] [--page-size 10]
node <SKILL_DIR>/autodl.mjs pro power-on <instance_uuid> [--start-command "..."]
node <SKILL_DIR>/autodl.mjs pro power-off <instance_uuid>
node <SKILL_DIR>/autodl.mjs pro release <instance_uuid>
node <SKILL_DIR>/autodl.mjs pro save-image <instance_uuid> --name <image_name>
node <SKILL_DIR>/autodl.mjs pro list-images [--page-index 1] [--page-size 10]
```

### Payloads

Power-on calls `POST /api/v1/dev/instance/pro/power_on` with:

```json
{
  "instance_uuid": "pro-xxxxxxxx",
  "payload": "gpu",
  "start_command": "bash /root/start.sh"
}
```

`payload` is always `"gpu"`. Omit `start_command` when the user did not provide one.

Save-image calls `POST /api/v1/dev/instance/pro/image/save` with:

```json
{
  "instance_uuid": "pro-xxxxxxxx",
  "image_name": "my-saved-image"
}
```

Release is destructive and the CLI does not power off implicitly: check status, power off, then release.

### Create config

Required: `req_gpu_amount` (1–4), `expand_system_disk_by_gb` (0–500), `gpu_spec_uuid`, `image_uuid`, `cuda_v_from` (integer code).

---

## Sync (Local ↔ Container over SSH)

Sync uses the external `rclone` binary to incrementally transfer code, weights, and logs directly over the container's SSH/SFTP, with no public-repo intermediary. It is documentation-driven (no CLI subcommand): the agent detects/installs `rclone`, derives SSH connection info from this skill, and runs `rclone` directly.

- Detect: `rclone version`. If missing, always show the install command and ask for confirmation before installing (`winget install Rclone.Rclone` on Windows, `https://rclone.org/install.sh` on Linux, `brew install rclone` on macOS).
- Get SSH: elastic from `autodl.mjs elastic containers` (`info.ssh_command` / `info.root_password`); pro from `autodl.mjs pro snapshot` (`ssh_command` / `proxy_host` / `ssh_port` / `root_password`).
- Default operation is `rclone copy` (never deletes remote files). `rclone sync` (mirror) is opt-in and requires a `--dry-run` preview plus explicit confirmation.
- The remote path has no default; the calling agent supplies it from its own AGENTS.md/context.

Full detail (install matrix, obscured-password ephemeral SFTP auth, push/pull, excludes, performance flags): see [sync-reference.md](sync-reference.md).

---

## Output

Success:

```json
{
  "status": "success",
  "deployment_uuid": "833f1cd5a764fa3",
  "waited_seconds": 120
}
```

Errors are structured JSON:

```json
{
  "status": "error",
  "error_type": "gpu_type_not_found",
  "message": "请求的 GPU 型号均不存在: [\"RTX 5090\"]",
  "details": { "requested": ["RTX 5090"], "available_gpus": ["RTX 4090", "RTX 3090"] }
}
```

## Error Handling

On error, the agent must guide the user to fix parameters based on `error_type` instead of blindly retrying.

| `error_type` | Meaning | Agent action |
|---|---|---|
| `validation_error` | Bad params (range inversion, missing field, legacy `cuda_v`, bad Pro create) | Show `details.errors`, ask how to fix |
| `image_not_found` | Image UUID does not exist | Show `details.available_images`, let user pick |
| `gpu_type_not_found` | Requested GPU types all missing | Show `details.available_gpus`, let user re-pick |
| `submission_error` | GPU free but submit failed repeatedly | This is the result after 3 submit failures; show response and suggestion, adjust price/CPU/memory/CUDA; 不要直接重试 |
| `timeout` | Waiting for GPU timed out | Show `details.last_stock`, suggest relaxing GPU/region or retry later |
| `token_missing` | No token in `.env` or env | Write `AUTODL_ELASTIC_TOKEN` or `AUTODL_PRO_TOKEN` |
| `config_error` | Config read or CLI argument error | Check path, JSON format, and arguments |
| `api_error` | HTTP/JSON/AutoDL API error | Show message/details, confirm before retry |

## Best Practices

1. Images: bake static environments into the image; keep frequently-changing code/models on network storage.
2. Start command: do not run only in the background, or the container closes when the parent exits.
3. Paths: `cd` first, e.g. `cd /root && python app.py`.
4. Debug: set `cmd` to `sleep infinity`, then SSH in to investigate.
5. `cmd1 && cmd2 || fallback` can make a Job impossible to stop; prefer semicolons or explicit `if`.
6. `memory_size_from`/`memory_size_to` are in GB (the API converts to bytes — never pass byte values). `*_from` fields are scheduling floors: start `memory_size_from` low (1–8) and raise only if needed, since a high floor can leave a deployment unschedulable.

## References

- Full API parameters and responses: [api-reference.md](api-reference.md)
- CLI and sync examples: [examples.md](examples.md)
- rclone SSH sync guide: [sync-reference.md](sync-reference.md)
