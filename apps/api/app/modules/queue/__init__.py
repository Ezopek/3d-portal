"""Read-only admin ARQ queue console (Story 34.1 / ADMIN-JOBS-1).

A single read-only, deploy-clean MVP slice: ``GET /api/admin/queues`` returns a live
snapshot of the three arq worker pools (API ``arq:api``, Render ``arq:queue``, Slicer
``arq:slicer``) built ONLY from bounded Redis reads. No write/mutation surface, no DB
ledger, no worker instrumentation — see the story spec for the deferred gates
(G-LEDGER / G-LIVENESS / G-ACTIONS).
"""
