# AutoDL Skills CLI Examples

All examples use this skill's `autodl.mjs`. Set credentials in this skill's `.env`:

```bash
AUTODL_ELASTIC_TOKEN=your_private_cloud_token_here
AUTODL_ELASTIC_HOST=https://private.autodl.com
AUTODL_PRO_TOKEN=your_public_cloud_token_here
AUTODL_PRO_HOST=https://api.autodl.com
```

Tokens are strictly namespaced; there is no `AUTODL_TOKEN` fallback.

---

# Elastic (Private Cloud)

## Create a ReplicaSet and queue for GPU

Dry-run response pattern: `not executed`; `no live API call`. Host `https://private.autodl.com`; token namespace `AUTODL_ELASTIC_TOKEN`; endpoint `POST /api/v1/dev/deployment`; command:

```bash
node <SKILL_DIR>/autodl.mjs elastic queue-submit deploy-replicaset.json --interval 30 --timeout 3600
```

`deploy-replicaset.json`:

```json
{
  "name": "inference-service",
  "deployment_type": "ReplicaSet",
  "replica_num": 4,
  "reuse_container": true,
  "container_template": {
    "dc_list": ["beijing"],
    "service_6006_port_protocol": "http",
    "service_6008_port_protocol": "http",
    "gpu_name_set": ["RTX 4090"],
    "gpu_num": 1,
    "cuda_v_from": 118,
    "cuda_v_to": 122,
    "cpu_num_from": 4,
    "cpu_num_to": 32,
    "memory_size_from": 16,
    "memory_size_to": 128,
    "cmd": "cd /root/app && python server.py",
    "price_from": 100,
    "price_to": 9000,
    "image_uuid": "image-xxxxxxxxxx"
  }
}
```

> `memory_size_from` / `memory_size_to` are in **GB** (the API converts to bytes; never pass byte values). `memory_size_from` is a scheduling floor — start it low (1–8) and raise only if needed; e.g. `16` failed to schedule on a private-cloud RTX 4090 D cluster while `8` succeeded.

## Create a Job for batch training

`deploy-job.json`:

```json
{
  "name": "batch-training",
  "deployment_type": "Job",
  "replica_num": 10,
  "parallelism_num": 3,
  "reuse_container": true,
  "container_template": {
    "dc_list": ["beijing", "shanghai"],
    "gpu_name_set": ["RTX 4090", "RTX 3090"],
    "gpu_num": 1,
    "cuda_v_from": 118,
    "cuda_v_to": 122,
    "cpu_num_from": 4,
    "cpu_num_to": 64,
    "memory_size_from": 16,
    "memory_size_to": 256,
    "cmd": "cd /root/train && python train.py --config /root/nas/config.yaml",
    "price_from": 100,
    "price_to": 9000,
    "image_uuid": "image-xxxxxxxxxx"
  }
}
```

```bash
node <SKILL_DIR>/autodl.mjs elastic queue-submit deploy-job.json --timeout 0
```

## Create a single debug container

`debug.json` uses `"cmd": "sleep infinity"` so you can SSH in.

```bash
node <SKILL_DIR>/autodl.mjs elastic queue-submit debug.json
```

## Inspect resources and objects

Dry-run pattern for read-only commands: `not executed`; `no live API call`. Always include host `https://private.autodl.com`, token namespace `AUTODL_ELASTIC_TOKEN`, the CLI command, and the endpoint:

- Containers: `POST /api/v1/dev/deployment/container/list`
- Region GPU stock: `POST /api/v1/dev/machine/region/gpu_stock`

```bash
node <SKILL_DIR>/autodl.mjs elastic images --page-size 100
node <SKILL_DIR>/autodl.mjs elastic gpu-stock --region beijing
node <SKILL_DIR>/autodl.mjs elastic deployments --page-index 1 --page-size 10
node <SKILL_DIR>/autodl.mjs elastic containers --deployment-uuid deploy-xxxxxxxx --page-size 100
node <SKILL_DIR>/autodl.mjs elastic events --deployment-uuid deploy-xxxxxxxx --offset 0
```

## Lifecycle management

```bash
node <SKILL_DIR>/autodl.mjs elastic set-replicas deploy-xxxxxxxx 8
node <SKILL_DIR>/autodl.mjs elastic stop-container container-xxxxxxxx --decrease-one-replica-num
node <SKILL_DIR>/autodl.mjs elastic blacklist container-xxxxxxxx --comment "container keeps crashing"
node <SKILL_DIR>/autodl.mjs elastic list-blacklist
node <SKILL_DIR>/autodl.mjs elastic stop-deployment deploy-xxxxxxxx
node <SKILL_DIR>/autodl.mjs elastic delete-deployment deploy-xxxxxxxx
```

---

# Pro (Public Cloud)

## Create

Dry-run response pattern: `not executed`; `no live API call`. Host `https://api.autodl.com`; token namespace `AUTODL_PRO_TOKEN`; endpoint `POST /api/v1/dev/instance/pro/create`; command:

```bash
node <SKILL_DIR>/autodl.mjs pro create --json <config.json>
```

`pro-create.json`:

```json
{
  "req_gpu_amount": 1,
  "expand_system_disk_by_gb": 50,
  "gpu_spec_uuid": "pro6000-p",
  "image_uuid": "image-xxxxxxxxxx",
  "cuda_v_from": 118
}
```

## Inspect

```bash
node <SKILL_DIR>/autodl.mjs pro list --page-index 1 --page-size 10
node <SKILL_DIR>/autodl.mjs pro status pro-xxxxxxxx
node <SKILL_DIR>/autodl.mjs pro snapshot pro-xxxxxxxx
```

## Power

Power-on endpoint and body for dry-run/review answers:

```text
POST /api/v1/dev/instance/pro/power_on
```

```json
{
  "instance_uuid": "pro-xxxxxxxx",
  "payload": "gpu",
  "start_command": "bash /root/start.sh"
}
```

```bash
node <SKILL_DIR>/autodl.mjs pro power-on pro-xxxxxxxx --start-command "bash /root/start.sh"
node <SKILL_DIR>/autodl.mjs pro power-on pro-xxxxxxxx
node <SKILL_DIR>/autodl.mjs pro power-off pro-xxxxxxxx
```

## Save image and list images

Save-image dry-run pattern: `not executed`; `no live API call`. Host `https://api.autodl.com`; token namespace `AUTODL_PRO_TOKEN`; endpoint `POST /api/v1/dev/instance/pro/image/save`; payload:

```json
{
  "instance_uuid": "pro-xxxxxxxx",
  "image_name": "my-saved-image"
}
```

```bash
node <SKILL_DIR>/autodl.mjs pro save-image pro-xxxxxxxx --name my-saved-image
node <SKILL_DIR>/autodl.mjs pro list-images --page-index 1 --page-size 10
```

## Release

Power off first, then release.

```bash
node <SKILL_DIR>/autodl.mjs pro status pro-xxxxxxxx
node <SKILL_DIR>/autodl.mjs pro power-off pro-xxxxxxxx
node <SKILL_DIR>/autodl.mjs pro release pro-xxxxxxxx
```

---

# Sync (rclone over SSH)

Full guide: [sync-reference.md](sync-reference.md). Quick examples below assume `rclone` is installed and the container SSH info was obtained from `autodl.mjs elastic containers` or `autodl.mjs pro snapshot`.

## Push local code/weights to a container (default, safe)

Dry-run first: append `--dry-run` and report `not executed` / `no live API call`.

```bash
# obscure the AutoDL root password once (value goes into an env var, never on the command line)
$env:RCLONE_SFTP_PASS = (rclone obscure "<root_password>")   # PowerShell
export RCLONE_SFTP_PASS="$(rclone obscure '<root_password>')" # bash

rclone copy ./runs ":sftp,host=<host>,port=<port>,user=root:<REMOTE_PATH>" `
  --exclude ".git/**" --exclude "__pycache__/**" --exclude "*.pyc" `
  --exclude ".ipynb_checkpoints/**" --exclude "node_modules/**" --exclude ".DS_Store" `
  --progress --transfers 4 --checkers 8 --multi-thread-streams 4 --stats 10s
```

## Pull logs/artifacts back from a container

```bash
rclone copy ":sftp,host=<host>,port=<port>,user=root:<REMOTE_PATH>/logs" ./logs --progress --stats 10s
```

## Mirror (dangerous, opt-in)

`rclone sync` deletes remote files not present locally. Always preview with `--dry-run` and confirm before the real run:

```bash
rclone sync ./site ":sftp,host=<host>,port=<port>,user=root:<REMOTE_PATH>" --dry-run   # preview deletions first
```
