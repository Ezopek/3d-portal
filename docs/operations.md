# Operations Runbook

> **Note:** Several scripts referenced in this runbook (`infra/scripts/deploy.sh`, `infra/scripts/sync-data.sh`, `infra/scripts/backup-sqlite.sh`, `infra/scripts/gen-htpasswd.sh`) and the production stack are introduced in Phase 12 of the implementation plan and may not exist yet. These instructions reflect the intended deployment workflow.

## Deploy to `.190`

```bash
bash infra/scripts/deploy.sh
```

This script builds images locally, ships them to `.190` via SSH, restarts the docker-compose stack, and runs alembic migrations to bring the schema in sync.

## Sync catalog

From WSL, after editing the catalog:

```bash
bash infra/scripts/sync-data.sh
```

This uses rsync over SSH to copy new/modified models from Windows to `.190`, then triggers the API to refresh its in-memory caches. For a safety net, add this to your WSL crontab to run every 15 minutes:

```
*/15 * * * * /mnt/c/Users/ezope/code/sync-data.sh
```

## First-time setup

**1. Generate htpasswd**

```bash
bash infra/scripts/gen-htpasswd.sh portal '<household-password>'
```

This creates the basic-auth file for nginx to use.

**2. Copy nginx config**

```bash
cp infra/nginx-180/3d-portal.conf ~/repos/configs/nginx/
cd ~/repos/configs && bash sync.sh
```

This deploys the edge proxy config to `.180` and reloads nginx.

**3. Generate JWT secret**

```bash
openssl rand -hex 32
```

Store this in `.env.production` as `JWT_SECRET`.

**4. Create GlitchTip project**

See `~/repos/configs/docs/glitchtip-agent-guide.md` for how to create a new project in GlitchTip and get its DSN.

## Backup

SQLite database backup runs nightly via cron on `.190`:

```bash
infra/scripts/backup-sqlite.sh
```

Backups are stored in `/mnt/raid/3d-portal-state/backups/` with 30-day retention (e.g. `portal-2026-04-29.db`).

**Restore:** Stop the api container, copy the backup back into `/mnt/raid/3d-portal-state/portal.db`, and restart the compose stack.

## Failure modes

| Symptom | Check | Fix |
|---|---|---|
| `5xx on /api/catalog/models` | Check OpenSearch `service.name=3d-portal-api` for trace | Likely `index.json` parse failure or volume not mounted; check docker-compose logs and volume mounts |
| Share link returns `401` | Confirm `/share/*` and `/api/share/*` bypass blocks present in `~/repos/configs/nginx/3d-portal.conf` | Re-deploy nginx config via `bash sync.sh` in configs repo |
| Render stuck on "running" | Inspect arq worker logs with `docker compose logs worker` | Restart worker; status TTL is 1h so it self-clears |

## Routine operations

**Log in to admin panel**

Open `/login` and use `ADMIN_EMAIL` and `ADMIN_PASSWORD` from your `.env.production`.

**Revoke a share token**

Via the admin UI (share list, coming in Phase 8), or directly:

```bash
curl -X DELETE https://3d.ezop.ddns.net/api/admin/share/{token} \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Retrigger a render**

```bash
curl -X POST https://3d.ezop.ddns.net/api/admin/render/{model_id} \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Force catalog refresh**

```bash
curl -X POST https://3d.ezop.ddns.net/api/admin/refresh-catalog \
  -H "Authorization: Bearer $JWT_TOKEN"
```

This is also called automatically by `infra/scripts/sync-data.sh` after an rsync completes.
