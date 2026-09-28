# CARE local deployment session

A training repository for learning to host and manage a CARE instance. Build a safe local lab with Docker Compose, verify that it works, practice routine operations, and prepare an owner-assigned hosting plan. This stack is not a production deployment template.

See [Architecture explanation](docs/architecture.md) for the Markdown and Mermaid view of the local system.

## Teaching progression

Start with the local diagram until participants can explain the two CARE images, runtime roles, and dependency responsibilities. Work through the [operator worksheet](docs/operator-worksheet.md): build, verify, diagnose, preserve data, choose a host, and assign owners.

Kubernetes is one possible way to host the same application model:

- [CARE on a simple Kubernetes cluster](docs/kubernetes-local-architecture.md)

GCP is an optional platform example in [From local Compose to GCP](docs/local-to-gcp.md), not a prerequisite to running your own instance.

The [managed-services GCP diagram](docs/gcp-managed-architecture.md) illustrates potential services. Verify CARE storage integration and Celery broker compatibility before selecting replacements.

## What runs

| Service | Purpose | Source or image |
|---|---|---|
| `frontend` | CARE browser application | Built from `ohcnetwork/care_fe` |
| `backend` | Django API and business logic | Built from `ohcnetwork/care` |
| `worker` | Celery asynchronous task processing | Same image as backend |
| `beat` | Startup initialization and scheduled-task dispatch | Same image as backend |
| `db` | PostgreSQL application database | `postgres:17-alpine` |
| `redis` | Cache and Celery message broker | `redis:8-alpine` |
| `silo` | Local S3-compatible object storage | `pgsty/silo` |
| Plugs | Backend extensions | Installed into the backend image at build time |

## Two CARE application images

The workshop builds two CARE images from the official repositories:

1. **Frontend image:** the `care_fe` Node build reads the `REACT_*` build environment, including `REACT_CARE_API_URL`. It generates static HTML, JavaScript, and CSS. The final image uses Nginx to serve those files.
2. **Backend image:** the `care` build receives `ADDITIONAL_PLUGS`, downloads the selected plug packages, and installs them into the image. The same image runs the API, worker, and Beat processes.

Changing a frontend build variable requires rebuilding the frontend image. Changing the plug list requires rebuilding the backend image. Database, S3, and cache/broker settings used by the backend remain runtime configuration.

## Why the backend processes share one image

The API, worker, and Beat scheduler run the same CARE code. Compose changes only the process entry point:

- API: `start.sh`
- Worker: `celery_worker.sh`
- Scheduler and startup initialization: `celery_beat.sh`

The current CARE `celery_beat.sh` waits for PostgreSQL and Redis, runs migrations, compiles messages, synchronizes permissions and value sets, marks itself healthy, and then starts Celery Beat. There is no separate initialization container.

This is the central deployment concept: one tested application artifact can run different roles.

## Prerequisites

- Git
- Docker Desktop or Docker Engine
- Docker Compose v2 (`docker compose version`)
- At least 8 GB of free memory recommended
- Free ports: `4000`, `9000`, `9001`, and `9100`

## 1. Clone this repository

```bash
git clone https://github.com/jesbinjoseph/care-session.git
cd care-session
```

## 2. Clone CARE source repositories

```bash
git clone --depth 1 --branch develop https://github.com/ohcnetwork/care.git
git clone --depth 1 --branch develop https://github.com/ohcnetwork/care_fe.git
```

The source directories are intentionally excluded from this repository. Participants can see exactly which upstream source is being built.

## 3. Create local configuration

```bash
test -f .env || cp .env.example .env
cp frontend.env.production.local care_fe/.env.production.local
```

The frontend setting points the participant's browser to `http://localhost:9000`. Container-to-container dependencies use Compose service names such as `db`, `redis`, and `silo`.

## 4. Review the resolved stack

```bash
docker compose config --services
docker compose config --quiet
```

Expected services:

```text
db
redis
silo
backend
worker
beat
frontend
```

## 5. Build and start CARE

```bash
docker compose up -d --build --wait
```

The first run takes longer because Docker downloads base images and builds both CARE repositories. Beat completes migrations and synchronization before becoming healthy; the backend and worker wait for that health signal.

## 6. Verify the deployment

```bash
docker compose ps -a
curl -f http://localhost:9000/ping/
curl -I http://localhost:4000/
docker compose exec backend python manage.py check
```

Expected endpoints:

| Endpoint | URL |
|---|---|
| CARE frontend | http://localhost:4000 |
| Backend health | http://localhost:9000/ping/ |
| API documentation | http://localhost:9000/swagger/ |
| Silo object-storage console | http://localhost:9001 |

## 7. Load synthetic workshop data

```bash
docker compose exec backend python -m pip install --target /tmp/care-fixtures-deps 'Faker==38.2.0'
docker compose exec -e PYTHONPATH=/tmp/care-fixtures-deps \
  -e 'DJANGO_ALLOWED_HOSTS=["localhost","127.0.0.1","backend","testserver"]' \
  backend python manage.py load_fixtures
```

The upstream production image omits the development-only Faker dependency, and the fixture runner uses Django's `testserver` host. These commands supply both only for the local fixture run; repeat the temporary install after recreating the backend container. Use only fixture accounts and synthetic records. Never enter production credentials or patient data into this environment.

## 8. Operate and troubleshoot the instance

Record outcomes in the [operator worksheet](docs/operator-worksheet.md). Confirm that a synthetic record can be saved and reopened, a test file uploaded and retrieved, and a *triggered* background job completed (otherwise mark it unknown). A passing health endpoint does not prove these actions.

For a daily check, inspect service health and the API/frontend response, then investigate the first failing dependency before downstream components:

```bash
docker compose logs -f frontend backend
docker compose logs -f worker beat
docker compose logs -f db redis silo
```

Practice a safe stop/restart and reopen the same synthetic record and file. Plan a separate isolated backup/restore test before making recovery claims. For a real instance, assign owners for alerts, release, migrations, storage, secrets, backup, restore and escalation.

## Backend plugs

CARE plugs are Django extensions. They are installed into the shared backend image during the Docker build and can add models, API routes, and Celery tasks. They are not a separate container.

Core CARE uses:

```env
ADDITIONAL_PLUGS=[]
```

A plug configuration follows this structure:

```env
ADDITIONAL_PLUGS=[{"name":"my_plugin","package_name":"git+https://github.com/example/my_plugin.git","version":"@v1.0.0","configs":{}}]
```

Use the exact package and configuration documented by the selected plug. Pin a release or commit; do not use a floating branch. Rebuild after changing plugs:

```bash
docker compose build --no-cache backend worker beat
docker compose up -d --wait
```

Do not place plug secrets inside `ADDITIONAL_PLUGS`. Supply required values separately through the local environment.

## Stop and restart

Stop containers while preserving local data:

```bash
docker compose down
```

Start again:

```bash
docker compose up -d --wait
```

Delete all local data and start from an empty environment:

```bash
docker compose down -v
```

`down -v` permanently removes the workshop database, Redis data, and object-storage volume.

## Troubleshooting

### Docker daemon unavailable

Start Docker Desktop or the Docker daemon, then verify:

```bash
docker info
docker compose version
```

### A service is unhealthy

```bash
docker compose ps -a
docker compose logs --tail=200 <service>
```

Check dependencies in this order: `db`, `redis`, `silo`, `beat`, `backend`, `worker`, and `frontend`.

### Rebuild after source or plug changes

```bash
docker compose build --no-cache
docker compose up -d --force-recreate --wait
```

### Reset the workshop

```bash
docker compose down -v
docker compose up -d --build --wait
```

## Production boundary

This repository is a learning environment, not a production deployment template. Production additionally requires:

- Managed secrets and controlled rotation
- TLS, DNS, load balancing, Gateway, and routing policy
- Private networking and workload identities
- Durable managed PostgreSQL and object storage
- Multiple replicas, resource policies, and disruption controls
- Centralized logs, metrics, dashboards, and alerts
- Tested backup, restore, rollback, and recovery procedures
- Pinned and approved release artifacts

## Presentation

The Session 3 deck is published with GitHub Pages at <https://jesbinjoseph.github.io/care-session/> (source: [docs/index.html](docs/index.html)). Use `#N` to jump to a slide. Pages serves the `docs/` folder on `main`, so pushing is the only deploy step.

## Additional material

- [Operator worksheet](docs/operator-worksheet.md)
- [Session 3 presentation](https://jesbinjoseph.github.io/care-session/)
- [Architecture explanation](docs/architecture.md)
- [CARE on a simple Kubernetes cluster](docs/kubernetes-local-architecture.md)
- [Recommended managed-services GCP architecture](docs/gcp-managed-architecture.md)
- [From local Compose to GCP](docs/local-to-gcp.md)
- [Facilitator guide](docs/facilitator-guide.md)
- [Deployment readiness checklist](docs/readiness-checklist.md)
- [Interactive architecture diagram](docs/architecture.html)
