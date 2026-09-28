# CARE session — infrastructure requirements and sizing guide

This document is for planning and scoping a **real deployment** after the local CARE session.
The workshop Compose stack is for training; production needs additional controls (HA, security, backups, observability, runbooks).

## 1) Tech stack overview and deployment modes

## Core runtime stack

- **Frontend (FE):** React static app served by Nginx
- **Backend (BE):** Django API
- **Worker:** Celery asynchronous task execution
- **Scheduler:** Celery Beat (single active scheduler)
- **Database:** PostgreSQL
- **Cache/task broker:** Redis (validate exact broker mode/version compatibility before production)
- **Object storage:** S3-compatible storage (local) or cloud object storage in managed environments

## Optional/adjacent components

- **Metabase (BI):** dashboards and analytics over a reporting database or read replica
- **AI engine:** optional service for summarization/coding/assistive workflows; typically a separate API service with queue-backed jobs
- **Gateway/Ingress + TLS:** public entry, certificates, routing
- **Observability stack:** logs, metrics, traces, alerting
- **Identity/secrets:** IAM/workload identity, secret manager, rotation controls

## Deployment modes

### A. Cloud (recommended default)

- Kubernetes or VM-based deployment in a cloud VPC
- Managed PostgreSQL and managed object storage preferred
- Private networking between app and stateful services
- Public access only through load balancer/gateway + TLS

**Best for:** multi-facility deployments, scale-out, easier DR options

### B. On-prem (hospital/DC)

- Kubernetes or VM stack in local datacenter
- Local PostgreSQL, Redis, and S3-compatible storage (or appliance equivalents)
- Requires explicit HA design for power/network/hardware failure domains

**Best for:** strict data locality/regulatory constraints, intermittent internet tolerance

### C. Hybrid connectivity

- App/control plane in cloud, selected integrations or data stores on-prem (or inverse)
- Site-to-site VPN / dedicated link
- Requires clear latency budgets and outage-mode behavior

**Best for:** phased migration and mixed governance constraints

## Connectivity requirements (all modes)

- Stable DNS and NTP
- TLS termination for user-facing endpoints
- Secure private connectivity for DB/Redis/object storage
- Controlled egress for updates, notifications, and third-party APIs
- Firewall rules by least privilege (source, destination, port, protocol)
- Defined offline/degraded behavior for facility outages

---

## 2) Components and minimum server hardware (starting point)

These are **minimum starting points** for production pilots, not final HA targets.

| Component | Minimum CPU | Minimum RAM | Minimum Storage | Notes |
|---|---:|---:|---:|---|
| FE (Nginx) | 1 vCPU | 1 GB | 10 GB | Stateless; scale horizontally if concurrent users rise |
| BE (Django API) | 2 vCPU | 4 GB | 20 GB | Keep stateless; externalize sessions/files |
| Worker (Celery) | 2 vCPU | 4 GB | 20 GB | CPU/RAM depends on async workload types |
| Beat (single replica) | 1 vCPU | 1 GB | 10 GB | One active scheduler only |
| PostgreSQL | 4 vCPU | 16 GB | 200 GB SSD | Use WAL archiving + backups + monitoring |
| Redis | 2 vCPU | 4 GB | 20 GB | Size by queue depth + cache hit target |
| Object storage | N/A service | N/A service | Start 500 GB+ | Prefer managed cloud object storage when possible |
| Metabase | 2 vCPU | 4 GB | 50 GB | Prefer separate app DB for Metabase metadata |
| AI engine (optional) | 4 vCPU | 8 GB | 50 GB | If self-hosted inference, size separately (often GPU) |
| Observability stack | 2 vCPU | 4 GB | 100 GB | If self-hosted logs/metrics; managed is simpler |

### HA baseline (recommended)

- FE/BE/Worker: at least 2 replicas per critical component
- Beat: 1 active + restart policy (not active-active scheduling)
- PostgreSQL: managed HA or primary/standby with tested failover
- Redis: managed HA or sentinel/cluster as required
- Multi-zone placement where available

---

## 3) Sizing and scaling by project requirement

Use workload drivers, not only facility count.

## Primary sizing inputs

- Number of facilities
- Peak concurrent active users (not total registered users)
- Daily patient registrations/encounters
- Async job profile (reports, notifications, exports, ETL)
- File upload volume (documents/images)
- Retention policy (years), audit requirements, backup RPO/RTO

## Practical capacity model

Define:

- **F** = facilities
- **U_peak** = peak concurrent users across all facilities
- **P_day** = patient/encounter records per day
- **J_day** = asynchronous jobs per day
- **S_file_day** = daily uploaded file volume (GB/day)

Then scale:

- FE/BE replicas by `U_peak` and API latency SLO
- Worker replicas by `J_day` and queue latency SLO
- PostgreSQL CPU/RAM by write/read mix and peak transaction rate
- Storage by `S_file_day × retention_window` (+ backup and versioning overhead)

## Starter sizing bands

| Band | Typical scope | FE/BE/Worker (starting replicas) | DB suggestion | Redis suggestion |
|---|---|---|---|---|
| Pilot | 1–5 facilities, <= 100 peak users | FE 1-2, BE 2, Worker 1-2 | 4 vCPU / 16 GB | 2 vCPU / 4 GB |
| District | 5–25 facilities, 100-500 peak users | FE 2, BE 3-4, Worker 2-4 | 8 vCPU / 32 GB | 2-4 vCPU / 8 GB |
| Statewide | 25+ facilities, 500+ peak users | FE 2-4, BE 4-8, Worker 4-12 | 16+ vCPU / 64+ GB | 4+ vCPU / 16+ GB |

> Validate with load testing before go-live and after each major release.

## Scaling triggers (example)

- API p95 latency > SLO for 15 min at normal error rates → scale BE
- Queue lag > target threshold for 10 min → scale workers
- DB CPU sustained > 70% or frequent slow queries → tune/index/read-replica/scale up
- Redis memory > 75% or eviction events rising → scale memory/capacity

---

## 4) Scoping and provisioning checklist

## Discovery

- [ ] Facilities, expected concurrency, and rollout phases documented
- [ ] Integrations identified (labs, HMIS, notification gateways, SSO, etc.)
- [ ] Regulatory/data-residency constraints confirmed
- [ ] RPO/RTO targets defined and approved

## Platform

- [ ] Deployment mode selected (cloud/on-prem/hybrid) with owner
- [ ] Environment plan: dev, staging, prod (and optional DR)
- [ ] Network plan: CIDRs, ingress, egress, DNS, TLS, firewall rules
- [ ] Capacity plan and autoscaling thresholds documented

## Data and state

- [ ] PostgreSQL HA/backup/restore design approved
- [ ] Object storage lifecycle/versioning/retention defined
- [ ] Redis persistence/HA policy defined
- [ ] Data archival and purge policy approved

## Security and access

- [ ] IAM/RBAC model and least-privilege roles implemented
- [ ] Secrets management and rotation workflow in place
- [ ] Audit logging and access review process defined
- [ ] Vulnerability and patching cadence defined

## Reliability and operations

- [ ] SLOs and alert rules defined (availability, latency, queue lag, DB health)
- [ ] Centralized logs/metrics/traces enabled
- [ ] Runbooks for incident, rollback, and dependency outage published
- [ ] Backup restore drill executed and evidenced
- [ ] Load test baseline report attached

## Release and change

- [ ] CI/CD with immutable artifacts and version pinning
- [ ] Schema migration and rollback strategy verified
- [ ] Change window and on-call ownership documented

---

## 5) Cost estimation framework

Use this as a planning model; replace unit prices with current regional cloud/on-prem rates.

## Monthly cost buckets

1. **Compute:** FE/BE/Worker/Beat + optional Metabase/AI/observability
2. **Database:** primary + HA/replica + backup storage + IOPS/throughput
3. **Cache:** Redis node(s) + HA premium
4. **Object storage:** active + infrequent/archive + request charges + egress
5. **Network:** load balancer, public IP, egress bandwidth, VPN/interconnect
6. **Security/ops:** secret manager, logging/metrics retention, monitoring tools
7. **DR overhead:** standby infra, replicated storage, test exercises

## Simple estimation template

`Total monthly = Compute + DB + Redis + Storage + Network + Security/Observability + DR + Support`

## Example planning envelopes (illustrative only)

| Profile | Typical scope | Estimated monthly range* |
|---|---|---:|
| Pilot | 1-5 facilities | USD 500-2,000 |
| District | 5-25 facilities | USD 2,000-8,000 |
| Statewide | 25+ facilities | USD 8,000-30,000+ |

\*Large variance comes from HA level, storage growth, egress, observability retention, managed-vs-self-hosted choices, and support model.

## Costing workflow (recommended)

1. Fix workload assumptions (`U_peak`, `P_day`, `J_day`, `S_file_day`)
2. Pick target SLO and RPO/RTO
3. Select deployment mode and HA tier
4. Build BoM per environment (dev/stage/prod/DR)
5. Add 20-35% headroom for growth and incident capacity
6. Re-estimate after load testing and first month of production telemetry

---

## 6) CARE session deliverables for infra planning

For each target project, produce:

- Infrastructure BoM (component-wise CPU/RAM/storage/replicas)
- Network and security design (ingress/egress, DNS, TLS, IAM)
- Backup/restore and DR plan with tested evidence
- Scaling policy with measurable triggers
- Monthly cost sheet with assumptions and confidence range
- Owner matrix (platform, DB, app, security, support)

This becomes the handoff baseline from workshop learning to production implementation.