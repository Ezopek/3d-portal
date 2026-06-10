# 3D Portal

Self-hosted 3D-printing portal for Michał's homelab. Browses the model collection synced from a Windows/Nextcloud catalog, gates household access through edge nginx, and exposes admin actions (share-links, render trigger, audit log) behind a JWT.

## Status

v1 in active implementation. See:

- Spec — [`docs/design/2026-04-29-portal-design.md`](docs/design/2026-04-29-portal-design.md)
- Plan — [`docs/plans/2026-04-29-portal-v1-implementation.md`](docs/plans/2026-04-29-portal-v1-implementation.md)
- Architecture — [`docs/architecture.md`](docs/architecture.md)
- Operations — [`docs/operations.md`](docs/operations.md)

## Features

- **Slicer Estimates**: Per-STL print time, mass, and cost estimates via headless OrcaSlicer.
- **Filament Policy**: Admin-managed mapping from Spoolman materials to Orca profiles with exact-override vs material-default honesty labels.
- **Spoolman**: Read-only inventory mirror (stock, filaments, vendors) with low-stock alerts.

## Quickstart (dev)

```bash
cp infra/env.example .env.dev.local
docker compose -f infra/docker-compose.dev.yml --env-file .env.dev.local up
```

- Web: <http://localhost:5173>
- API: <http://localhost:8000>
- API docs: <http://localhost:8000/docs>

## Production

See `docs/operations.md` — deployed at `https://3d.ezop.ddns.net` (homelab DDNS).

## License

Private. Not licensed for redistribution.
