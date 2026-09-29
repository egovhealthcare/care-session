# Deployment readiness checklist

Use this alongside the [operator worksheet](operator-worksheet.md). Record command output or screenshots as evidence rather than marking an item complete from memory. A workshop pass is not approval for a real deployment.

## Local workshop readiness

- [ ] Docker daemon is running.
- [ ] Docker Compose v2 is available.
- [ ] Required ports are free.
- [ ] Both CARE submodules are initialised at the intended commit (`git submodule status`).
- [ ] `.env` was copied from `.env.example`.
- [ ] Frontend local API configuration was copied into `care_fe`.
- [ ] `docker compose config` succeeds.
- [ ] The database is healthy.
- [ ] The cache and task broker are healthy.
- [ ] S3-compatible storage is healthy.
- [ ] Beat completed migrations and synchronization and is healthy.
- [ ] Backend health endpoint succeeds.
- [ ] Frontend returns an HTTP response.
- [ ] Worker is running.
- [ ] Beat is running and healthy.
- [ ] Django system check succeeds.
- [ ] Synthetic fixtures load successfully.
- [ ] A synthetic clinical workflow succeeds.
- [ ] A test file can be uploaded and retrieved.
- [ ] A triggered background task completes; otherwise mark unknown.
- [ ] Stop and restart preserve a specific synthetic record and uploaded test file.
- [ ] Destructive reset behavior is understood.
- [ ] An operator can diagnose a prepared failure and name the first failing dependency.

## Production discussion gates

These are discussion prompts only; the local stack does not satisfy them.

- [ ] Capacity assumptions and headroom are documented.
- [ ] DNS, TLS, routing, and ownership are defined.
- [ ] Database availability, backups, and restore tests meet objectives.
- [ ] Object-storage recovery and lifecycle policies are defined.
- [ ] Secrets and rotation procedures are managed.
- [ ] Workload identities follow least privilege.
- [ ] Release artifacts are pinned and approved.
- [ ] Logs, metrics, alerts, and runbooks are operational.
- [ ] Rollback and recovery procedures are tested.
- [ ] Operators and escalation owners are assigned.
- [ ] CARE/Celery compatibility with the selected cache/task broker is tested.
- [ ] CARE integration with the selected file-storage service is tested.
- [ ] The owner and last successful isolated restore test for records and files are recorded.
- [ ] The migration owner and release verification/rollback trigger are recorded.

For each real-deployment gate, record **owner, evidence link, result, and next test** in the operator worksheet. Unknown critical evidence is a no-go, not an assumed pass.
