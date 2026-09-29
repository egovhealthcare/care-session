# CARE instance: operator worksheet

Use this with [Session 3 slides](https://egovhealthcare.github.io/care-session/) and the [local setup instructions](../README.md). Record evidence or **unknown**; a successful container start is not a completed exercise. This lab uses synthetic records and local demo credentials only. Do not copy its configuration into a real service.

## 1. What are we hosting?

| Responsibility | Local workshop service | Who runs it in our proposed environment? | Evidence or open question |
|---|---|---|---|
| Browser frontend (build-time API URL) | `frontend` | | |
| Backend API | `backend` | | |
| Background tasks | `worker` | | |
| Initialization and scheduled tasks | `beat` | | |
| Structured records | `db` | | |
| S3-compatible file storage | `silo` | | |
| Cache and task transport | `redis` | | |

The frontend and the three backend process roles use **two CARE images**. The last three rows are replaceable dependency implementations, not CARE images. Describe the hosting *capability* before selecting a product or provider.

## 2. Bring up and verify a local instance

| Check | Command or action | Result / evidence | Status (pass / fail / unknown) |
|---|---|---|---|
| Source and configuration | Clone the two upstream repositories; copy local examples without overwriting an existing `.env` | | |
| Compose model | `docker compose config --quiet` and `docker compose config --services` | | |
| Start | `docker compose up -d --build --wait` | | |
| Dependencies and Beat | `docker compose ps -a` | | |
| Backend | `curl -f http://localhost:9000/ping/` | | |
| Frontend | `curl -I http://localhost:4000/` | | |
| Django checks | `docker compose exec backend python manage.py check` | | |
| Synthetic record | Load fixtures using the [local-only preparation](../README.md#7-load-synthetic-workshop-data), sign in, save and reopen a synthetic record | | |
| Synthetic file | Upload and retrieve a test file | | |
| Background job | Trigger a known test task, then find its outcome in worker logs | | |

Only run `load_fixtures` in this synthetic local lab. Never use it on a real CARE instance. If no task was triggered, record **unknown**, not pass.

## 3. Manage it, not just start it

| Operator exercise | Action | What must be observed? | Result / owner |
|---|---|---|---|
| Diagnose a failed role | `docker compose ps -a`; inspect the first failing dependency's logs before downstream logs | Symptom, cause, corrective action | |
| Preserve state on shutdown | `docker compose down`, then `docker compose up -d --wait` | Synthetic record and file still accessible | |
| Understand deletion | Explain what `docker compose down -v` removes **without running it** | Operator can name lost volumes/data | |
| Make a release plan | Identify the frontend and backend image versions, plug set, config, migration owner, and rollback target | Written release and rollback steps | |
| Restore plan | Specify how to restore records and files to a consistent point, then verify a real test restore in an isolated environment | Measured RPO/RTO and application check | |

**Do not run `docker compose down -v` during the exercise.** Restores are a planning item here until an isolated test environment and real backup procedure exist.

## 4. Design an instance you can own

Choose a workstation, VM, server, container host, or cluster as appropriate. Containers are one delivery method, not a CARE requirement. Managed database, file-storage, and broker services are options only after application compatibility has been verified.

| Decision | Team answer and named owner |
|---|---|
| Users, traffic, facilities, file volume, retention, integrations, plugs | |
| Host/platform and who maintains it | |
| Browser-reachable HTTPS API URL; DNS and TLS owner | |
| Frontend build variables and backend runtime configuration | |
| Database, S3-compatible file storage, cache and broker endpoints | |
| Isolation between development, staging, and live data | |
| Secrets and least-privilege identities | |
| Monitoring: availability, errors, task age, storage and capacity; who receives alerts | |
| Backup frequency, restore owner, recovery time and recovery point targets | |
| Release approval, migration window, rollback condition and on-call handoff | |

**Compatibility gates:** verify the chosen object-storage integration with CARE, and verify the chosen broker against CARE/Celery; do not infer compatibility from a service name. Sizing numbers require workload evidence and a load test.

## 5. Decision

- **Ready for the local learning exercise:** all basic health checks plus a synthetic record and file action pass. Mark untested capabilities unknown.
- **Ready for a real deployment:** separate security, capacity, functional, backup/restore, rollback, and operational evidence exists, with an owner for each item in [the readiness checklist](readiness-checklist.md).
- **Not ready:** a critical item is failed or unknown. State who will resolve it and what test will close it.

| Decision | Strongest evidence | Biggest unknown / blocker | Owner | Next verification |
|---|---|---|---|---|
| | | | | |
