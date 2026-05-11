# `infra/nginx-180/` — historical snapshot only

The actual edge nginx config for `https://3d.ezop.ddns.net` lives in a separate operator-managed repository, NOT in this directory:

- **Source of truth:** `~/repos/configs/nginx/3d.ezop.ddns.net.conf`
- **Deployed by:** `~/repos/configs/sync.sh`

This directory contains **only an archived snapshot** of an older config (under `.archived/`). The snapshot predates the move from basic-auth + htpasswd to LAN+VPN IP-allowlist; it is kept for grep archaeology, NOT for deployment.

## Differences between archived snapshot and live config

| Aspect | `.archived/3d-portal.conf.pre-IP-allowlist` | live `~/repos/configs/nginx/3d.ezop.ddns.net.conf` |
|---|---|---|
| Auth model | basic-auth + htpasswd file | IP allowlist (`192.168.2.0/24` + `10.8.0.0/24`) |
| HSTS | none | `Strict-Transport-Security max-age=31536000` |
| SSL ciphers | nginx default | explicit `TLSv1.2+TLSv1.3` cipher list |
| Per-location bypasses | 3 (`/share/`, `/api/share/`, `/agent-runbook`) | 0 (catch-all suffices) |
| Long timeouts | none | `proxy_read_timeout 300s; proxy_send_timeout 300s` |
| 80→443 redirect | none | yes |

If you find yourself editing the archived snapshot expecting it to deploy: stop. Edit `~/repos/configs/nginx/3d.ezop.ddns.net.conf` and run that repo's `sync.sh`.
