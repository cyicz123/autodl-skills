# AutoDL Skills API Reference

Two clouds, one CLI. Auth header for both: `Authorization: <token>`, `Content-Type: application/json`.

- Elastic (private cloud): host `https://private.autodl.com`, token `AUTODL_ELASTIC_TOKEN`.
- Pro (public cloud): host `https://api.autodl.com`, token `AUTODL_PRO_TOKEN`. Pro requires personal or enterprise verification.

SSH connection info for sync is taken from the elastic `container list` (`info.ssh_command` / `info.root_password`) and the pro `snapshot` (`ssh_command` / `proxy_host` / `ssh_port` / `root_password`).

---

# Elastic (Private Cloud)

## 1. List images — `POST /api/v1/dev/image/private/list`

Request: `page_index` (Int, required), `page_size` (Int, required), `offset` (Int, optional).

Response `data.list[]`: `id`, `image_uuid` (used to create deployments), `name`, `status`.

## 2. Create deployment — `POST /api/v1/dev/deployment`

Top-level fields:

| Field | Type | Required | Notes |
|---|---|---|---|
| name | String | yes | Deployment name |
| deployment_type | String | yes | `ReplicaSet` / `Job` / `Container` |
| replica_num | Int | ReplicaSet/Job | Replica count |
| parallelism_num | Int | Job | Concurrent containers |
| reuse_container | Bool | no | Reuse stopped containers |
| container_template | Object | yes | See below |

`container_template`:

| Field | Type | Required | Notes |
|---|---|---|---|
| dc_list | List\<String\> | yes | Schedulable data centers / regions |
| service_6006_port_protocol | String | no | e.g. `http` |
| service_6008_port_protocol | String | no | e.g. `http` |
| cuda_v_from | Int | yes | Min CUDA code (e.g. 118 = 11.8) |
| cuda_v_to | Int | yes | Max CUDA code (e.g. 122 = 12.2) |
| gpu_name_set | List\<String\> | yes | Schedulable GPU models |
| gpu_num | Int | yes | GPU count |
| memory_size_from / memory_size_to | Int | yes | Memory range in **GB** (integers). The API converts to bytes internally — do **not** pass byte values (e.g. `17179869184`), which overflow. The container-list response reports `memory_size` in bytes, so do not reuse that value as input. |
| cpu_num_from / cpu_num_to | Int | yes | CPU core range |
| price_from / price_to | Int | yes | Price range (yuan × 1000) |
| image_uuid | String | yes | Image UUID |
| cmd | String | yes | Start command (see warning) |

**Sizing tips:** `memory_size_from` / `cpu_num_from` are scheduling floors, not requests — a high floor can leave a deployment unschedulable. Start `memory_size_from` low (1–8 GB) and raise it only if needed; in practice `memory_size_from: 16` failed to schedule on a private-cloud RTX 4090 D cluster while `memory_size_from: 8` succeeded.

**`cmd` trap:** combining `&&` with `||` (e.g. `cmd1 && cmd2 || cmd3`) can make a `Job` impossible to stop. Prefer semicolons or an explicit `if`:

```bash
# avoid
ls /data && process || echo "fallback"
# prefer
ls /data ; process ; if [ $? -ne 0 ]; then echo "fallback"; fi
```

Response: `data.deployment_uuid`.

## 3. List deployments — `POST /api/v1/dev/deployment/list`

Request: `page_index`, `page_size`. Response `data.list[]`: `uuid`, `name`, `deployment_type`, `status`, `replica_num`, `parallelism_num`, `reuse_container`, `starting_num`, `running_num`, `finished_num`, `image_uuid`, `template`.

## 4. Container events — `POST /api/v1/dev/deployment/container/event/list`

Request: `deployment_uuid` (required), `deployment_container_uuid` (optional), `page_index`, `page_size`, `offset` (optional). Response `data.list[]`: `deployment_container_uuid`, `status`, `created_at`.

Status flow: `creating` → `created` → `starting` → `oss_merged` → `running` → `shutting_down` → `shutdown`.

## 5. List containers — `POST /api/v1/dev/deployment/container/list`

Inside a container, `AutoDLContainerUUID` holds the container UUID.

Request: `deployment_uuid` (required), plus optional filters (`container_uuid`, `date_from`/`date_to`, `gpu_name`, cpu/memory/price ranges, `released`), `page_index`, `page_size`.

Response `data.list[]`:

| Field | Type | Notes |
|---|---|---|
| uuid | String | Container UUID |
| deployment_uuid | String | Deployment UUID |
| machine_id | String | Host UUID |
| status | String | Container status |
| gpu_name / gpu_num / cpu_num | — | Resources |
| memory_size | Int | Memory in **bytes** (e.g. `17179869184` = 16 GB). Input fields `memory_size_from/to` use GB, not bytes. |
| image_uuid | String | Image UUID |
| price | Float | Base price (yuan × 1000) |
| **info.ssh_command** | String | **SSH login command (used by sync)** |
| **info.root_password** | String | **SSH password (used by sync)** |
| info.service_url | String | Custom service URL |
| started_at / stopped_at | String | Timestamps |

## 6. Stop a container — `PUT /api/v1/dev/deployment/container/stop`

Request: `deployment_container_uuid` (required), `decrease_one_replica_num` (Bool, optional, ReplicaSet only).

## 7. Set replica count — `PUT /api/v1/dev/deployment/replica_num`

ReplicaSet only. Request: `deployment_uuid`, `replica_num`.

## 8. Stop deployment — `PUT /api/v1/dev/deployment/operate`

Request: `deployment_uuid`, `operate` fixed to `"stop"`.

## 9. Delete deployment — `DELETE /api/v1/dev/deployment`

Request: `deployment_uuid`. A running deployment is stopped first, then deleted.

## 10. Scheduling blacklist — `POST /api/v1/dev/deployment/blacklist`

Marks the container's host non-schedulable (auto-cleared after 24h). Request: `deployment_container_uuid` (required), `comment` (optional).

## 11. Global GPU stock — `GET /api/v1/dev/machine/gpu_stock`

No params. Response `data[]` items like `{"RTX 4090": {"idle_gpu_num": 215, "total_gpu_num": 2285}}`.

## 12. Region GPU stock — `POST /api/v1/dev/machine/region/gpu_stock`

Request: `region_sign` (optional), `dc_list` (optional). The CLI normalizes the response to `{ "RTX 4090": { "idle": 215, "total": 2285 } }`.

---

# Pro (Public Cloud)

| Operation | Method | Endpoint |
|---|---|---|
| Create instance | POST | `/api/v1/dev/instance/pro/create` |
| Snapshot/details | GET | `/api/v1/dev/instance/pro/snapshot` |
| Status | GET | `/api/v1/dev/instance/pro/status` |
| List instances | POST | `/api/v1/dev/instance/pro/list` |
| Power on | POST | `/api/v1/dev/instance/pro/power_on` |
| Power off | POST | `/api/v1/dev/instance/pro/power_off` |
| Release | POST | `/api/v1/dev/instance/pro/release` |
| Save image | POST | `/api/v1/dev/instance/pro/image/save` |
| List private images | POST | `/api/v1/dev/instance/pro/image/private/list` |

## Create — `POST /api/v1/dev/instance/pro/create`

Required: `req_gpu_amount` (1–4), `expand_system_disk_by_gb` (0–500), `gpu_spec_uuid`, `image_uuid`, `cuda_v_from` (integer code). Optional: `data_center_list`, `instance_name`, `start_command`. Response `data` is the new `instance_uuid`.

## Snapshot — `GET /api/v1/dev/instance/pro/snapshot`

Request: `{ "instance_uuid": "pro-xxxxxxxx" }`. Response `data` includes resource/usage info plus the SSH fields used by sync:

| Field | Notes |
|---|---|
| **ssh_command** | e.g. `ssh -p 34222 root@connect.xxx.autodl.com` |
| **proxy_host** | SSH host address |
| **ssh_port** | SSH port |
| **root_password** | SSH password |
| jupyter_token / jupyter_domain | JupyterLab access |
| service_6006_domain / service_6008_domain | Mapped service URLs |
| region_sign, payg_price, usage_info, ... | Region / pricing / live usage |

## Status — `GET /api/v1/dev/instance/pro/status`

Request: `{ "instance_uuid": "pro-xxxxxxxx" }`. Response `data` is a status string, e.g. `running`.

## Power on — `POST /api/v1/dev/instance/pro/power_on`

```json
{ "instance_uuid": "pro-xxxxxxxx", "payload": "gpu", "start_command": "bash /root/start.sh" }
```

`payload` is always `gpu`. `start_command` is omitted when not provided.

## Power off / Release

`power_off` and `release` take `{ "instance_uuid": "pro-xxxxxxxx" }`. Power off before releasing; the CLI does not power off implicitly.

## Save image — `POST /api/v1/dev/instance/pro/image/save`

```json
{ "instance_uuid": "pro-xxxxxxxx", "image_name": "my-saved-image" }
```

Response `data.image_uuid`.

## List images — `POST /api/v1/dev/instance/pro/image/private/list`

Request: `page_index`, `page_size`.

---

## Common Response

```json
{ "code": "Success", "msg": "", "data": {} }
```
